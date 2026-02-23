# Voice Trainer Session 3 — Display & Packaging Design
*Date: 2026-02-23*

---

## Overview

Two improvements to the voice trainer app:

1. **Logarithmic frequency scale** — redistribute the spectrogram y-axis so the F0/F1/F2 voice range (80–1,400 Hz) occupies ~62% of the display height instead of the current ~17%
2. **macOS .app bundle** — package the app with PyInstaller so it launches like a native Mac app with no terminal required

---

## Feature 1: Logarithmic Frequency Scale

### Problem

The spectrogram currently uses a linear frequency scale from 80–8,000 Hz. Every FFT bin gets equal pixel height. This means:

- 80–1,400 Hz (F0 fundamental, F1, F2, Singer's Formant) = ~17% of display height
- 1,400–8,000 Hz (upper harmonics, breath noise) = ~83% of display height

Most of the visible voice signal is crammed into the bottom fifth of the screen.

### Solution

Replace the linear bin mapping with a **512-bin logarithmic frequency grid** spanning 80–8,000 Hz. Each octave gets equal vertical space regardless of where it falls in the spectrum.

**Result:** 80–1,400 Hz occupies ~62% of the display. The upper range (1,400–8,000 Hz) is compressed to ~38% but remains fully visible.

### Implementation

**File changed:** `ui/spectrogram.py` only.

**Key change — `__init__`:**

Replace the linear `_freq_mask` approach with a log-spaced display grid and a pre-computed index map:

```python
N_LOG_BINS = 512

# Log-spaced frequency grid: 512 bins from FREQ_MIN_HZ to FREQ_MAX_HZ
self._display_freqs = np.logspace(
    np.log10(FREQ_MIN_HZ),
    np.log10(FREQ_MAX_HZ),
    N_LOG_BINS,
)
self._n_freq_bins = N_LOG_BINS

# Pre-compute mapping: for each log display bin, the nearest linear FFT bin index
all_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
self._freq_indices = np.searchsorted(all_freqs, self._display_freqs)
self._freq_indices = np.clip(self._freq_indices, 0, len(all_freqs) - 1)
```

**Key change — `add_column`:**

Replace the boolean mask lookup with the pre-computed index map:

```python
# was: display_col = spectrum_db[self._freq_mask]
display_col = spectrum_db[self._freq_indices]
```

**No other changes required.** Singer's Formant band, F1/F2 scatter, and frequency tick labels all already use `np.searchsorted(self._display_freqs, hz)` — they adapt automatically.

### Future Feature: Hover Frequency Readout

When the user hovers over any point on the spectrogram, a tooltip should display the exact frequency in Hz. Implementation: connect `mouseMoveEvent` on the PlotWidget, convert pixel y-position to a bin index, look up `_display_freqs[bin_index]`. Useful across all frequency ranges, especially the compressed upper zone. **Not in this session — noted for a future session.**

---

## Feature 2: macOS .app Bundle

### Goal

Build a double-clickable `VoiceTrainer.app` that can be placed in `/Applications` and launched like any native Mac app. No terminal, no venv activation, no `python main.py`.

### Tool: PyInstaller

PyInstaller bundles Python, all dependencies, and the PortAudio binary into a self-contained `.app`. A `VoiceTrainer.spec` file controls the build. A `build_app.sh` script runs the whole process with one command.

**Note on Python 3.14:** PyInstaller officially supports Python 3.8–3.12. Python 3.14 is newer. We attempt PyInstaller first. If it fails, fallback is **py2app** (macOS-native, more likely to handle 3.14).

### Key Requirements

**1. Microphone permission (NSMicrophoneUsageDescription)**

macOS requires every `.app` that accesses the microphone to declare a usage description in `Info.plist`. Without it, the app receives no audio and fails silently. This is added to the PyInstaller spec:

```python
info_plist = {
    'NSMicrophoneUsageDescription': 'Voice Trainer needs microphone access to analyze your singing voice in real time.',
}
```

**2. PortAudio binary**

sounddevice ships its own PortAudio `.dylib` inside `_sounddevice_data`. PyInstaller must be told to include it:

```python
datas=[
    (
        str(Path(sounddevice.__file__).parent / '_sounddevice_data'),
        '_sounddevice_data',
    )
],
```

**3. Ad-hoc code signing**

The built app is signed with a free local certificate so it opens cleanly on your Mac without Gatekeeper warnings:

```bash
codesign --deep --force --sign - dist/VoiceTrainer.app
```

This does not require an Apple Developer account. It only works on the Mac that built the app.

**Future path to App Store:** Ad-hoc signing can be replaced with a proper Apple Developer certificate at any time by re-running `codesign` with the real certificate. App Store submission will also require sandboxing entitlements and notarization — that is a separate future project.

**4. First launch on other Macs (without signing certificate)**

If the app is copied to another Mac, Gatekeeper will block it. One-time fix: right-click → Open. Document in README.

### Build Output

```
dist/VoiceTrainer.app    ← drag to /Applications
build/                   ← intermediate files, can be deleted
```

### Files Added/Modified

- `VoiceTrainer.spec` — PyInstaller spec (new file)
- `build_app.sh` — one-command build script (new file)
- `README.md` — add build and launch instructions

---

## Architecture Notes

- The log scale change is entirely self-contained in `ui/spectrogram.py` — no changes to analysis, capture, or app wiring
- PyInstaller bundles everything including the venv; the source venv is not affected
- Ad-hoc signing is a post-build step in `build_app.sh`; replacing it with a real certificate later requires no structural changes
