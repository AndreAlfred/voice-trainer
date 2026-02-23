# Display & Packaging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redistribute the spectrogram y-axis to a logarithmic scale so the voice range (F0/F1/F2) occupies ~62% of the display, and package the app as a double-clickable macOS `.app` bundle.

**Architecture:** The log scale change is a self-contained edit to `ui/spectrogram.py` — replace the linear FFT bin mask with a 512-bin log-spaced grid and a pre-computed index map. The packaging uses PyInstaller with a custom spec file that declares microphone access and bundles the PortAudio binary; a shell script handles the full build + ad-hoc signing in one command.

**Tech Stack:** Python 3.14, PySide6 6.10.2, pyqtgraph 0.14.0, numpy 2.4.2, PyInstaller (to be installed), codesign (built into macOS)

**Design doc:** `docs/plans/2026-02-23-display-and-packaging-design.md`

---

## Before You Start

All commands run from the project root with the venv active:

```bash
cd ~/voice-trainer
source venv/bin/activate
```

Run the full test suite before touching anything to confirm baseline:

```bash
pytest tests/ -v
```

Expected: **21 passed**

---

## Task 1: Log-Spaced Frequency Scale

**Files:**
- Modify: `ui/spectrogram.py`
- Create: `tests/test_spectrogram.py`

---

### Step 1: Write the failing tests

Create `tests/test_spectrogram.py` with this exact content:

```python
"""
tests/test_spectrogram.py — Tests for SpectrogramWidget frequency scale.

These tests verify that the log-spaced frequency grid is constructed correctly
and that the widget still accepts new columns without error.
"""

import sys
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    """Single QApplication instance shared across all tests in this file."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestLogFrequencyScale:
    """Verify the log-spaced display frequency grid in SpectrogramWidget."""

    def test_display_freqs_starts_near_freq_min(self, qt_app):
        """First display bin should be at or near FREQ_MIN_HZ (80 Hz)."""
        from ui.spectrogram import SpectrogramWidget, FREQ_MIN_HZ
        w = SpectrogramWidget()
        assert abs(w._display_freqs[0] - FREQ_MIN_HZ) < 1.0, (
            f"Expected _display_freqs[0] ≈ {FREQ_MIN_HZ}, got {w._display_freqs[0]}"
        )

    def test_display_freqs_ends_near_freq_max(self, qt_app):
        """Last display bin should be at or near FREQ_MAX_HZ (8000 Hz)."""
        from ui.spectrogram import SpectrogramWidget, FREQ_MAX_HZ
        w = SpectrogramWidget()
        assert abs(w._display_freqs[-1] - FREQ_MAX_HZ) < 10.0, (
            f"Expected _display_freqs[-1] ≈ {FREQ_MAX_HZ}, got {w._display_freqs[-1]}"
        )

    def test_display_freqs_is_log_spaced(self, qt_app):
        """Consecutive frequency ratios should be nearly constant (log spacing)."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        ratios = w._display_freqs[1:] / w._display_freqs[:-1]
        # Standard deviation of ratios should be tiny if truly log-spaced
        assert np.std(ratios) < 0.001, (
            f"Frequency ratios not constant — std={np.std(ratios):.6f}. "
            "Array may still be linear."
        )

    def test_display_freqs_length_is_512(self, qt_app):
        """Display grid should have exactly 512 bins."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert len(w._display_freqs) == 512, (
            f"Expected 512 display bins, got {len(w._display_freqs)}"
        )

    def test_display_freqs_is_monotonically_increasing(self, qt_app):
        """All frequencies should be strictly increasing."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert np.all(np.diff(w._display_freqs) > 0), (
            "Frequency array is not monotonically increasing."
        )

    def test_add_column_accepts_full_spectrum(self, qt_app):
        """add_column should not raise when given a valid spectrum array."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget(n_fft=2048)
        # n_fft=2048 → spectrum shape is (1025,)
        spectrum = np.full(1025, -40.0, dtype=np.float32)
        w.add_column(spectrum)  # must not raise

    def test_buffer_shape_matches_display_bins(self, qt_app):
        """Internal buffer second dimension should equal number of display bins."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        assert w._buffer.shape[1] == w._n_freq_bins, (
            f"Buffer shape {w._buffer.shape} doesn't match n_freq_bins={w._n_freq_bins}"
        )
```

---

### Step 2: Run tests to verify they fail

```bash
pytest tests/test_spectrogram.py -v
```

Expected output (all 7 tests FAIL — `_display_freqs` is still linear):

```
FAILED tests/test_spectrogram.py::TestLogFrequencyScale::test_display_freqs_is_log_spaced
FAILED tests/test_spectrogram.py::TestLogFrequencyScale::test_display_freqs_length_is_512
... (some may pass, some fail — that's fine)
```

The key failure is `test_display_freqs_is_log_spaced` — the std of ratios will be large.

---

### Step 3: Implement the log-spaced frequency grid

Open `ui/spectrogram.py`. Make these two changes:

**Change 1 — Add `N_LOG_BINS` constant** (after the existing `DISPLAY_DB_MAX` constant, around line 25):

```python
# Number of log-spaced display bins on the frequency axis.
# More bins = smoother gradient but slightly more memory. 512 is a good balance.
N_LOG_BINS = 512
```

**Change 2 — Replace the linear frequency mask in `__init__`** (around lines 52–58).

Remove this block:
```python
        # Frequency axis: array of Hz values for each FFT bin
        self._all_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)

        # Only display bins in our target range (80–8000 Hz)
        self._freq_mask = (self._all_freqs >= FREQ_MIN_HZ) & (self._all_freqs <= FREQ_MAX_HZ)
        self._display_freqs = self._all_freqs[self._freq_mask]
        self._n_freq_bins = int(self._freq_mask.sum())
```

Replace with:
```python
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
        self._freq_indices = np.searchsorted(_all_freqs, self._display_freqs)
        self._freq_indices = np.clip(self._freq_indices, 0, len(_all_freqs) - 1)
```

**Change 3 — Update `add_column`** (around line 188).

Remove:
```python
        # Extract only the frequency bins in our display range
        display_col = spectrum_db[self._freq_mask]
```

Replace with:
```python
        # Map the linear FFT spectrum onto the log-spaced display grid
        display_col = spectrum_db[self._freq_indices]
```

That's the entire change. Everything else (`add_formants`, singer's formant band, tick labels) already uses `np.searchsorted(self._display_freqs, hz)` and adapts automatically.

---

### Step 4: Run the tests to verify they pass

```bash
pytest tests/test_spectrogram.py -v
```

Expected: **7 passed**

Then run the full suite to confirm nothing broke:

```bash
pytest tests/ -v
```

Expected: **28 passed** (21 original + 7 new)

---

### Step 5: Smoke-test the running app

```bash
python main.py
```

Verify visually:
- The spectrogram y-axis now shows the 80–1,400 Hz region taking up most of the display height
- The Singer's Formant gold band is still visible in the correct position (~2,000–3,500 Hz, now in the upper third of the display)
- Frequency tick labels are still readable and correctly placed
- F1/F2 dots appear when singing

Close the app when satisfied.

---

### Step 6: Commit

```bash
git add ui/spectrogram.py tests/test_spectrogram.py
git commit -m "feat: log-spaced frequency axis — voice range now ~62% of display height"
```

---

## Task 2: PyInstaller Spec File

**Files:**
- Create: `VoiceTrainer.spec`

There is no unit test for a build spec file. The "test" is the successful build in Task 3.

---

### Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

Verify install:

```bash
pyinstaller --version
```

Expected: prints a version number (e.g. `6.x.x`). If this fails with a Python 3.14 incompatibility error, skip to the **py2app fallback** note at the end of Task 3.

---

### Step 2: Create `VoiceTrainer.spec`

Create `VoiceTrainer.spec` in the project root with this exact content:

```python
# VoiceTrainer.spec — PyInstaller build specification for macOS .app bundle.
#
# Build with: pyinstaller VoiceTrainer.spec
# Or use:     ./build_app.sh   (handles venv activation + signing automatically)

import os
import sys
import sounddevice

# Path to sounddevice's bundled PortAudio binary.
# sounddevice ships its own PortAudio .dylib inside _sounddevice_data/.
# PyInstaller won't find it automatically — we declare it explicitly.
_sd_data_src = os.path.join(os.path.dirname(sounddevice.__file__), '..', '_sounddevice_data')
_sd_data_src = os.path.normpath(_sd_data_src)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (_sd_data_src, '_sounddevice_data'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtOpenGL',
        'pyqtgraph',
        'numpy',
        'scipy',
        'scipy.signal',
        'sounddevice',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zlib, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceTrainer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,       # UPX compression can break PySide6 binaries — leave off
    console=False,   # no terminal window when launched from Finder
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceTrainer',
)

app = BUNDLE(
    coll,
    name='VoiceTrainer.app',
    icon=None,
    bundle_identifier='com.voicetrainer.app',
    info_plist={
        # Required for microphone access — without this macOS gives the app no audio
        'NSMicrophoneUsageDescription': (
            'Voice Trainer needs microphone access to analyze your singing voice in real time.'
        ),
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'CFBundleName': 'Voice Trainer',
        'CFBundleDisplayName': 'Voice Trainer',
    },
)
```

---

### Step 3: Commit the spec file

```bash
git add VoiceTrainer.spec
git commit -m "build: add PyInstaller spec for macOS app bundle"
```

---

## Task 3: Build Script, App Build, and Ad-hoc Signing

**Files:**
- Create: `build_app.sh`

---

### Step 1: Create `build_app.sh`

Create `build_app.sh` in the project root:

```bash
#!/bin/bash
# build_app.sh — Build VoiceTrainer.app for macOS.
#
# Usage:
#   ./build_app.sh
#
# Output: dist/VoiceTrainer.app  (drag to /Applications to install)
#
# Requirements:
#   - Run from the voice-trainer project root
#   - venv must already be set up (python3 -m venv venv && pip install -r requirements.txt)

set -e  # stop immediately on any error

echo "==> Activating virtual environment..."
source venv/bin/activate

echo "==> Installing PyInstaller (if not already installed)..."
pip install pyinstaller --quiet

echo "==> Cleaning previous build artifacts..."
rm -rf build dist

echo "==> Building VoiceTrainer.app with PyInstaller..."
pyinstaller VoiceTrainer.spec

echo "==> Applying ad-hoc code signature..."
# Ad-hoc signing (uses '-' as identity = local self-signed).
# This prevents the Gatekeeper warning when launching on THIS Mac.
# To distribute, replace '-' with your Apple Developer certificate name.
codesign --deep --force --sign - dist/VoiceTrainer.app

echo ""
echo "✓ Build complete."
echo ""
echo "  App:     dist/VoiceTrainer.app"
echo "  Install: drag dist/VoiceTrainer.app to /Applications"
echo ""
```

Make it executable:

```bash
chmod +x build_app.sh
```

---

### Step 2: Run the build

```bash
./build_app.sh
```

This will take 1–3 minutes (PyInstaller bundles ~150–200 MB of Python + Qt libraries).

**Expected final output:**
```
✓ Build complete.

  App:     dist/VoiceTrainer.app
  Install: drag dist/VoiceTrainer.app to /Applications
```

**If the build fails with a Python 3.14 error from PyInstaller:**

PyInstaller's official support ends at Python 3.12. If you hit a hard compatibility error, use py2app instead:

```bash
pip install py2app
```

Create `setup.py` in the project root:

```python
from setuptools import setup

APP = ['main.py']
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'NSMicrophoneUsageDescription': (
            'Voice Trainer needs microphone access to analyze your singing voice in real time.'
        ),
        'NSHighResolutionCapable': True,
        'CFBundleName': 'Voice Trainer',
    },
    'packages': ['PySide6', 'pyqtgraph', 'numpy', 'scipy', 'sounddevice'],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

Build with py2app:

```bash
python setup.py py2app
codesign --deep --force --sign - dist/VoiceTrainer.app
```

---

### Step 3: Test the built app

Open the app directly from the terminal to see any startup errors:

```bash
open dist/VoiceTrainer.app
```

Verify:
- App window opens (no terminal required)
- Spectrogram is visible with log-spaced y-axis
- Speak or sing — signal appears in the display
- Pitch readout updates at the bottom

If the app opens but shows no audio, check the system microphone permission:
- System Settings → Privacy & Security → Microphone → enable VoiceTrainer

---

### Step 4: Commit

```bash
git add build_app.sh
git commit -m "build: add build_app.sh — one-command macOS .app build with ad-hoc signing"
```

---

## Task 4: Update README

**Files:**
- Modify: `README.md`

---

### Step 1: Update README.md

Replace the entire contents of `README.md` with:

```markdown
# Voice Trainer

Real-time voice analysis tool for classical singers.

## Quick Start (macOS App)

1. Download or build `VoiceTrainer.app`
2. Drag to `/Applications`
3. Right-click → Open (first launch only — bypasses Gatekeeper for unsigned apps)
4. Grant microphone access when prompted

## Building the App from Source

### Prerequisites

1. Install Homebrew: https://brew.sh
2. `brew install portaudio`
3. `python3 -m venv venv`
4. `source venv/bin/activate`
5. `pip install -r requirements.txt`

### Build

```bash
./build_app.sh
```

Output: `dist/VoiceTrainer.app` — drag to `/Applications`.

## Running from Terminal (Development)

```bash
source venv/bin/activate   # only needed once per Terminal session
python main.py
```

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

Expected: 28 passed

## Project Structure

- `audio/capture.py`   — microphone capture (background thread)
- `audio/analysis.py`  — signal processing (spectrogram, pitch, formants)
- `ui/spectrogram.py`  — scrolling log-frequency spectrogram widget
- `ui/pitch_display.py`— pitch readout widget
- `ui/app.py`          — main window
- `main.py`            — entry point
- `VoiceTrainer.spec`  — PyInstaller build spec
- `build_app.sh`       — one-command build script

## Display Guide

- **Spectrogram colors:** Dark teal = quiet, orange = moderate, pale yellow = loud
- **Gold band:** Singer's Formant zone (2,000–3,500 Hz) — energy here gives the voice carrying power
- **Blue dots:** F1 formant (200–900 Hz) — correlates with vowel openness
- **Green dots:** F2 formant (700–3,200 Hz) — correlates with tongue front/back position
- **Frequency scale:** Logarithmic — each octave takes equal vertical space
```

---

### Step 2: Commit

```bash
git add README.md
git commit -m "docs: update README with app bundle install and build instructions"
```

---

## Done

Run the full test suite one final time to confirm everything is clean:

```bash
pytest tests/ -v
```

Expected: **28 passed**

The app is at `dist/VoiceTrainer.app`. Drag it to `/Applications`.
