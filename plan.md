# Voice Trainer — Master Plan

The single source of truth for what we're building and why. This is the map;
granular, trackable work lives in **GitHub Issues**. See also
[CLAUDE.md](CLAUDE.md) (working conventions) and [Lessons.md](Lessons.md)
(mistakes log).

## Vision
Give classical singers real-time, visual feedback on their voice — pitch,
resonance, and vowel formants — as a free, open desktop tool. Grow incrementally
from a solid spectrogram core toward richer pedagogical features.

## Current state (shipped)
- Real-time scrolling spectrogram (80–8000 Hz, logarithmic frequency)
- Fundamental frequency display (Hz + note name)
- Custom colormap with a visible quiet-sound floor (−60 dB)
- Singer's Formant highlight band (2,000–3,500 Hz)
- F1/F2 formant rolling-dot overlay
- Visual customization sidebar — colormap presets, dB range, dot sizes,
  background — all persisted
- Smooth topographic rendering (linear interpolation + Gaussian blur, 1024 log bins)
- Packaged as a macOS `.app` (PyInstaller)

## Active roadmap (next up)
1. **IPA vowel display** — map live (F1, F2) → nearest IPA vowel symbol and show
   it in the UI, with confidence thresholding so it only appears when estimates
   are stable. Reference: Peterson & Barney (1952) vowel formant data.
2. **Color scheme exploration** — evaluate alternative spectrogram palettes that
   preserve quiet-sound contrast (real color at the −60 dB floor) and stay
   legible under the gold Singer's Formant band.

## Backlog (not yet designed)
- Vibrato rate + extent tracking
- Vowel-modification recommendations (F1/F2 + voice type)
- Time-scale zoom for the scrolling window (narrow/widen)
- Session recording + playback
- Reference overlays (compare against a recording)
- Higher FFT resolution/overlap (n_fft 4096, 75% overlap)

## How we track work
- **This file** = the map: vision, priorities, what's done.
- **GitHub Issues** = the granular units for each roadmap item (one issue per feature).
- **docs/plans/** = detailed design + implementation docs, per feature (historical and active).

## Working agreement (learning goals)
This project doubles as a place to build professional developer habits. Favor:
branches + pull requests over direct commits to `main`, Conventional Commit
messages, tests kept green, and capturing every wrong turn in
[Lessons.md](Lessons.md).
