# Voice Trainer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a macOS desktop app that displays a live scrolling spectrogram and real-time pitch readout for classical singers.

**Architecture:** Audio is captured on a background thread and placed into a queue. A Qt timer polls the queue ~60×/sec, runs signal processing (STFT + autocorrelation pitch detection), and updates two widgets: a scrolling spectrogram and a pitch/note display. All signal processing uses numpy and scipy only — no heavy ML libraries — for clean installation on Python 3.14.

**Tech Stack:** Python 3.14, PySide6, pyqtgraph, sounddevice, numpy, scipy, pytest

---

## Task 1: Install system dependency and create Python environment

PortAudio is a C library that sounddevice wraps. It must be installed via Homebrew before sounddevice can work on Mac.

**Files:** None created yet.

**Step 1: Install PortAudio**

Open Terminal and run:
```bash
brew install portaudio
```
Expected output: `==> Installing portaudio` followed by `✔ portaudio` (or "already installed").

**Step 2: Create the virtual environment**

A virtual environment keeps this project's Python packages separate from everything else on your Mac.

```bash
cd ~/voice-trainer
python3 -m venv venv
```
Expected: a new folder `venv/` appears inside `voice-trainer/`.

**Step 3: Activate the environment**

```bash
source venv/bin/activate
```
Expected: your Terminal prompt now starts with `(venv)`. You'll need to run this every time you open a new Terminal window to work on this project.

**Step 4: Install all dependencies**

```bash
pip install PySide6 pyqtgraph sounddevice numpy scipy pytest
```
Expected: several lines of download progress, ending with `Successfully installed ...`. This may take 2–3 minutes.

**Step 5: Verify every import works**

```bash
python3 -c "
import PySide6
import pyqtgraph
import sounddevice
import numpy
import scipy
print('All imports OK')
"
```
Expected output: `All imports OK`

If any import fails, note the error message — the most common issue is sounddevice failing because PortAudio isn't found. Fix: `brew install portaudio` then `pip install --force-reinstall sounddevice`.

**Step 6: Commit**

```bash
cd ~/voice-trainer
git add -A
git commit -m "chore: add venv (gitignored) — dependencies verified"
```

Note: we will add a `.gitignore` file in Task 2 so the `venv/` folder is not committed to git.

---

## Task 2: Project scaffolding

Create all files and folders so the project structure exists before we fill in code.

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `README.md`
- Create: `audio/__init__.py`
- Create: `audio/capture.py` (empty for now)
- Create: `audio/analysis.py` (empty for now)
- Create: `ui/__init__.py`
- Create: `ui/app.py` (empty for now)
- Create: `ui/spectrogram.py` (empty for now)
- Create: `ui/pitch_display.py` (empty for now)
- Create: `main.py` (empty for now)
- Create: `tests/__init__.py`
- Create: `tests/test_analysis.py` (empty for now)

**Step 1: Create `.gitignore`**

```bash
cat > ~/voice-trainer/.gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.DS_Store
*.egg-info/
dist/
build/
EOF
```

**Step 2: Create `requirements.txt`**

```
PySide6
pyqtgraph
sounddevice
numpy
scipy
pytest
```

**Step 3: Create `README.md`**

```markdown
# Voice Trainer

Real-time voice analysis tool for classical singers.

## Setup

1. Install Homebrew (if not installed): https://brew.sh
2. `brew install portaudio`
3. `cd ~/voice-trainer`
4. `python3 -m venv venv`
5. `source venv/bin/activate`
6. `pip install -r requirements.txt`

## Running

```bash
source venv/bin/activate   # only needed once per Terminal session
python main.py
```

## Project structure

- `audio/capture.py`  — microphone capture (background thread)
- `audio/analysis.py` — signal processing (spectrogram + pitch)
- `ui/spectrogram.py` — scrolling spectrogram widget
- `ui/pitch_display.py` — pitch readout widget
- `ui/app.py`         — main window
- `main.py`           — entry point
```

**Step 4: Create all empty Python files**

```bash
mkdir -p ~/voice-trainer/audio ~/voice-trainer/ui ~/voice-trainer/tests
touch ~/voice-trainer/audio/__init__.py
touch ~/voice-trainer/ui/__init__.py
touch ~/voice-trainer/tests/__init__.py
touch ~/voice-trainer/audio/capture.py
touch ~/voice-trainer/audio/analysis.py
touch ~/voice-trainer/ui/spectrogram.py
touch ~/voice-trainer/ui/pitch_display.py
touch ~/voice-trainer/ui/app.py
touch ~/voice-trainer/main.py
touch ~/voice-trainer/tests/test_analysis.py
```

**Step 5: Verify structure**

```bash
find ~/voice-trainer -not -path '*/venv/*' -not -path '*/.git/*' | sort
```

Expected output:
```
voice-trainer
voice-trainer/.gitignore
voice-trainer/README.md
voice-trainer/audio
voice-trainer/audio/__init__.py
voice-trainer/audio/analysis.py
voice-trainer/audio/capture.py
voice-trainer/docs
voice-trainer/docs/plans/...
voice-trainer/main.py
voice-trainer/requirements.txt
voice-trainer/tests
voice-trainer/tests/__init__.py
voice-trainer/tests/test_analysis.py
voice-trainer/ui
voice-trainer/ui/__init__.py
voice-trainer/ui/app.py
voice-trainer/ui/pitch_display.py
voice-trainer/ui/spectrogram.py
```

**Step 6: Commit**

```bash
cd ~/voice-trainer
git add -A
git commit -m "chore: scaffold project structure"
```

---

## Task 3: Note name conversion — audio/analysis.py (TDD)

The first real code. `hz_to_note_name` converts a frequency in Hz to a musical note name like "A4" or "C#5". This is a pure function with no dependencies on hardware — perfect for test-driven development.

**Files:**
- Modify: `audio/analysis.py`
- Modify: `tests/test_analysis.py`

**Step 1: Write the failing tests first**

Open `tests/test_analysis.py` and write:

```python
"""
Tests for audio/analysis.py

Run with: pytest tests/test_analysis.py -v
"""

import pytest
from audio.analysis import hz_to_note_name


class TestHzToNoteName:
    """Test note name conversion from frequency in Hz."""

    def test_a4_is_440_hz(self):
        """A4 (concert A) is exactly 440 Hz."""
        note, octave = hz_to_note_name(440.0)
        assert note == "A"
        assert octave == 4

    def test_middle_c_is_c4(self):
        """Middle C is approximately 261.63 Hz."""
        note, octave = hz_to_note_name(261.63)
        assert note == "C"
        assert octave == 4

    def test_c5_above_middle_c(self):
        """C5 is one octave above middle C, ~523.25 Hz."""
        note, octave = hz_to_note_name(523.25)
        assert note == "C"
        assert octave == 5

    def test_g4_is_392_hz(self):
        """G4 is approximately 392 Hz — common baritone top note."""
        note, octave = hz_to_note_name(392.0)
        assert note == "G"
        assert octave == 4

    def test_returns_none_for_zero(self):
        """Zero Hz is silence — return None for both values."""
        note, octave = hz_to_note_name(0.0)
        assert note is None
        assert octave is None

    def test_returns_none_for_negative(self):
        """Negative frequencies are impossible — return None."""
        note, octave = hz_to_note_name(-100.0)
        assert note is None
        assert octave is None

    def test_c3_low_bass_note(self):
        """C3 (~130.81 Hz) is a low note, common for bass singers."""
        note, octave = hz_to_note_name(130.81)
        assert note == "C"
        assert octave == 3
```

**Step 2: Run tests — expect FAILURE**

```bash
cd ~/voice-trainer
source venv/bin/activate
pytest tests/test_analysis.py -v
```

Expected: `ImportError: cannot import name 'hz_to_note_name' from 'audio.analysis'`

This is the right failure — the test knows what it needs, and the code doesn't exist yet. That's TDD.

**Step 3: Implement `hz_to_note_name` in `audio/analysis.py`**

```python
"""
audio/analysis.py — Signal processing for the voice trainer.

This module contains all the math:
  - hz_to_note_name:          convert a frequency (Hz) to a note name
  - compute_spectrogram_column: compute one time-slice of the spectrogram
  - estimate_pitch:            estimate the fundamental frequency of a sound

All functions are pure (no side effects, no hardware access) so they
are easy to test and reason about.
"""

import math
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard tuning: A4 = 440 Hz, MIDI note 69
_A4_HZ = 440.0
_A4_MIDI = 69

# All 12 chromatic note names starting from C
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---------------------------------------------------------------------------
# Note name conversion
# ---------------------------------------------------------------------------

def hz_to_note_name(frequency_hz: float) -> tuple[str | None, int | None]:
    """Convert a frequency in Hz to a musical note name and octave number.

    Uses equal temperament tuning (A4 = 440 Hz).

    Args:
        frequency_hz: Frequency in Hz. Must be positive.

    Returns:
        (note_name, octave) tuple, e.g. ("A", 4) for 440 Hz.
        Returns (None, None) if frequency is zero or negative.

    Examples:
        >>> hz_to_note_name(440.0)
        ('A', 4)
        >>> hz_to_note_name(261.63)
        ('C', 4)
    """
    if frequency_hz <= 0:
        return None, None

    # Convert Hz to MIDI note number.
    # Formula: MIDI = 69 + 12 * log2(f / 440)
    # Each octave doubles the frequency; each semitone multiplies by 2^(1/12).
    midi = round(_A4_MIDI + 12 * math.log2(frequency_hz / _A4_HZ))

    # Extract note name (0=C, 1=C#, ... 11=B)
    note_name = _NOTE_NAMES[midi % 12]

    # Extract octave number. MIDI 0 = C-1, MIDI 12 = C0, MIDI 60 = C4.
    octave = (midi // 12) - 1

    return note_name, octave
```

**Step 4: Run tests — expect PASS**

```bash
pytest tests/test_analysis.py -v
```

Expected output:
```
tests/test_analysis.py::TestHzToNoteName::test_a4_is_440_hz PASSED
tests/test_analysis.py::TestHzToNoteName::test_middle_c_is_c4 PASSED
tests/test_analysis.py::TestHzToNoteName::test_c5_above_middle_c PASSED
tests/test_analysis.py::TestHzToNoteName::test_g4_is_392_hz PASSED
tests/test_analysis.py::TestHzToNoteName::test_returns_none_for_zero PASSED
tests/test_analysis.py::TestHzToNoteName::test_returns_none_for_negative PASSED
tests/test_analysis.py::TestHzToNoteName::test_c3_low_bass_note PASSED

7 passed in 0.05s
```

**Step 5: Commit**

```bash
git add audio/analysis.py tests/test_analysis.py
git commit -m "feat: add hz_to_note_name with tests"
```

---

## Task 4: Spectrogram column computation — audio/analysis.py (TDD)

`compute_spectrogram_column` takes a chunk of audio samples and returns a magnitude spectrum in decibels — one vertical slice of the spectrogram.

**Files:**
- Modify: `audio/analysis.py`
- Modify: `tests/test_analysis.py`

**Step 1: Add tests to `tests/test_analysis.py`**

Append these to the existing file (after the `TestHzToNoteName` class):

```python
from audio.analysis import compute_spectrogram_column


class TestComputeSpectrogramColumn:
    """Test spectrogram column computation."""

    SAMPLE_RATE = 44100
    N_FFT = 2048

    def _sine_wave(self, frequency_hz: float, n_samples: int = 2048) -> np.ndarray:
        """Generate a pure sine wave at the given frequency."""
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        return np.sin(2 * np.pi * frequency_hz * t).astype(np.float32)

    def test_output_shape_is_correct(self):
        """Output should have n_fft//2 + 1 frequency bins."""
        samples = self._sine_wave(440.0)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        expected_bins = self.N_FFT // 2 + 1
        assert spectrum.shape == (expected_bins,)

    def test_output_is_in_decibels(self):
        """Spectrum values should be in dB (negative values expected for typical audio)."""
        samples = self._sine_wave(440.0)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        # A 440 Hz sine wave at full amplitude should have values in dB range
        assert spectrum.max() <= 10.0   # Not unreasonably large
        assert spectrum.min() >= -200.0  # Not unreasonably small

    def test_silence_is_very_quiet(self):
        """A silent signal should produce a very low-level spectrum."""
        samples = np.zeros(self.N_FFT, dtype=np.float32)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)
        assert spectrum.max() < -60.0  # Should be well below -60 dB

    def test_peak_is_near_sine_frequency(self):
        """The peak frequency bin should be near the sine wave frequency."""
        freq_hz = 1000.0
        samples = self._sine_wave(freq_hz)
        spectrum = compute_spectrogram_column(samples, self.SAMPLE_RATE, self.N_FFT)

        # Find which bin has the highest energy
        freq_resolution = self.SAMPLE_RATE / self.N_FFT  # Hz per bin
        peak_bin = np.argmax(spectrum)
        peak_freq = peak_bin * freq_resolution

        # Peak should be within one bin of the true frequency
        assert abs(peak_freq - freq_hz) <= freq_resolution
```

**Step 2: Run tests — expect failure on the new tests**

```bash
pytest tests/test_analysis.py::TestComputeSpectrogramColumn -v
```

Expected: `ImportError: cannot import name 'compute_spectrogram_column'`

**Step 3: Add `compute_spectrogram_column` to `audio/analysis.py`**

Add this after the `hz_to_note_name` function:

```python
# ---------------------------------------------------------------------------
# Spectrogram computation
# ---------------------------------------------------------------------------

def compute_spectrogram_column(
    samples: np.ndarray,
    sample_rate: int = 44100,
    n_fft: int = 2048,
) -> np.ndarray:
    """Compute one vertical column of a spectrogram from audio samples.

    Applies a Hann window to reduce spectral leakage, then computes the
    real FFT and converts to decibels.

    Args:
        samples:     Audio samples as a 1D float32 numpy array.
                     Should have length >= n_fft.
        sample_rate: Samples per second (Hz). Default: 44100.
        n_fft:       FFT size. Larger = better frequency resolution but
                     more CPU. Default: 2048 (~46 ms at 44100 Hz).

    Returns:
        1D numpy array of shape (n_fft//2 + 1,) containing the magnitude
        spectrum in decibels (dB). Higher values = louder at that frequency.

    Note:
        The frequency of bin i is: i * sample_rate / n_fft Hz.
        So bin 0 = 0 Hz (DC), bin 1 = ~21.5 Hz, ..., bin 1024 = 22050 Hz.
    """
    # Use the most recent n_fft samples (or all samples if shorter)
    chunk = samples[-n_fft:] if len(samples) >= n_fft else samples

    # Pad with zeros if shorter than n_fft
    if len(chunk) < n_fft:
        chunk = np.pad(chunk, (0, n_fft - len(chunk)))

    # Apply a Hann window to reduce "spectral leakage" — the phenomenon
    # where energy from one frequency bleeds into neighboring bins.
    window = np.hanning(n_fft)
    windowed = chunk.astype(np.float64) * window

    # Real FFT: since audio is real-valued, we only need the positive
    # frequency half. Output has n_fft//2 + 1 complex values.
    spectrum_complex = np.fft.rfft(windowed, n=n_fft)

    # Magnitude: |complex| gives amplitude at each frequency bin.
    magnitude = np.abs(spectrum_complex)

    # Convert to decibels. Add a tiny floor (1e-10) to avoid log(0).
    # 20 * log10 because we're working with amplitude (not power).
    spectrum_db = 20.0 * np.log10(magnitude + 1e-10)

    return spectrum_db.astype(np.float32)
```

**Step 4: Run all tests — expect all PASS**

```bash
pytest tests/test_analysis.py -v
```

Expected: `11 passed`

**Step 5: Commit**

```bash
git add audio/analysis.py tests/test_analysis.py
git commit -m "feat: add compute_spectrogram_column with tests"
```

---

## Task 5: Pitch estimation — audio/analysis.py (TDD)

`estimate_pitch` uses autocorrelation to find the fundamental frequency in a chunk of audio. This algorithm works well for singing voices without requiring any external libraries.

**Files:**
- Modify: `audio/analysis.py`
- Modify: `tests/test_analysis.py`

**Step 1: Add tests to `tests/test_analysis.py`**

```python
from audio.analysis import estimate_pitch


class TestEstimatePitch:
    """Test pitch estimation using autocorrelation."""

    SAMPLE_RATE = 44100

    def _sine_wave(self, frequency_hz: float, n_samples: int = 4096) -> np.ndarray:
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        return np.sin(2 * np.pi * frequency_hz * t).astype(np.float32)

    def test_detects_a4_440hz(self):
        """Should detect A4 (440 Hz) within 5 Hz tolerance."""
        samples = self._sine_wave(440.0)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 440.0) < 5.0

    def test_detects_middle_c_261hz(self):
        """Should detect middle C (~261.63 Hz) within 5 Hz tolerance."""
        samples = self._sine_wave(261.63)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 261.63) < 5.0

    def test_detects_high_soprano_c6(self):
        """Should detect C6 (~1046.5 Hz) within 10 Hz tolerance."""
        samples = self._sine_wave(1046.5)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is not None
        assert abs(pitch - 1046.5) < 10.0

    def test_silence_returns_none(self):
        """Silence should return None — no pitch detected."""
        samples = np.zeros(4096, dtype=np.float32)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        assert pitch is None

    def test_noise_returns_none_or_a_value(self):
        """Random noise may or may not have a pitch — just shouldn't crash."""
        rng = np.random.default_rng(seed=42)
        samples = rng.uniform(-0.1, 0.1, size=4096).astype(np.float32)
        pitch = estimate_pitch(samples, self.SAMPLE_RATE)
        # May return None or a value — either is acceptable, but shouldn't crash
        assert pitch is None or (80.0 <= pitch <= 1200.0)
```

**Step 2: Run tests — expect failure**

```bash
pytest tests/test_analysis.py::TestEstimatePitch -v
```

Expected: `ImportError: cannot import name 'estimate_pitch'`

**Step 3: Add `estimate_pitch` to `audio/analysis.py`**

```python
# ---------------------------------------------------------------------------
# Pitch estimation
# ---------------------------------------------------------------------------

def estimate_pitch(
    samples: np.ndarray,
    sample_rate: int = 44100,
    fmin: float = 80.0,
    fmax: float = 1200.0,
    confidence_threshold: float = 0.3,
) -> float | None:
    """Estimate the fundamental frequency (pitch) of a voice signal.

    Uses normalized autocorrelation: a signal with a period of T samples
    will have a strong autocorrelation peak at lag T.

    Args:
        samples:              Audio samples, 1D float array.
        sample_rate:          Samples per second.
        fmin:                 Minimum detectable pitch in Hz (default: 80 Hz, low bass).
        fmax:                 Maximum detectable pitch in Hz (default: 1200 Hz, high soprano).
        confidence_threshold: Minimum normalized correlation to accept as voiced.
                              Range 0–1. Higher = stricter. Default: 0.3.

    Returns:
        Estimated frequency in Hz, or None if no clear pitch is detected.
    """
    if len(samples) < 2:
        return None

    # Convert lag range from Hz to samples.
    # A 440 Hz pitch repeats every 44100/440 ≈ 100 samples.
    min_lag = int(sample_rate / fmax)  # shortest period = highest pitch
    max_lag = int(sample_rate / fmin)  # longest period = lowest pitch

    if max_lag >= len(samples):
        max_lag = len(samples) - 1
    if min_lag >= max_lag:
        return None

    # Normalize samples to avoid scale effects on confidence
    samples_f = samples.astype(np.float64)
    samples_norm = samples_f / (np.max(np.abs(samples_f)) + 1e-10)

    # Check signal level — don't try to pitch-detect silence
    rms = np.sqrt(np.mean(samples_norm ** 2))
    if rms < 0.01:  # Threshold: ~-40 dB
        return None

    # Compute autocorrelation via convolution with reversed self.
    # autocorr[lag] measures how similar the signal is to itself shifted by `lag` samples.
    n = len(samples_norm)
    autocorr = np.correlate(samples_norm, samples_norm, mode='full')
    autocorr = autocorr[n - 1:]  # Keep only non-negative lags

    # Normalize by the zero-lag value (autocorr[0] = total signal energy).
    # This gives values in [-1, 1] regardless of signal amplitude.
    if autocorr[0] <= 0:
        return None
    autocorr = autocorr / autocorr[0]

    # Find the lag with the highest autocorrelation within our pitch range.
    search_region = autocorr[min_lag:max_lag + 1]
    if len(search_region) == 0:
        return None

    peak_offset = np.argmax(search_region)
    peak_lag = peak_offset + min_lag
    peak_confidence = autocorr[peak_lag]

    # Reject if confidence is too low — likely noise or silence.
    if peak_confidence < confidence_threshold:
        return None

    # Convert lag (samples) back to frequency (Hz).
    return float(sample_rate / peak_lag)
```

**Step 4: Run all tests — expect all PASS**

```bash
pytest tests/test_analysis.py -v
```

Expected: `16 passed`

**Step 5: Commit**

```bash
git add audio/analysis.py tests/test_analysis.py
git commit -m "feat: add estimate_pitch with autocorrelation and tests"
```

---

## Task 6: Audio capture module — audio/capture.py

`AudioCapture` runs a background thread that continuously reads from the microphone and places chunks into a queue that the UI can safely read.

There is no automated unit test for hardware audio — we'll verify manually.

**Files:**
- Modify: `audio/capture.py`

**Step 1: Write `audio/capture.py`**

```python
"""
audio/capture.py — Microphone capture running in a background thread.

The AudioCapture class starts a sounddevice input stream in a background
thread. Each audio callback deposits a numpy array of samples into a
thread-safe queue. The UI thread can call get_chunk() to retrieve samples.

Usage:
    capture = AudioCapture()
    capture.start()
    # ... in UI timer:
    chunk = capture.get_chunk()  # returns None if nothing available
    # ...
    capture.stop()
"""

import queue
import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures microphone audio in a background thread.

    Audio data is placed into an internal queue as numpy float32 arrays.
    Call get_chunk() from any thread to retrieve a chunk (non-blocking).
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """Create an AudioCapture instance.

        Args:
            sample_rate: Audio sample rate in Hz. 44100 is CD quality.
            block_size:  Number of samples per callback (~23 ms at 44100 Hz).
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._stream: sd.InputStream | None = None

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time,
        status: sd.CallbackFlags,
    ) -> None:
        """Called by sounddevice on every audio block.

        This runs in a separate thread managed by sounddevice/PortAudio.
        IMPORTANT: Do NOT call Qt methods from here — only put data into
        the queue. The UI thread reads the queue via a QTimer.

        Args:
            indata: Audio samples, shape (frames, channels), float32.
            frames: Number of frames (same as block_size).
            time:   Timestamps (unused).
            status: Flags indicating overflows or underflows.
        """
        if status:
            print(f"[AudioCapture] Warning: {status}")

        # Take the first channel (mono). Copy because indata is a view.
        mono = indata[:, 0].copy()

        # Drop oldest chunk if queue is full (prevents memory growth if UI is slow)
        try:
            self._queue.put_nowait(mono)
        except queue.Full:
            try:
                self._queue.get_nowait()  # discard oldest
            except queue.Empty:
                pass
            self._queue.put_nowait(mono)

    def start(self) -> None:
        """Open the microphone stream and begin capturing."""
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=1,          # mono
            dtype=np.float32,    # standard float range [-1.0, 1.0]
            callback=self._callback,
        )
        self._stream.start()
        print(f"[AudioCapture] Started — {self.sample_rate} Hz, {self.block_size} samples/block")

    def stop(self) -> None:
        """Stop capturing and release the microphone."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            print("[AudioCapture] Stopped")

    def get_chunk(self) -> np.ndarray | None:
        """Return one chunk of audio samples, or None if the queue is empty.

        Non-blocking. Returns a 1D float32 numpy array of length block_size,
        or None if no new audio has arrived.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
```

**Step 2: Smoke test — verify no import errors**

```bash
cd ~/voice-trainer
source venv/bin/activate
python3 -c "from audio.capture import AudioCapture; print('AudioCapture import OK')"
```

Expected: `AudioCapture import OK`

**Step 3: Commit**

```bash
git add audio/capture.py
git commit -m "feat: add AudioCapture microphone capture module"
```

---

## Task 7: Spectrogram widget — ui/spectrogram.py

A pyqtgraph widget that displays a scrolling spectrogram. New frequency columns are added on the right; old ones scroll off the left.

**Files:**
- Modify: `ui/spectrogram.py`

**Step 1: Write `ui/spectrogram.py`**

```python
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


# Frequency range to display
FREQ_MIN_HZ = 80.0
FREQ_MAX_HZ = 8000.0

# dB range for color mapping: anything below DISPLAY_DB_MIN is shown as black
DISPLAY_DB_MIN = -70.0
DISPLAY_DB_MAX = 0.0


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
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.sample_rate = sample_rate
        self.n_fft = n_fft

        # Frequency axis: array of Hz values for each FFT bin
        self._all_freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)

        # Only display bins in our target range (80–8000 Hz)
        self._freq_mask = (self._all_freqs >= FREQ_MIN_HZ) & (self._all_freqs <= FREQ_MAX_HZ)
        self._display_freqs = self._all_freqs[self._freq_mask]
        self._n_freq_bins = int(self._freq_mask.sum())

        # Time axis: number of columns = display_seconds * update_rate
        # Update rate ≈ sample_rate / (n_fft // 2) due to 50% overlap
        hop = n_fft // 2
        self._update_rate = sample_rate / hop  # columns per second
        self._n_time_cols = int(display_seconds * self._update_rate)

        # Rolling buffer: shape (time_cols, freq_bins), filled with silence
        self._buffer = np.full(
            (self._n_time_cols, self._n_freq_bins),
            fill_value=DISPLAY_DB_MIN,
            dtype=np.float32,
        )

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

        # Magma colormap: perceptually uniform dark→light
        colormap = pg.colormap.get('magma')
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

    def _build_frequency_ticks(self) -> list[tuple[float, str]]:
        """Build y-axis tick marks at musically meaningful frequencies."""
        target_hz = [100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 8000]
        ticks = []
        for hz in target_hz:
            if FREQ_MIN_HZ <= hz <= FREQ_MAX_HZ:
                # Find the bin index closest to this frequency
                idx = np.searchsorted(self._display_freqs, hz)
                if idx < self._n_freq_bins:
                    label = f"{hz} Hz" if hz < 1000 else f"{hz // 1000}k Hz"
                    ticks.append((float(idx), label))
        return ticks

    def add_column(self, spectrum_db: np.ndarray) -> None:
        """Add a new spectrum column and refresh the display.

        Call this every time a new audio chunk has been analyzed.

        Args:
            spectrum_db: Full magnitude spectrum in dB, shape (n_fft//2+1,).
                         Produced by audio.analysis.compute_spectrogram_column().
        """
        # Extract only the frequency bins in our display range
        display_col = spectrum_db[self._freq_mask]

        # Scroll the buffer left by one column and place the new column on the right
        self._buffer[:-1] = self._buffer[1:]
        self._buffer[-1] = display_col

        # Update the image. pyqtgraph ImageItem interprets shape (x, y):
        # x = time (horizontal), y = frequency (vertical)
        self._image_item.setImage(self._buffer, autoLevels=False)
```

**Step 2: Smoke test imports**

```bash
python3 -c "from ui.spectrogram import SpectrogramWidget; print('SpectrogramWidget import OK')"
```

Expected: `SpectrogramWidget import OK`

**Step 3: Commit**

```bash
git add ui/spectrogram.py
git commit -m "feat: add SpectrogramWidget rolling display"
```

---

## Task 8: Pitch display widget — ui/pitch_display.py

A simple widget showing the current pitch in Hz and as a note name.

**Files:**
- Modify: `ui/pitch_display.py`

**Step 1: Write `ui/pitch_display.py`**

```python
"""
ui/pitch_display.py — Real-time pitch readout widget.

PitchDisplayWidget shows two pieces of information:
  1. The musical note name and octave (e.g. "A4")
  2. The frequency in Hz (e.g. "440 Hz")

Call update_pitch(frequency_hz) with the latest pitch estimate.
Pass None to indicate silence / no pitch detected.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from audio.analysis import hz_to_note_name


class PitchDisplayWidget(QWidget):
    """Displays current pitch as a note name and frequency in Hz.

    Args:
        parent: Parent QWidget, or None for a top-level widget.
    """

    # Colors
    _COLOR_ACTIVE = "#f0e68c"    # warm yellow when voice is detected
    _COLOR_SILENT = "#555566"    # muted when silent
    _BG_COLOR = "#0d0d1a"        # slightly lighter than spectrogram bg

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet(f"background-color: {self._BG_COLOR};")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the label layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)

        # Note name label (large, prominent)
        self._note_label = QLabel("—")
        note_font = QFont("Courier", 28, QFont.Weight.Bold)
        self._note_label.setFont(note_font)
        self._note_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
        self._note_label.setFixedWidth(100)
        self._note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Frequency label (smaller)
        self._freq_label = QLabel("No pitch detected")
        freq_font = QFont("Courier", 16)
        self._freq_label.setFont(freq_font)
        self._freq_label.setStyleSheet(f"color: {self._COLOR_SILENT};")

        layout.addWidget(self._note_label)
        layout.addSpacing(16)
        layout.addWidget(self._freq_label)
        layout.addStretch()

    def update_pitch(self, frequency_hz: float | None) -> None:
        """Update the display with a new pitch estimate.

        Args:
            frequency_hz: Frequency in Hz, or None if no pitch detected.
        """
        if frequency_hz is None:
            self._note_label.setText("—")
            self._note_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
            self._freq_label.setText("No pitch detected")
            self._freq_label.setStyleSheet(f"color: {self._COLOR_SILENT};")
        else:
            note_name, octave = hz_to_note_name(frequency_hz)
            if note_name is not None:
                self._note_label.setText(f"{note_name}{octave}")
                self._note_label.setStyleSheet(f"color: {self._COLOR_ACTIVE};")
                self._freq_label.setText(f"{frequency_hz:.1f} Hz")
                self._freq_label.setStyleSheet(f"color: {self._COLOR_ACTIVE};")
```

**Step 2: Smoke test**

```bash
python3 -c "from ui.pitch_display import PitchDisplayWidget; print('PitchDisplayWidget import OK')"
```

Expected: `PitchDisplayWidget import OK`

**Step 3: Commit**

```bash
git add ui/pitch_display.py
git commit -m "feat: add PitchDisplayWidget note name display"
```

---

## Task 9: Main window — ui/app.py

`MainWindow` wires together the spectrogram, pitch display, audio capture, and analysis. A `QTimer` fires ~60×/second to drain the audio queue, analyze new samples, and update both widgets.

**Files:**
- Modify: `ui/app.py`

**Step 1: Write `ui/app.py`**

```python
"""
ui/app.py — Main application window.

MainWindow creates and lays out the two display widgets (SpectrogramWidget
and PitchDisplayWidget) and manages the audio processing loop.

The audio loop uses a QTimer (not a separate thread) to periodically:
  1. Drain new audio chunks from AudioCapture's queue
  2. Accumulate them into an analysis buffer
  3. When the buffer is large enough, run spectrogram and pitch analysis
  4. Update the display widgets with new results

This approach keeps all Qt calls on the main thread (required by Qt) while
the audio capture itself runs in a background thread.
"""

import numpy as np
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont

from audio.capture import AudioCapture
from audio.analysis import compute_spectrogram_column, estimate_pitch
from ui.spectrogram import SpectrogramWidget
from ui.pitch_display import PitchDisplayWidget


# Audio processing settings — must match between capture and analysis
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024    # samples per audio callback (~23 ms)
N_FFT = 2048         # FFT window size (~46 ms) — larger = better frequency resolution
HOP_SIZE = N_FFT // 2  # 50% overlap between analysis frames

# How often the UI updates (milliseconds). 16 ms ≈ 60 fps.
TIMER_INTERVAL_MS = 16


class MainWindow(QMainWindow):
    """Main application window for the voice trainer.

    Owns:
      - AudioCapture instance (background thread)
      - SpectrogramWidget (upper half of window)
      - PitchDisplayWidget (lower strip)
      - QTimer (drives the audio → display update loop)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer — Classical Singing Analysis")
        self.resize(1100, 650)
        self.setStyleSheet("background-color: #1a1a2e;")

        # Audio system
        self._capture = AudioCapture(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)

        # Accumulation buffer: we collect audio chunks here until we have
        # enough samples for a full FFT analysis window.
        self._audio_buffer = np.zeros(0, dtype=np.float32)

        # Build the UI
        self._setup_ui()

        # Start the audio capture
        self._capture.start()

        # Start the processing timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_audio)
        self._timer.start(TIMER_INTERVAL_MS)

    def _setup_ui(self) -> None:
        """Create and arrange the UI widgets."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title = QLabel("VOICE TRAINER")
        title_font = QFont("Courier", 11)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(30)
        title.setStyleSheet("color: #666688; background-color: #0d0d1a; letter-spacing: 4px;")
        layout.addWidget(title)

        # Main spectrogram (takes up most of the window)
        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            display_seconds=8.0,
        )
        layout.addWidget(self._spectrogram, stretch=1)

        # Pitch readout at the bottom
        self._pitch_display = PitchDisplayWidget()
        layout.addWidget(self._pitch_display)

    def _process_audio(self) -> None:
        """Called ~60 times/second by QTimer. Drains audio queue and updates display.

        This is the core audio processing loop:
          1. Pull all available chunks from the audio queue
          2. Accumulate them into a buffer
          3. Analyze each complete window (N_FFT samples)
          4. Update the display widgets
        """
        # Drain all available chunks from the capture queue
        new_chunks = []
        while True:
            chunk = self._capture.get_chunk()
            if chunk is None:
                break
            new_chunks.append(chunk)

        if not new_chunks:
            return  # Nothing new — skip this timer tick

        # Append new samples to the accumulation buffer
        self._audio_buffer = np.concatenate([self._audio_buffer] + new_chunks)

        # Process as many complete windows as we have samples for
        latest_pitch = None
        while len(self._audio_buffer) >= N_FFT:
            # Take one window of samples
            window = self._audio_buffer[:N_FFT]

            # --- Signal analysis ---
            spectrum_db = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz = estimate_pitch(window, SAMPLE_RATE)

            # Update spectrogram with this new column
            self._spectrogram.add_column(spectrum_db)

            # Keep track of most recent pitch estimate
            if pitch_hz is not None:
                latest_pitch = pitch_hz

            # Advance the buffer by HOP_SIZE (50% overlap)
            self._audio_buffer = self._audio_buffer[HOP_SIZE:]

        # Update pitch display with whatever we found
        self._pitch_display.update_pitch(latest_pitch)

    def closeEvent(self, event) -> None:
        """Called when the window is closed. Stop audio before exiting."""
        self._timer.stop()
        self._capture.stop()
        event.accept()
```

**Step 2: Smoke test**

```bash
python3 -c "from ui.app import MainWindow; print('MainWindow import OK')"
```

Expected: `MainWindow import OK`

**Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat: add MainWindow with audio-to-display processing loop"
```

---

## Task 10: Entry point and full app launch — main.py

The final piece: `main.py` creates the Qt application and launches the window.

**Files:**
- Modify: `main.py`

**Step 1: Write `main.py`**

```python
"""
main.py — Entry point for the Voice Trainer application.

Run with:
    source venv/bin/activate
    python main.py

The app will ask for microphone permission the first time it runs on Mac.
Allow access when prompted, then sing into your microphone and watch the
spectrogram respond.
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.app import MainWindow


def main() -> int:
    """Create and show the main application window.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Trainer")
    app.setOrganizationName("VoiceTrainer")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Run the app**

```bash
cd ~/voice-trainer
source venv/bin/activate
python main.py
```

**First run on Mac:** macOS will show a permission dialog asking if the app can access your microphone. Click **OK** / **Allow**.

Expected result:
- A dark window opens (~1100 × 650 pixels)
- The spectrogram is black (no signal yet)
- Pitch display shows "No pitch detected"
- Sing or hum into your microphone
- The spectrogram scrolls leftward with color bands appearing at harmonic frequencies
- The pitch display shows your note name and Hz (e.g. "A4 — 440.0 Hz")

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add entry point — voice trainer app complete"
```

---

## Task 11: Run all tests one final time

Confirm the full test suite passes before declaring victory.

**Step 1: Run all tests**

```bash
cd ~/voice-trainer
source venv/bin/activate
pytest tests/ -v
```

Expected:
```
tests/test_analysis.py::TestHzToNoteName::test_a4_is_440_hz PASSED
tests/test_analysis.py::TestHzToNoteName::test_middle_c_is_c4 PASSED
... (all 16 tests passing)

16 passed in X.XXs
```

**Step 2: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: final cleanup — all tests pass"
```

---

## Done! What you built

```
~/voice-trainer/
├── main.py                 ← run this: python main.py
├── requirements.txt
├── README.md
├── audio/
│   ├── capture.py          ← microphone background thread
│   └── analysis.py         ← STFT spectrogram + autocorrelation pitch
└── ui/
    ├── spectrogram.py      ← scrolling color spectrogram
    ├── pitch_display.py    ← note name + Hz readout
    └── app.py              ← main window, timer, wiring
```

**What you'll see:** A dark window with a scrolling color spectrogram showing your voice's harmonic structure in real time, and a pitch readout naming each note you sing.

**Next steps from the design doc:** Singer's formant highlight band → time-scale zoom → vibrato tracking → vowel modification recommendations.
