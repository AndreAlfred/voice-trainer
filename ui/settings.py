"""
ui/settings.py — Application settings: data model and JSON persistence.

AppSettings is the single source of truth for all visual parameters.
Saved automatically to ~/.voicetrainer/settings.json on every change.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

SETTINGS_DIR  = Path.home() / ".voicetrainer"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class AppSettings:
    # Colormap — three RGB tuples for the pyqtgraph ColorMap stops
    color_floor: tuple = (13, 79, 82)        # dark teal   #0d4f52
    color_mid:   tuple = (212, 80, 10)       # warm orange #d4500a
    color_peak:  tuple = (255, 240, 160)     # pale yellow #fff0a0

    # dB display range
    db_floor:   float = -60.0
    db_ceiling: float =   0.0

    # Scrolling window duration in seconds
    display_seconds: float = 8.0

    # Formant dot appearance
    f1_color: tuple = (100, 180, 255)   # light blue
    f2_color: tuple = (80,  240, 120)   # bright green
    dot_size:   int = 4

    # Overlay visibility
    singers_formant_visible: bool = True

    # Window / plot background
    background_color: tuple = (26, 26, 46)  # #1a1a2e

    @classmethod
    def load(cls) -> "AppSettings":
        """Load from SETTINGS_FILE. Returns defaults if file is missing or corrupt."""
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            for key in ("color_floor", "color_mid", "color_peak",
                        "f1_color", "f2_color", "background_color"):
                if key in data:
                    data[key] = tuple(data[key])
            valid = {k: v for k, v in data.items()
                     if k in cls.__dataclass_fields__}
            return cls(**valid)
        except Exception:
            return cls()

    def save(self) -> None:
        """Save to SETTINGS_FILE atomically. Creates directory if needed."""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(asdict(self), f, indent=2)
        tmp.replace(SETTINGS_FILE)
