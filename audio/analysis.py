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
