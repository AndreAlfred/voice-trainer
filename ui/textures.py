"""
ui/textures.py — Procedurally generated texture assets for the theme.

CD-ROM-era skeuomorphism needs bitmaps, not gradients: parchment fiber,
marble veining, walnut grain, sandstone brick, and the fountain-pen-nib
slider handle are generated here (numpy noise + QPainter), cached as PNGs
under ~/.voicetrainer/theme_cache/, and referenced by the stylesheet via
url().

All generators are deterministic (fixed RNG seeds) and the noise textures
are seamlessly tileable (smoothing uses wrap-around boundaries).

Call ensure_textures() after QApplication exists; it generates any missing
files and returns {name: absolute_path}.
"""

from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

from PySide6.QtCore import QPointF
from PySide6.QtGui import (
    QImage, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath,
)

CACHE_DIR = Path.home() / ".voicetrainer" / "theme_cache"

# Bump to invalidate cached PNGs when a generator changes
_VERSION = "v1"


# ---------------------------------------------------------------------------
# Noise helpers
# ---------------------------------------------------------------------------

def _noise(shape, sigma, seed) -> np.ndarray:
    """Smoothed, tileable noise normalized to 0..1."""
    rng = np.random.default_rng(seed)
    n = gaussian_filter(rng.standard_normal(shape), sigma, mode="wrap")
    n -= n.min()
    peak = n.max()
    return n / peak if peak > 0 else n


def _save_rgb(arr: np.ndarray, path: Path) -> None:
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    h, w, _ = arr.shape
    data = arr.tobytes()
    QImage(data, w, h, 3 * w, QImage.Format.Format_RGB888).copy().save(str(path))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def _gen_parchment(path: Path) -> None:
    """Aged parchment: broad stains, fine grain, directional fibers."""
    s = 512
    base = np.array([242.0, 232.0, 213.0])
    stain_col = np.array([205.0, 182.0, 140.0])

    mottle = _noise((s, s), 26, seed=11) - 0.5      # broad water stains
    grain = _noise((s, s), 1.2, seed=12) - 0.5      # fine tooth
    fiber = _noise((s, s), (14, 2), seed=13) - 0.5  # horizontal fibers

    v = 1.0 + 0.07 * mottle + 0.05 * grain + 0.04 * fiber
    col = base[None, None, :] * v[..., None]

    # Darker mottle areas drift toward umber stain
    stain = np.clip(0.5 - mottle, 0.0, 1.0) * 0.22
    col = col * (1 - stain[..., None]) + stain_col[None, None, :] * stain[..., None]
    _save_rgb(col, path)


def _gen_marble(path: Path) -> None:
    """Cream marble with two scales of gray and warm veining."""
    s = 384
    base = np.array([238.0, 233.0, 224.0])
    cloud = _noise((s, s), 34, seed=21) - 0.5
    col = base[None, None, :] * (1.0 + 0.05 * cloud)[..., None]

    for seed, sigma, width, weight, vein_col in (
        (22, 7, 0.055, 0.55, np.array([128.0, 124.0, 120.0])),   # gray veins
        (23, 3, 0.035, 0.30, np.array([176.0, 156.0, 122.0])),   # warm hairlines
    ):
        v = _noise((s, s), sigma, seed)
        ridge = np.clip(1.0 - np.abs(v - 0.5) / width, 0.0, 1.0) ** 2 * weight
        col = col * (1 - ridge[..., None]) + vein_col[None, None, :] * ridge[..., None]

    grain = (_noise((s, s), 1.0, seed=24) - 0.5) * 8.0
    _save_rgb(col + grain[..., None], path)


def _gen_walnut(path: Path) -> None:
    """Walnut plank: warped growth-ring stripes with fine streaking."""
    h, w = 128, 512
    dark = np.array([58.0, 41.0, 22.0])
    light = np.array([118.0, 84.0, 47.0])

    yy = np.linspace(0.0, 1.0, h)[:, None] * np.ones((1, w))
    warp = _noise((h, w), (10, 60), seed=31)
    rings = np.sin(2 * np.pi * (yy * 6.5 + warp * 2.2)) * 0.5 + 0.5
    t = rings ** 1.4
    col = dark[None, None, :] * (1 - t)[..., None] + light[None, None, :] * t[..., None]

    streak = (_noise((h, w), (1, 26), seed=32) - 0.5) * 26.0
    _save_rgb(col + streak[..., None], path)


def _gen_stone(path: Path) -> None:
    """Sandstone brick facade with mortar joints and per-brick tone."""
    h, w = 128, 256
    bh, bw, mortar = 32, 64, 3
    base = np.array([199.0, 180.0, 148.0])
    mortar_col = np.array([148.0, 136.0, 116.0])

    yy, xx = np.mgrid[0:h, 0:w]
    row = yy // bh
    x_off = (xx + (row % 2) * (bw // 2)) % w
    is_mortar = ((yy % bh) < mortar) | ((x_off % bw) < mortar)

    # Per-brick tone jitter (deterministic)
    rng = np.random.default_rng(41)
    tones = rng.uniform(0.86, 1.10, size=(h // bh + 1, w // bw + 2))
    tone = tones[row, x_off // bw]

    # Slight top-light shading within each brick
    shade = 1.04 - 0.10 * ((yy % bh) / bh)
    grain = (_noise((h, w), 1.5, seed=42) - 0.5) * 0.14 + 1.0

    col = base[None, None, :] * (tone * shade * grain)[..., None]
    col[is_mortar] = mortar_col * (0.95 + 0.1 * grain[is_mortar, None])
    _save_rgb(col, path)


def _gen_nib(path: Path) -> None:
    """Fountain-pen-nib slider handle, pointing down into the groove."""
    w, h = 18, 30
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    nib = QPainterPath()
    nib.moveTo(4, 2)
    nib.lineTo(14, 2)
    nib.lineTo(14, 13)
    nib.lineTo(9, 28)
    nib.lineTo(4, 13)
    nib.closeSubpath()

    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0.0, QColor("#fbf0c8"))
    grad.setColorAt(0.45, QColor("#c9a227"))
    grad.setColorAt(1.0, QColor("#6b4f14"))
    p.setPen(QPen(QColor("#4a3810"), 1.2))
    p.setBrush(QBrush(grad))
    p.drawPath(nib)

    # Slit and breather hole
    p.setPen(QPen(QColor("#4a3810"), 1))
    p.drawLine(QPointF(9, 15.5), QPointF(9, 26.5))
    p.setBrush(QColor("#4a3810"))
    p.drawEllipse(QPointF(9, 14), 1.6, 1.6)

    # Left-edge highlight
    p.setPen(QPen(QColor(255, 246, 214, 170), 1))
    p.drawLine(QPointF(5, 3), QPointF(5, 12.5))
    p.end()
    img.save(str(path))


_GENERATORS = {
    "parchment": _gen_parchment,
    "marble": _gen_marble,
    "walnut": _gen_walnut,
    "stone": _gen_stone,
    "nib": _gen_nib,
}


def ensure_textures() -> dict[str, str]:
    """Generate any missing texture PNGs and return {name: absolute path}."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, gen in _GENERATORS.items():
        path = CACHE_DIR / f"{name}_{_VERSION}.png"
        if not path.exists():
            gen(path)
        paths[name] = str(path)
    return paths
