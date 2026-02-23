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
