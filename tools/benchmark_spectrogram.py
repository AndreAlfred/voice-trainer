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
    """
    if hop is None:
        hop = n_fft // 2

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
            display_seconds=8.0,
        )

    audio = generate_synthetic_voice(duration_s, SAMPLE_RATE)

    latencies_ms = []
    n_columns = 0

    buffer = np.zeros(0, dtype=np.float32)
    buffer_start = 0  # index into `audio` of buffer[0]
    pos = 0

    start = time.perf_counter()
    while pos + block_size <= len(audio):
        buffer = np.concatenate([buffer, audio[pos:pos + block_size]])
        pos += block_size
        buffer_start = pos - len(buffer)

        while len(buffer) >= n_fft:
            window = buffer[:n_fft]
            spectrum_db = compute_spectrogram_column(window, SAMPLE_RATE, n_fft)
            _pitch_hz = estimate_pitch(window, SAMPLE_RATE)
            f1_hz, f2_hz = estimate_formants(window, SAMPLE_RATE)

            if widget is not None:
                widget.add_column(spectrum_db)
                widget.add_formants(f1_hz, f2_hz)
                app.processEvents()

            last_sample_index = buffer_start + n_fft - 1
            audio_time_s = last_sample_index / SAMPLE_RATE
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bins", type=int, default=2048, help="log-frequency display bins")
    parser.add_argument("--n-fft", type=int, default=2048, help="FFT size")
    parser.add_argument("--duration", type=float, default=30.0, help="synthetic audio seconds")
    parser.add_argument("--block-size", type=int, default=1024, help="capture block size")
    parser.add_argument("--hop", type=int, default=None,
                        help="analysis hop in samples (default: n_fft // 2)")
    parser.add_argument("--no-render", action="store_true", help="skip Qt widget rendering (analysis only)")
    args = parser.parse_args()

    result = run_benchmark(
        n_fft=args.n_fft,
        n_log_bins=args.bins,
        duration_s=args.duration,
        block_size=args.block_size,
        hop=args.hop,
        render=not args.no_render,
    )
    print(result.report())
    print("litmus (>=30fps, p95<=120ms):", "PASS" if result.meets_litmus() else "FAIL")


if __name__ == "__main__":
    main()
