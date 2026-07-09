"""
ui/pitch_display.py — Real-time pitch readout widget.

PitchDisplayWidget shows two pieces of information:
  1. The musical note name and octave (e.g. "A4")
  2. The frequency in Hz (e.g. "440 Hz")

Call update_pitch(frequency_hz) with the latest pitch estimate.
Pass None to indicate silence / no pitch detected.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from audio.analysis import hz_to_note_name
from ui import theme


class PitchDisplayWidget(QWidget):
    """Displays current pitch as a note name and frequency in Hz.

    Args:
        parent: Parent QWidget, or None for a top-level widget.
    """

    # Colors — vermillion "rubrication" when a pitch is live, faded ink
    # when silent, on a raised parchment panel.
    _COLOR_ACTIVE = theme.VERMILLION
    _COLOR_SILENT = theme.SEPIA_FAINT
    _BG_COLOR = theme.PARCHMENT_LIGHT

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet(
            f"background-color: {self._BG_COLOR}; "
            f"border-top: 1px solid {theme.UMBER};"
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the label layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)

        # Note name label (large, prominent)
        self._note_label = QLabel("—")
        note_font = QFont(theme.SERIF_FAMILY, 30, QFont.Weight.Bold)
        self._note_label.setFont(note_font)
        self._note_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
        self._note_label.setFixedWidth(100)
        self._note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Frequency label (smaller)
        self._freq_label = QLabel("No pitch detected")
        freq_font = QFont(theme.SERIF_FAMILY, 16)
        freq_font.setItalic(True)
        self._freq_label.setFont(freq_font)
        self._freq_label.setStyleSheet(f"color: {self._COLOR_SILENT};")

        layout.addWidget(self._note_label)
        layout.addSpacing(16)
        layout.addWidget(self._freq_label)
        layout.addStretch()

    def update_pitch(self, frequency_hz: float | None) -> None:
        """Update the display with a new pitch estimate.

        Args:
            frequency_hz: Frequency in Hz, or None if no pitch detected.
        """
        if frequency_hz is None:
            self._note_label.setText("—")
            self._note_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
            self._freq_label.setText("No pitch detected")
            self._freq_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
        else:
            note_name, octave = hz_to_note_name(frequency_hz)
            if note_name is not None:
                self._note_label.setText(f"{note_name}{octave}")
                self._note_label.setStyleSheet(f"color: {self._COLOR_ACTIVE};")
                self._freq_label.setText(f"{frequency_hz:.1f} Hz")
                self._freq_label.setStyleSheet(f"color: {self._COLOR_ACTIVE};")
