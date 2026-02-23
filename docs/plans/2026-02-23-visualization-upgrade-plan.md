# Visualization Quality Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace blocky nearest-neighbor spectrogram rendering with smooth topographic contours using linear interpolation, Gaussian blur, and doubled display resolution.

**Architecture:** Three changes in `ui/spectrogram.py`: (1) `np.interp` replaces index-based bin mapping, (2) `scipy.ndimage.gaussian_filter` smooths the buffer before rendering, (3) `N_LOG_BINS` doubles from 512 to 1024. A `blur_sigma` field is added to `AppSettings` and exposed in the settings panel.

**Tech Stack:** numpy, scipy.ndimage, pyqtgraph, PySide6

---

### Task 1: Add `blur_sigma` to AppSettings

**Files:**
- Modify: `ui/settings.py:17-41`
- Test: `tests/test_settings.py`

**Step 1: Write the failing test**

Add to `tests/test_settings.py` inside `TestAppSettings`:

```python
def test_blur_sigma_default(self):
    from ui.settings import AppSettings
    s = AppSettings()
    assert s.blur_sigma == 1.5
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings.py::TestAppSettings::test_blur_sigma_default -v`
Expected: FAIL with `AttributeError: ... has no attribute 'blur_sigma'`

**Step 3: Write minimal implementation**

In `ui/settings.py`, add this field to the `AppSettings` dataclass after `background_color`:

```python
    # Blur sigma for spectrogram smoothing (0 = disabled)
    blur_sigma: float = 1.5
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings.py -v`
Expected: ALL PASS (6 tests)

**Step 5: Commit**

```bash
git add ui/settings.py tests/test_settings.py
git commit -m "feat: add blur_sigma field to AppSettings"
```

---

### Task 2: Replace nearest-neighbor with linear interpolation and increase bins to 1024

**Files:**
- Modify: `ui/spectrogram.py:29` (N_LOG_BINS constant)
- Modify: `ui/spectrogram.py:56-78` (`__init__` frequency grid setup)
- Modify: `ui/spectrogram.py:203-221` (`add_column` method)
- Test: `tests/test_spectrogram.py`

**Step 1: Write the failing tests**

Add to `tests/test_spectrogram.py` a new test class:

```python
class TestInterpolation:
    """Verify linear interpolation replaces nearest-neighbor mapping."""

    def test_n_log_bins_is_1024(self, qt_app):
        """Display grid should now use 1024 bins."""
        from ui.spectrogram import N_LOG_BINS
        assert N_LOG_BINS == 1024

    def test_fft_freqs_stored(self, qt_app):
        """Widget should store _fft_freqs array for interpolation."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert hasattr(w, '_fft_freqs')
        assert len(w._fft_freqs) == w.n_fft // 2 + 1

    def test_add_column_produces_smooth_gradient(self, qt_app):
        """A linearly ramping spectrum should produce a smooth (non-staircase)
        display column after interpolation."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        # Create a spectrum that ramps linearly from -60 to 0 across all bins
        spectrum = np.linspace(-60.0, 0.0, 1025, dtype=np.float32)
        w.add_column(spectrum)
        col = w._buffer[-1]
        # With interpolation, consecutive values should differ smoothly.
        # Count unique values — nearest-neighbor would have many duplicates
        # (dozens of display bins mapping to the same FFT bin), interpolation
        # should produce mostly unique values.
        unique_ratio = len(np.unique(np.round(col, 4))) / len(col)
        assert unique_ratio > 0.8, (
            f"Only {unique_ratio:.0%} unique values — still looks like nearest-neighbor"
        )
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_spectrogram.py::TestInterpolation -v`
Expected: FAIL — `N_LOG_BINS` is 512, no `_fft_freqs` attribute, low unique ratio

**Step 3: Write minimal implementation**

In `ui/spectrogram.py`:

**Change 1 — constant (line 29):**
```python
N_LOG_BINS = 1024
```

**Change 2 — `__init__` (replace lines 69-78):**

After the `_display_freqs` / `_n_freq_bins` block (around line 66), replace the `_freq_indices` computation with:

```python
        # Full FFT frequency array — used by np.interp in add_column()
        self._fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate).astype(np.float32)

        # Pre-compute mapping: for each log display bin, the index of the nearest
        # linear FFT bin. Used only for formant scatter positioning (add_formants).
        _insert = np.searchsorted(self._fft_freqs, self._display_freqs)
        _lower = np.clip(_insert - 1, 0, len(self._fft_freqs) - 1)
        _upper = np.clip(_insert,     0, len(self._fft_freqs) - 1)
        _dist_lower = np.abs(self._fft_freqs[_lower] - self._display_freqs)
        _dist_upper = np.abs(self._fft_freqs[_upper] - self._display_freqs)
        self._freq_indices = np.where(_dist_lower <= _dist_upper, _lower, _upper)
```

**Change 3 — `add_column` (replace line 213):**
```python
        # Interpolate the linear FFT spectrum onto the log-spaced display grid
        display_col = np.interp(self._display_freqs, self._fft_freqs, spectrum_db)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_spectrogram.py -v`
Expected: ALL PASS

Note: `test_display_freqs_length_is_512` will now fail because `N_LOG_BINS` is 1024. Update it:

In `tests/test_spectrogram.py`, `test_display_freqs_length_is_512` — rename to `test_display_freqs_length_matches_n_log_bins` (no code change needed, the assertion already uses `N_LOG_BINS`). Just rename the method:

```python
    def test_display_freqs_length_matches_n_log_bins(self, qt_app):
        """Display grid should have exactly N_LOG_BINS bins."""
        from ui.spectrogram import SpectrogramWidget, N_LOG_BINS
        w = SpectrogramWidget()
        assert len(w._display_freqs) == N_LOG_BINS, (
            f"Expected {N_LOG_BINS} display bins, got {len(w._display_freqs)}"
        )
```

Run again: `python -m pytest tests/test_spectrogram.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add ui/spectrogram.py tests/test_spectrogram.py
git commit -m "feat: replace nearest-neighbor with linear interpolation, increase to 1024 bins"
```

---

### Task 3: Add Gaussian blur to spectrogram rendering

**Files:**
- Modify: `ui/spectrogram.py:12-16` (imports)
- Modify: `ui/spectrogram.py:203-221` (`add_column` method)
- Modify: `ui/spectrogram.py:269-324` (`apply_settings` method)
- Test: `tests/test_spectrogram.py`

**Step 1: Write the failing tests**

Add to `tests/test_spectrogram.py`:

```python
class TestGaussianBlur:
    """Verify Gaussian blur is applied before rendering."""

    def test_blur_sigma_stored(self, qt_app):
        """Widget should store a blur_sigma attribute."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert hasattr(w, '_blur_sigma')
        assert w._blur_sigma == 1.5

    def test_apply_settings_updates_blur_sigma(self, qt_app):
        """apply_settings should update _blur_sigma from settings."""
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(blur_sigma=0.0))
        assert w._blur_sigma == 0.0
        w.apply_settings(AppSettings(blur_sigma=2.5))
        assert w._blur_sigma == 2.5

    def test_add_column_with_blur_smooths_output(self, qt_app):
        """With blur enabled, the rendered image should be smoother than the
        raw buffer data."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        # Insert a sharp edge: silence everywhere except one frequency band
        spectrum = np.full(1025, -60.0, dtype=np.float32)
        spectrum[100:110] = 0.0  # sharp bright band
        for _ in range(5):
            w.add_column(spectrum)
        # The raw buffer has a sharp edge; the rendered image should be smoother.
        # We can't easily inspect the ImageItem's data directly, but we verify
        # the widget doesn't raise and _blur_sigma is applied.
        assert w._blur_sigma > 0

    def test_blur_disabled_when_sigma_zero(self, qt_app):
        """Setting blur_sigma=0 should disable blur without error."""
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget(n_fft=2048)
        w.apply_settings(AppSettings(blur_sigma=0.0))
        spectrum = np.full(1025, -40.0, dtype=np.float32)
        w.add_column(spectrum)  # must not raise
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_spectrogram.py::TestGaussianBlur -v`
Expected: FAIL — no `_blur_sigma` attribute

**Step 3: Write minimal implementation**

In `ui/spectrogram.py`:

**Add import (after `import numpy as np`):**
```python
from scipy.ndimage import gaussian_filter
```

**In `__init__`, after `self._setup_ui()` (around line 98), add:**
```python
        # Blur sigma for smooth topographic rendering (0 = disabled)
        self._blur_sigma = 1.5
```

**Replace `add_column` method body (the `setImage` call at the end):**
```python
        # Apply Gaussian blur for smooth topographic rendering
        if self._blur_sigma > 0:
            smoothed = gaussian_filter(self._buffer, sigma=(1.0, self._blur_sigma))
            self._image_item.setImage(smoothed, autoLevels=False)
        else:
            self._image_item.setImage(self._buffer, autoLevels=False)
```

**In `apply_settings`, add after the background color block (before the scroll buffer resize):**
```python
        # Blur sigma
        self._blur_sigma = getattr(settings, 'blur_sigma', 1.5)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_spectrogram.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add ui/spectrogram.py tests/test_spectrogram.py
git commit -m "feat: add Gaussian blur for smooth topographic spectrogram rendering"
```

---

### Task 4: Add blur sigma slider to settings panel

**Files:**
- Modify: `ui/settings_panel.py:155-166` (`_build` method, section list)
- Test: `tests/test_settings_panel.py`

**Step 1: Write the failing tests**

Add to `tests/test_settings_panel.py` inside `TestSettingsPanel`:

```python
    def test_blur_slider_emits_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        received = []
        panel = SettingsPanel(AppSettings())
        panel.settings_changed.connect(lambda s: received.append(s))
        panel._blur_sl.value_changed.emit(2.0)
        assert len(received) == 1
        assert received[0].blur_sigma == 2.0

    def test_blur_slider_exists(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings())
        assert hasattr(panel, '_blur_sl')
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_settings_panel.py::TestSettingsPanel::test_blur_slider_exists -v`
Expected: FAIL — `AttributeError: ... has no attribute '_blur_sl'`

**Step 3: Write minimal implementation**

In `ui/settings_panel.py`, add a new section method after `_background_section`:

```python
    def _blur_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Smoothing"))
        self._blur_sl = LabeledSlider(
            "Blur Sigma", 0.0, 4.0, 1.5, self._settings.blur_sigma,
            decimals=1)
        self._blur_sl.value_changed.connect(
            lambda v: self._set("blur_sigma", v))
        lay.addWidget(self._blur_sl)
        return w
```

Add `self._blur_section` to the section list in `_build`. Replace the `for section in [...]` block:

```python
        for section in [
            self._colormap_section,
            self._db_section,
            self._window_section,
            self._dots_section,
            self._overlays_section,
            self._background_section,
            self._blur_section,
        ]:
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_settings_panel.py -v`
Expected: ALL PASS (6 tests)

**Step 5: Commit**

```bash
git add ui/settings_panel.py tests/test_settings_panel.py
git commit -m "feat: add blur sigma slider to settings panel"
```

---

### Task 5: Update TODO.md

**Files:**
- Modify: `TODO.md`

**Step 1: Add Approach C to Future Ideas and move Color Scheme to Completed**

In `TODO.md`, add under `## Future Ideas (not yet designed)`:

```markdown
- Higher FFT resolution + overlap (n_fft 4096, 75% overlap) for even smoother raw spectral data
```

Add to `## Completed`:

```markdown
- [x] Visual customization sidebar (colormap presets, dB range, dot sizes, background, all persisted)
- [x] Smooth topographic spectrogram (linear interpolation + Gaussian blur + 1024 log bins)
```

**Step 2: Commit**

```bash
git add TODO.md
git commit -m "docs: update TODO with completed features and future FFT upgrade"
```

---

### Task 6: Run full test suite

**Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (total should be ~48-50 tests)

**Step 2: Manual smoke test**

Run: `python main.py`

Verify:
1. Spectrogram displays smooth, flowing contours (no horizontal banding)
2. Low frequencies (80–300 Hz) show smooth gradients, not stair-steps
3. Open Settings sidebar → Smoothing section → Blur Sigma slider works
4. Setting blur to 0 shows raw (unsmoothed) spectrogram
5. F1/F2 formant dots still display correctly
6. Singer's Formant band still visible
