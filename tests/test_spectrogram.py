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


class TestMatplotlibColormap:
    """Verify matplotlib colormap integration."""

    def test_build_colormap_returns_pg_colormap(self, qt_app):
        """_build_colormap should return a pyqtgraph ColorMap."""
        import pyqtgraph as pg
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("inferno")
        assert isinstance(cmap, pg.ColorMap)

    def test_build_colormap_has_256_stops(self, qt_app):
        """Colormap should be sampled at 256 points."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("inferno")
        # pg.ColorMap stores positions; 256 sample points
        assert len(cmap.pos) == 256

    def test_build_colormap_invalid_falls_back_to_inferno(self, qt_app):
        """Invalid colormap name should fall back to inferno without error."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("nonexistent_colormap_xyz")
        assert cmap is not None

    def test_apply_settings_with_colormap_name(self, qt_app):
        """apply_settings should accept colormap_name and not raise."""
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(colormap_name="viridis"))
        # Should not raise


class TestHopParameter:
    """The hop is decoupled from n_fft (spec: hold hop at 1024 while n_fft
    grows to 4096, preserving the ~43 col/s scroll rate)."""

    def test_default_hop_is_half_n_fft(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        assert w.hop == 1024

    def test_explicit_hop_sets_scroll_rate(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=4096, hop=1024, display_seconds=8.0)
        # 44100 / 1024 ≈ 43.07 columns/sec → 344 columns at 8 s
        assert w._n_time_cols == int(8.0 * (44100 / 1024))

    def test_hop_used_after_apply_settings_resize(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget(n_fft=4096, hop=1024, display_seconds=8.0)
        w.apply_settings(AppSettings(display_seconds=4.0))
        assert w._n_time_cols == int(4.0 * (44100 / 1024))


class TestResamplerWiring:
    """add_column must use the precomputed matrix, with no blur pass."""

    def test_no_blur_attribute(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert not hasattr(w, '_blur_sigma')

    def test_resample_matrix_built(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        assert w._resample_matrix.shape == (w._n_freq_bins, 2048 // 2 + 1)

    def test_flat_spectrum_stays_flat_in_buffer(self, qt_app):
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        w.add_column(np.full(1025, -40.0, dtype=np.float32))
        np.testing.assert_allclose(w._buffer[-1], -40.0, atol=1e-3)


class TestMultiresRendering:
    """Widget stitches per-band spectra into one display column."""

    def test_band_matrices_built_when_bands_given(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from audio.analysis import MULTIRES_BANDS
        w = SpectrogramWidget(bands=MULTIRES_BANDS)
        assert len(w._band_matrices) == len(MULTIRES_BANDS)
        for (_, _, n_fft), W in zip(MULTIRES_BANDS, w._band_matrices):
            assert W.shape == (w._n_freq_bins, n_fft // 2 + 1)

    def test_every_display_bin_covered_exactly_once(self, qt_app):
        """Summed across bands, each display row's weights must total 1 —
        no gaps and no double-painting at band boundaries."""
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        from audio.analysis import MULTIRES_BANDS
        w = SpectrogramWidget(bands=MULTIRES_BANDS)
        total = sum(W.sum(axis=1) for W in w._band_matrices)
        np.testing.assert_allclose(total, 1.0, atol=1e-4)

    def test_add_column_accepts_band_spectra_list(self, qt_app):
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        from audio.analysis import MULTIRES_BANDS
        w = SpectrogramWidget(bands=MULTIRES_BANDS)
        spectra = [np.full(n_fft // 2 + 1, -40.0, dtype=np.float32)
                   for (_, _, n_fft) in MULTIRES_BANDS]
        w.add_column(spectra)
        np.testing.assert_allclose(w._buffer[-1], -40.0, atol=1e-3)

    def test_single_spectrum_path_still_works(self, qt_app):
        """bands=None keeps the original one-FFT behavior."""
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        w.add_column(np.full(1025, -40.0, dtype=np.float32))
        np.testing.assert_allclose(w._buffer[-1], -40.0, atol=1e-3)
