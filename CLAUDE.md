# CLAUDE.md — Voice Trainer

Real-time acoustic feedback for classical singers: a scrolling log-frequency
spectrogram with live pitch and formant (F1/F2) tracking. Desktop app for macOS.

## How the project docs fit together
- **CLAUDE.md** (this file) — durable, high-signal guidance for working in this
  repo. Read every session, so keep it lean. Rewrite it semi-often as the code
  and our conventions evolve.
- **[plan.md](plan.md)** — the master spec + roadmap: what we're building and
  why, what's shipped, what's next. Update when goals or priorities change.
  **To start a work session, read its `▶ Next up` section first** — it names the
  next concrete task so a fresh session can begin without re-planning.
- **[Lessons.md](Lessons.md)** — running log of wrong turns and mistakes so we
  don't repeat them. Prune stale entries; when a lesson proves durable, promote
  it into this file as a standing rule.

## Prime directive
- **Never reference "VoceVista" anywhere** — code, comments, docs, commit
  messages, PR/issue text. This is a free alternative to a commercial tool;
  describe the inspiration generically ("professional voice-analysis software")
  if it must be described at all. The repo is public — history and messages are
  world-readable.
- **Never commit copyrighted source material** — e.g. the Berton Coffin vowel-chart
  photos or Kenneth Bozeman's *Practical Vocal Acoustics* text. Implement the
  underlying acoustics, cite the authors, and keep source scans out of the repo
  (they live at `~/Desktop/passaggiatta/`, local only). See [plan.md](plan.md) Goal 2.

## Stack
- Python 3, PySide6 (Qt), pyqtgraph, numpy, scipy, matplotlib
- Audio input via sounddevice / portaudio
- Packaged as a macOS `.app` via PyInstaller (`VoiceTrainer.spec`)

## Commands
```bash
source venv/bin/activate         # activate the virtualenv (once per shell)
python main.py                   # run in development
pytest tests/ -v                 # run tests (expect 28 passed)
./build_app.sh                   # build dist/VoiceTrainer.app
```
First-time setup: `brew install portaudio`, then `pip install -r requirements.txt`.

## Architecture
- `audio/capture.py`  — microphone capture on a background thread
- `audio/analysis.py` — DSP: spectrogram, pitch (f0), formants (F1/F2)
- `ui/spectrogram.py` — scrolling log-frequency spectrogram widget
- `ui/pitch_display.py` — pitch readout widget
- `ui/app.py`         — main window; wires widgets and settings together
- `main.py`           — entry point
- `tools/benchmark_spectrogram.py` — perf litmus harness (FPS + glass-to-glass
  latency at a given bin count) for the Goal 1a loop. Run via
  `python -m tools.benchmark_spectrogram --bins 2048 --duration 30`.
- Visual settings (colormap, dB range, dot sizes, background) persist via `AppSettings`.

## Conventions
- **Commits:** Conventional Commits — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`.
- **Branches:** descriptive and prefixed — `feat/…`, `fix/…`, `docs/…`. Work on a
  branch, open a PR into `main`; don't commit directly to `main`.
- **Tests:** keep `pytest tests/` green; add tests for new DSP logic.
- **Privacy:** this repo uses a repo-local git identity with a GitHub `noreply`
  email. Never reintroduce `/Users/<name>` absolute paths or personal emails into
  tracked files.

## Maintenance
Rewrite this file semi-often — when commands, architecture, or conventions drift,
or when a [Lessons.md](Lessons.md) entry hardens into a standing rule. Keep it
short and high-signal; it costs context every session.
