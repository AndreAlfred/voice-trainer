"""
ui/pitch_display.py — Real-time pitch readout widget.

PitchDisplayWidget shows two pieces of information:
  1. The musical note name and octave, stamped into a vermillion wax seal
  2. The frequency in Hz, engraved on a brass plate

Call update_pitch(frequency_hz) with the latest pitch estimate.
Pass None to indicate silence / no pitch detected — the seal cools to
gray wax and the plate reads "No pitch detected".
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QFont

from audio.analysis import hz_to_note_name
from ui import theme
from ui.ornaments import WaxSeal


class PitchDisplayWidget(QWidget):
    """Displays current pitch as a wax-seal note stamp and a brass Hz plate.

    Args:
        parent: Parent QWidget, or None for a top-level widget.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(96)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the label layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 4, 20, 4)

        self._seal = WaxSeal()

        self._freq_label = QLabel("No pitch detected")
        freq_font = QFont(theme.SERIF_FAMILY, 16)
        freq_font.setItalic(True)
        self._freq_label.setFont(freq_font)
        self._freq_label.setStyleSheet(theme.BRASS_PLATE_STYLESHEET)

        layout.addWidget(self._seal)
        layout.addSpacing(14)
        layout.addWidget(self._freq_label)
        layout.addStretch()

    def update_pitch(self, frequency_hz: float | None) -> None:
        """Update the display with a new pitch estimate.

        Args:
            frequency_hz: Frequency in Hz, or None if no pitch detected.
        """
        if frequency_hz is None:
            self._seal.set_note(None)
            self._freq_label.setText("No pitch detected")
        else:
            note_name, octave = hz_to_note_name(frequency_hz)
            if note_name is not None:
                self._seal.set_note(f"{note_name}{octave}")
                self._freq_label.setText(f"{frequency_hz:.1f} Hz")
