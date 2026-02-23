# Voice Trainer

Real-time voice analysis tool for classical singers.

## Quick Start (macOS App)

1. Build the app (see below) or use an existing `VoiceTrainer.app`
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
chmod +x build_app.sh   # only needed once after cloning
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
