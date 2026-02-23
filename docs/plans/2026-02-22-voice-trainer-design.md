# Voice Trainer — Design Document
*Date: 2026-02-22*

---

## Overview

A desktop application for classical singing voice training that provides real-time acoustic analysis via a scrolling spectrogram and pitch display. Modeled conceptually after professional voice-analysis software, but built in Python and designed to grow incrementally.

**Target user:** Classical singers of any level who want visual feedback on their voice in real time.

**Platform:** macOS (Apple Silicon / Intel)

**Launch method:** `python main.py` from the Terminal (first version); packaging as a `.app` bundle is a future consideration.

---

## Tech Stack

| Component | Library | Reason |
|-----------|---------|--------|
| GUI framework | PySide6 | Official Qt for Python, LGPL licensed, native Mac look, scales well |
| Real-time plotting | pyqtgraph | Purpose-built for fast scientific data display, far faster than matplotlib for live audio |
| Microphone capture | sounddevice | Clean Python API, cross-platform, built on PortAudio |
| Audio analysis | librosa | Industry-standard; `pyin` pitch algorithm handles vibrato and the singing voice well |
| Numerics | numpy / scipy | Standard scientific Python; librosa depends on both |

**Python version:** 3.14.x (installed via Homebrew). A virtual environment (`venv`) will isolate dependencies.

---

## Project Structure

```
~/voice-trainer/
├── main.py              ← Entry point — run this to launch the app
├── requirements.txt     ← All dependencies, pinned for reproducibility
├── README.md            ← Setup and usage instructions
├── docs/
│   └── plans/
│       └── 2026-02-22-voice-trainer-design.md   ← this file
├── audio/
│   ├── __init__.py      ← Makes 'audio' importable as a package
│   ├── capture.py       ← Background thread: microphone → audio queue
│   └── analysis.py      ← STFT spectrogram + pyin pitch detection
└── ui/
    ├── __init__.py
    ├── app.py           ← Main QMainWindow, QTimer, layout
    ├── spectrogram.py   ← Scrolling spectrogram widget (pyqtgraph ImageItem)
    └── pitch_display.py ← Real-time Hz + note name readout widget
```

The `audio/` package handles everything the computer hears.
The `ui/` package handles everything the user sees.
`main.py` wires them together and starts the Qt event loop.

---

## Data Flow

```
Microphone hardware
    │
    ▼
capture.py  [background thread]
    • sounddevice.InputStream callback fires every ~23 ms
    • Appends raw audio chunks (numpy arrays) to a thread-safe queue.Queue
    │
    ▼
analysis.py  [called by Qt timer in main thread, ~60 Hz]
    • Drains queue, accumulates samples into an analysis buffer
    • When buffer has ≥ 2048 samples:
        – STFT → magnitude spectrum → one new spectrogram column
        – pyin pitch estimation → fundamental frequency F0 (Hz) or None
    │
    ├──▶ spectrogram.py   — appends column to rolling display buffer, redraws
    └──▶ pitch_display.py — converts F0 to note name, updates labels
```

**Audio settings:**

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| Sample rate | 44,100 Hz | Standard; covers full audio spectrum |
| Analysis window | 2,048 samples (~46 ms) | Good frequency resolution for voice |
| Window overlap | 50% (1,024 hop) | Smooth time resolution without excess CPU |
| Frequency display range | 80 Hz – 8,000 Hz | Covers full classical voice + audible harmonics |
| Default visible time | ~8 seconds | Enough to see a phrase; user-adjustable later |

**Thread safety:** All audio data crosses the thread boundary via `queue.Queue`. The UI thread never blocks on audio; the audio thread never touches Qt objects.

---

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   SCROLLING SPECTROGRAM                                 │
│   ← time scrolls leftward as you sing                  │
│                                                         │
│   Y-axis: 80 Hz (bottom) to 8,000 Hz (top), log scale  │
│   Color:  dark=quiet  →  bright=loud  (magma colormap)  │
│                                                         │
│   [bright horizontal bands = harmonics of your voice]   │
│   [closely-spaced bands = richer, more resonant tone]   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  PITCH READOUT                                          │
│  Fundamental: 293 Hz          Note: D4                  │
│  (updates in real time — blank when no pitch detected)  │
└─────────────────────────────────────────────────────────┘
```

**Visual style:** Dark background (#1a1a2e), magma colormap for spectrogram. Readable at a glance during a singing lesson.

**Note name conversion:**
```
MIDI number = round(69 + 12 × log₂(F0 / 440))
Note name   = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"][MIDI % 12]
Octave      = (MIDI // 12) - 1
Display     = f"{note_name}{octave}  —  {F0:.0f} Hz"
```

---

## Phase 1 Scope (What We Build Now)

- [ ] Project scaffolding: folder structure, `requirements.txt`, `README.md`, `venv`
- [ ] `capture.py`: microphone capture thread
- [ ] `analysis.py`: STFT spectrogram column + pyin pitch estimation
- [ ] `spectrogram.py`: scrolling spectrogram widget
- [ ] `pitch_display.py`: Hz + note name readout
- [ ] `app.py` + `main.py`: wire everything together, launch window

**Success criterion:** Sing into the microphone and see a live scrolling spectrogram with harmonic structure visible, and a pitch readout that correctly names the note being sung.

---

## Future Features (Not Built Now)

These are listed here so the Phase 1 architecture doesn't accidentally block them.

### Time Scale Zoom
The user wants to switch between seeing several minutes of singing spread across the graph ("bird's eye") and a zoomed-in granular view (individual vibrato cycles visible).

**Architecture note:** Store a rolling buffer of pre-computed spectrogram columns (not just the display window). The display widget always reads a configurable time-slice from this buffer. Zoom = change slice width. This is already how the buffer is designed in Phase 1.

### Singer's Formant Visualization
Highlight the 2,000–3,500 Hz region with a subtle tinted band on the spectrogram. The "singer's formant cluster" is what gives the classical voice its carrying power over an orchestra. A bright region here visually confirms good forward resonance.

### Vibrato Rate and Extent
Track F0 values over a rolling ~3-second window. Apply a short FFT to the pitch contour to detect oscillation rate (target: 5–7 Hz for classical vibrato). Display rate in Hz and extent in semitones.

### Vowel Formant (F1/F2) Overlay
Use LPC (Linear Predictive Coding, available in scipy) to estimate the first two formant frequencies. Plot them as moving dots over the spectrogram. Useful for understanding vowel placement and registration shifts.

### Vowel Modification Recommendations
*Classical singing pedagogy feature.*

As a singer ascends in pitch, the vocal tract must adjust vowel shape to maintain resonance and avoid registration breaks (the "passaggio"). This feature would detect the current pitch, voice type, and inferred vowel (from F1/F2 analysis), then display a real-time recommendation.

**Voice types and passaggio zones (approximate):**

| Voice type | First passaggio | Second passaggio |
|------------|----------------|------------------|
| Bass | Eb3–E3 | Eb4–E4 |
| Baritone | Ab3–A3 | Ab4–A4 |
| Tenor | Eb4–E4 | Eb5–E5 |
| Contralto | Eb3–E3 | Eb4–E4 |
| Mezzo-soprano | Ab3–A3 | Ab4–A4 |
| Soprano | Eb4–E4 | Eb5–E5 |

**Example recommendations:**
- "Approaching upper passaggio — modify [a] toward [ɔ] (rounder /aw/)"
- "In the upper passaggio — [i] should be slightly less spread, aim for [ɪ]"
- "Above the second passaggio — allow full cover; all vowels toward [o]/[u]"

**Implementation approach:**
1. User selects voice type on first launch (stored in a config file)
2. F0 is checked against passaggio ranges for that voice type
3. F1/F2 estimates suggest which vowel family is being sung
4. A recommendation string is displayed below the pitch readout
5. Recommendations update no faster than ~2 Hz to avoid being distracting

*Requires the F1/F2 vowel overlay feature as a prerequisite.*

### Session Recording and Review
Record microphone audio + synchronized spectrogram data. Replay session with the same visual display. Store sessions as timestamped files.

### Comparison Overlays
Load a previous session or a reference recording. Display its spectrogram data as a semi-transparent overlay so the singer can compare phrasing, resonance, and vibrato side-by-side.

---

## Architecture Constraints Carried Forward

1. **Audio and UI are always on separate threads** — Qt timer polls a queue; audio thread never touches widgets.
2. **Rolling buffer is the source of truth** — the display window is always a view into the buffer, enabling time zoom without re-architecture.
3. **Voice type is a user setting**, not inferred, to keep analysis simple and reliable.
4. **All analysis is offline-compatible** — no internet connection required. All models and algorithms run locally.
