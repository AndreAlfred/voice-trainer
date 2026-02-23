# Voice Trainer Session 5 — Visualization Quality Upgrade Design
*Date: 2026-02-23*

---

## Overview

Upgrade the spectrogram rendering from blocky/banded appearance to smooth, topographic contours. The current display looks like a dense scatter-plot due to nearest-neighbor bin mapping, no smoothing, and coarse display resolution.

---

## Problem

The spectrogram uses 512 log-spaced display bins mapped to FFT bins via nearest-neighbor index lookup:

```python
display_col = spectrum_db[self._freq_indices]
```

In the 80–300 Hz range, the log grid is much finer than the FFT's ~21.5 Hz bin resolution. Dozens of display bins map to the same FFT bin, creating visible horizontal banding. Combined with no temporal/spectral smoothing and sharp per-pixel rendering, the result looks pixelated rather than smooth.

---

## Solution: Interpolation + Gaussian Blur + Higher Bin Count

Three changes, all contained to `ui/spectrogram.py` plus a new settings field:

### 1. Linear Interpolation for Log Mapping

Replace the nearest-neighbor index lookup with `np.interp`:

```python
# Before (nearest-neighbor — causes banding)
display_col = spectrum_db[self._freq_indices]

# After (linear interpolation — smooth gradient)
display_col = np.interp(self._display_freqs, self._fft_freqs, spectrum_db)
```

This linearly blends between adjacent FFT bins for each display frequency. The pre-computed `_freq_indices` array is no longer needed for the main spectrogram column (retained for formant scatter positioning). A new `_fft_freqs` array is stored once at init.

### 2. Gaussian Blur Before Rendering

Apply a light 2D Gaussian blur to the buffer before passing it to `setImage`:

```python
from scipy.ndimage import gaussian_filter
smoothed = gaussian_filter(self._buffer, sigma=(1.0, 1.5))
self._image_item.setImage(smoothed, autoLevels=False)
```

- `sigma=(1.0, 1.5)` — slightly more blur along frequency (1.5) than time (1.0), targeting the axis where banding was worst
- Applied to the full visible buffer each frame — display-only, the raw `_buffer` stays unsmoothed
- Performance: ~0.3ms per frame on a 1024x~344 float32 array (~2% of 16ms frame budget)
- User-controllable: `blur_sigma` field in `AppSettings` (default 1.5), exposed as a slider in the settings panel. Setting to 0 disables blur.

### 3. Increase Display Bins to 1024

Change `N_LOG_BINS` from 512 to 1024. With interpolation providing smooth values, the finer grid resolves continuous gradients instead of repeating the same value across adjacent bins.

Buffer grows from ~1.4 MB to ~2.8 MB — negligible.

---

## Files Changed

| File | Change |
|------|--------|
| `ui/spectrogram.py` | Replace nearest-neighbor with `np.interp`, apply `gaussian_filter` before rendering, increase `N_LOG_BINS` to 1024, store `_fft_freqs` at init |
| `ui/settings.py` | Add `blur_sigma: float = 1.5` field to `AppSettings` |
| `ui/settings_panel.py` | Add Blur Sigma slider to settings panel |
| `ui/spectrogram.py` `apply_settings()` | Read and apply `blur_sigma` from settings |
| `TODO.md` | Add Approach C (higher FFT resolution) to Future Ideas |

No changes to `audio/analysis.py`, `audio/capture.py`, or `ui/app.py`.

---

## Future: Higher FFT Resolution + Overlap (Approach C)

Earmarked for a future session: increase `n_fft` from 2048 to 4096 (frequency resolution ~10.7 Hz) and overlap from 50% to 75% (smoother time axis). Requires audio pipeline changes. Complements this interpolation/blur approach by providing more raw spectral data to interpolate from.

---

## Architecture Notes

- All rendering changes are contained to `spectrogram.py` — no audio analysis pipeline changes
- The raw rolling buffer remains unsmoothed; blur is applied to a copy at render time only
- `_freq_indices` is retained for formant scatter bin positioning (unchanged)
- `scipy.ndimage` is the only new import; scipy is already a transitive dependency
- The `blur_sigma` setting integrates with the existing `AppSettings` / `SettingsPanel` / `apply_settings` pattern established in session 4
