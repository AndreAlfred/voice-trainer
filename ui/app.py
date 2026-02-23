"""
ui/app.py — Main application window.

MainWindow creates and lays out the two display widgets (SpectrogramWidget
and PitchDisplayWidget) and manages the audio processing loop.

The audio loop uses a QTimer (not a separate thread) to periodically:
  1. Drain new audio chunks from AudioCapture's queue
  2. Accumulate them into an analysis buffer
  3. When the buffer is large enough, run spectrogram and pitch analysis
  4. Update the display widgets with new results

This approach keeps all Qt calls on the main thread (required by Qt) while
the audio capture itself runs in a background thread.
"""

import numpy as np
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont

from audio.capture import AudioCapture
from audio.analysis import compute_spectrogram_column, estimate_pitch
from ui.spectrogram import SpectrogramWidget
from ui.pitch_display import PitchDisplayWidget


# Audio processing settings — must match between capture and analysis
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024    # samples per audio callback (~23 ms)
N_FFT = 2048         # FFT window size (~46 ms) — larger = better frequency resolution
HOP_SIZE = N_FFT // 2  # 50% overlap between analysis frames

# How often the UI updates (milliseconds). 16 ms ≈ 60 fps.
TIMER_INTERVAL_MS = 16


class MainWindow(QMainWindow):
    """Main application window for the voice trainer.

    Owns:
      - AudioCapture instance (background thread)
      - SpectrogramWidget (upper half of window)
      - PitchDisplayWidget (lower strip)
      - QTimer (drives the audio → display update loop)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer — Classical Singing Analysis")
        self.resize(1100, 650)
        self.setStyleSheet("background-color: #1a1a2e;")

        # Audio system
        self._capture = AudioCapture(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)

        # Accumulation buffer: we collect audio chunks here until we have
        # enough samples for a full FFT analysis window.
        self._audio_buffer = np.zeros(0, dtype=np.float32)

        # Build the UI
        self._setup_ui()

        # Start the audio capture
        self._capture.start()

        # Start the processing timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_audio)
        self._timer.start(TIMER_INTERVAL_MS)

    def _setup_ui(self) -> None:
        """Create and arrange the UI widgets."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title = QLabel("VOICE TRAINER")
        title_font = QFont("Courier", 11)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(30)
        title.setStyleSheet("color: #666688; background-color: #0d0d1a; letter-spacing: 4px;")
        layout.addWidget(title)

        # Main spectrogram (takes up most of the window)
        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            display_seconds=8.0,
        )
        layout.addWidget(self._spectrogram, stretch=1)

        # Pitch readout at the bottom
        self._pitch_display = PitchDisplayWidget()
        layout.addWidget(self._pitch_display)

    def _process_audio(self) -> None:
        """Called ~60 times/second by QTimer. Drains audio queue and updates display.

        This is the core audio processing loop:
          1. Pull all available chunks from the audio queue
          2. Accumulate them into a buffer
          3. Analyze each complete window (N_FFT samples)
          4. Update the display widgets
        """
        # Drain all available chunks from the capture queue
        new_chunks = []
        while True:
            chunk = self._capture.get_chunk()
            if chunk is None:
                break
            new_chunks.append(chunk)

        if not new_chunks:
            return  # Nothing new — skip this timer tick

        # Append new samples to the accumulation buffer
        self._audio_buffer = np.concatenate([self._audio_buffer] + new_chunks)

        # Process as many complete windows as we have samples for
        latest_pitch = None
        while len(self._audio_buffer) >= N_FFT:
            # Take one window of samples
            window = self._audio_buffer[:N_FFT]

            # --- Signal analysis ---
            spectrum_db = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz = estimate_pitch(window, SAMPLE_RATE)

            # Update spectrogram with this new column
            self._spectrogram.add_column(spectrum_db)

            # Keep track of most recent pitch estimate
            if pitch_hz is not None:
                latest_pitch = pitch_hz

            # Advance the buffer by HOP_SIZE (50% overlap)
            self._audio_buffer = self._audio_buffer[HOP_SIZE:]

        # Update pitch display with whatever we found
        self._pitch_display.update_pitch(latest_pitch)

    def closeEvent(self, event) -> None:
        """Called when the window is closed. Stop audio before exiting."""
        self._timer.stop()
        self._capture.stop()
        event.accept()
