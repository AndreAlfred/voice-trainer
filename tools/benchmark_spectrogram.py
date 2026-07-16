"""
tools/benchmark_spectrogram.py — Spectrogram pipeline benchmark harness.

Feeds synthetic audio through the same analysis + render pipeline as
ui/app.py's MainWindow._process_audio, and reports FPS and glass-to-glass
latency. This is the self-verifiable litmus for the Goal 1a perf loop
(plan.md): "sustain >= 30 FPS and <= 120 ms glass-to-glass latency at 2048
log-frequency bins over a 30 s synthetic run."

Usage:
    python -m tools.benchmark_spectrogram
    python -m tools.benchmark_spectrogram --bins 2048 --n-fft 4096 --duration 30
    python -m tools.benchmark_spectrogram --no-render   # analysis only, no Qt paint cost
"""

import argparse
import os
import time
from dataclasses import dataclass

import numpy as np

# Must be set before importing PySide6/pyqtgraph: run headless (no display
# needed, works in CI and over SSH).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from audio.analysis import (  # noqa: E402
    compute_spectrogram_column,
    estimate_formants,
    estimate_pitch,
)

SAMPLE_RATE = 44100


def generate_synthetic_voice(duration_s: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a sung-voice-like test signal.

    A vibrato glide (A3 -> A4) with a harmonic series shaped by two fixed
    resonances (~700 Hz, ~1220 Hz), so the benchmark exercises the pitch
    and formant estimators the way a real voice would rather than a bare
    sine tone (which formant estimation would trivially reject as silence-
    like or pass through unrealistically).
    """
    n_samples = int(duration_s * sample_rate)
    t = np.arange(n_samples) / sample_rate

    f0_base = 220.0 * (2.0 ** (t / duration_s))          # A3 -> A4 glide
    vibrato = 1.0 + 0.02 * np.sin(2 * np.pi * 5.5 * t)    # 5.5 Hz, ~35 cent depth
    f0 = f0_base * vibrato

    phase = 2 * np.pi * np.cumsum(f0) / sample_rate

    formants = [(700.0, 1.0), (1220.0, 0.5)]  # approximate F1/F2 for "ah"
    signal = np.zeros(n_samples, dtype=np.float64)
    for k in range(1, 12):
        harmonic_freq = f0 * k
        weight = sum(np.exp(-0.5 * ((harmonic_freq - fc) / 300.0) ** 2) * a for fc, a in formants)
        amp = 0.05 + 0.95 * weight
        signal += (amp / k) * np.sin(phase * k)

    signal = signal / np.max(np.abs(signal)) * 0.8
    return signal.astype(np.float32)


@dataclass
class BenchmarkResult:
    n_columns: int
    wall_seconds: float
    fps: float
    mean_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float

    def report(self) -> str:
        return (
            f"columns={self.n_columns}  wall={self.wall_seconds:.2f}s  "
            f"fps={self.fps:.1f}  "
            f"latency: mean={self.mean_latency_ms:.1f}ms "
            f"p95={self.p95_latency_ms:.1f}ms max={self.max_latency_ms:.1f}ms"
        )

    def meets_litmus(self, min_fps: float = 30.0, max_latency_ms: float = 120.0) -> bool:
        return self.fps >= min_fps and self.p95_latency_ms <= max_latency_ms


def run_benchmark(
    n_fft: int = 2048,
    n_log_bins: int = 2048,
    duration_s: float = 30.0,
    block_size: int = 1024,
    hop: int | None = None,
    render: bool = True,
    multires: bool = False,
) -> BenchmarkResult:
    """Feed `duration_s` seconds of synthetic audio through the analysis
    (+ optional render) pipeline flat-out, and measure how far real
    processing drifts behind the audio's own clock.

    Each column of output "represents" a moment in audio time (the
    timestamp of the newest sample in its analysis window). Glass-to-glass
    latency for that column is (wall-clock time it finished) minus (that
    audio timestamp) — exactly the real-time backlog a live session would
    accumulate if the pipeline can't keep up. FPS is columns produced per
    wall-clock second. Together these are the litmus from plan.md.

    With multires=True the loop mirrors ui/app.py exactly: a rolling
    history sized for the longest band window, one multi-band column per
    hop, pitch/formants from the recent 4096-sample tail.
    """
    from audio.analysis import (
        MULTIRES_BANDS, MULTIRES_MAX_WINDOW, compute_multires_column,
    )

    if hop is None:
        hop = 1024 if multires else n_fft // 2

    widget = None
    app = None
    if render:
        app = QApplication.instance() or QApplication([])
        from ui.spectrogram import SpectrogramWidget
        widget = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            n_log_bins=n_log_bins,
            hop=hop,
            bands=MULTIRES_BANDS if multires else None,
            display_seconds=8.0,
        )

    audio = generate_synthetic_voice(duration_s, SAMPLE_RATE)

    latencies_ms = []
    n_columns = 0

    buffer = np.zeros(0, dtype=np.float32)
    buffer_start = 0  # index into `audio` of buffer[0]
    pos = 0
    history = np.zeros(MULTIRES_MAX_WINDOW, dtype=np.float32)
    min_ready = hop if multires else n_fft

    start = time.perf_counter()
    while pos + block_size <= len(audio):
        buffer = np.concatenate([buffer, audio[pos:pos + block_size]])
        pos += block_size
        buffer_start = pos - len(buffer)

        while len(buffer) >= min_ready:
            if multires:
                history = np.concatenate([history[hop:], buffer[:hop]])
                spectrum = compute_multires_column(history, SAMPLE_RATE)
                recent = history[-4096:]
                newest_sample = buffer_start + hop - 1
            else:
                window = buffer[:n_fft]
                spectrum = compute_spectrogram_column(window, SAMPLE_RATE, n_fft)
                recent = window
                newest_sample = buffer_start + n_fft - 1

            _pitch_hz = estimate_pitch(recent, SAMPLE_RATE)
            f1_hz, f2_hz = estimate_formants(recent, SAMPLE_RATE)

            if widget is not None:
                widget.add_column(spectrum)
                widget.add_formants(f1_hz, f2_hz)
                app.processEvents()

            audio_time_s = newest_sample / SAMPLE_RATE
            wall_elapsed_s = time.perf_counter() - start
            latencies_ms.append((wall_elapsed_s - audio_time_s) * 1000.0)

            buffer = buffer[hop:]
            buffer_start += hop
            n_columns += 1

    wall_seconds = time.perf_counter() - start
    latencies = np.clip(np.array(latencies_ms), 0.0, None)

    return BenchmarkResult(
        n_columns=n_columns,
        wall_seconds=wall_seconds,
        fps=n_columns / wall_seconds if wall_seconds > 0 else 0.0,
        mean_latency_ms=float(np.mean(latencies)) if len(latencies) else 0.0,
        p95_latency_ms=float(np.percentile(latencies, 95)) if len(latencies) else 0.0,
        max_latency_ms=float(np.max(latencies)) if len(latencies) else 0.0,
    )


# ---------------------------------------------------------------------------
# Resolution metric — the "eye chart"
# ---------------------------------------------------------------------------

# Candidate two-tone gaps, in cents (100 cents = 1 semitone), coarsest last.
CENTS_CANDIDATES = (25, 50, 100, 200, 300, 400, 600, 800, 1200)

# Musically spread test centers: G2 (low bass) up to A7 (top of display).
DEFAULT_CENTERS = (98.0, 131.0, 196.0, 262.0, 440.0, 880.0, 1760.0, 3520.0)


def _region_max(col: np.ndarray, display_freqs: np.ndarray,
                f_lo: float, f_hi: float) -> float:
    """Max of the display column between two frequencies. Falls back to the
    single nearest bin when the region is narrower than one display bin."""
    lo = int(np.searchsorted(display_freqs, f_lo))
    hi = int(np.searchsorted(display_freqs, f_hi))
    if hi <= lo:
        idx = min(max(lo, 0), len(col) - 1)
        return float(col[idx])
    return float(np.max(col[lo:hi]))


def min_separable_cents(
    center_hz: float,
    n_fft: int,
    sample_rate: int = SAMPLE_RATE,
    n_log_bins: int = 1024,
    candidates: tuple = CENTS_CANDIDATES,
    min_dip_db: float = 6.0,
    bands: tuple | None = None,
) -> float | None:
    """Smallest two-tone gap (cents) that renders as two distinct ridges.

    The optometrist's-chart definition of resolution: synthesize two equal
    sines centered geometrically on `center_hz`, push them through the real
    analysis (FFT → dB) and display resampling (W), and check whether the
    rendered column shows two peaks with a valley at least `min_dip_db`
    below the weaker peak. Try gaps from fine to coarse; return the first
    that separates, or None if even the coarsest candidate fails (or falls
    outside the 80–8000 Hz display range).

    Measures the data itself, so the result is independent of display
    contrast settings (dB floor/ceiling).
    """
    from ui.spectrogram import (
        FREQ_MIN_HZ, FREQ_MAX_HZ, build_log_resample_matrix,
    )

    display_freqs = np.logspace(
        np.log10(FREQ_MIN_HZ), np.log10(FREQ_MAX_HZ), n_log_bins,
        dtype=np.float32,
    )
    if bands is not None:
        from audio.analysis import compute_multires_column
        from ui.spectrogram import build_band_resample_matrices
        band_ws = build_band_resample_matrices(bands, sample_rate, display_freqs)
        window = max(nf for (_, _, nf) in bands)
    else:
        fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate).astype(np.float32)
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        window = n_fft

    t = np.arange(window) / sample_rate
    for cents in candidates:
        f_a = center_hz * 2.0 ** (-cents / 2400.0)
        f_b = center_hz * 2.0 ** (+cents / 2400.0)
        if f_a < FREQ_MIN_HZ * 1.05 or f_b > FREQ_MAX_HZ * 0.95:
            continue  # tones would leave the display range

        tone = (0.5 * np.sin(2 * np.pi * f_a * t)
                + 0.5 * np.sin(2 * np.pi * f_b * t)).astype(np.float32)
        if bands is not None:
            spectra = compute_multires_column(tone, sample_rate, bands)
            col = band_ws[0] @ spectra[0]
            for Wb, spec in zip(band_ws[1:], spectra[1:]):
                col += Wb @ spec
        else:
            col = W @ compute_spectrogram_column(tone, sample_rate, n_fft)

        # Peak regions: ± quarter-gap around each tone.
        # Valley region: the middle quarter-gap between them.
        q = cents / 4.0
        peak_a = _region_max(col, display_freqs,
                             f_a * 2.0 ** (-q / 1200.0),
                             f_a * 2.0 ** (+q / 1200.0))
        peak_b = _region_max(col, display_freqs,
                             f_b * 2.0 ** (-q / 1200.0),
                             f_b * 2.0 ** (+q / 1200.0))
        valley = _region_max(col, display_freqs,
                             center_hz * 2.0 ** (-q / 2400.0),
                             center_hz * 2.0 ** (+q / 2400.0))

        if valley < min(peak_a, peak_b) - min_dip_db:
            return float(cents)
    return None


def measure_resolution(
    n_fft: int,
    sample_rate: int = SAMPLE_RATE,
    n_log_bins: int = 1024,
    centers: tuple = DEFAULT_CENTERS,
    bands: tuple | None = None,
) -> dict:
    """min_separable_cents at each test center. Keys = center Hz."""
    return {
        c: min_separable_cents(c, n_fft, sample_rate, n_log_bins, bands=bands)
        for c in centers
    }


def print_resolution_table(n_fft: int, n_log_bins: int = 1024,
                           bands: tuple | None = None) -> None:
    from audio.analysis import hz_to_note_name
    table = measure_resolution(n_fft, n_log_bins=n_log_bins, bands=bands)
    mode = "multires bands" if bands is not None else f"n_fft={n_fft}"
    print(f"resolution eye chart @ {mode}, bins={n_log_bins}")
    print(f"{'center':>8}  {'note':>5}  min separable gap")
    for hz, cents in table.items():
        note, octave = hz_to_note_name(hz)
        label = f"{note}{octave}" if note else "—"
        if cents is None:
            verdict = "NOT SEPARABLE at any tested gap"
        elif cents <= 100:
            verdict = f"{cents:.0f} cents  (≤ 1 semitone ✓)"
        else:
            verdict = f"{cents:.0f} cents  ({cents / 100.0:.1f} semitones)"
        print(f"{hz:>7.0f}Hz  {label:>5}  {verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bins", type=int, default=2048, help="log-frequency display bins")
    parser.add_argument("--n-fft", type=int, default=2048, help="FFT size")
    parser.add_argument("--duration", type=float, default=30.0, help="synthetic audio seconds")
    parser.add_argument("--block-size", type=int, default=1024, help="capture block size")
    parser.add_argument("--hop", type=int, default=None,
                        help="analysis hop in samples (default: n_fft // 2)")
    parser.add_argument("--no-render", action="store_true", help="skip Qt widget rendering (analysis only)")
    parser.add_argument("--resolution", action="store_true",
                        help="print the resolution eye chart instead of the FPS/latency run")
    parser.add_argument("--multires", action="store_true",
                        help="use the app's multi-resolution bands instead of a single n_fft")
    args = parser.parse_args()

    if args.resolution:
        from audio.analysis import MULTIRES_BANDS
        print_resolution_table(
            args.n_fft, n_log_bins=args.bins,
            bands=MULTIRES_BANDS if args.multires else None)
        return

    result = run_benchmark(
        n_fft=args.n_fft,
        n_log_bins=args.bins,
        duration_s=args.duration,
        block_size=args.block_size,
        hop=args.hop,
        render=not args.no_render,
        multires=args.multires,
    )
    print(result.report())
    print("litmus (>=30fps, p95<=120ms):", "PASS" if result.meets_litmus() else "FAIL")


if __name__ == "__main__":
    main()
