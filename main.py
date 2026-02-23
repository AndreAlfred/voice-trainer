"""
main.py — Entry point for the Voice Trainer application.

Run with:
    source venv/bin/activate
    python main.py

The app will ask for microphone permission the first time it runs on Mac.
Allow access when prompted, then sing into your microphone and watch the
spectrogram respond.
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.app import MainWindow


def main() -> int:
    """Create and show the main application window.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Trainer")
    app.setOrganizationName("VoiceTrainer")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
