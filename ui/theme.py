"""
ui/theme.py — Renaissance-skeuomorphic theme (frutiger aero, renaissance materials).

Single source of truth for the look of everything around the spectrogram's
heat map: window chrome, toolbar, pitch readout, settings panel, plot axes.
Glossy dimensional controls in renaissance materials — gold leaf, walnut,
lapis lazuli, vermillion wax, parchment.

The spectrogram's amplitude colormap and formant-dot colors are functional
(they encode the analysis) and are deliberately NOT defined here.
Custom-painted ornaments (gilded frame, wax seal) live in ui/ornaments.py.
"""

# ---------------------------------------------------------------------------
# Palette — renaissance pigments and materials
# ---------------------------------------------------------------------------

PARCHMENT       = "#f2e8d5"   # aged paper ground
PARCHMENT_LIGHT = "#f9f2e3"   # raised panels / readouts
PARCHMENT_DARK  = "#e4d5b7"   # recessed areas, hover states
UMBER           = "#8a6f47"   # raw umber — borders and frames
SEPIA           = "#3b2f1e"   # ink — primary text
SEPIA_FAINT     = "#9c8a6a"   # faded ink — secondary text, silence
ULTRAMARINE     = "#274690"   # lapis lazuli — emphasis, active states
VERMILLION      = "#c8371f"   # rubrication red — section headers, alerts

# Gold leaf / polished brass
BRASS_LIGHT     = "#f4e2a4"
BRASS           = "#c9a227"
BRASS_DARK      = "#8a6a1f"
BRASS_DEEP      = "#6b4f14"

# Walnut rail (toolbar)
WALNUT_LIGHT    = "#7a5a35"
WALNUT          = "#5c4326"
WALNUT_DARK     = "#3f2d18"

# Palatino ships with macOS and is named for Giambattista Palatino,
# a 16th-century calligrapher — the most renaissance font a Mac has.
SERIF_FAMILY = "Palatino"

# Typographic fleurons for headers and labels
FLEURON = "❦"
RUBRIC_LEAF = "❧"

# ---------------------------------------------------------------------------
# Reusable gradient snippets (Qt stylesheet syntax)
# ---------------------------------------------------------------------------
# The "aero gloss" trick: lightness doubles back partway down the surface,
# which reads as reflection on a curved solid rather than a flat tint.

_GLOSS_BRASS = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #fbf0c8, stop:0.45 {BRASS_LIGHT},"
    f" stop:0.5 {BRASS}, stop:1 {BRASS_DARK})"
)
_GLOSS_BRASS_PRESSED = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {BRASS_DARK}, stop:0.5 {BRASS}, stop:1 {BRASS_LIGHT})"
)
_GLOSS_LAPIS = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #8fa8e8, stop:0.45 #4266bd,"
    f" stop:0.5 {ULTRAMARINE}, stop:1 #16295c)"
)
_WALNUT_RAIL = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {WALNUT_LIGHT}, stop:0.12 {WALNUT},"
    f" stop:0.9 {WALNUT_DARK}, stop:1 #2b1e0f)"
)
_PARCHMENT_WALL = (
    "qlineargradient(x1:0, y1:0, x2:0.3, y2:1,"
    f" stop:0 {PARCHMENT_LIGHT}, stop:0.5 {PARCHMENT}, stop:1 {PARCHMENT_DARK})"
)
_BRASS_PLAQUE = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {BRASS_LIGHT}, stop:0.5 #d9bc6a, stop:1 {BRASS})"
)
_BRASS_KNOB = (
    "qradialgradient(cx:0.38, cy:0.32, radius:0.9, fx:0.38, fy:0.32,"
    f" stop:0 #fbf0c8, stop:0.55 {BRASS}, stop:1 {BRASS_DEEP})"
)

# ---------------------------------------------------------------------------
# Application stylesheet
# ---------------------------------------------------------------------------

APP_STYLESHEET = f"""
QMainWindow {{
    background: {_PARCHMENT_WALL};
}}

QWidget {{
    color: {SEPIA};
    font-family: "{SERIF_FAMILY}";
}}

QLabel {{
    background: transparent;
}}

/* --- Walnut toolbar rail with glossy inlaid buttons --- */
QToolBar {{
    background: {_WALNUT_RAIL};
    border: none;
    border-bottom: 2px solid {BRASS_DEEP};
    spacing: 8px;
    padding: 4px 10px;
}}
QToolBar QToolButton {{
    background: {_GLOSS_BRASS};
    color: {SEPIA};
    border: 1px solid {BRASS_DEEP};
    border-radius: 9px;
    padding: 3px 14px;
    font-weight: bold;
}}
QToolBar QToolButton:hover {{
    border-color: #fbf0c8;
}}
QToolBar QToolButton:pressed {{
    background: {_GLOSS_BRASS_PRESSED};
}}
QToolBar QToolButton:checked {{
    background: {_GLOSS_LAPIS};
    color: {PARCHMENT_LIGHT};
    border-color: #16295c;
}}

/* --- Settings dock: brass plaque title over parchment --- */
QDockWidget {{
    color: {SEPIA};
    font-weight: bold;
}}
QDockWidget::title {{
    background: {_BRASS_PLAQUE};
    border: 1px solid {BRASS_DEEP};
    border-radius: 3px;
    padding: 6px;
    text-align: center;
}}

/* --- Glossy parchment-brass buttons --- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fefaef, stop:0.45 {PARCHMENT_LIGHT},
        stop:0.5 {PARCHMENT}, stop:1 {PARCHMENT_DARK});
    color: {SEPIA};
    border: 1px solid {UMBER};
    border-radius: 8px;
    padding: 4px 10px;
}}
QPushButton:hover {{
    border-color: {BRASS_DARK};
    color: {ULTRAMARINE};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
}}

/* --- Checkboxes: lapis cabochon when set --- */
QCheckBox {{
    color: {SEPIA};
    spacing: 7px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {UMBER};
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
}}
QCheckBox::indicator:checked {{
    background: {_GLOSS_LAPIS};
    border-color: #16295c;
}}

/* --- Sliders: recessed channel, gold fill, turned-brass knob --- */
QSlider {{
    background: transparent;
    height: 22px;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #c9b892, stop:0.5 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
    border: 1px solid {UMBER};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRASS_LIGHT}, stop:0.5 {BRASS}, stop:1 {BRASS_DARK});
    border: 1px solid {BRASS_DEEP};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 9px;
    background: {_BRASS_KNOB};
    border: 1px solid {BRASS_DEEP};
}}
QSlider::handle:horizontal:hover {{
    border-color: #fbf0c8;
}}

/* --- Scroll areas / scrollbars --- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: {PARCHMENT_DARK};
    width: 12px;
    margin: 0;
    border-left: 1px solid {UMBER};
}}
QScrollBar::handle:vertical {{
    background: {_GLOSS_BRASS};
    border: 1px solid {BRASS_DEEP};
    border-radius: 5px;
    min-height: 26px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""

# Title banner: illuminated header strip above the framed spectrogram
TITLE_STYLESHEET = f"""
color: {ULTRAMARINE};
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #fdf7e7, stop:0.55 {PARCHMENT_LIGHT}, stop:1 {PARCHMENT_DARK});
letter-spacing: 6px;
border: 1px solid {UMBER};
border-bottom: 2px solid {BRASS};
border-radius: 6px;
"""

# Engraved brass plate for the frequency readout
BRASS_PLATE_STYLESHEET = f"""
background: {_BRASS_PLAQUE};
color: {SEPIA};
border: 1px solid {BRASS_DEEP};
border-radius: 6px;
padding: 6px 16px;
"""
