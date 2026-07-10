"""
ui/theme.py — Renaissance-skeuomorphic theme (frutiger aero, renaissance materials).

Single source of truth for the look of everything around the spectrogram's
heat map: window chrome, toolbar, pitch readout, settings panel, plot axes.
CD-ROM-era skeuomorphism: tiled procedural textures (parchment, marble,
walnut, sandstone — see ui/textures.py), chunky ridge/inset bevels, glossy
brass and lapis gradients, fountain-pen-nib slider handles.

The spectrogram's amplitude colormap and formant-dot colors are functional
(they encode the analysis) and are deliberately NOT defined here.
Custom-painted ornaments (gilded frame, wax seal, hover glow) live in
ui/ornaments.py.

Call build_app_stylesheet() after QApplication exists (it generates the
texture PNGs on first run).
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

# Hover glow (gauche and proud)
GLOW            = "#ffdf8e"

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
_GLOSS_BRASS_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #fff8dc, stop:0.45 #f8ecc0,"
    f" stop:0.5 #dcb945, stop:1 {BRASS})"
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
_GLOSS_PARCHMENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #fefaef, stop:0.45 {PARCHMENT_LIGHT},"
    f" stop:0.5 {PARCHMENT}, stop:1 {PARCHMENT_DARK})"
)
_GLOSS_PARCHMENT_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #fffdf5, stop:0.45 #fdf8ea,"
    f" stop:0.5 {PARCHMENT_LIGHT}, stop:1 {PARCHMENT})"
)
_BRASS_PLAQUE = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {BRASS_LIGHT}, stop:0.5 #d9bc6a, stop:1 {BRASS})"
)


def build_app_stylesheet() -> str:
    """Assemble the app stylesheet, generating texture PNGs if needed.

    Must be called after QApplication exists.
    """
    from ui.textures import ensure_textures
    tex = ensure_textures()

    return f"""
QMainWindow {{
    background-image: url("{tex['parchment']}");
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
    background-image: url("{tex['walnut']}");
    border: none;
    border-bottom: 3px ridge {BRASS_DEEP};
    spacing: 8px;
    padding: 4px 10px;
}}
QToolBar QToolButton {{
    background: {_GLOSS_BRASS};
    color: {SEPIA};
    border: 2px ridge {BRASS_DEEP};
    border-radius: 9px;
    padding: 3px 14px;
    font-weight: bold;
}}
QToolBar QToolButton:hover {{
    background: {_GLOSS_BRASS_HOVER};
    border: 2px ridge {GLOW};
}}
QToolBar QToolButton:pressed {{
    background: {_GLOSS_BRASS_PRESSED};
    border-style: inset;
}}
QToolBar QToolButton:checked {{
    background: {_GLOSS_LAPIS};
    color: {PARCHMENT_LIGHT};
    border: 2px inset #16295c;
}}

/* --- Settings dock: marble plaque title over parchment --- */
QDockWidget {{
    color: {SEPIA};
    font-weight: bold;
}}
QDockWidget::title {{
    background-image: url("{tex['marble']}");
    border: 2px ridge {BRASS_DARK};
    border-radius: 3px;
    padding: 7px;
    text-align: center;
}}

/* --- Settings panel wall: parchment sheet --- */
#settings_panel {{
    background-image: url("{tex['parchment']}");
    border-left: 2px groove {BRASS_DARK};
}}

/* --- Title banner: engraved marble lintel --- */
#title_banner {{
    color: {ULTRAMARINE};
    background-image: url("{tex['marble']}");
    letter-spacing: 6px;
    border: 2px ridge {BRASS};
    border-radius: 6px;
}}

/* --- Pitch readout shelf: sandstone ledge --- */
#pitch_shelf {{
    background-image: url("{tex['stone']}");
    border: 3px ridge {BRASS_DARK};
    border-radius: 8px;
}}

/* --- Glossy parchment-brass buttons with gauche hover glow --- */
QPushButton {{
    background: {_GLOSS_PARCHMENT};
    color: {SEPIA};
    border: 2px ridge {UMBER};
    border-radius: 6px;
    padding: 4px 10px;
}}
QPushButton:hover {{
    background: {_GLOSS_PARCHMENT_HOVER};
    border: 2px ridge {GLOW};
    color: {ULTRAMARINE};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
    border-style: inset;
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
    border: 2px inset {UMBER};
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
}}
QCheckBox::indicator:checked {{
    background: {_GLOSS_LAPIS};
    border: 2px ridge {BRASS_DARK};
}}

/* --- Sliders: recessed channel, gold fill, fountain-pen nib --- */
QSlider {{
    background: transparent;
    height: 32px;
}}
QSlider::groove:horizontal {{
    height: 8px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b9a67e, stop:0.5 {PARCHMENT_DARK}, stop:1 {PARCHMENT_LIGHT});
    border: 2px groove {UMBER};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRASS_LIGHT}, stop:0.5 {BRASS}, stop:1 {BRASS_DARK});
    border: 2px groove {BRASS_DEEP};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    image: url("{tex['nib']}");
    width: 18px;
    margin: -12px 0;
    background: transparent;
    border: none;
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


# Engraved brass plate for the frequency readout
BRASS_PLATE_STYLESHEET = f"""
background: {_BRASS_PLAQUE};
color: {SEPIA};
border: 2px ridge {BRASS_DEEP};
border-radius: 6px;
padding: 6px 16px;
"""
