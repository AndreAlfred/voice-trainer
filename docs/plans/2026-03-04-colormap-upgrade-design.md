# Voice Trainer — Colormap Upgrade Design
*Date: 2026-03-04*

---

## Overview

Replace the 3-stop custom colormap system with matplotlib's perceptually uniform colormaps, sampled at 256 points. This gives 6-8 perceptible color zones across the -60 to 0 dB dynamic range, creating a topographic map feel with smooth transitions and clear visual reference points between dynamic levels.

---

## Problem

The current colormap uses 3 stops (floor/mid/peak) with linear interpolation between them. This produces only two color gradients across the entire 60 dB range — not enough visual granularity to distinguish subtle dynamic differences. The result feels "distilled" compared to topographic maps which use 6-8+ distinct hue shifts.

---

## Solution: Matplotlib Colormap Presets

### Settings Model

**Remove** from `AppSettings`:
- `color_floor: tuple`
- `color_mid: tuple`
- `color_peak: tuple`

**Add** to `AppSettings`:
- `colormap_name: str = "inferno"`

### Colormap Sampling

Sample the named matplotlib colormap at 256 evenly-spaced points and convert to a pyqtgraph `ColorMap`:

```python
import matplotlib.cm as cm

mpl_cmap = cm.get_cmap(colormap_name)
positions = np.linspace(0.0, 1.0, 256)
colors = (mpl_cmap(positions) * 255).astype(np.uint8)
colormap = pg.ColorMap(pos=positions, color=colors)
```

Only `matplotlib.cm` is imported — no pyplot, no figure rendering, no GUI backend.

### Preset Buttons

Four presets chosen for voice analysis:

| Button | Colormap | Character |
|--------|----------|-----------|
| **Inferno** (default) | `inferno` | Black -> purple -> red -> orange -> yellow. Perceptually uniform, great dynamic range. |
| **Viridis** | `viridis` | Dark purple -> teal -> green -> yellow. Colorblind-safe, smooth transitions. |
| **Magma** | `magma` | Black -> purple -> pink -> pale gold. Warm, dramatic. |
| **Terrain** | `gist_earth` | Dark blue -> green -> brown -> white. Literal topographic map feel. |

### Settings Panel Changes

The Colormap section simplifies:

**Removed:**
- 3 ColorButton widgets (Floor, Mid, Peak)
- `_apply_preset()` method that set 3 colors

**Replaced with:**
- 4 preset buttons: Inferno, Viridis, Magma, Terrain
- Clicking a button sets `colormap_name` and emits `settings_changed`
- Active preset button gets a subtle highlight border

All other panel sections unchanged (dB range, scroll window, formant dots, overlays, background, smoothing).

---

## Files Changed

| File | Change |
|------|--------|
| `ui/settings.py` | Remove `color_floor`, `color_mid`, `color_peak`. Add `colormap_name: str = "inferno"`. |
| `ui/settings_panel.py` | Remove color pickers. Replace presets with matplotlib names. Add active highlight. |
| `ui/spectrogram.py` `_setup_ui` | Build colormap by sampling matplotlib. |
| `ui/spectrogram.py` `apply_settings` | Read `colormap_name`, sample matplotlib, set colormap. |
| `requirements.txt` | Add `matplotlib`. |
| `tests/test_settings.py` | Update defaults test. |
| `tests/test_settings_panel.py` | Update preset test. |
| `tests/test_spectrogram.py` | Update apply_settings tests. |

No changes to: `audio/analysis.py`, `audio/capture.py`, `ui/app.py`, `ui/pitch_display.py`.

---

## Architecture Notes

- `matplotlib.cm` is the only matplotlib submodule imported — lightweight, no GUI backend needed
- 256 sample points is standard for colormap LUTs — matches what pyqtgraph interpolates internally
- The `colormap_name` string is validated against matplotlib's registry; invalid names fall back to "inferno"
- Perceptually uniform colormaps (inferno, viridis, magma) ensure equal dB differences produce equal perceived color differences — important for reading dynamics accurately
