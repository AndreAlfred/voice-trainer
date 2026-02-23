"""
ui/spectrogram.py — Live scrolling spectrogram widget.

SpectrogramWidget is a QWidget that displays a rolling buffer of frequency
spectra as a color image (time on the x-axis, frequency on the y-axis).
The display updates when add_column() is called with a new spectrum array.

The display range is 80–8000 Hz, which covers the full classical singing
voice including harmonics. Color uses the 'magma' colormap: dark purple
= quiet, red = moderate, yellow/white = loud.
"""

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt


# Frequency range to display
FREQ_MIN_HZ = 80.0
FREQ_MAX_HZ = 8000.0

# dB range for color mapping: anything below DISPLAY_DB_MIN is shown as black
DISPLAY_DB_MIN = -70.0
DISPLAY_DB_MAX = 0.0


class SpectrogramWidget(QWidget):
    """Scrolling spectrogram display widget.

    Maintains a rolling buffer of spectrogram columns and renders them
    as a color image using pyqtgraph's ImageItem.

    Args:
        sample_rate:     Audio sample rate (Hz). Must match analysis settings.
        n_fft:           FFT size used in analysis. Must match analysis settings.
        display_seconds: How many seconds of audio to show at once.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        n_fft: int = 2048,
        display_seconds: float = 8.0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.sample_rate = sample_rate
        self.n_fft = n_fft

        # Frequency axis: array of Hz values for each FFT bin
        self._all_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)

        # Only display bins in our target range (80–8000 Hz)
        self._freq_mask = (self._all_freqs >= FREQ_MIN_HZ) & (self._all_freqs <= FREQ_MAX_HZ)
        self._display_freqs = self._all_freqs[self._freq_mask]
        self._n_freq_bins = int(self._freq_mask.sum())

        # Time axis: number of columns = display_seconds * update_rate
        # Update rate ≈ sample_rate / (n_fft // 2) due to 50% overlap
        hop = n_fft // 2
        self._update_rate = sample_rate / hop  # columns per second
        self._n_time_cols = int(display_seconds * self._update_rate)

        # Rolling buffer: shape (time_cols, freq_bins), filled with silence
        self._buffer = np.full(
            (self._n_time_cols, self._n_freq_bins),
            fill_value=DISPLAY_DB_MIN,
            dtype=np.float32,
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the pyqtgraph plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Use dark background throughout
        pg.setConfigOption('background', '#1a1a2e')
        pg.setConfigOption('foreground', '#c8c8d4')

        self._plot = pg.PlotWidget()
        layout.addWidget(self._plot)

        # ImageItem renders the 2D buffer as a color image
        self._image_item = pg.ImageItem()
        self._plot.addItem(self._image_item)

        # Magma colormap: perceptually uniform dark→light
        colormap = pg.colormap.get('magma')
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([DISPLAY_DB_MIN, DISPLAY_DB_MAX])

        # Y-axis: label frequency bins with Hz values at key points
        self._plot.setLabel('left', 'Frequency', units='Hz')
        self._plot.setLabel('bottom', 'Time (scrolling →)')
        self._plot.showGrid(x=False, y=True, alpha=0.3)

        # Add Hz tick marks at musically meaningful frequencies
        freq_ticks = self._build_frequency_ticks()
        self._plot.getAxis('left').setTicks([freq_ticks])

        # Fix the displayed range
        self._plot.setYRange(0, self._n_freq_bins, padding=0)
        self._plot.setXRange(0, self._n_time_cols, padding=0)

        # Disable auto-ranging so the view doesn't jump around
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()

    def _build_frequency_ticks(self) -> list[tuple[float, str]]:
        """Build y-axis tick marks at musically meaningful frequencies."""
        target_hz = [100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 8000]
        ticks = []
        for hz in target_hz:
            if FREQ_MIN_HZ <= hz <= FREQ_MAX_HZ:
                # Find the bin index closest to this frequency
                idx = np.searchsorted(self._display_freqs, hz)
                if idx < self._n_freq_bins:
                    label = f"{hz} Hz" if hz < 1000 else f"{hz // 1000}k Hz"
                    ticks.append((float(idx), label))
        return ticks

    def add_column(self, spectrum_db: np.ndarray) -> None:
        """Add a new spectrum column and refresh the display.

        Call this every time a new audio chunk has been analyzed.

        Args:
            spectrum_db: Full magnitude spectrum in dB, shape (n_fft//2+1,).
                         Produced by audio.analysis.compute_spectrogram_column().
        """
        # Extract only the frequency bins in our display range
        display_col = spectrum_db[self._freq_mask]

        # Scroll the buffer left by one column and place the new column on the right
        self._buffer[:-1] = self._buffer[1:]
        self._buffer[-1] = display_col

        # Update the image. pyqtgraph ImageItem interprets shape (x, y):
        # x = time (horizontal), y = frequency (vertical)
        self._image_item.setImage(self._buffer, autoLevels=False)
