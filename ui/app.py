"""
ui/app.py — Main application window.

Loads AppSettings on startup, creates the spectrogram and pitch widgets,
wraps a SettingsPanel in a QDockWidget on the right, and wires everything
together so every settings change applies live and auto-saves to disk.
"""

import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QDockWidget, QToolBar,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QAction

from audio.capture import AudioCapture
from audio.analysis import compute_spectrogram_column, estimate_pitch, estimate_formants
from ui.settings import AppSettings
from ui.settings_panel import SettingsPanel
from ui.spectrogram import SpectrogramWidget
from ui.pitch_display import PitchDisplayWidget

SAMPLE_RATE      = 44100
BLOCK_SIZE       = 1024
N_FFT            = 2048
HOP_SIZE         = N_FFT // 2
TIMER_INTERVAL_MS = 16


class MainWindow(QMainWindow):
    """Main application window for the voice trainer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer — Classical Singing Analysis")
        self.resize(1100, 650)

        self._settings = AppSettings.load()
        r, g, b = self._settings.background_color
        self.setStyleSheet(f"background-color: rgb({r},{g},{b});")

        self._capture = AudioCapture(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
        self._audio_buffer = np.zeros(0, dtype=np.float32)

        self._setup_ui()
        self._setup_settings_dock()
        self._spectrogram.apply_settings(self._settings)

        self._capture.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_audio)
        self._timer.start(TIMER_INTERVAL_MS)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("VOICE TRAINER")
        title.setFont(QFont("Courier", 11))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(30)
        title.setStyleSheet(
            "color: #666688; background-color: #0d0d1a; letter-spacing: 4px;"
        )
        layout.addWidget(title)

        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            display_seconds=self._settings.display_seconds,
        )
        layout.addWidget(self._spectrogram, stretch=1)

        self._pitch_display = PitchDisplayWidget()
        layout.addWidget(self._pitch_display)

    def _setup_settings_dock(self) -> None:
        self._settings_panel = SettingsPanel(self._settings)
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

        dock = QDockWidget("Visual Settings", self)
        dock.setObjectName("settings_dock")
        dock.setWidget(self._settings_panel)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.hide()
        self._settings_dock = dock

        toolbar = QToolBar("Settings", self)
        toolbar.setMovable(False)
        toggle = QAction("⚙  Settings", self)
        toggle.setCheckable(True)
        toggle.toggled.connect(dock.setVisible)
        dock.visibilityChanged.connect(toggle.setChecked)
        toolbar.addAction(toggle)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _on_settings_changed(self, settings: AppSettings) -> None:
        r, g, b = settings.background_color
        self.setStyleSheet(f"background-color: rgb({r},{g},{b});")
        self._spectrogram.apply_settings(settings)

    def _process_audio(self) -> None:
        new_chunks = []
        while True:
            chunk = self._capture.get_chunk()
            if chunk is None:
                break
            new_chunks.append(chunk)

        if not new_chunks:
            return

        self._audio_buffer = np.concatenate([self._audio_buffer] + new_chunks)
        latest_pitch = None

        while len(self._audio_buffer) >= N_FFT:
            window = self._audio_buffer[:N_FFT]
            spectrum_db  = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz     = estimate_pitch(window, SAMPLE_RATE)
            f1_hz, f2_hz = estimate_formants(window, SAMPLE_RATE)

            self._spectrogram.add_column(spectrum_db)
            self._spectrogram.add_formants(f1_hz, f2_hz)

            if pitch_hz is not None:
                latest_pitch = pitch_hz

            self._audio_buffer = self._audio_buffer[HOP_SIZE:]

        self._pitch_display.update_pitch(latest_pitch)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._capture.stop()
        event.accept()
