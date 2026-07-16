"""
tests/test_benchmark.py — Tests for the spectrogram benchmark harness
(tools/benchmark_spectrogram.py).

Uses short synthetic durations so the suite stays fast; the harness itself
is designed to be run standalone with `--duration 30` for the real litmus
check (see plan.md).
"""

import numpy as np
import pytest

from tools.benchmark_spectrogram import (
    BenchmarkResult,
    generate_synthetic_voice,
    run_benchmark,
)


class TestSyntheticVoice:
    def test_generates_requested_duration(self):
        audio = generate_synthetic_voice(2.0, sample_rate=44100)
        assert len(audio) == 2.0 * 44100

    def test_output_is_bounded_float32(self):
        audio = generate_synthetic_voice(1.0)
        assert audio.dtype == np.float32
        assert np.max(np.abs(audio)) <= 1.0

    def test_not_silent(self):
        """The synthetic signal should have real signal energy, not near-zero
        RMS — otherwise pitch/formant estimators would just see silence."""
        audio = generate_synthetic_voice(1.0)
        rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))
        assert rms > 0.05


class TestRunBenchmarkAnalysisOnly:
    """render=False skips Qt entirely — fastest, most deterministic path."""

    def test_produces_expected_column_count(self):
        # duration=2s, n_fft=2048, hop=1024, block_size=1024 -> after the
        # first full window, one new column per block.
        result = run_benchmark(n_fft=2048, duration_s=2.0, block_size=1024, render=False)
        expected_blocks = int(2.0 * 44100) // 1024
        # First N_FFT/hop blocks fill the initial window; after that it's
        # one column per block fed.
        assert result.n_columns > 0
        assert result.n_columns <= expected_blocks

    def test_result_fields_are_sane(self):
        result = run_benchmark(duration_s=2.0, render=False)
        assert isinstance(result, BenchmarkResult)
        assert result.wall_seconds > 0
        assert result.fps > 0
        assert result.mean_latency_ms >= 0
        assert result.p95_latency_ms >= result.mean_latency_ms - 1e-6
        assert result.max_latency_ms >= result.p95_latency_ms - 1e-6

    def test_meets_litmus_thresholds(self):
        passing = BenchmarkResult(
            n_columns=100, wall_seconds=1.0, fps=100.0,
            mean_latency_ms=10.0, p95_latency_ms=50.0, max_latency_ms=60.0,
        )
        assert passing.meets_litmus()

        too_slow = BenchmarkResult(
            n_columns=100, wall_seconds=10.0, fps=10.0,
            mean_latency_ms=10.0, p95_latency_ms=50.0, max_latency_ms=60.0,
        )
        assert not too_slow.meets_litmus()

        too_laggy = BenchmarkResult(
            n_columns=100, wall_seconds=1.0, fps=100.0,
            mean_latency_ms=10.0, p95_latency_ms=200.0, max_latency_ms=300.0,
        )
        assert not too_laggy.meets_litmus()

    def test_report_string_contains_key_metrics(self):
        result = run_benchmark(duration_s=1.0, render=False)
        text = result.report()
        assert "fps=" in text
        assert "latency" in text


class TestRunBenchmarkWithRender:
    """render=True exercises the real SpectrogramWidget + Qt event loop."""

    def test_runs_without_error_at_given_bin_count(self):
        result = run_benchmark(n_fft=2048, n_log_bins=2048, duration_s=1.0, render=True)
        assert result.n_columns > 0
        assert result.fps > 0

    def test_bin_count_is_configurable(self):
        """Different --bins values should both run cleanly (this is the
        'measure FPS + latency at a given bin count' requirement)."""
        for bins in (512, 2048):
            result = run_benchmark(n_fft=2048, n_log_bins=bins, duration_s=1.0, render=True)
            assert result.n_columns > 0


@pytest.mark.parametrize("n_fft", [1024, 2048])
def test_reproducible_column_count_across_runs(n_fft):
    """Same config, run twice, should produce the same number of columns
    (deterministic synthetic input + deterministic hop math)."""
    a = run_benchmark(n_fft=n_fft, duration_s=1.5, render=False)
    b = run_benchmark(n_fft=n_fft, duration_s=1.5, render=False)
    assert a.n_columns == b.n_columns


def test_hop_is_configurable_and_sets_column_count():
    """The harness must benchmark the app's real config (n_fft 4096, hop
    1024) — hop halves/doubles the column count for the same audio."""
    dense = run_benchmark(n_fft=4096, hop=1024, duration_s=2.0, render=False)
    sparse = run_benchmark(n_fft=4096, hop=2048, duration_s=2.0, render=False)
    assert dense.n_columns > 1.5 * sparse.n_columns


class TestResolutionMetric:
    """The 'eye chart': the smallest two-tone gap (in cents) that still
    renders as two distinct ridges in the display column. This is the
    machine-measurable definition of spectrogram resolution, immune to
    display settings like dB floor/ceiling."""

    def test_high_frequency_resolves_a_quarter_tone(self):
        """At A7 (3520 Hz) a 4096 FFT has ~10.8 Hz bins while a quarter
        tone is ~102 Hz — easily separable."""
        from tools.benchmark_spectrogram import min_separable_cents
        result = min_separable_cents(3520.0, n_fft=4096)
        assert result is not None and result <= 50

    def test_low_frequencies_are_coarser_than_high(self):
        """Physics: fixed ~10.8 Hz bins are a bigger musical interval at
        the bottom of the range than at the top."""
        from tools.benchmark_spectrogram import min_separable_cents
        low = min_separable_cents(110.0, n_fft=4096)
        high = min_separable_cents(3520.0, n_fft=4096)
        assert high is not None
        assert low is None or low >= high

    def test_bigger_fft_resolves_finer_or_equal(self):
        """Doubling the FFT window must never make resolution worse."""
        from tools.benchmark_spectrogram import min_separable_cents
        at_2048 = min_separable_cents(440.0, n_fft=2048)
        at_4096 = min_separable_cents(440.0, n_fft=4096)
        inf = float("inf")
        assert (at_4096 if at_4096 is not None else inf) <= \
               (at_2048 if at_2048 is not None else inf)

    def test_measure_resolution_returns_all_centers(self):
        from tools.benchmark_spectrogram import measure_resolution
        centers = (262.0, 880.0)
        table = measure_resolution(n_fft=4096, centers=centers)
        assert set(table.keys()) == set(centers)
