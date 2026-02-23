# Voice Trainer Session 4 — Customization Sidebar & IPA Vowel Display Design
*Date: 2026-02-23*

---

## Overview

Two features:

1. **Visual Customization Sidebar** — a collapsible `QDockWidget` on the right side of the window giving live, persistent control over all visual settings
2. **IPA Vowel Display** — real-time identification of the vowel being sung, shown as an IPA symbol derived from live F1/F2 formant positions

---

## Feature 1: Visual Customization Sidebar

### Goal

Allow the user to tune every visual parameter of the app in real time, with changes auto-saved to `~/.voicetrainer/settings.json` so they persist across sessions.

### Architecture

**New file: `ui/settings.py`**

`AppSettings` dataclass holding all customizable values. Provides `load()` (reads `~/.voicetrainer/settings.json`, falls back to defaults silently if missing or corrupt) and `save()` (writes JSON atomically). This is the single source of truth — no settings values are stored anywhere else.

```python
@dataclass
class AppSettings:
    # Colormap — three RGB tuples for the three stops
    color_floor: tuple = (13, 79, 82)       # dark teal  #0d4f52
    color_mid:   tuple = (212, 80, 10)      # warm orange #d4500a
    color_peak:  tuple = (255, 240, 160)    # pale yellow #fff0a0

    # dB display range
    db_floor:   float = -60.0   # DISPLAY_DB_MIN
    db_ceiling: float =   0.0   # DISPLAY_DB_MAX

    # Scrolling window duration
    display_seconds: float = 8.0

    # F1/F2 formant dot appearance
    f1_color: tuple = (100, 180, 255)   # light blue
    f2_color: tuple = (80, 240, 120)    # bright green
    dot_size:   int = 4

    # Overlays
    singers_formant_visible: bool = True

    # Window background
    background_color: tuple = (26, 26, 46)  # #1a1a2e
```

**New file: `ui/settings_panel.py`**

`SettingsPanel(QWidget)` — all controls, organized into labelled sections. Every control emits a `settings_changed` signal (carrying the updated `AppSettings`) whenever the user adjusts anything. No "Apply" button — changes are live.

Sections:
- **Colormap** — 4 preset buttons, then 3 color picker buttons (Floor / Mid / Peak)
- **Display Range** — dB Floor slider, dB Ceiling slider
- **Scroll Window** — Display Seconds slider
- **Formant Dots** — F1 color, F2 color, Dot Size slider
- **Overlays** — Singer's Formant Band checkbox
- **Background** — Background Color button

Each numerical slider has a permanently visible grey label beneath it showing the factory default (e.g. `default: -60 dB`, `default: 8 s`, `default: 4 px`). These are static `QLabel` widgets — always visible, not tooltips.

**Modified: `ui/app.py`**

- Loads `AppSettings` on startup via `AppSettings.load()`
- Wraps `SettingsPanel` in a `QDockWidget` (right side, initially hidden)
- Adds a ⚙ toolbar button that toggles the dock visible/hidden
- Connects `settings_changed` signal → `_on_settings_changed()` slot that applies updates live and auto-saves

**Modified: `ui/spectrogram.py`**

Adds `apply_settings(settings: AppSettings)` method that updates in place:
- Colormap (rebuilds `pg.ColorMap` and calls `setColorMap`)
- dB levels (`setLevels`)
- F1/F2 dot colors and sizes
- Singer's Formant band visibility
- Background color (`pg.setConfigOption` + widget stylesheet)
- `display_seconds` — reinitializes the scroll buffer to the new column count (allocates new array, copies as much history as fits, swaps in place — no restart needed)

### Colormap Presets

Four preset buttons at the top of the Colormap section. Clicking one sets all three color stops at once:

| Button | Floor | Mid | Peak | Character |
|--------|-------|-----|------|-----------|
| **Voice** (default) | `#0d4f52` dark teal | `#d4500a` warm orange | `#fff0a0` pale yellow | Current default |
| **Magma** | `#0d0221` near-black | `#a62e00` deep red | `#fdf6b2` pale gold | Classic spectrogram |
| **Ocean** | `#050a2e` deep navy | `#0066ff` electric blue | `#ffffff` white | High contrast |
| **Ember** | `#1a0500` dark brown | `#c0392b` crimson | `#ffb347` bright amber | Warm, dramatic |

### Data Flow

```
User adjusts control
  → SettingsPanel emits settings_changed(AppSettings)
  → MainWindow._on_settings_changed(settings)
      → settings.save()                         # persist to disk
      → spectrogram.apply_settings(settings)    # live update
      → update window stylesheet for background
```

### Files

- Create: `ui/settings.py`
- Create: `ui/settings_panel.py`
- Modify: `ui/app.py`
- Modify: `ui/spectrogram.py`

---

## Feature 2: IPA Vowel Display

### Goal

Identify the vowel being sung in real time from live F1/F2 formant positions and display its IPA symbol in the pitch readout strip.

### Architecture

**Modified: `audio/analysis.py`**

New function `estimate_vowel(f1_hz, f2_hz)`:

- Looks up the nearest vowel in the Hillenbrand et al. (1995) reference table using normalized Euclidean distance in F1/F2 space
- Normalization: divide F1 by 900 and F2 by 3200 (their approximate max values) before computing distance — this gives both dimensions equal weight despite F2 spanning ~4× the Hz range of F1
- Returns `(ipa_symbol, keyword, confidence)` where confidence is `1 / (1 + distance)` normalized to [0, 1]
- Returns `(None, None, 0.0)` when either formant is None

**Vowel reference table** (Hillenbrand et al. 1995, male speaker averages):

| IPA | Keyword | F1 (Hz) | F2 (Hz) |
|-----|---------|---------|---------|
| /i/ | heed    | 342     | 2322    |
| /ɪ/ | hid     | 427     | 2034    |
| /e/ | hayed   | 476     | 2089    |
| /ɛ/ | head    | 580     | 1799    |
| /æ/ | had     | 588     | 1952    |
| /ɑ/ | hot     | 768     | 1333    |
| /ɔ/ | hawed   | 652     | 997     |
| /o/ | hoed    | 497     | 910     |
| /ʊ/ | hood    | 469     | 1122    |
| /u/ | who'd   | 378     | 997     |
| /ʌ/ | hud     | 623     | 1200    |

**Confidence gating**

The IPA symbol is only rendered when:
1. Both F1 and F2 are detected (not None)
2. Confidence score ≥ 0.35 (rejects ambiguous / out-of-range positions)
3. The same vowel has been returned for ≥ 3 consecutive frames (prevents single-frame flicker)

When gating fails, the symbol area shows `—`.

**Modified: `ui/pitch_display.py`**

Adds a right-aligned IPA section to the existing display strip:
- Large IPA symbol (e.g. `/ɑ/`) in a prominent font
- Small keyword label beneath it (e.g. `hot`)
- Greyed out `—` when no vowel detected

**Modified: `ui/app.py`**

Adds `estimate_vowel` to the existing import from `audio.analysis` and calls it in `_process_audio()` after `estimate_formants()`, passing the result to `pitch_display.update_vowel(ipa, keyword)`.

### Data Flow

```
Audio window
  → estimate_formants()  → (f1_hz, f2_hz)
  → estimate_vowel(f1, f2) → (ipa, keyword, confidence)
  → PitchDisplayWidget.update_vowel(ipa, keyword)
      → 3-frame stability check
      → render symbol or '—'
```

### Files

- Modify: `audio/analysis.py` — add `estimate_vowel()`
- Modify: `ui/pitch_display.py` — add IPA display section
- Modify: `ui/app.py` — call `estimate_vowel()`, pass to display

---

## Architecture Notes

- `AppSettings` is the only place where default values live — `spectrogram.py` constants (`DISPLAY_DB_MIN`, etc.) become initial values for the dataclass, not authoritative sources
- The 3-frame stability buffer in `PitchDisplayWidget` is a simple `collections.deque(maxlen=3)` — no new state in the audio path
- Both features are purely additive — no existing analysis logic changes
- `estimate_vowel` is a pure function (no side effects) and is straightforward to unit test with known F1/F2 pairs
