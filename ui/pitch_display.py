"""
ui/pitch_display.py — Real-time pitch readout widget.

Two dressings, switched with the app theme:
  light — the note name stamped into a wax seal on a lapis ribbon, the
          frequency engraved on a brass plate, all on a sandstone ledge
  dark  — the original readout: big Courier note name and Hz label on a
          flat midnight strip

Call update_pitch(frequency_hz) with the latest pitch estimate.
Pass None to indicate silence / no pitch detected.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from audio.analysis import hz_to_note_name
from ui import theme
from ui.ornaments import WaxSeal


class PitchDisplayWidget(QWidget):
    """Displays current pitch as a note name and frequency in Hz.

    Args:
        parent: Parent QWidget, or None for a top-level widget.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("pitch_shelf")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._note: str | None = None
        self._freq: str | None = None
        self._mode = "light"
        self._setup_ui()
        self.set_theme_mode(theme.mode())

    def _setup_ui(self) -> None:
        """Build both dressings; set_theme_mode shows one."""
        self._layout = QHBoxLayout(self)

        self._seal = WaxSeal()

        # Classic dark-mode note label (hidden in light mode)
        self._note_label = QLabel("—")
        self._note_label.setFixedWidth(100)
        self._note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._freq_label = QLabel("No pitch detected")

        self._layout.addWidget(self._seal)
        self._layout.addWidget(self._note_label)
        self._layout.addSpacing(14)
        self._layout.addWidget(self._freq_label)
        self._layout.addStretch()

    def set_theme_mode(self, mode: str) -> None:
        """Swap between the wax-seal shelf and the classic flat readout."""
        self._mode = mode
        if mode == "dark":
            self.setFixedHeight(72)
            self._layout.setContentsMargins(20, 8, 20, 8)
            self._seal.hide()
            self._note_label.show()
            self._note_label.setFont(QFont("Courier", 28, QFont.Weight.Bold))
            self._freq_label.setFont(QFont("Courier", 16))
        else:
            self.setFixedHeight(118)
            self._layout.setContentsMargins(24, 4, 24, 4)
            self._note_label.hide()
            self._seal.show()
            freq_font = QFont(theme.SERIF_FAMILY, 16)
            freq_font.setItalic(True)
            self._freq_label.setFont(freq_font)
        self._refresh()

    def update_pitch(self, frequency_hz: float | None) -> None:
        """Update the display with a new pitch estimate.

        Args:
            frequency_hz: Frequency in Hz, or None if no pitch detected.
        """
        if frequency_hz is None:
            self._note = None
            self._freq = None
        else:
            note_name, octave = hz_to_note_name(frequency_hz)
            if note_name is None:
                return   # keep the previous reading, as the original did
            self._note = f"{note_name}{octave}"
            self._freq = f"{frequency_hz:.1f} Hz"
        self._refresh()

    def _refresh(self) -> None:
        self._seal.set_note(self._note)
        self._note_label.setText(self._note or "—")
        self._freq_label.setText(self._freq or "No pitch detected")
        if self._mode == "dark":
            color = theme.DARK_ACTIVE if self._note else theme.DARK_SILENT
            self._note_label.setStyleSheet(f"color: {color};")
            self._freq_label.setStyleSheet(f"color: {color};")
        else:
            self._note_label.setStyleSheet("")
            self._freq_label.setStyleSheet(theme.BRASS_PLATE_STYLESHEET)
