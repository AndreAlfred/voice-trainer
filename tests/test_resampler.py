"""
tests/test_resampler.py — Tests for build_log_resample_matrix.

The matrix W maps a linear-frequency FFT spectrum onto the log-spaced
display grid: overlap-averaging where display bins are wide (high
frequencies), linear interpolation where they are narrow (low
frequencies). Replaces np.interp + Gaussian blur.
"""

import numpy as np

from ui.spectrogram import build_log_resample_matrix


def make_grids(n_fft=4096, sample_rate=44100, n_display=1024,
               fmin=80.0, fmax=8000.0):
    fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate).astype(np.float32)
    display_freqs = np.logspace(
        np.log10(fmin), np.log10(fmax), n_display, dtype=np.float32)
    return fft_freqs, display_freqs


class TestMatrixShapeAndWeights:
    def test_shape(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        assert W.shape == (len(display_freqs), len(fft_freqs))

    def test_rows_sum_to_one(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        np.testing.assert_allclose(W.sum(axis=1), 1.0, atol=1e-4)

    def test_weights_nonnegative(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        assert (W >= 0).all()


class TestMapping:
    def test_flat_spectrum_maps_flat(self):
        """A constant-level input must produce a constant-level display
        column (rows sum to 1 makes this a weighted average)."""
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        flat = np.full(len(fft_freqs), -40.0, dtype=np.float32)
        out = W @ flat
        np.testing.assert_allclose(out, -40.0, atol=1e-3)

    def test_mapping_is_monotonic_in_frequency(self):
        """The weighted-mean source frequency of each display row must be
        strictly increasing — no frequency folding."""
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        centers = W @ fft_freqs.astype(np.float64)
        assert np.all(np.diff(centers) > 0)

    def test_row_center_tracks_display_freq(self):
        """Each row's weighted-mean source frequency should be close to
        that display bin's nominal frequency (within one FFT bin width)."""
        fft_freqs, display_freqs = make_grids()
        df = float(fft_freqs[1] - fft_freqs[0])
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        centers = W @ fft_freqs.astype(np.float64)
        assert np.max(np.abs(centers - display_freqs)) < df


class TestTwoToneSeparability:
    def test_two_close_tones_render_as_two_peaks(self):
        """End-to-end resolution check: two sines 80 Hz apart near 700 Hz
        must appear as two separable peaks (peak–valley–peak) in the
        display column at n_fft=4096. This is the machine-checkable half
        of 'genuinely crisp' (spec: Verification #2)."""
        from audio.analysis import compute_spectrogram_column

        sample_rate, n_fft = 44100, 4096
        fft_freqs, display_freqs = make_grids(n_fft=n_fft)
        W = build_log_resample_matrix(fft_freqs, display_freqs)

        t = np.arange(n_fft) / sample_rate
        f_a, f_b = 660.0, 740.0
        tone = (0.5 * np.sin(2 * np.pi * f_a * t)
                + 0.5 * np.sin(2 * np.pi * f_b * t)).astype(np.float32)

        spectrum_db = compute_spectrogram_column(tone, sample_rate, n_fft)
        col = W @ spectrum_db

        def region_max(freq_lo, freq_hi):
            lo = int(np.searchsorted(display_freqs, freq_lo))
            hi = int(np.searchsorted(display_freqs, freq_hi))
            return float(np.max(col[lo:hi]))

        peak_a = region_max(640.0, 680.0)
        peak_b = region_max(720.0, 760.0)
        valley = region_max(690.0, 710.0)  # max of the gap region

        # The gap between the tones must dip at least 6 dB below the
        # weaker peak — i.e. the two tones are visibly separate.
        assert valley < min(peak_a, peak_b) - 6.0, (
            f"peaks {peak_a:.1f}/{peak_b:.1f} dB, valley {valley:.1f} dB — "
            "tones not separable"
        )
