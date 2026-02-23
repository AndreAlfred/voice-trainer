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
