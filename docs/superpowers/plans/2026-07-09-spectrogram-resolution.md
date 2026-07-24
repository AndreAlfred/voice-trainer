# Spectrogram Resolution Round 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Gaussian-blur band-aid with a precomputed log-resampling matrix and double real FFT resolution (2048→4096, hop held at 1024), so the spectrogram is genuinely crisp instead of blurred.

**Architecture:** A pure function `build_log_resample_matrix(fft_freqs, display_freqs)` builds a `(n_display, n_fft_bins)` matrix `W` once at widget construction: overlap-averaging where a display bin spans multiple FFT bins (high frequencies), two-point linear interpolation where it doesn't (low frequencies — spec decision A). `add_column` becomes `W @ spectrum` with no per-frame blur of the whole buffer. The hop is decoupled from `n_fft` and threaded explicitly through app, widget, and benchmark harness.

**Tech Stack:** Python 3, numpy, PySide6/pyqtgraph, pytest. Spec: `docs/superpowers/specs/2026-07-09-spectrogram-resolution-design.md`.

**Environment note:** Work happens in the worktree `/Users/andrewtrimble/voice-trainer/.claude/worktrees/spectrogram-resolution` on branch `feat/spectrogram-resolution`. The venv lives in the main checkout — every shell needs `source /Users/andrewtrimble/voice-trainer/venv/bin/activate` first. Run all commands from the worktree root. Qt tests need no display (`QT_QPA_PLATFORM=offscreen` is set by the harness; pytest's Qt tests already run headless on macOS).

---

### Task 1: The resampling matrix (pure function + tests)

**Files:**
- Modify: `ui/spectrogram.py` (add module-level function `build_log_resample_matrix`, after the constants block at line ~32)
- Create: `tests/test_resampler.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resampler.py`:

```python
"""
tests/test_resampler.py — Tests for build_log_resample_matrix.

The matrix W maps a linear-frequency FFT spectrum onto the log-spaced
display grid: overlap-averaging where display bins are wide (high
frequencies), linear interpolation where they are narrow (low
frequencies). Replaces np.interp + Gaussian blur.
"""

import numpy as np

from ui.spectrogram import build_log_resample_matrix


def make_grids(n_fft=4096, sample_rate=44100, n_display=1024,
               fmin=80.0, fmax=8000.0):
    fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate).astype(np.float32)
    display_freqs = np.logspace(
        np.log10(fmin), np.log10(fmax), n_display, dtype=np.float32)
    return fft_freqs, display_freqs


class TestMatrixShapeAndWeights:
    def test_shape(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        assert W.shape == (len(display_freqs), len(fft_freqs))

    def test_rows_sum_to_one(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        np.testing.assert_allclose(W.sum(axis=1), 1.0, atol=1e-4)

    def test_weights_nonnegative(self):
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        assert (W >= 0).all()


class TestMapping:
    def test_flat_spectrum_maps_flat(self):
        """A constant-level input must produce a constant-level display
        column (rows sum to 1 makes this a weighted average)."""
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        flat = np.full(len(fft_freqs), -40.0, dtype=np.float32)
        out = W @ flat
        np.testing.assert_allclose(out, -40.0, atol=1e-3)

    def test_mapping_is_monotonic_in_frequency(self):
        """The weighted-mean source frequency of each display row must be
        strictly increasing — no frequency folding."""
        fft_freqs, display_freqs = make_grids()
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        centers = W @ fft_freqs.astype(np.float64)
        assert np.all(np.diff(centers) > 0)

    def test_row_center_tracks_display_freq(self):
        """Each row's weighted-mean source frequency should be close to
        that display bin's nominal frequency (within one FFT bin width)."""
        fft_freqs, display_freqs = make_grids()
        df = float(fft_freqs[1] - fft_freqs[0])
        W = build_log_resample_matrix(fft_freqs, display_freqs)
        centers = W @ fft_freqs.astype(np.float64)
        assert np.max(np.abs(centers - display_freqs)) < df


class TestTwoToneSeparability:
    def test_two_close_tones_render_as_two_peaks(self):
        """End-to-end resolution check: two sines 80 Hz apart near 700 Hz
        must appear as two separable peaks (peak–valley–peak) in the
        display column at n_fft=4096. This is the machine-checkable half
        of 'genuinely crisp' (spec: Verification #2)."""
        from audio.analysis import compute_spectrogram_column

        sample_rate, n_fft = 44100, 4096
        fft_freqs, display_freqs = make_grids(n_fft=n_fft)
        W = build_log_resample_matrix(fft_freqs, display_freqs)

        t = np.arange(n_fft) / sample_rate
        f_a, f_b = 660.0, 740.0
        tone = (0.5 * np.sin(2 * np.pi * f_a * t)
                + 0.5 * np.sin(2 * np.pi * f_b * t)).astype(np.float32)

        spectrum_db = compute_spectrogram_column(tone, sample_rate, n_fft)
        col = W @ spectrum_db

        def region_max(freq_lo, freq_hi):
            lo = int(np.searchsorted(display_freqs, freq_lo))
            hi = int(np.searchsorted(display_freqs, freq_hi))
            return float(np.max(col[lo:hi]))

        peak_a = region_max(640.0, 680.0)
        peak_b = region_max(720.0, 760.0)
        valley = region_max(690.0, 710.0)  # max of the gap region

        # The gap between the tones must dip at least 6 dB below the
        # weaker peak — i.e. the two tones are visibly separate.
        assert valley < min(peak_a, peak_b) - 6.0, (
            f"peaks {peak_a:.1f}/{peak_b:.1f} dB, valley {valley:.1f} dB — "
            "tones not separable"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/andrewtrimble/voice-trainer/.claude/worktrees/spectrogram-resolution
source /Users/andrewtrimble/voice-trainer/venv/bin/activate
pytest tests/test_resampler.py -v
```
Expected: FAIL — `ImportError: cannot import name 'build_log_resample_matrix'`.

- [ ] **Step 3: Implement `build_log_resample_matrix`**

In `ui/spectrogram.py`, directly below the `N_LOG_BINS = 1024` constant (before `class SpectrogramWidget`), add:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_resampler.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_resampler.py ui/spectrogram.py
git commit -m "feat: add log-resampling matrix (overlap-average + low-freq interp)"
```

---

### Task 2: Wire the resampler into SpectrogramWidget; drop the blur; add hop parameter

**Files:**
- Modify: `ui/spectrogram.py` (`__init__` ~line 46, `add_column` ~line 213, `apply_settings` ~line 284, imports ~line 14)
- Modify: `tests/test_spectrogram.py` (delete `TestGaussianBlur` class ~lines 189–228; add `TestHopParameter`)

- [ ] **Step 1: Update tests — delete blur tests, add hop + resampler-wiring tests**

In `tests/test_spectrogram.py`, delete the entire `TestGaussianBlur` class (the last class in the file, lines 189–228). In its place add:

```python
class TestHopParameter:
    """The hop is decoupled from n_fft (spec: hold hop at 1024 while n_fft
    grows to 4096, preserving the ~43 col/s scroll rate)."""

    def test_default_hop_is_half_n_fft(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        assert w.hop == 1024

    def test_explicit_hop_sets_scroll_rate(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=4096, hop=1024, display_seconds=8.0)
        # 44100 / 1024 ≈ 43.07 columns/sec → 344 columns at 8 s
        assert w._n_time_cols == int(8.0 * (44100 / 1024))

    def test_hop_used_after_apply_settings_resize(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget(n_fft=4096, hop=1024, display_seconds=8.0)
        w.apply_settings(AppSettings(display_seconds=4.0))
        assert w._n_time_cols == int(4.0 * (44100 / 1024))


class TestResamplerWiring:
    """add_column must use the precomputed matrix, with no blur pass."""

    def test_no_blur_attribute(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert not hasattr(w, '_blur_sigma')

    def test_resample_matrix_built(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        assert w._resample_matrix.shape == (w._n_freq_bins, 2048 // 2 + 1)

    def test_flat_spectrum_stays_flat_in_buffer(self, qt_app):
        import numpy as np
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        w.add_column(np.full(1025, -40.0, dtype=np.float32))
        np.testing.assert_allclose(w._buffer[-1], -40.0, atol=1e-3)
```

- [ ] **Step 2: Run tests to verify the new ones fail**

```bash
pytest tests/test_spectrogram.py -v
```
Expected: the `TestHopParameter` and `TestResamplerWiring` tests FAIL (`no attribute 'hop'`, `no attribute '_resample_matrix'`, `has attribute '_blur_sigma'`); pre-existing tests still pass.

- [ ] **Step 3: Modify `ui/spectrogram.py`**

3a. Remove the scipy import (line 14): delete `from scipy.ndimage import gaussian_filter`.

3b. In `__init__`, change the signature and hop/time-axis math. Replace:

```python
    def __init__(
        self,
        sample_rate: int = 44100,
        n_fft: int = 2048,
        display_seconds: float = 8.0,
        n_log_bins: int = N_LOG_BINS,
        parent: QWidget | None = None,
    ):
```
with:
```python
    def __init__(
        self,
        sample_rate: int = 44100,
        n_fft: int = 2048,
        display_seconds: float = 8.0,
        n_log_bins: int = N_LOG_BINS,
        hop: int | None = None,
        parent: QWidget | None = None,
    ):
```

3c. Replace the time-axis block:
```python
        # Time axis: number of columns = display_seconds * update_rate
        # Update rate ≈ sample_rate / (n_fft // 2) due to 50% overlap
        hop = n_fft // 2
        self._update_rate = sample_rate / hop  # columns per second
        self._n_time_cols = int(display_seconds * self._update_rate)
```
with:
```python
        # Time axis: number of columns = display_seconds * update_rate.
        # The hop (analysis stride) is decoupled from n_fft so a larger FFT
        # window doesn't slow the scroll; it must match the hop used by the
        # audio loop in ui/app.py.
        self.hop = hop if hop is not None else n_fft // 2
        self._update_rate = sample_rate / self.hop  # columns per second
        self._n_time_cols = int(display_seconds * self._update_rate)
```

3d. Directly after the `self._fft_freqs = ...` line, add:
```python
        # Precomputed log-resampling matrix: display_col = W @ spectrum_db.
        # Overlap-averages where display bins are wide, interpolates where
        # they are narrow. Replaces per-frame np.interp + Gaussian blur.
        self._resample_matrix = build_log_resample_matrix(
            self._fft_freqs, self._display_freqs)
```

3e. At the end of `__init__`, delete:
```python
        # Blur sigma for smooth topographic rendering (0 = disabled)
        self._blur_sigma = 1.5
```

Also delete the dead `_freq_indices` precompute block (its comment claims it's used by `add_formants`, but `add_formants` calls `np.searchsorted` directly — nothing reads `_freq_indices`):
```python
        # Pre-compute mapping: for each log display bin, the index of the nearest
        # linear FFT bin. Used only for formant scatter positioning (add_formants).
        _insert = np.searchsorted(self._fft_freqs, self._display_freqs)
        _lower = np.clip(_insert - 1, 0, len(self._fft_freqs) - 1)
        _upper = np.clip(_insert,     0, len(self._fft_freqs) - 1)
        _dist_lower = np.abs(self._fft_freqs[_lower] - self._display_freqs)
        _dist_upper = np.abs(self._fft_freqs[_upper] - self._display_freqs)
        self._freq_indices = np.where(_dist_lower <= _dist_upper, _lower, _upper)
```
Verify before deleting: `grep -rn "_freq_indices" ui/ tests/ tools/` must show only the `__init__` assignment.

3f. In `add_column`, replace:
```python
        # Interpolate the linear FFT spectrum onto the log-spaced display grid
        display_col = np.interp(self._display_freqs, self._fft_freqs, spectrum_db)

        # Scroll the buffer left by one column and place the new column on the right
        self._buffer[:-1] = self._buffer[1:]
        self._buffer[-1] = display_col

        # Update the image. pyqtgraph ImageItem interprets shape (x, y):
        # x = time (horizontal), y = frequency (vertical)
        # Apply Gaussian blur for smooth topographic rendering
        if self._blur_sigma > 0:
            smoothed = gaussian_filter(self._buffer, sigma=(1.0, self._blur_sigma))
            self._image_item.setImage(smoothed, autoLevels=False)
        else:
            self._image_item.setImage(self._buffer, autoLevels=False)
```
with:
```python
        # Resample the linear FFT spectrum onto the log display grid —
        # a single matrix-vector product against the precomputed matrix.
        display_col = self._resample_matrix @ spectrum_db

        # Scroll the buffer left by one column and place the new column on the right
        self._buffer[:-1] = self._buffer[1:]
        self._buffer[-1] = display_col

        # Update the image. pyqtgraph ImageItem interprets shape (x, y):
        # x = time (horizontal), y = frequency (vertical)
        self._image_item.setImage(self._buffer, autoLevels=False)
```

3g. In `apply_settings`, delete:
```python
        # Blur sigma
        self._blur_sigma = getattr(settings, 'blur_sigma', 1.5)
```
and replace the resize hop line:
```python
        # Scroll buffer resize when display_seconds changes
        hop = self.n_fft // 2
        new_cols = int(settings.display_seconds * (self.sample_rate / hop))
```
with:
```python
        # Scroll buffer resize when display_seconds changes
        new_cols = int(settings.display_seconds * (self.sample_rate / self.hop))
```

- [ ] **Step 4: Run the spectrogram tests**

```bash
pytest tests/test_spectrogram.py tests/test_resampler.py -v
```
Expected: all pass, including the pre-existing `test_add_column_produces_smooth_gradient` (satisfied by W now) — and no `TestGaussianBlur` remains.

- [ ] **Step 5: Commit**

```bash
git add ui/spectrogram.py tests/test_spectrogram.py
git commit -m "feat: render via resampling matrix, drop Gaussian blur, decouple hop"
```

---

### Task 3: Remove the blur setting and its panel control

**Files:**
- Modify: `ui/settings.py` (delete field, lines 40–41)
- Modify: `ui/settings_panel.py` (docstring line 14, section list line 163, `_blur_section` lines 299–310)
- Modify: `tests/test_settings.py` (replace `test_blur_sigma_default`, lines 30–33)
- Modify: `tests/test_settings_panel.py` (replace blur tests, lines 53–67)

- [ ] **Step 1: Update the tests first**

In `tests/test_settings.py`, replace:
```python
    def test_blur_sigma_default(self):
        from ui.settings import AppSettings
        s = AppSettings()
        assert s.blur_sigma == 1.5
```
with:
```python
    def test_no_blur_sigma_field(self):
        """Blur was removed in the Round 1 resolution work — the resampling
        matrix renders crisply without post-hoc smoothing."""
        from ui.settings import AppSettings
        assert not hasattr(AppSettings(), 'blur_sigma')
```

In `tests/test_settings_panel.py`, replace both blur tests (lines 53–67):
```python
    def test_blur_slider_exists(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings())
        assert hasattr(panel, '_blur_sl')

    def test_blur_slider_emits_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        received = []
        panel = SettingsPanel(AppSettings())
        panel.settings_changed.connect(lambda s: received.append(s))
        panel._blur_sl.value_changed.emit(2.0)
        assert len(received) == 1
        assert received[0].blur_sigma == 2.0
```
with:
```python
    def test_no_blur_slider(self, qt_app):
        """The Smoothing section was removed with the blur feature."""
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings())
        assert not hasattr(panel, '_blur_sl')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_settings.py tests/test_settings_panel.py -v
```
Expected: `test_no_blur_sigma_field` and `test_no_blur_slider` FAIL (the field/slider still exist).

- [ ] **Step 3: Remove the setting and the panel section**

In `ui/settings.py`, delete lines 40–41:
```python
    # Blur sigma for spectrogram smoothing (0 = disabled)
    blur_sigma: float = 1.5
```
(Old saved settings.json files containing `blur_sigma` remain loadable: `load()` already filters to known dataclass fields.)

In `ui/settings_panel.py`:
- Delete the docstring line `  Smoothing     — blur sigma slider` (line 14).
- In `_build`, remove `self._blur_section,` from the sections list (line 163).
- Delete the whole `_blur_section` method (lines 299–310).

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_settings.py tests/test_settings_panel.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add ui/settings.py ui/settings_panel.py tests/test_settings.py tests/test_settings_panel.py
git commit -m "refactor: remove blur_sigma setting and Smoothing panel section"
```

---

### Task 4: New analysis defaults in the app (N_FFT 4096, explicit HOP_SIZE 1024)

**Files:**
- Modify: `ui/app.py` (constants lines 23–27, widget construction line 70)

- [ ] **Step 1: Update the constants**

In `ui/app.py`, replace:
```python
SAMPLE_RATE      = 44100
BLOCK_SIZE       = 1024
N_FFT            = 2048
HOP_SIZE         = N_FFT // 2
TIMER_INTERVAL_MS = 16
```
with:
```python
SAMPLE_RATE      = 44100
BLOCK_SIZE       = 1024
N_FFT            = 4096   # ~10.8 Hz bins; window ~93 ms
HOP_SIZE         = 1024   # decoupled from N_FFT: 75% overlap, ~43 columns/s
TIMER_INTERVAL_MS = 16
```

- [ ] **Step 2: Pass the hop to the widget**

Replace:
```python
        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            display_seconds=self._settings.display_seconds,
        )
```
with:
```python
        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            hop=HOP_SIZE,
            display_seconds=self._settings.display_seconds,
        )
```
(No other `_process_audio` change needed: it already windows by `N_FFT` and trims by `HOP_SIZE`.)

- [ ] **Step 3: Run the full suite**

```bash
pytest tests/ -v
```
Expected: all pass (no test imports app-level constants).

- [ ] **Step 4: Commit**

```bash
git add ui/app.py
git commit -m "feat: raise FFT to 4096 with hop held at 1024 (75% overlap)"
```

---

### Task 5: Thread hop through the benchmark harness; run the litmus

**Files:**
- Modify: `tools/benchmark_spectrogram.py` (`run_benchmark` signature ~line 96, hop line ~line 118, widget construction ~line 108, CLI ~line 168)
- Modify: `tests/test_benchmark.py` (add one hop test)

- [ ] **Step 1: Write the failing test**

Add at the bottom of `tests/test_benchmark.py`:

```python
def test_hop_is_configurable_and_sets_column_count():
    """The harness must benchmark the app's real config (n_fft 4096, hop
    1024) — hop halves/doubles the column count for the same audio."""
    dense = run_benchmark(n_fft=4096, hop=1024, duration_s=2.0, render=False)
    sparse = run_benchmark(n_fft=4096, hop=2048, duration_s=2.0, render=False)
    assert dense.n_columns > 1.5 * sparse.n_columns
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/test_benchmark.py::test_hop_is_configurable_and_sets_column_count -v
```
Expected: FAIL — `run_benchmark() got an unexpected keyword argument 'hop'`.

- [ ] **Step 3: Add hop to the harness**

In `tools/benchmark_spectrogram.py`:

3a. Change the `run_benchmark` signature:
```python
def run_benchmark(
    n_fft: int = 2048,
    n_log_bins: int = 2048,
    duration_s: float = 30.0,
    block_size: int = 1024,
    hop: int | None = None,
    render: bool = True,
) -> BenchmarkResult:
```

3b. Resolve the hop as the FIRST lines of the function body (before the `widget = None` block, so the widget construction below can use it):
```python
    if hop is None:
        hop = n_fft // 2
```
Then delete the now-redundant `hop = n_fft // 2` line that currently sits after the widget construction block.

3c. Pass hop to the widget. Replace:
```python
        widget = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            n_log_bins=n_log_bins,
            display_seconds=8.0,
        )
```
with:
```python
        widget = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            n_log_bins=n_log_bins,
            hop=hop,
            display_seconds=8.0,
        )
```

3d. Add the CLI flag in `main()` after the `--block-size` argument:
```python
    parser.add_argument("--hop", type=int, default=None,
                        help="analysis hop in samples (default: n_fft // 2)")
```
and pass it through:
```python
    result = run_benchmark(
        n_fft=args.n_fft,
        n_log_bins=args.bins,
        duration_s=args.duration,
        block_size=args.block_size,
        hop=args.hop,
        render=not args.no_render,
    )
```

- [ ] **Step 4: Run the tests**

```bash
pytest tests/test_benchmark.py -v
```
Expected: all pass.

- [ ] **Step 5: Run the litmus at the new app config and record the numbers**

```bash
python -m tools.benchmark_spectrogram --bins 1024 --n-fft 4096 --hop 1024 --duration 30
```
Expected: prints `fps=…` and `litmus (>=30fps, p95<=120ms): PASS`. **Record the exact output** — it goes in the plan.md update (Task 6) and the PR body. If it FAILs, stop and reassess (fallback per spec: n_fft 3072).

- [ ] **Step 6: Commit**

```bash
git add tools/benchmark_spectrogram.py tests/test_benchmark.py
git commit -m "feat: add --hop to benchmark harness; litmus at 4096/1024 config"
```

---

### Task 6: Full verification, docs, and the human checkpoint

**Files:**
- Modify: `plan.md` (`▶ Next up` section)

- [ ] **Step 1: Full test suite**

```bash
pytest tests/ -v
```
Expected: all pass (~75 tests).

- [ ] **Step 2: Update plan.md `▶ Next up`**

Rewrite item 3 of the `▶ Next up` section (the "Don't optimize a non-problem" item) to reflect Round 1 landing. Replace that item with:

```markdown
3. **Round 1 resolution work landed** (see
   `docs/superpowers/specs/2026-07-09-spectrogram-resolution-design.md`):
   Gaussian blur removed, log-resampling matrix in its place, FFT 2048→4096
   with hop held at 1024. Litmus re-verified at the new config: <paste the
   harness output line here>. **Next decision (Andrew's eyes):** is the
   low-frequency region crisp enough now, or is the Round 2 constant-Q
   rebuild warranted?
```

- [ ] **Step 3: Commit**

```bash
git add plan.md
git commit -m "docs: record Round 1 resolution results in plan.md"
```

- [ ] **Step 4: Human visual checkpoint (Andrew)**

Launch the app from the worktree so Andrew can judge crispness — the whole point of the round:
```bash
cd /Users/andrewtrimble/voice-trainer/.claude/worktrees/spectrogram-resolution
source /Users/andrewtrimble/voice-trainer/venv/bin/activate
python main.py
```
Ask Andrew to sing/sustain low notes (the region the blur used to hide) and judge: crisp or still coarse? Capture his verdict; it decides whether Round 2 (constant-Q) gets planned. **Do not merge before this checkpoint.**

- [ ] **Step 5: Push and open the PR**

```bash
git push -u origin feat/spectrogram-resolution
gh pr create --title "feat: genuinely crisp spectrogram — resampling matrix replaces blur, FFT 4096" --body "<summary of the spec, the litmus numbers from Task 5, and Andrew's visual verdict>"
```
Note: this branch stacks on `feat/benchmark-harness` (PR #15). If #15 has merged, rebase onto main first; otherwise open the PR with base `feat/benchmark-harness`.
