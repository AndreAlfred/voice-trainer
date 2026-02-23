# Voice Trainer Session 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three improvements to the voice trainer: better spectrogram contrast (custom colormap + raised noise floor), a singer's formant highlight band, and real-time F1/F2 vowel formant dots scrolling over the spectrogram.

**Architecture:** All three features are additive changes. The contrast fix and formant band are visual-only changes to `ui/spectrogram.py`. The F1/F2 overlay adds a new `estimate_formants()` function to `audio/analysis.py`, two new scatter plot layers to `ui/spectrogram.py`, and one new call in the `_process_audio()` loop in `ui/app.py`.

**Tech Stack:** Python 3.14, PySide6, pyqtgraph, numpy, scipy (for `scipy.signal.lpc`), pytest

---

## Task 1: Contrast fix — custom colormap and raised noise floor

Change `ui/spectrogram.py` to use a 3-stop teal→orange→yellow colormap with a -45 dB floor instead of magma at -70 dB. No new tests (visual change only), but verify the existing 16 tests still pass.

**Files:**
- Modify: `ui/spectrogram.py`

**Step 1: Change the DISPLAY_DB_MIN constant**

In `ui/spectrogram.py`, find this line:
```python
DISPLAY_DB_MIN = -70.0
```
Replace it with:
```python
DISPLAY_DB_MIN = -45.0
```

**Step 2: Replace the colormap block**

Find this exact block in `_setup_ui()`:
```python
        # Magma colormap: perceptually uniform dark→light
        colormap = pg.colormap.get('magma')
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([DISPLAY_DB_MIN, DISPLAY_DB_MAX])
```

Replace it with:
```python
        # Custom 3-stop colormap: dark teal → warm orange → pale yellow.
        # Starts at a visible teal (not pure black) so quiet sounds always
        # appear as a real color rather than near-invisible dark purple.
        colormap = pg.ColorMap(
            pos=np.array([0.0, 0.5, 1.0]),
            color=np.array([
                [ 13,  79,  82, 255],  # dark teal  — silence / very quiet
                [212,  80,  10, 255],  # warm orange — moderate energy
                [255, 240, 160, 255],  # pale yellow — loud / strong harmonics
            ], dtype=np.uint8),
        )
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([DISPLAY_DB_MIN, DISPLAY_DB_MAX])
```

**Step 3: Smoke test — verify import and all tests pass**

```bash
cd ~/voice-trainer
source venv/bin/activate
python3 -c "from ui.spectrogram import SpectrogramWidget; print('import OK')"
pytest tests/ -v --tb=short
```

Expected: `import OK` and `16 passed`

**Step 4: Commit**

```bash
cd ~/voice-trainer
git add ui/spectrogram.py
git commit -m "feat: improve spectrogram contrast — custom colormap and -45 dB floor"
```

---

## Task 2: Singer's formant highlight band

Add a semi-transparent gold horizontal band to the spectrogram covering 2,000–3,500 Hz, with a text label. This is the "singer's formant cluster" — the frequency region that gives classical voice its carrying power.

**Files:**
- Modify: `ui/spectrogram.py`

**Step 1: Add the band at the end of `_setup_ui()`**

In `_setup_ui()`, find this line (the last line of the method):
```python
        self._plot.hideButtons()
```

After that line (still inside `_setup_ui()`), add:
```python

        # --- Singer's formant band (2000–3500 Hz) ---
        # The "singer's formant cluster" in this frequency range gives the
        # classical voice its carrying power and "ring" over an orchestra.
        # A persistent gold band makes it easy to see whether harmonics
        # are landing in this zone.
        f_lo_bin = int(np.searchsorted(self._display_freqs, 2000.0))
        f_hi_bin = int(np.searchsorted(self._display_freqs, 3500.0))

        self._singers_formant_region = pg.LinearRegionItem(
            values=[f_lo_bin, f_hi_bin],
            orientation='horizontal',   # horizontal = bounded by y-axis range
            movable=False,
            brush=pg.mkBrush(255, 215, 0, 22),   # very faint gold fill
            pen=pg.mkPen(255, 215, 0, 60),        # slightly more visible border
        )
        self._plot.addItem(self._singers_formant_region)

        # Label anchored to the top-left corner of the band
        formant_label = pg.TextItem(
            "Singer's Formant", color=(255, 215, 0, 140), anchor=(0, 1))
        formant_label.setPos(0, f_hi_bin)
        self._plot.addItem(formant_label)
```

**Step 2: Smoke test and verify tests**

```bash
cd ~/voice-trainer
source venv/bin/activate
python3 -c "from ui.spectrogram import SpectrogramWidget; print('import OK')"
pytest tests/ -v --tb=short
```

Expected: `import OK` and `16 passed`

**Step 3: Commit**

```bash
cd ~/voice-trainer
git add ui/spectrogram.py
git commit -m "feat: add singer's formant highlight band (2000–3500 Hz)"
```

---

## Task 3: F1/F2 formant estimation — TDD

Add `estimate_formants()` to `audio/analysis.py`. Uses LPC (Linear Predictive Coding) — the standard speech science technique for finding resonance peaks (formants) in a vocal signal. Write tests first.

**Files:**
- Modify: `audio/analysis.py`
- Modify: `tests/test_analysis.py`

**Step 1: Update the module docstring in `audio/analysis.py`**

Find this line in the module docstring (line 7):
```python
  - estimate_pitch:            estimate the fundamental frequency of a sound
```
Replace with:
```python
  - estimate_pitch:            estimate the fundamental frequency of a sound
  - estimate_formants:         estimate F1 and F2 vowel formant frequencies (LPC)
```

**Step 2: Write failing tests — APPEND to `tests/test_analysis.py`**

The file currently ends after `TestEstimatePitch`. APPEND the following at the very end:

```python
from audio.analysis import estimate_formants


class TestEstimateFormants:
    """Test F1/F2 vowel formant estimation using LPC."""

    SAMPLE_RATE = 44100

    def _voiced_signal(self, f0: float = 150.0, n_samples: int = 4096) -> np.ndarray:
        """Generate a voiced harmonic signal at fundamental frequency f0.

        A real voice is a sum of harmonics at f0, 2*f0, 3*f0, ...
        This mimics that structure so LPC has something to latch onto.
        """
        t = np.linspace(0, n_samples / self.SAMPLE_RATE, n_samples, endpoint=False)
        signal = np.zeros(n_samples, dtype=np.float64)
        for k in range(1, 20):
            signal += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t)
        signal /= np.max(np.abs(signal)) + 1e-10
        return signal.astype(np.float32)

    def test_silence_returns_none_none(self):
        """Silence has no formants — both return values must be None."""
        samples = np.zeros(4096, dtype=np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        assert f1 is None
        assert f2 is None

    def test_short_buffer_returns_none_none(self):
        """Buffer shorter than LPC order must return None safely without crashing."""
        samples = np.random.randn(5).astype(np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        assert f1 is None
        assert f2 is None

    def test_detected_f1_is_in_valid_range(self):
        """Any detected F1 must be in the valid F1 range (200–900 Hz)."""
        samples = self._voiced_signal(f0=150.0)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        if f1 is not None:
            assert 200.0 <= f1 <= 900.0, f"F1={f1:.1f} Hz is outside valid range 200–900"

    def test_detected_f2_is_in_valid_range(self):
        """Any detected F2 must be in the valid F2 range (700–3200 Hz)."""
        samples = self._voiced_signal(f0=150.0)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)
        if f2 is not None:
            assert 700.0 <= f2 <= 3200.0, f"F2={f2:.1f} Hz is outside valid range 700–3200"

    def test_does_not_crash_on_noise(self):
        """Random noise must not raise an exception — return None or valid values."""
        rng = np.random.default_rng(seed=99)
        samples = rng.uniform(-0.5, 0.5, size=4096).astype(np.float32)
        f1, f2 = estimate_formants(samples, self.SAMPLE_RATE)  # must not raise
        if f1 is not None:
            assert 200.0 <= f1 <= 900.0
        if f2 is not None:
            assert 700.0 <= f2 <= 3200.0
```

**Step 3: Run new tests — confirm failure**

```bash
cd ~/voice-trainer
source venv/bin/activate
pytest tests/test_analysis.py::TestEstimateFormants -v
```

Expected: `ImportError: cannot import name 'estimate_formants'`

**Step 4: Add `estimate_formants` to `audio/analysis.py`**

APPEND the following to the END of `audio/analysis.py` (after `estimate_pitch`):

```python
# ---------------------------------------------------------------------------
# Formant estimation
# ---------------------------------------------------------------------------

def estimate_formants(
    samples: np.ndarray,
    sample_rate: int = 44100,
    order: int = 14,
) -> tuple[float | None, float | None]:
    """Estimate F1 and F2 vowel formant frequencies using LPC.

    LPC (Linear Predictive Coding) models the vocal tract as an all-pole
    filter. The poles of this filter correspond to the resonance peaks
    (formants) of the vocal tract. F1 and F2 are the two lowest-frequency
    resonances and directly reflect vowel articulation:
      - F1 correlates with jaw openness (low jaw → high F1)
      - F2 correlates with tongue front/back position (front tongue → high F2)

    Args:
        samples:     Audio samples, 1D float array. Must be > order samples.
        sample_rate: Samples per second.
        order:       LPC model order. 14 is standard for voice analysis
                     (rule of thumb: order ≈ 2 + sample_rate / 1000).

    Returns:
        (f1_hz, f2_hz) tuple. Either value is None if not reliably detected.
        F1 range: 200–900 Hz. F2 range: 700–3200 Hz.
    """
    from scipy.signal import lpc

    if len(samples) <= order:
        return None, None

    # Silence check — LPC on near-silent signals gives meaningless results
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    if rms < 0.01:
        return None, None

    # Pre-emphasis filter: y[n] = x[n] - 0.97 * x[n-1]
    # Boosts high frequencies so formants above 1 kHz are clearly visible
    # to the LPC model. Standard in speech processing.
    pre = np.empty_like(samples, dtype=np.float64)
    pre[0] = samples[0]
    pre[1:] = samples[1:].astype(np.float64) - 0.97 * samples[:-1].astype(np.float64)

    # Fit an all-pole LPC model of the given order.
    # `a` is shape (order+1,) with a[0] = 1. The vocal tract is modelled as
    # H(z) = 1 / A(z) where A(z) = sum(a[k] * z^(-k)).
    a = lpc(pre, order=order)

    # Find the poles: roots of the LPC polynomial A(z).
    roots = np.roots(a)

    # Keep only roots with non-negative imaginary part.
    # Roots come in conjugate pairs; the positive-imaginary root of each pair
    # gives a unique frequency. (Its conjugate gives the same frequency.)
    roots = roots[np.imag(roots) >= 0]

    # Convert root angles to frequencies in Hz.
    # A root at angle θ on the unit circle corresponds to frequency f = θ·sr/(2π).
    freqs = np.angle(roots) * sample_rate / (2.0 * np.pi)

    # Bandwidth of each resonance: narrow bandwidth = sharp, real formant.
    # Formula: BW = -ln(|root|) * sr / π
    # Roots well inside the unit circle (|root| << 1) have large bandwidth
    # (broad, diffuse resonances) — likely artifacts, not formants.
    bandwidths = -np.log(np.abs(roots) + 1e-12) * sample_rate / np.pi

    # Keep poles in the voice frequency range with reasonably narrow bandwidth.
    valid = (
        (freqs > 90.0) &        # above noise floor
        (freqs < 4000.0) &      # below the range we care about
        (bandwidths > 0.0) &    # stable pole (inside unit circle)
        (bandwidths < 500.0)    # narrow enough to be a real resonance
    )
    freqs = np.sort(freqs[valid])

    # Apply formant-specific range gates and take the lowest candidate in each.
    # F1: jaw/height vowel dimension (200–900 Hz)
    # F2: tongue front/back dimension (700–3200 Hz)
    f1_candidates = freqs[(freqs >= 200.0) & (freqs <= 900.0)]
    f2_candidates = freqs[(freqs >= 700.0) & (freqs <= 3200.0)]

    f1 = float(f1_candidates[0]) if len(f1_candidates) > 0 else None
    f2 = float(f2_candidates[0]) if len(f2_candidates) > 0 else None

    return f1, f2
```

**Step 5: Run ALL tests — confirm 21 pass**

```bash
pytest tests/ -v
```

Expected: `21 passed`

If a test fails (especially the range tests), check whether the voiced signal is loud enough for the RMS gate. The `_voiced_signal` helper normalizes to near 1.0, so RMS should be well above 0.01. If failing, debug by printing `f1, f2` in the test.

**Step 6: Commit**

```bash
cd ~/voice-trainer
git add audio/analysis.py tests/test_analysis.py
git commit -m "feat: add estimate_formants (LPC) with tests"
```

---

## Task 4: F1/F2 rolling scatter display in SpectrogramWidget

Add rolling F1/F2 position buffers and two ScatterPlotItem layers to `ui/spectrogram.py`. Also add the `add_formants()` method that the main window will call each audio frame.

**Files:**
- Modify: `ui/spectrogram.py`

**Step 1: Add F1/F2 rolling buffers in `__init__`**

In `__init__`, find this block:
```python
        # Rolling buffer: shape (time_cols, freq_bins), filled with silence
        self._buffer = np.full(
            (self._n_time_cols, self._n_freq_bins),
            fill_value=DISPLAY_DB_MIN,
            dtype=np.float32,
        )
```

Directly after that block (before `self._setup_ui()`), add:
```python
        # Rolling F1/F2 formant position buffers — one value per time column.
        # NaN = no detection at that time step (dot not drawn at that position).
        self._f1_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)
        self._f2_bins = np.full(self._n_time_cols, np.nan, dtype=np.float32)
```

**Step 2: Add F1/F2 ScatterPlotItems in `_setup_ui()`**

Find this line at the end of `_setup_ui()` (after the formant label added in Task 2):
```python
        self._plot.addItem(formant_label)
```

After that, add:
```python

        # F1 (light blue) and F2 (bright green) formant scatter overlays.
        # These dots scroll with the spectrogram and show vowel formant history.
        self._f1_scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,
            brush=pg.mkBrush(100, 180, 255, 200),   # light blue
        )
        self._f2_scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,
            brush=pg.mkBrush(80, 240, 120, 200),    # bright green
        )
        self._plot.addItem(self._f1_scatter)
        self._plot.addItem(self._f2_scatter)
```

**Step 3: Add `add_formants()` method**

After the existing `add_column()` method (at the very end of the class), add:

```python
    def add_formants(self, f1_hz: float | None, f2_hz: float | None) -> None:
        """Add new F1/F2 estimates and refresh the scatter display.

        Call this once per audio analysis frame, immediately after add_column().
        The scatter dots scroll left in sync with the spectrogram image.

        Args:
            f1_hz: First formant frequency in Hz, or None if not detected.
            f2_hz: Second formant frequency in Hz, or None if not detected.
        """
        # Scroll both position buffers left (oldest drops off the left edge)
        self._f1_bins[:-1] = self._f1_bins[1:]
        self._f2_bins[:-1] = self._f2_bins[1:]

        # Convert Hz to the freq-bin index used by the image coordinate system.
        # Use NaN when the formant is not detected or out of the display range.
        freq_lo = self._display_freqs[0]
        freq_hi = self._display_freqs[-1]

        if f1_hz is not None and freq_lo <= f1_hz <= freq_hi:
            self._f1_bins[-1] = float(np.searchsorted(self._display_freqs, f1_hz))
        else:
            self._f1_bins[-1] = np.nan

        if f2_hz is not None and freq_lo <= f2_hz <= freq_hi:
            self._f2_bins[-1] = float(np.searchsorted(self._display_freqs, f2_hz))
        else:
            self._f2_bins[-1] = np.nan

        # Build x-positions (time column indices 0 … n_time_cols-1)
        x_all = np.arange(self._n_time_cols, dtype=np.float32)

        # Update F1 scatter — skip NaN entries (no detection = no dot)
        mask1 = ~np.isnan(self._f1_bins)
        if mask1.any():
            self._f1_scatter.setData(x=x_all[mask1], y=self._f1_bins[mask1])
        else:
            self._f1_scatter.setData(x=[], y=[])

        # Update F2 scatter
        mask2 = ~np.isnan(self._f2_bins)
        if mask2.any():
            self._f2_scatter.setData(x=x_all[mask2], y=self._f2_bins[mask2])
        else:
            self._f2_scatter.setData(x=[], y=[])
```

**Step 4: Smoke test and verify tests**

```bash
cd ~/voice-trainer
source venv/bin/activate
python3 -c "from ui.spectrogram import SpectrogramWidget; print('import OK')"
pytest tests/ -v --tb=short
```

Expected: `import OK` and `21 passed`

**Step 5: Commit**

```bash
cd ~/voice-trainer
git add ui/spectrogram.py
git commit -m "feat: add F1/F2 rolling scatter overlay to SpectrogramWidget"
```

---

## Task 5: Wire F1/F2 into the audio processing loop

Update `ui/app.py` to call `estimate_formants()` each audio frame and pass the result to the spectrogram widget.

**Files:**
- Modify: `ui/app.py`

**Step 1: Update the import line**

Find:
```python
from audio.analysis import compute_spectrogram_column, estimate_pitch
```
Replace with:
```python
from audio.analysis import compute_spectrogram_column, estimate_pitch, estimate_formants
```

**Step 2: Add formant call inside `_process_audio()`**

Find this block inside the `while len(self._audio_buffer) >= N_FFT:` loop:
```python
            # --- Signal analysis ---
            spectrum_db = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz = estimate_pitch(window, SAMPLE_RATE)

            # Update spectrogram with this new column
            self._spectrogram.add_column(spectrum_db)
```

Replace it with:
```python
            # --- Signal analysis ---
            spectrum_db = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz = estimate_pitch(window, SAMPLE_RATE)
            f1_hz, f2_hz = estimate_formants(window, SAMPLE_RATE)

            # Update spectrogram with this new column and formant positions
            self._spectrogram.add_column(spectrum_db)
            self._spectrogram.add_formants(f1_hz, f2_hz)
```

**Step 3: Smoke test**

```bash
cd ~/voice-trainer
source venv/bin/activate
python3 -c "from ui.app import MainWindow; print('import OK')"
pytest tests/ -v --tb=short
```

Expected: `import OK` and `21 passed`

**Step 4: Commit**

```bash
cd ~/voice-trainer
git add ui/app.py
git commit -m "feat: wire F1/F2 formant estimation into audio processing loop"
```

---

## Task 6: Final test suite and git log

Confirm everything is green and the commit history is clean.

**Step 1: Run full test suite**

```bash
cd ~/voice-trainer
source venv/bin/activate
pytest tests/ -v
```

Expected:
```
tests/test_analysis.py::TestHzToNoteName::...              PASSED  (7 tests)
tests/test_analysis.py::TestComputeSpectrogramColumn::...  PASSED  (4 tests)
tests/test_analysis.py::TestEstimatePitch::...             PASSED  (5 tests)
tests/test_analysis.py::TestEstimateFormants::...          PASSED  (5 tests)

21 passed
```

**Step 2: Show git log**

```bash
cd ~/voice-trainer && git log --oneline
```

Expected (newest first):
```
feat: wire F1/F2 formant estimation into audio processing loop
feat: add F1/F2 rolling scatter overlay to SpectrogramWidget
feat: add estimate_formants (LPC) with tests
feat: add singer's formant highlight band (2000–3500 Hz)
feat: improve spectrogram contrast — custom colormap and -45 dB floor
Add session 2 design doc
feat: add entry point — voice trainer app complete
...
```

**Step 3: No cleanup commit needed**

If all 21 tests pass and the log looks correct, the work is complete. Only commit if a genuine bug was caught during this verification step.

---

## What changed

| File | What was added/modified |
|------|------------------------|
| `ui/spectrogram.py` | Custom colormap, -45 dB floor, singer's formant band, F1/F2 buffers + scatter items + `add_formants()` |
| `audio/analysis.py` | `estimate_formants()` using LPC |
| `ui/app.py` | Import + call `estimate_formants()` + call `add_formants()` |
| `tests/test_analysis.py` | 5 new tests for `estimate_formants` (21 total) |

**What you'll see in the app:**
- Spectrogram is teal for quiet, orange for medium, pale yellow for loud — soft overtones no longer invisible
- Faint gold band across the 2–3.5 kHz region at all times
- Blue dots (F1) scrolling near the 300–800 Hz area during vowels
- Green dots (F2) scrolling in the 700–2500 Hz range, shifting as your tongue moves
