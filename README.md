# Voice Trainer

Real-time acoustic feedback for classical singers — a scrolling log-frequency
spectrogram with live pitch and formant tracking, wrapped in a
renaissance-skeuomorphic interface. Free, open source, macOS.

## What it shows

- **Scrolling spectrogram** — 80–8,000 Hz on a logarithmic axis, so each
  octave gets equal vertical space (the way the ear hears). Default
  colormap is *inferno*: near-black = quiet, purple/red = moderate,
  yellow = loud.
- **Live pitch readout** — the sung note (e.g. `A4`) and its frequency in Hz.
- **Formant tracking** — F1 dots (vowel openness) and F2 dots (tongue
  front/back position) scroll in sync with the spectrogram.
- **Singer's Formant band** — a gold overlay at 2,000–3,500 Hz; harmonic
  energy landing here is what lets a classical voice carry over an orchestra.

## Two faces

- **Light mode** — renaissance skeuomorphism: the spectrogram hangs in a
  gilded frame on a parchment wall, the current note is stamped into a wax
  seal, sliders ride fountain-pen nibs, and the toolbar is walnut.
- **Dark mode** (☾ toolbar toggle) — a flat midnight instrument panel for
  distraction-free practice.

All visual settings (colormap, dB range, scroll window, dot colors, backdrop,
theme) adjust live from the ⚙ Settings panel and persist between sessions.

## Quick start (macOS app)

1. Build the app (below) or use an existing `VoiceTrainer.app`
2. Drag to `/Applications`
3. Right-click → Open (first launch only — bypasses Gatekeeper for unsigned apps)
4. Grant microphone access when prompted

## Building from source

Prerequisites:

```bash
brew install portaudio        # requires Homebrew: https://brew.sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Build:

```bash
./build_app.sh                # output: dist/VoiceTrainer.app
```

## Development

```bash
source venv/bin/activate      # once per shell
python main.py                # run the app
pytest tests/                 # run the test suite (expect all green)
python -m tools.benchmark_spectrogram --bins 2048 --duration 30
                              # performance harness: FPS + latency
```

## Project structure

| Path | Purpose |
|---|---|
| `audio/capture.py` | microphone capture on a background thread |
| `audio/analysis.py` | DSP: spectrogram, pitch (f0), formants (F1/F2) |
| `ui/spectrogram.py` | scrolling log-frequency spectrogram widget |
| `ui/pitch_display.py` | pitch readout (wax seal / classic label) |
| `ui/app.py` | main window and theme switching |
| `ui/theme.py` | light/dark palettes and stylesheets |
| `ui/ornaments.py` | custom-painted gilded frame, wax seal, hover glow |
| `ui/textures.py` | procedural parchment/marble/walnut/stone textures |
| `ui/settings.py`, `ui/settings_panel.py` | persistent visual settings + panel |
| `tools/benchmark_spectrogram.py` | FPS / glass-to-glass latency harness |
| `main.py` | entry point |

## License

[MIT](LICENSE)
