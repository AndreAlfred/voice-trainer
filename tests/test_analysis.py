"""
Tests for audio/analysis.py

Run with: pytest tests/test_analysis.py -v
"""

import pytest
import numpy as np
from audio.analysis import hz_to_note_name


class TestHzToNoteName:
    """Test note name conversion from frequency in Hz."""

    def test_a4_is_440_hz(self):
        """A4 (concert A) is exactly 440 Hz."""
        note, octave = hz_to_note_name(440.0)
        assert note == "A"
        assert octave == 4

    def test_middle_c_is_c4(self):
        """Middle C is approximately 261.63 Hz."""
        note, octave = hz_to_note_name(261.63)
        assert note == "C"
        assert octave == 4

    def test_c5_above_middle_c(self):
        """C5 is one octave above middle C, ~523.25 Hz."""
        note, octave = hz_to_note_name(523.25)
        assert note == "C"
        assert octave == 5

    def test_g4_is_392_hz(self):
        """G4 is approximately 392 Hz — common baritone top note."""
        note, octave = hz_to_note_name(392.0)
        assert note == "G"
        assert octave == 4

    def test_returns_none_for_zero(self):
        """Zero Hz is silence — return None for both values."""
        note, octave = hz_to_note_name(0.0)
        assert note is None
        assert octave is None

    def test_returns_none_for_negative(self):
        """Negative frequencies are impossible — return None."""
        note, octave = hz_to_note_name(-100.0)
        assert note is None
        assert octave is None

    def test_c3_low_bass_note(self):
        """C3 (~130.81 Hz) is a low note, common for bass singers."""
        note, octave = hz_to_note_name(130.81)
        assert note == "C"
        assert octave == 3


from audio.analysis import compute_spectrogram_column


class TestComputeSpectrogramColumn:
    """Test spectrogram column computation."""

    SAMPLE_RATE = 44100
    N_FFT = 2048

    def _sine_wave(self, frequency_hz: float, n_samples: int = 2048) -> np.ndarray:
        """Generate a pure sine wave at the given frequency."""
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        return np.sin(2 * np.pi * frequency_hz * t).astype(np.float32)

    def test_output_shape_is_correct(self):
        """Output should have n_fft//2 + 1 frequency bins."""
        samples = self._sine_wave(440.0)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        expected_bins = self.N_FFT // 2 + 1
        assert spectrum.shape == (expected_bins,)

    def test_output_is_in_decibels(self):
        """Spectrum values should be in dB (negative values expected for typical audio)."""
        samples = self._sine_wave(440.0)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        assert spectrum.max() <= 10.0
        assert spectrum.min() >= -200.0

    def test_silence_is_very_quiet(self):
        """A silent signal should produce a very low-level spectrum."""
        samples = np.zeros(self.N_FFT, dtype=np.float32)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        assert spectrum.max() < -60.0

    def test_peak_is_near_sine_frequency(self):
        """The peak frequency bin should be near the sine wave frequency."""
        freq_hz = 1000.0
        samples = self._sine_wave(freq_hz)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)

        freq_resolution = self.SAMPLE_RATE / self.N_FFT  # Hz per bin
        peak_bin = np.argmax(spectrum)
        peak_freq = peak_bin * freq_resolution

        # Peak should be within one bin of the true frequency
        assert abs(peak_freq - freq_hz) <= freq_resolution


from audio.analysis import estimate_pitch


class TestEstimatePitch:
    """Test pitch estimation using autocorrelation."""

    SAMPLE_RATE = 44100

    def _sine_wave(self, frequency_hz: float, n_samples: int = 4096) -> np.ndarray:
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        return np.sin(2 * np.pi * frequency_hz * t).astype(np.float32)

    def test_detects_a4_440hz(self):
        """Should detect A4 (440 Hz) within 5 Hz tolerance."""
        samples = self._sine_wave(440.0)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 440.0) < 5.0

    def test_detects_middle_c_261hz(self):
        """Should detect middle C (~261.63 Hz) within 5 Hz tolerance."""
        samples = self._sine_wave(261.63)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 261.63) < 5.0

    def test_detects_high_soprano_c6(self):
        """Should detect C6 (~1046.5 Hz) within 10 Hz tolerance."""
        samples = self._sine_wave(1046.5)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 1046.5) < 10.0

    def test_silence_returns_none(self):
        """Silence should return None — no pitch detected."""
        samples = np.zeros(4096, dtype=np.float32)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is None

    def test_noise_returns_none_or_a_value(self):
        """Random noise may or may not have a pitch — just shouldn't crash."""
        rng = np.random.default_rng(seed=42)
        samples = rng.uniform(-0.1, 0.1, size=4096).astype(np.float32)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is None or (80.0 <= pitch <= 1200.0)


from audio.analysis import estimate_formants


class TestEstimateFormants:
    """Test F1/F2 vowel formant estimation using LPC."""

    SAMPLE_RATE = 44100

    def _voiced_signal(self, f0: float = 150.0, n_samples: int = 4096) -> np.ndarray:
        """Generate a voiced harmonic signal at fundamental frequency f0.

        A real voice is a sum of harmonics at f0, 2*f0, 3*f0, ...
        This mimics that structure so LPC has something to latch onto.
        """
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        signal = np.zeros(n_samples, dtype=np.float64)
        for k in range(1, 20):
            signal += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t)
        signal /= np.max(np.abs(signal)) + 1e-10
        return signal.astype(np.float32)

    def test_silence_returns_none_none(self):
        """Silence has no formants — both return values must be None."""
        samples = np.zeros(4096, dtype=np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        assert f1 is None
        assert f2 is None

    def test_short_buffer_returns_none_none(self):
        """Buffer shorter than LPC order must return None safely without crashing."""
        samples = np.random.randn(5).astype(np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        assert f1 is None
        assert f2 is None

    def test_detected_f1_is_in_valid_range(self):
        """Any detected F1 must be in the valid F1 range (200–900 Hz)."""
        samples = self._voiced_signal(f0=150.0)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        if f1 is not None:
            assert 200.0 <= f1 <= 900.0, f"F1={f1:.1f} Hz is outside valid range 200–900"

    def test_detected_f2_is_in_valid_range(self):
        """Any detected F2 must be in the valid F2 range (700–3200 Hz)."""
        samples = self._voiced_signal(f0=150.0)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        if f2 is not None:
            assert 700.0 <= f2 <= 3200.0, f"F2={f2:.1f} Hz is outside valid range 700–3200"

    def test_does_not_crash_on_noise(self):
        """Random noise must not raise an exception — return None or valid values."""
        rng = np.random.default_rng(seed=99)
        samples = rng.uniform(-0.5, 0.5, size=4096).astype(np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)  # must not raise
        if f1 is not None:
            assert 200.0 <= f1 <= 900.0
        if f2 is not None:
            assert 700.0 <= f2 <= 3200.0


class TestMultiresColumn:
    """Multi-resolution analysis: one FFT per band, long windows low,
    short windows high (Goal 1a Round 2)."""

    def test_returns_one_spectrum_per_band(self):
        from audio.analysis import compute_multires_column, MULTIRES_BANDS
        samples = np.random.default_rng(0).standard_normal(40000).astype(np.float32)
        spectra = compute_multires_column(samples, 44100)
        assert len(spectra) == len(MULTIRES_BANDS)
        for (lo, hi, n_fft), spec in zip(MULTIRES_BANDS, spectra):
            assert spec.shape == (n_fft // 2 + 1,)

    def test_bands_tile_display_range_without_gaps(self):
        """Band edges must cover 80-8000 Hz contiguously: each band's hi
        equals the next band's lo, first lo <= 80, last hi is None (open)."""
        from audio.analysis import MULTIRES_BANDS
        assert MULTIRES_BANDS[0][0] <= 80.0
        assert MULTIRES_BANDS[-1][1] is None
        for (_, hi, _), (lo, _, _) in zip(MULTIRES_BANDS[:-1], MULTIRES_BANDS[1:]):
            assert hi == lo

    def test_windows_shrink_as_frequency_rises(self):
        """The whole point: long windows (fine pitch) low, short windows
        (crisp time) high."""
        from audio.analysis import MULTIRES_BANDS
        sizes = [n_fft for (_, _, n_fft) in MULTIRES_BANDS]
        assert sizes == sorted(sizes, reverse=True)

    def test_short_input_is_padded_not_crashed(self):
        from audio.analysis import compute_multires_column, MULTIRES_BANDS
        samples = np.zeros(1000, dtype=np.float32)
        spectra = compute_multires_column(samples, 44100)
        assert len(spectra) == len(MULTIRES_BANDS)
