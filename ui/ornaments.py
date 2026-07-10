"""
ui/ornaments.py — Custom-painted skeuomorphic widgets for the renaissance theme.

Flat stylesheets can't do gold leaf. These widgets paint their own materials:

  GildedFrame — wraps any widget in a picture-frame of gold-leaf gradient
                bands with a bead chain, dentil molding, and petaled corner
                rosettes. The spectrogram hangs in one like an old master.
  WaxSeal     — a vermillion wax seal on a lapis ribbon, stamped with the
                current note name; cools to gray wax in silence.
  HoverGlow   — event filter that adds a warm gold glow to a widget on
                hover (attach with attach_glow()).
"""

import math

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QObject, QEvent, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QRadialGradient,
)

from ui import theme


# ---------------------------------------------------------------------------
# Hover glow
# ---------------------------------------------------------------------------

class HoverGlow(QObject):
    """Adds a warm gold aura to the watched widget while hovered."""

    def __init__(self, color: str = theme.GLOW, radius: int = 24,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._color = color
        self._radius = radius

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Enter:
            glow = QGraphicsDropShadowEffect(obj)
            glow.setOffset(0, 0)
            glow.setBlurRadius(self._radius)
            glow.setColor(QColor(self._color))
            obj.setGraphicsEffect(glow)
        elif event.type() in (QEvent.Type.Leave, QEvent.Type.Hide):
            obj.setGraphicsEffect(None)
        return False


def attach_glow(widget: QWidget, color: str = theme.GLOW,
                radius: int = 24) -> None:
    """Install a HoverGlow filter on widget (kept alive as its child)."""
    widget.installEventFilter(HoverGlow(color, radius, parent=widget))


# ---------------------------------------------------------------------------
# Gilded frame
# ---------------------------------------------------------------------------

class GildedFrame(QWidget):
    """Paints an ornate gold-leaf picture frame around a single child widget."""

    FRAME = 20   # thickness of the gold band, px

    def __init__(self, inner: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        m = self.FRAME + 5
        lay.setContentsMargins(m, m, m, m)
        lay.addWidget(inner)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)

        # Gold band: diagonal gradient with a double sheen, like light
        # raking across leafed molding.
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.00, QColor("#f4e2a4"))
        grad.setColorAt(0.18, QColor("#caa53a"))
        grad.setColorAt(0.38, QColor("#8a6a1f"))
        grad.setColorAt(0.55, QColor("#eed489"))
        grad.setColorAt(0.78, QColor("#a5842a"))
        grad.setColorAt(1.00, QColor("#6b4f14"))
        p.setPen(QPen(QColor("#4a3810"), 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(r, 9, 9)

        # Outer bevel highlight just inside the edge
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(253, 243, 205, 160), 1))
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 8, 8)

        # Bead chain along the middle of the band
        self._bead_chain(p, r.adjusted(6.5, 6.5, -6.5, -6.5))

        # Dentil molding along the sight edge
        inner = r.adjusted(self.FRAME, self.FRAME, -self.FRAME, -self.FRAME)
        self._dentils(p, inner.adjusted(-5, -5, 5, 5))

        # Rebate around the "canvas": thin gold fillet + dark sight edge
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(247, 231, 181, 200), 1))
        p.drawRoundedRect(inner.adjusted(-2, -2, 2, 2), 5, 5)
        p.setPen(QPen(QColor("#40320e"), 2))
        p.drawRoundedRect(inner, 4, 4)

        # Petaled corner rosettes over everything
        for corner in (
            r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()
        ):
            cx = corner.x() + (self.FRAME / 2 + 1) * (1 if corner.x() < r.center().x() else -1)
            cy = corner.y() + (self.FRAME / 2 + 1) * (1 if corner.y() < r.center().y() else -1)
            self._rosette(p, QPointF(cx, cy), self.FRAME / 2 + 1)

    @staticmethod
    def _bead_chain(p: QPainter, band: QRectF, spacing: float = 9.0) -> None:
        """Rows of tiny gold beads along each straight run of the band."""
        margin = 16.0
        runs = [
            # (start point, dx, dy, length)
            (QPointF(band.left() + margin, band.top()), 1, 0,
             band.width() - 2 * margin),
            (QPointF(band.left() + margin, band.bottom()), 1, 0,
             band.width() - 2 * margin),
            (QPointF(band.left(), band.top() + margin), 0, 1,
             band.height() - 2 * margin),
            (QPointF(band.right(), band.top() + margin), 0, 1,
             band.height() - 2 * margin),
        ]
        for start, dx, dy, length in runs:
            n = max(int(length // spacing), 0)
            for i in range(n + 1):
                c = QPointF(start.x() + dx * i * spacing,
                            start.y() + dy * i * spacing)
                p.setPen(QPen(QColor("#5a4312"), 0.8))
                p.setBrush(QColor("#8a6a1f"))
                p.drawEllipse(c, 2.2, 2.2)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#f7e7b5"))
                p.drawEllipse(QPointF(c.x() - 0.6, c.y() - 0.6), 1.0, 1.0)

    @staticmethod
    def _dentils(p: QPainter, edge: QRectF, step: float = 11.0) -> None:
        """Alternating notches (dentil molding) just outside the sight edge."""
        pen = QPen(QColor(74, 56, 16, 150), 1)
        p.setPen(pen)
        x = edge.left() + 8
        while x < edge.right() - 8:
            p.drawLine(QPointF(x, edge.top() - 2), QPointF(x, edge.top() + 2))
            p.drawLine(QPointF(x, edge.bottom() - 2), QPointF(x, edge.bottom() + 2))
            x += step
        y = edge.top() + 8
        while y < edge.bottom() - 8:
            p.drawLine(QPointF(edge.left() - 2, y), QPointF(edge.left() + 2, y))
            p.drawLine(QPointF(edge.right() - 2, y), QPointF(edge.right() + 2, y))
            y += step

    @staticmethod
    def _rosette(p: QPainter, center: QPointF, radius: float) -> None:
        """Eight-petaled acanthus rosette with a domed center boss."""
        petal_grad = QLinearGradient(center.x(), center.y() - radius,
                                     center.x(), center.y() + radius)
        petal_grad.setColorAt(0.0, QColor("#eed489"))
        petal_grad.setColorAt(1.0, QColor("#8a6a1f"))
        p.setPen(QPen(QColor("#4a3810"), 1))
        p.setBrush(QBrush(petal_grad))
        for i in range(8):
            p.save()
            p.translate(center)
            p.rotate(i * 45.0)
            p.drawEllipse(QRectF(-radius * 0.28, -radius * 1.05,
                                 radius * 0.56, radius * 0.95))
            p.restore()
        boss = QRadialGradient(center.x() - radius * 0.25,
                               center.y() - radius * 0.25, radius)
        boss.setColorAt(0.0, QColor("#fbf0c8"))
        boss.setColorAt(0.6, QColor("#c9a227"))
        boss.setColorAt(1.0, QColor("#6b4f14"))
        p.setBrush(QBrush(boss))
        p.drawEllipse(center, radius * 0.5, radius * 0.5)


# ---------------------------------------------------------------------------
# Wax seal
# ---------------------------------------------------------------------------

class WaxSeal(QWidget):
    """A charter seal on a lapis ribbon, stamped with the current note.

    Crimson and glossy while a pitch is sounding; cold gray wax when
    silent. Call set_note("A4") or set_note(None).
    """

    SIZE = 104
    SCALLOPS = 14

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._note: str | None = None

    def set_note(self, note: str | None) -> None:
        if note != self._note:
            self._note = note
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2 - 4)
        R = self.SIZE * 0.31

        # --- Lapis ribbon tails hanging behind the seal ---
        for angle in (-26.0, 26.0):
            p.save()
            p.translate(c)
            p.rotate(angle)
            ribbon = QPainterPath()
            ribbon.moveTo(-8, R * 0.3)
            ribbon.lineTo(8, R * 0.3)
            ribbon.lineTo(8, R + 22)
            ribbon.lineTo(0, R + 13)          # swallow-tail notch
            ribbon.lineTo(-8, R + 22)
            ribbon.closeSubpath()
            rg = QLinearGradient(0, 0, 0, R + 22)
            rg.setColorAt(0.0, QColor("#4266bd"))
            rg.setColorAt(1.0, QColor("#16295c"))
            p.setPen(QPen(QColor("#101d40"), 1))
            p.setBrush(QBrush(rg))
            p.drawPath(ribbon)
            p.restore()

        # --- Wax body ---
        if self._note is not None:
            hi, body, rim = "#f07a4e", "#c0341c", "#8c2012"
            edge_line = QColor("#5e130a")
            text_color = QColor("#ffe3cf")
        else:
            hi, body, rim = "#c2b193", "#8d7b5c", "#67593f"
            edge_line = QColor("#4a3f2c")
            text_color = QColor("#efe5d0")

        wax = QRadialGradient(c.x() - R * 0.35, c.y() - R * 0.4, R * 2.2)
        wax.setColorAt(0.0, QColor(hi))
        wax.setColorAt(0.55, QColor(body))
        wax.setColorAt(1.0, QColor(rim))
        p.setPen(QPen(edge_line, 1.2))
        p.setBrush(QBrush(wax))

        # Regular scalloped rim — a pressed rosette, not random drips
        scallop_r = R * 0.24
        for i in range(self.SCALLOPS):
            a = 2 * math.pi * i / self.SCALLOPS
            p.drawEllipse(
                QPointF(c.x() + math.cos(a) * R, c.y() + math.sin(a) * R),
                scallop_r, scallop_r,
            )
        p.drawEllipse(c, R + scallop_r * 0.55, R + scallop_r * 0.55)

        # --- Stamp impression ---
        # Recessed double ring
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(edge_line, 1.6))
        p.drawEllipse(c, R * 0.80, R * 0.80)
        p.setPen(QPen(QColor(255, 235, 220, 90), 1))
        p.drawEllipse(c, R * 0.80 - 1.6, R * 0.80 - 1.6)

        # Radial fluting between ring and rim
        p.setPen(QPen(QColor(edge_line.red(), edge_line.green(),
                             edge_line.blue(), 90), 1))
        for i in range(24):
            a = 2 * math.pi * i / 24
            p.drawLine(
                QPointF(c.x() + math.cos(a) * R * 0.86,
                        c.y() + math.sin(a) * R * 0.86),
                QPointF(c.x() + math.cos(a) * R * 0.98,
                        c.y() + math.sin(a) * R * 0.98),
            )

        # --- Aero gloss pooling across the upper face ---
        gloss = QLinearGradient(c.x(), c.y() - R, c.x(), c.y())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 95))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(gloss))
        p.drawEllipse(QRectF(c.x() - R * 0.78, c.y() - R * 0.9,
                             R * 1.56, R * 0.95))

        # --- Stamped note name, embossed ---
        text = self._note if self._note is not None else "—"
        size = 23 if len(text) <= 2 else 18
        p.setFont(QFont(theme.SERIF_FAMILY, size, QFont.Weight.Bold))
        rect = QRectF(c.x() - R, c.y() - R, R * 2, R * 2)
        p.setPen(QColor(0, 0, 0, 130))
        p.drawText(rect.translated(1.2, 1.5), Qt.AlignmentFlag.AlignCenter, text)
        p.setPen(text_color)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
