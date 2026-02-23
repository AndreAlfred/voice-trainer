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
