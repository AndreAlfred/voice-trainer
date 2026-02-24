"""
tests/test_spectrogram.py — Tests for SpectrogramWidget frequency scale.

These tests verify that the log-spaced frequency grid is constructed correctly
and that the widget still accepts new columns without error.
"""

import sys
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    """Single QApplication instance shared across all tests in this file."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestLogFrequencyScale:
    """Verify the log-spaced display frequency grid in SpectrogramWidget."""

    def test_display_freqs_starts_near_freq_min(self, qt_app):
        """First display bin should be at or near FREQ_MIN_HZ (80 Hz)."""
        from ui.spectrogram import SpectrogramWidget, FREQ_MIN_HZ
        w = SpectrogramWidget()
        assert abs(w._display_freqs[0] - FREQ_MIN_HZ) < 1.0, (
            f"Expected _display_freqs[0] ≈ {FREQ_MIN_HZ}, got {w._display_freqs[0]}"
        )

    def test_display_freqs_ends_near_freq_max(self, qt_app):
        """Last display bin should be at or near FREQ_MAX_HZ (8000 Hz)."""
        from ui.spectrogram import SpectrogramWidget, FREQ_MAX_HZ
        w = SpectrogramWidget()
        assert abs(w._display_freqs[-1] - FREQ_MAX_HZ) < 1.0, (
            f"Expected _display_freqs[-1] ≈ {FREQ_MAX_HZ}, got {w._display_freqs[-1]}"
        )

    def test_display_freqs_is_log_spaced(self, qt_app):
        """Consecutive frequency ratios should be nearly constant (log spacing)."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        ratios = w._display_freqs[1:] / w._display_freqs[:-1]
        # Standard deviation of ratios should be tiny if truly log-spaced
        assert np.std(ratios) < 0.001, (
            f"Frequency ratios not constant — std={np.std(ratios):.6f}. "
            "Array may still be linear."
        )

    def test_display_freqs_length_matches_n_log_bins(self, qt_app):
        """Display grid should have exactly N_LOG_BINS bins."""
        from ui.spectrogram import SpectrogramWidget, N_LOG_BINS
        w = SpectrogramWidget()
        assert len(w._display_freqs) == N_LOG_BINS, (
            f"Expected {N_LOG_BINS} display bins, got {len(w._display_freqs)}"
        )

    def test_display_freqs_is_monotonically_increasing(self, qt_app):
        """All frequencies should be strictly increasing."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert np.all(np.diff(w._display_freqs) > 0), (
            "Frequency array is not monotonically increasing."
        )

    def test_add_column_accepts_full_spectrum(self, qt_app):
        """add_column should not raise when given a valid spectrum array."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        # n_fft=2048 → spectrum shape is (1025,)
        spectrum = np.full(1025, -40.0, dtype=np.float32)
        w.add_column(spectrum)  # must not raise

    def test_buffer_shape_matches_display_bins(self, qt_app):
        """Internal buffer second dimension should equal number of display bins."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert w._buffer.shape[1] == w._n_freq_bins, (
            f"Buffer shape {w._buffer.shape} doesn't match n_freq_bins={w._n_freq_bins}"
        )


class TestInterpolation:
    """Verify linear interpolation replaces nearest-neighbor mapping."""

    def test_n_log_bins_is_1024(self, qt_app):
        """Display grid should now use 1024 bins."""
        from ui.spectrogram import N_LOG_BINS
        assert N_LOG_BINS == 1024

    def test_fft_freqs_stored(self, qt_app):
        """Widget should store _fft_freqs array for interpolation."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert hasattr(w, '_fft_freqs')
        assert len(w._fft_freqs) == w.n_fft // 2 + 1

    def test_add_column_produces_smooth_gradient(self, qt_app):
        """A linearly ramping spectrum should produce a smooth (non-staircase)
        display column after interpolation."""
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        # Create a spectrum that ramps linearly from -60 to 0 across all bins
        spectrum = np.linspace(-60.0, 0.0, 1025, dtype=np.float32)
        w.add_column(spectrum)
        col = w._buffer[-1]
        # With interpolation, consecutive values should differ smoothly.
        # Count unique values — nearest-neighbor would have many duplicates
        # (dozens of display bins mapping to the same FFT bin), interpolation
        # should produce mostly unique values.
        unique_ratio = len(np.unique(np.round(col, 4))) / len(col)
        assert unique_ratio > 0.8, (
            f"Only {unique_ratio:.0%} unique values — still looks like nearest-neighbor"
        )


class TestApplySettings:

    def test_apply_settings_does_not_raise(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        SpectrogramWidget().apply_settings(AppSettings())

    def test_apply_settings_hides_singers_formant(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(singers_formant_visible=False))
        assert not w._singers_formant_region.isVisible()

    def test_apply_settings_resizes_buffer(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget(display_seconds=8.0)
        original = w._n_time_cols
        w.apply_settings(AppSettings(display_seconds=4.0))
        assert w._n_time_cols < original
        assert w._buffer.shape[0] == w._n_time_cols
        assert len(w._f1_bins) == w._n_time_cols

    def test_apply_settings_restores_singers_formant(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(singers_formant_visible=False))
        w.apply_settings(AppSettings(singers_formant_visible=True))
        assert w._singers_formant_region.isVisible()
