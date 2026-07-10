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
import matplotlib as mpl


# Frequency range to display
FREQ_MIN_HZ = 80.0
FREQ_MAX_HZ = 8000.0

# dB range for color mapping: anything below DISPLAY_DB_MIN is shown as black
DISPLAY_DB_MIN = -60.0
DISPLAY_DB_MAX = 0.0

# Number of log-spaced display bins on the frequency axis.
# More bins = smoother gradient but slightly more memory. 1024 with interpolation.
N_LOG_BINS = 1024


def build_log_resample_matrix(
    fft_freqs: np.ndarray,
    display_freqs: np.ndarray,
) -> np.ndarray:
    """Build a matrix W mapping a linear FFT spectrum to log display bins.

    Each display bin owns a frequency band (bounded by the geometric
    midpoints to its neighbors). Two regimes:

    - Band spans >= one FFT bin width (high frequencies on a log axis):
      weights are the overlap between the display band and each FFT bin's
      band — a proper area-weighted average. Crisp and anti-aliased with
      no post-hoc blur.
    - Band is narrower than one FFT bin (low frequencies): two-point
      linear interpolation between the neighboring FFT bin centers, so the
      low end shows smooth ramps between real values instead of a
      staircase (design decision A in the 2026-07-09 resolution spec).

    Rows sum to 1, so a flat spectrum maps to a flat column and dB levels
    are preserved.

    Args:
        fft_freqs:     Linear FFT bin center frequencies, shape (n_fft//2+1,).
        display_freqs: Log-spaced display bin centers, strictly increasing.

    Returns:
        float32 matrix of shape (len(display_freqs), len(fft_freqs)).
        Apply as `display_col = W @ spectrum_db`.
    """
    n_fft_bins = len(fft_freqs)
    n_display = len(display_freqs)
    df = float(fft_freqs[1] - fft_freqs[0])

    # FFT bin k covers the linear band [f_k - df/2, f_k + df/2].
    fft_lo = fft_freqs.astype(np.float64) - df / 2.0
    fft_hi = fft_freqs.astype(np.float64) + df / 2.0

    # Display bin d covers [lo_edges[d], hi_edges[d]] — geometric midpoints
    # between neighboring centers; end bins extended by the same log step.
    centers = display_freqs.astype(np.float64)
    mids = np.sqrt(centers[:-1] * centers[1:])
    step = centers[1] / centers[0]
    lo_edges = np.concatenate([[centers[0] / np.sqrt(step)], mids])
    hi_edges = np.concatenate([mids, [centers[-1] * np.sqrt(step)]])

    W = np.zeros((n_display, n_fft_bins), dtype=np.float32)
    for d in range(n_display):
        lo, hi = lo_edges[d], hi_edges[d]
        if (hi - lo) >= df:
            # Downsampling regime: average all FFT bins overlapping the band.
            overlap = np.minimum(hi, fft_hi) - np.maximum(lo, fft_lo)
            np.clip(overlap, 0.0, None, out=overlap)
            total = overlap.sum()
            if total > 0.0:
                W[d] = (overlap / total).astype(np.float32)
                continue
        # Upsampling regime: linear interpolation between the two FFT bin
        # centers straddling this display bin's center frequency.
        c = centers[d]
        k = int(np.searchsorted(fft_freqs, c))
        k = min(max(k, 1), n_fft_bins - 1)
        t = (c - fft_freqs[k - 1]) / (fft_freqs[k] - fft_freqs[k - 1])
        t = float(np.clip(t, 0.0, 1.0))
        W[d, k - 1] = 1.0 - t
        W[d, k] = t
    return W


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
        n_log_bins: int = N_LOG_BINS,
        hop: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.sample_rate = sample_rate
        self.n_fft = n_fft

        # Log-spaced frequency grid: N_LOG_BINS bins from FREQ_MIN_HZ to FREQ_MAX_HZ.
        # Each octave gets equal vertical space — this matches how the ear hears
        # and gives the 80–3200 Hz voice range ~80% of the display height instead
        # of the ~39% it gets with a linear scale.
        self._display_freqs = np.logspace(
            np.log10(FREQ_MIN_HZ),
            np.log10(FREQ_MAX_HZ),
            n_log_bins,
            dtype=np.float32,
        )
        self._n_freq_bins = n_log_bins

        # Full FFT frequency array (linear grid of the analysis spectrum)
        self._fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate).astype(np.float32)

        # Precomputed log-resampling matrix: display_col = W @ spectrum_db.
        # Overlap-averages where display bins are wide, interpolates where
        # they are narrow. Replaces per-frame np.interp + Gaussian blur.
        self._resample_matrix = build_log_resample_matrix(
            self._fft_freqs, self._display_freqs)

        # Time axis: number of columns = display_seconds * update_rate.
        # The hop (analysis stride) is decoupled from n_fft so a larger FFT
        # window doesn't slow the scroll; it must match the hop used by the
        # audio loop in ui/app.py.
        self.hop = hop if hop is not None else n_fft // 2
        self._update_rate = sample_rate / self.hop  # columns per second
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

        # Perceptually uniform colormap sampled at 256 points from matplotlib.
        # Default is 'inferno': black → purple → red → orange → yellow.
        colormap = self._build_colormap("inferno")
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
                    if hz < 1000:
                        label = f"{hz} Hz"
                    elif hz % 1000 == 0:
                        label = f"{hz // 1000}k Hz"
                    else:
                        label = f"{hz / 1000:.1f}k Hz"
                    ticks.append((float(idx), label))
        return ticks

    def _build_colormap(self, name: str) -> pg.ColorMap:
        """Sample a matplotlib colormap at 256 points and return a pg.ColorMap.

        Falls back to 'inferno' if the name is not found.
        """
        try:
            mpl_cmap = mpl.colormaps[name]
        except (KeyError, ValueError):
            mpl_cmap = mpl.colormaps["inferno"]
        positions = np.linspace(0.0, 1.0, 256)
        colors = (mpl_cmap(positions) * 255).astype(np.uint8)
        return pg.ColorMap(pos=positions, color=colors)

    def add_column(self, spectrum_db: np.ndarray) -> None:
        """Add a new spectrum column and refresh the display.

        Call this every time a new audio chunk has been analyzed.

        Args:
            spectrum_db: Full magnitude spectrum in dB, shape (n_fft//2+1,).
                         Produced by audio.analysis.compute_spectrogram_column().
        """
        # Resample the linear FFT spectrum onto the log display grid —
        # a single matrix-vector product against the precomputed matrix.
        display_col = self._resample_matrix @ spectrum_db

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

    def apply_settings(self, settings: object) -> None:
        """Apply all visual settings live — no restart needed.

        Args:
            settings: AppSettings instance from ui.settings.
        """
        import pyqtgraph as pg

        # Colormap
        colormap_name = getattr(settings, 'colormap_name', 'inferno')
        colormap = self._build_colormap(colormap_name)
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([settings.db_floor, settings.db_ceiling])

        # Formant dots
        self._f1_scatter.setBrush(pg.mkBrush(*settings.f1_color, 200))
        self._f2_scatter.setBrush(pg.mkBrush(*settings.f2_color, 200))
        self._f1_scatter.setSize(settings.dot_size)
        self._f2_scatter.setSize(settings.dot_size)

        # Singer's formant band
        self._singers_formant_region.setVisible(settings.singers_formant_visible)

        # Background
        r, g, b = settings.background_color
        self._plot.setBackground(f"#{r:02x}{g:02x}{b:02x}")

        # Scroll buffer resize when display_seconds changes
        new_cols = int(settings.display_seconds * (self.sample_rate / self.hop))
        if new_cols != self._n_time_cols:
            new_buf = np.full(
                (new_cols, self._n_freq_bins),
                fill_value=settings.db_floor,
                dtype=np.float32,
            )
            copy = min(new_cols, self._n_time_cols)
            new_buf[-copy:] = self._buffer[-copy:]
            self._buffer = new_buf

            new_f1 = np.full(new_cols, np.nan, dtype=np.float32)
            new_f2 = np.full(new_cols, np.nan, dtype=np.float32)
            cf = min(new_cols, len(self._f1_bins))
            new_f1[-cf:] = self._f1_bins[-cf:]
            new_f2[-cf:] = self._f2_bins[-cf:]
            self._f1_bins = new_f1
            self._f2_bins = new_f2

            self._n_time_cols = new_cols
            self._plot.setXRange(0, new_cols, padding=0)
