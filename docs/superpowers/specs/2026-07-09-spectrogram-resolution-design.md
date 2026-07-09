# Spectrogram Resolution — Round 1 Design (honest STFT fix)

**Date:** 2026-07-09
**Goal reference:** plan.md, North Star Goal 1a (high-resolution spectrogram
without lag). Follows the benchmark-harness work (issue #4, PR #15), which
confirmed the current pipeline is fast enough at 2048 bins (synthetic ~97 FPS,
human-confirmed no perceptible lag).

## Motivation

The spectrogram currently leans on a Gaussian blur to *look* smooth. That blur
is a band-aid over two different problems:

1. **A cosmetic staircase** — the display uses `np.interp` to point-sample one
   value per log-spaced display bin from a linear FFT spectrum. Where the log
   axis stretches few real FFT bins across the wide low-frequency region, this
   produces visible steps, which the blur smears away.
2. **Genuinely coarse low-frequency detail** — a single 2048-sample FFT window
   only *has* ~21.5 Hz of frequency resolution, regardless of display tricks.

Andrew's steer: stop faking smoothness; earn crispness from real data, working
iteratively rather than jumping straight to the most sophisticated transform.
Chosen staging: **honest STFT fix first, reassess, and only then consider a
constant-Q / multi-resolution rebuild (Round 2).**

## Scope

### In scope (Round 1)

1. **Replace point-interpolation + Gaussian blur with a precomputed resampling
   matrix.** Build a matrix `W` of shape `(n_display_bins, n_fft_bins)` once at
   widget construction. Each new spectrum column becomes `display_col = W @
   spectrum` — one small matrix-vector product per column, touching only the new
   column.
2. **Increase the FFT window from 2048 to 4096 samples** — real low-frequency
   detail roughly doubles (bins ~21.5 Hz → ~10.8 Hz).
3. **Drop the Gaussian blur entirely** — remove it from the render hot loop and
   remove the now-dead `blur_sigma` setting and its settings-panel slider.

### Explicitly out of scope (deferred to possible Round 2)

- Constant-Q / multi-resolution transform (variable window length per
  frequency). We take this on only if, after Round 1, low notes still read as
  coarse to Andrew's eye.
- Raising the display-bin count (see rationale below — not the bottleneck).
- Any changes to pitch/formant estimation.

## Design detail

### The resampler (`W`)

`W` maps FFT bins to log-spaced display bins by **interval overlap**. Each FFT
bin covers a frequency band of width `sr / n_fft` centered on its frequency;
each display bin covers a log-spaced band (midpoints between neighbors). The
weight `W[d, k]` is the overlap between display band `d` and FFT band `k`. Rows
are normalized to sum to 1, so the result is a weighted average of contributing
FFT bins.

- **High-frequency regime (downsampling):** many FFT bins fall inside one wide
  display bin → `W` averages them → crisp, anti-aliased, no blur.
- **Low-frequency regime (upsampling):** a narrow display bin sits inside a
  single wide FFT bin. Pure overlap-weighting would make adjacent display bins
  share one FFT value (an honest but chunky staircase). **Decision (A): linearly
  interpolate in this regime** so the low end shows smooth ramps between real
  FFT values rather than steps. Rationale: the 4096 FFT shrinks this regime, so
  most interpolation merely bridges genuinely close real samples. The residual
  chunkiness that remains is the honest signal for whether Round 2 is worth it.

Implementation note: a clean way to get regime-appropriate behavior in one
operator is to construct `W` so that (a) where a display bin spans ≥1 FFT bin it
uses overlap-area weights, and (b) where a display bin falls between FFT-bin
centers it uses the two-point linear-interpolation weights. Both are just row
patterns in the same sparse matrix; the per-frame cost is identical. `W` is
computed once and reused.

The spectrum fed to `W` is dB-valued (as today). Averaging in dB is a
deliberate, simple choice consistent with the current display; revisit only if
it looks wrong.

### Analysis parameters

- **`N_FFT`: 2048 → 4096.** Frequency bins 1025 → 2049. Window duration ~46ms →
  ~93ms of audio per column (the time-smear cost).
- **Hop decoupled from window size, held at 1024.** Today the hop is derived as
  `n_fft // 2` in both `app.py` (`HOP_SIZE = N_FFT // 2`) and
  `SpectrogramWidget.__init__` (`hop = n_fft // 2`, used to size the time axis).
  A 4096 window would silently make the hop 2048, halving the scroll rate
  (~43 → ~21 columns/sec). Fix: make `hop` an explicit parameter shared between
  `app.py` and `SpectrogramWidget`, default 1024. Overlap rises 50% → 75%,
  preserving scroll rate and offsetting the longer window's time smear.
- **Display bins: unchanged at 1024.** 1024 log bins over 80–8000 Hz is ~7.7
  cents/bin — finer than the eye needs. Display bins don't add information; real
  FFT resolution does. Remains tunable via the `n_log_bins` arg for harness
  sweeps.

### Files touched

- `ui/spectrogram.py` — build/store `W`; replace `np.interp` + `gaussian_filter`
  in `add_column` with `W @ spectrum`; accept `hop` as a parameter and size the
  time axis from it; remove `blur_sigma` from the render path. Verify and remove
  `_freq_indices` if it proves unused after the change.
- `ui/app.py` — `N_FFT` 2048 → 4096; introduce an explicit `HOP_SIZE` (1024)
  decoupled from `N_FFT`; pass `hop` to `SpectrogramWidget`.
- `ui/settings.py` — remove the `blur_sigma` field.
- `ui/settings_panel.py` — remove the blur slider and its signal wiring.
- `tools/benchmark_spectrogram.py` — **add an explicit `hop` parameter and
  `--hop` CLI flag** (default 1024). Currently `run_benchmark` hardcodes
  `hop = n_fft // 2`, so at n_fft 4096 it would benchmark hop 2048 and no longer
  match the app — invalidating it as a litmus. The hop must be threaded through
  the same way as in the app so the benchmark measures the real configuration.
- `tests/` — rewrite blur tests (feature removed); keep the smooth-gradient test
  (now satisfied by `W`); add resampler tests; update settings/panel tests for
  the removed blur control.

## Verification

1. **Latency guard (autonomous, harness):** re-run
   `python -m tools.benchmark_spectrogram --bins 1024 --n-fft 4096 --hop 1024 --duration 30`.
   Must hold **≥30 FPS and ≤120ms p95 glass-to-glass latency**.
   Dropping the per-frame full-buffer blur should *help* latency, partly paying
   for the bigger FFT.
2. **Objective resolution check (new, machine-checkable):** a test feeds two
   closely-spaced sine tones through the analysis + resampler and asserts they
   render as two separable peaks (peak–valley–peak) in the display column at a
   defined separation. Turns part of "crisp" into a regression guard.
3. **Visual checkpoint (Andrew, the real arbiter):** render the same sung
   passage before/after (or sing live) and judge genuine crispness. Per plan.md,
   visual quality is human-judged — iterate-with-checkpoints, not an autonomous
   loop.
4. **Tests green:** `pytest tests/` passes. New resampler tests cover: every row
   of `W` sums to 1 (within tolerance); a flat input spectrum maps to a flat
   display column (energy/level preserved); mapping is monotonic in frequency;
   two-tone separability as above.

## Success criteria

- Spectrogram renders with **no Gaussian blur** and looks crisp to Andrew,
  especially that the low-frequency region is smooth (interpolated) rather than
  stair-stepped or mushy.
- Harness litmus still met at n_fft 4096 / hop 1024.
- `pytest tests/` green, including new resampler + resolution tests.
- Decision recorded afterward: is low-frequency detail good enough, or is the
  Round 2 constant-Q rebuild warranted? (Captured in plan.md `▶ Next up`.)

## Open questions / risks

- **dB-domain averaging** in `W` may look subtly different from the old
  blur-of-dB. Low risk; judged at the visual checkpoint.
- **Longer window time-smear** (~93ms) could soften vibrato onset visibility.
  75% overlap mitigates; the visual checkpoint confirms it's acceptable. If not,
  a fallback is n_fft 3072 or keeping 2048 and accepting the low-freq staircase
  is only fixable by Round 2.
- **Hop parameter threading** is the main integration risk — the time axis,
  scroll rate, and `apply_settings` buffer-resize math all read the hop. All
  must move to the shared parameter together.
