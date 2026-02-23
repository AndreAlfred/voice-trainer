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
DISPLAY_DB_MIN = -60.0
DISPLAY_DB_MAX = 0.0

# Number of log-spaced display bins on the frequency axis.
# More bins = smoother gradient but slightly more memory. 512 is a good balance.
N_LOG_BINS = 512


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

        # Log-spaced frequency grid: 512 bins from FREQ_MIN_HZ to FREQ_MAX_HZ.
        # Each octave gets equal vertical space — this matches how the ear hears
        # and gives the F0/F1/F2 voice range ~62% of the display height instead
        # of the ~17% it gets with a linear scale.
        self._display_freqs = np.logspace(
            np.log10(FREQ_MIN_HZ),
            np.log10(FREQ_MAX_HZ),
            N_LOG_BINS,
            dtype=np.float32,
        )
        self._n_freq_bins = N_LOG_BINS

        # Pre-compute mapping: for each log display bin, the index of the nearest
        # linear FFT bin. Built once at startup so add_column() is a fast index lookup.
        _all_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
        # searchsorted gives the insertion point (next-higher bin).
        # Compare that bin and the one below it; keep whichever is closer in Hz.
        _insert = np.searchsorted(_all_freqs, self._display_freqs)
        _lower = np.clip(_insert - 1, 0, len(_all_freqs) - 1)
        _upper = np.clip(_insert,     0, len(_all_freqs) - 1)
        _dist_lower = np.abs(_all_freqs[_lower] - self._display_freqs)
        _dist_upper = np.abs(_all_freqs[_upper] - self._display_freqs)
        self._freq_indices = np.where(_dist_lower <= _dist_upper, _lower, _upper)

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

        # Rolling F1/F2 formant position buffers — one value per time column.
        # NaN = no detection at that time step (dot not drawn at that position).
        self._f1_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)
        self._f2_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)

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

        # Custom 3-stop colormap: dark teal → warm orange → pale yellow.
        # Starts at a visible teal (not pure black) so quiet sounds always
        # appear as a real color rather than near-invisible dark purple.
        colormap = pg.ColorMap(
            pos=np.array([0.0, 0.5, 1.0]),
            color=np.array([
                [ 13,  79,  82, 255],  # dark teal  — silence / very quiet
                [212,  80,  10, 255],  # warm orange — moderate energy
                [255, 240, 160, 255],  # pale yellow — loud / strong harmonics
            ], dtype=np.uint8),
        )
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

        # --- Singer's formant band (2000–3500 Hz) ---
        # The "singer's formant cluster" in this frequency range gives the
        # classical voice its carrying power and "ring" over an orchestra.
        # A persistent gold band makes it easy to see whether harmonics
        # are landing in this zone.
        f_lo_bin = int(np.searchsorted(self._display_freqs, 2000.0))
        f_hi_bin = int(np.searchsorted(self._display_freqs, 3500.0))

        self._singers_formant_region = pg.LinearRegionItem(
            values=[f_lo_bin, f_hi_bin],
            orientation='horizontal',   # horizontal = bounded by y-axis range
            movable=False,
            brush=pg.mkBrush(255, 215, 0, 22),   # very faint gold fill
            pen=pg.mkPen(255, 215, 0, 60),        # slightly more visible border
        )
        self._plot.addItem(self._singers_formant_region)

        # Label anchored to the top-left corner of the band
        formant_label = pg.TextItem(
            "Singer's Formant", color=(255, 215, 0, 140), anchor=(0, 1))
        formant_label.setPos(0, f_hi_bin)
        self._plot.addItem(formant_label)

        # F1 (light blue) and F2 (bright green) formant scatter overlays.
        # These dots scroll with the spectrogram and show vowel formant history.
        self._f1_scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,
            brush=pg.mkBrush(100, 180, 255, 200),   # light blue
        )
        self._f2_scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,
            brush=pg.mkBrush(80, 240, 120, 200),    # bright green
        )
        self._plot.addItem(self._f1_scatter)
        self._plot.addItem(self._f2_scatter)

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
        # Map the linear FFT spectrum onto the log-spaced display grid
        display_col = spectrum_db[self._freq_indices]

        # Scroll the buffer left by one column and place the new column on the right
        self._buffer[:-1] = self._buffer[1:]
        self._buffer[-1] = display_col

        # Update the image. pyqtgraph ImageItem interprets shape (x, y):
        # x = time (horizontal), y = frequency (vertical)
        self._image_item.setImage(self._buffer, autoLevels=False)

    def add_formants(self, f1_hz: float | None, f2_hz: float | None) -> None:
        """Add new F1/F2 estimates and refresh the scatter display.

        Call this once per audio analysis frame, immediately after add_column().
        The scatter dots scroll left in sync with the spectrogram image.

        Args:
            f1_hz: First formant frequency in Hz, or None if not detected.
            f2_hz: Second formant frequency in Hz, or None if not detected.
        """
        # Scroll both position buffers left (oldest drops off the left edge)
        self._f1_bins[:-1] = self._f1_bins[1:]
        self._f2_bins[:-1] = self._f2_bins[1:]

        # Convert Hz to the freq-bin index used by the image coordinate system.
        # Use NaN when the formant is not detected or out of the display range.
        freq_lo = self._display_freqs[0]
        freq_hi = self._display_freqs[-1]

        if f1_hz is not None and freq_lo <= f1_hz <= freq_hi:
            self._f1_bins[-1] = float(np.searchsorted(self._display_freqs, f1_hz))
        else:
            self._f1_bins[-1] = np.nan

        if f2_hz is not None and freq_lo <= f2_hz <= freq_hi:
            self._f2_bins[-1] = float(np.searchsorted(self._display_freqs, f2_hz))
        else:
            self._f2_bins[-1] = np.nan

        # Build x-positions (time column indices 0 … n_time_cols-1)
        x_all = np.arange(self._n_time_cols, dtype=np.float32)

        # Update F1 scatter — skip NaN entries (no detection = no dot)
        mask1 = ~np.isnan(self._f1_bins)
        if mask1.any():
            self._f1_scatter.setData(x=x_all[mask1], y=self._f1_bins[mask1])
        else:
            self._f1_scatter.setData(x=[], y=[])

        # Update F2 scatter
        mask2 = ~np.isnan(self._f2_bins)
        if mask2.any():
            self._f2_scatter.setData(x=x_all[mask2], y=self._f2_bins[mask2])
        else:
            self._f2_scatter.setData(x=[], y=[])
