"""
ui/ornaments.py — Custom-painted skeuomorphic widgets for the renaissance theme.

Flat stylesheets can't do gold leaf. These widgets paint their own materials:

  GildedFrame — wraps any widget in a picture-frame of gold-leaf gradient
                bands, bevels, and corner rosettes. The spectrogram hangs
                in one like an old master in a gallery.
  WaxSeal     — a glossy vermillion wax seal that stamps the current note
                name; fades to cold gray wax in silence.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QLinearGradient, QRadialGradient,
)

from ui import theme


class GildedFrame(QWidget):
    """Paints a gold-leaf picture frame around a single child widget."""

    FRAME = 16   # thickness of the gold band, px

    def __init__(self, inner: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        m = self.FRAME + 4
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

        # Rebate around the "canvas": dark sight edge + thin gold fillet
        inner = r.adjusted(self.FRAME, self.FRAME, -self.FRAME, -self.FRAME)
        p.setPen(QPen(QColor(247, 231, 181, 200), 1))
        p.drawRoundedRect(inner.adjusted(-2, -2, 2, 2), 5, 5)
        p.setPen(QPen(QColor("#40320e"), 2))
        p.drawRoundedRect(inner, 4, 4)

        # Corner rosettes — little turned medallions
        for corner in (
            r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()
        ):
            cx = corner.x() + (self.FRAME / 2 + 1) * (1 if corner.x() < r.center().x() else -1)
            cy = corner.y() + (self.FRAME / 2 + 1) * (1 if corner.y() < r.center().y() else -1)
            self._rosette(p, QPointF(cx, cy), self.FRAME / 2 - 1)

    @staticmethod
    def _rosette(p: QPainter, center: QPointF, radius: float) -> None:
        glow = QRadialGradient(center.x() - radius * 0.3,
                               center.y() - radius * 0.3, radius * 2)
        glow.setColorAt(0.0, QColor("#f7e7b5"))
        glow.setColorAt(0.55, QColor("#c9a227"))
        glow.setColorAt(1.0, QColor("#6b4f14"))
        p.setPen(QPen(QColor("#4a3810"), 1))
        p.setBrush(QBrush(glow))
        p.drawEllipse(center, radius, radius)
        p.setPen(QPen(QColor("#8a6a1f"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, radius * 0.55, radius * 0.55)


class WaxSeal(QWidget):
    """A round wax seal stamped with the current note name.

    Vermillion and glossy while a pitch is sounding; cold gray wax when
    silent. Call set_note("A4") or set_note(None).
    """

    SIZE = 84

    # Fixed blob layout (angle in degrees, radial offset, blob radius) so
    # the seal's drips don't jitter between repaints.
    _BLOBS = [
        (12, 1.00, 7.5), (55, 0.96, 6.0), (98, 1.03, 8.0),
        (137, 0.97, 5.5), (176, 1.02, 7.0), (214, 0.95, 6.5),
        (251, 1.04, 8.5), (289, 0.98, 5.5), (327, 1.01, 7.0),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._note: str | None = None

    def set_note(self, note: str | None) -> None:
        if note != self._note:
            self._note = note
            self.update()

    def paintEvent(self, event) -> None:
        import math

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        base_r = self.SIZE * 0.34

        if self._note is not None:
            hi, mid, edge = "#e86a42", "#b03418", "#7c1e10"
            text_color = QColor("#f6e8d4")
        else:
            hi, mid, edge = "#b3a284", "#8d7b5c", "#67593f"
            text_color = QColor("#efe5d0")

        wax = QRadialGradient(c.x() - base_r * 0.35, c.y() - base_r * 0.4,
                              base_r * 2.1)
        wax.setColorAt(0.0, QColor(hi))
        wax.setColorAt(0.55, QColor(mid))
        wax.setColorAt(1.0, QColor(edge))
        p.setPen(QPen(QColor(edge).darker(130), 1))
        p.setBrush(QBrush(wax))

        # Irregular dripped edge: overlapping blobs around the rim
        for angle_deg, dist, blob_r in self._BLOBS:
            a = math.radians(angle_deg)
            bx = c.x() + math.cos(a) * base_r * dist
            by = c.y() + math.sin(a) * base_r * dist
            p.drawEllipse(QPointF(bx, by), blob_r, blob_r)

        # Main pool of wax over the blobs
        p.drawEllipse(c, base_r + 4, base_r + 4)

        # Stamp impression ring
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(edge).darker(115), 1.5))
        p.drawEllipse(c, base_r - 3, base_r - 3)

        # Aero gloss: translucent light pooling across the upper face
        gloss = QLinearGradient(c.x(), c.y() - base_r, c.x(), c.y())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 90))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(gloss))
        p.drawEllipse(QRectF(c.x() - base_r * 0.75, c.y() - base_r * 0.85,
                             base_r * 1.5, base_r * 0.95))

        # Stamped note name, embossed into the wax
        font = QFont(theme.SERIF_FAMILY, 17, QFont.Weight.Bold)
        p.setFont(font)
        text = self._note if self._note is not None else "—"
        rect = QRectF(0, 0, self.width(), self.height())
        p.setPen(QColor(0, 0, 0, 110))
        p.drawText(rect.translated(1, 1), Qt.AlignmentFlag.AlignCenter, text)
        p.setPen(text_color)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
