# Voice Trainer Session 2 — Design Document
*Date: 2026-02-22*

---

## Overview

Three improvements to the Phase 1 voice trainer app:

1. **Contrast fix** — spectrogram is hard to read; quiet sounds look near-black
2. **Singer's formant band** — visual highlight of the 2,000–3,500 Hz carrying-power zone
3. **F1/F2 vowel formant overlay** — rolling dots showing vowel formant history in real time

---

## Feature 1: Contrast Fix

### Problem
`DISPLAY_DB_MIN = -70.0` spreads the colormap over a 70 dB range. Real vocal sounds in a room typically sit between -50 and 0 dB, so quiet-but-audible sounds map to near-black — effectively invisible.

### Solution

**Two simultaneous changes to `ui/spectrogram.py`:**

**A. Raise the noise floor**
```python
DISPLAY_DB_MIN = -45.0  # was -70.0
```
The colormap now spans -45 to 0 dB — a range that actually contains real voice signal. Sounds that were near-invisible dark purple will now appear as visible teal/orange.

**B. Custom colormap**

Replace the built-in `magma` with a 3-stop gradient using `pg.ColorMap`:

| dB level | Color | Hex | Purpose |
|----------|-------|-----|---------|
| -45 dB (floor) | Dark teal | `#0d4f52` | Silence / very quiet — a real color, never pure black |
| -22 dB (mid) | Warm orange | `#d4500a` | Moderate energy — harmonics at medium intensity |
| 0 dB (top) | Pale yellow | `#fff0a0` | Loud / strong harmonics |

```python
import numpy as np
colormap = pg.ColorMap(
    pos=np.array([0.0, 0.5, 1.0]),
    color=np.array([
        [13,  79,  82, 255],   # dark teal
        [212, 80,  10, 255],   # warm orange
        [255, 240, 160, 255],  # pale yellow
    ], dtype=np.uint8)
)
```

**Files changed:** `ui/spectrogram.py` only (constants + colormap construction).

---

## Feature 2: Singer's Formant Band

### Purpose
The "singer's formant cluster" — harmonics in the 2,000–3,500 Hz region — is what gives the classical voice its carrying power over an orchestra. A persistent highlight band on the spectrogram gives the singer instant visual feedback: bright energy in this zone = good forward resonance.

### Implementation

Add a `LinearRegionItem` to the spectrogram plot in `_setup_ui()`:

```python
# Convert Hz bounds to freq bin indices
f_lo = int(np.searchsorted(self._display_freqs, 2000.0))
f_hi = int(np.searchsorted(self._display_freqs, 3500.0))

self._singers_formant_region = pg.LinearRegionItem(
    values=[f_lo, f_hi],
    orientation='horizontal',
    movable=False,
    brush=pg.mkBrush(255, 215, 0, 22),   # semi-transparent gold, very faint
    pen=pg.mkPen(255, 215, 0, 60),        # slightly more visible gold border
)
self._plot.addItem(self._singers_formant_region)
```

A small text label "Singer's Formant" is added to the left axis using a `pg.InfLineLabel` or a `TextItem` anchored to the upper-left of the region.

**Files changed:** `ui/spectrogram.py` only (`_setup_ui()`).

---

## Feature 3: F1/F2 Vowel Formant Overlay

### Purpose
F1 (first formant, ~200–900 Hz) correlates with vowel openness (jaw height). F2 (second formant, ~700–3,200 Hz) correlates with tongue front/back position. Seeing these as scrolling dots on the spectrogram lets a singer visually track vowel placement across a phrase.

### Analysis: `estimate_formants()` in `audio/analysis.py`

Uses **LPC (Linear Predictive Coding)** — the standard technique in speech science for formant estimation:

```
Samples
  → pre-emphasis filter (boosts high frequencies for clearer resonances)
  → scipy.signal.lpc(order=14)       ← LPC order 14 is standard for voice
  → np.roots(lpc_coefficients)       ← poles of the vocal tract model
  → convert angles to Hz: freq = angle × sr / (2π)
  → filter: keep poles with positive imaginary part, close to unit circle
  → sort by frequency, apply range gates:
      F1: 200–900 Hz
      F2: 700–3,200 Hz
  → return (f1_hz, f2_hz) or None per formant
```

Requires `scipy.signal.lpc` (available in scipy ≥ 1.9; user has 1.17.1 ✓).

**Function signature:**
```python
def estimate_formants(
    samples: np.ndarray,
    sample_rate: int = 44100,
    order: int = 14,
) -> tuple[float | None, float | None]:
    """Return (F1, F2) in Hz, or (None, None) if not detectable."""
```

**Tests (TDD):**
1. Pure tone — no formants, returns None
2. Silence — returns None
3. A known LPC response — F1 in expected range 200–900 Hz
4. Doesn't crash on noise (any output in valid range or None)

### Display: Rolling scatter overlay in `ui/spectrogram.py`

Two parallel rolling position buffers — same length as `_n_time_cols` — storing the frequency bin index of F1/F2 at each time step. `None` = no detection at that step (dot not drawn).

```python
self._f1_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)
self._f2_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)

self._f1_scatter = pg.ScatterPlotItem(size=4, pen=None,
    brush=pg.mkBrush(100, 180, 255, 200))   # light blue
self._f2_scatter = pg.ScatterPlotItem(size=4, pen=None,
    brush=pg.mkBrush(80, 240, 120, 200))    # bright green
self._plot.addItem(self._f1_scatter)
self._plot.addItem(self._f2_scatter)
```

New method `add_formants(f1_hz, f2_hz)` on `SpectrogramWidget`:
- Converts Hz to bin index via `np.searchsorted(self._display_freqs, hz)`
- Scrolls `_f1_bins` and `_f2_bins` left, appends new value on right
- Rebuilds x/y arrays (filtering NaN) and calls `setData()` on each ScatterPlotItem

### Data flow addition in `ui/app.py`

```python
# Inside _process_audio(), after existing analysis:
f1_hz, f2_hz = estimate_formants(window, SAMPLE_RATE)
self._spectrogram.add_formants(f1_hz, f2_hz)
```

Import added: `from audio.analysis import compute_spectrogram_column, estimate_pitch, estimate_formants`

**Files changed:**
- `audio/analysis.py` — add `estimate_formants()`
- `ui/spectrogram.py` — add scatter items, `add_formants()` method
- `ui/app.py` — call `estimate_formants()`, pass to widget

---

## Visual Result

```
┌──────────────────────────────────────────────────────────────┐
│  SCROLLING SPECTROGRAM                                        │
│                                                               │
│  8k Hz ┤                                                      │
│  5k Hz ┤                                                      │
│  3k Hz ┤────── ░ Singer's Formant (gold band) ──────────     │
│  2k Hz ┤─────── (band bottom) ──────────────────────────     │
│  1k Hz ┤      ●●●●●●●●●●●●●●● F2 (green dots)               │
│  500Hz ┤  ●●●●●●●●●●●●●●●●●● F1 (blue dots)                 │
│  100Hz ┤                                                      │
│        └──────────────────────────────────────── time →      │
├──────────────────────────────────────────────────────────────┤
│  A4  —  440.0 Hz                                             │
└──────────────────────────────────────────────────────────────┘
```

Colors: Teal (quiet) → Orange (medium) → Pale yellow (loud). Gold band = singer's formant zone. Blue dots = F1. Green dots = F2.

---

## Architecture Notes

- All three changes are additive — nothing is removed or restructured from Phase 1
- F1/F2 buffer uses `np.nan` for "no detection" so scatter rendering can skip those columns efficiently
- LPC order 14 is a safe default; higher order = more formants detected but more CPU
- The rolling buffer design from Phase 1 (F1/F2 arrays parallel to spectrogram buffer) naturally supports the planned time-scale zoom future feature
