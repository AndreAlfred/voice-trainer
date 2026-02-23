"""
audio/analysis.py — Signal processing for the voice trainer.

This module contains all the math:
  - hz_to_note_name:          convert a frequency (Hz) to a note name
  - compute_spectrogram_column: compute one time-slice of the spectrogram
  - estimate_pitch:            estimate the fundamental frequency of a sound

All functions are pure (no side effects, no hardware access) so they
are easy to test and reason about.
"""

import math
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard tuning: A4 = 440 Hz, MIDI note 69
_A4_HZ = 440.0
_A4_MIDI = 69

# All 12 chromatic note names starting from C
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---------------------------------------------------------------------------
# Note name conversion
# ---------------------------------------------------------------------------

def hz_to_note_name(frequency_hz: float) -> tuple[str | None, int | None]:
    """Convert a frequency in Hz to a musical note name and octave number.

    Uses equal temperament tuning (A4 = 440 Hz).

    Args:
        frequency_hz: Frequency in Hz. Must be positive.

    Returns:
        (note_name, octave) tuple, e.g. ("A", 4) for 440 Hz.
        Returns (None, None) if frequency is zero or negative.

    Examples:
        >>> hz_to_note_name(440.0)
        ('A', 4)
        >>> hz_to_note_name(261.63)
        ('C', 4)
    """
    if frequency_hz <= 0:
        return None, None

    # Convert Hz to MIDI note number.
    # Formula: MIDI = 69 + 12 * log2(f / 440)
    # Each octave doubles the frequency; each semitone multiplies by 2^(1/12).
    midi = round(_A4_MIDI + 12 * math.log2(frequency_hz / _A4_HZ))

    # Extract note name (0=C, 1=C#, ... 11=B)
    note_name = _NOTE_NAMES[midi % 12]

    # Extract octave number. MIDI 0 = C-1, MIDI 12 = C0, MIDI 60 = C4.
    octave = (midi // 12) - 1

    return note_name, octave


# ---------------------------------------------------------------------------
# Spectrogram computation
# ---------------------------------------------------------------------------

def compute_spectrogram_column(
    samples: np.ndarray,
    sample_rate: int = 44100,
    n_fft: int = 2048,
) -> np.ndarray:
    """Compute one vertical column of a spectrogram from audio samples.

    Applies a Hann window to reduce spectral leakage, then computes the
    real FFT and converts to decibels.

    Args:
        samples:     Audio samples as a 1D float32 numpy array.
                     Should have length >= n_fft.
        sample_rate: Samples per second (Hz). Default: 44100.
        n_fft:       FFT size. Larger = better frequency resolution but
                     more CPU. Default: 2048 (~46 ms at 44100 Hz).

    Returns:
        1D numpy array of shape (n_fft//2 + 1,) containing the magnitude
        spectrum in decibels (dB). Higher values = louder at that frequency.

    Note:
        The frequency of bin i is: i * sample_rate / n_fft Hz.
        So bin 0 = 0 Hz (DC), bin 1 = ~21.5 Hz, ..., bin 1024 = 22050 Hz.
    """
    # Use the most recent n_fft samples (or all samples if shorter)
    chunk = samples[-n_fft:] if len(samples) >= n_fft else samples

    # Pad with zeros if shorter than n_fft
    if len(chunk) < n_fft:
        chunk = np.pad(chunk, (0, n_fft - len(chunk)))

    # Apply a Hann window to reduce "spectral leakage" — the phenomenon
    # where energy from one frequency bleeds into neighboring bins.
    window = np.hanning(n_fft)
    windowed = chunk.astype(np.float64) * window

    # Real FFT: since audio is real-valued, we only need the positive
    # frequency half. Output has n_fft//2 + 1 complex values.
    spectrum_complex = np.fft.rfft(windowed, n=n_fft)

    # Magnitude: |complex| gives amplitude at each frequency bin.
    # Normalize by n_fft so that a full-scale sine wave peaks near 0 dB.
    magnitude = np.abs(spectrum_complex) / n_fft

    # Convert to decibels. Add a tiny floor (1e-10) to avoid log(0).
    # 20 * log10 because we're working with amplitude (not power).
    spectrum_db = 20.0 * np.log10(magnitude + 1e-10)

    return spectrum_db.astype(np.float32)
