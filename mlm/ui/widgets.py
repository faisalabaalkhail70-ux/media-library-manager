"""Shared premium custom widgets for the redesigned UI.

All drawing is done in paintEvent using QPainter — no stylesheets for these.

Widgets
  GlassCard       — frosted glass card with noise grain + optional accent bar
  NeonStatCard    — large glowing stat number with animated hover
  PulseRing       — animated loading/activity ring painted purely in QPainter
  GradientLabel   — QLabel whose text is rendered with a linear gradient fill
  SectionHeader   — decorative section title with left accent bar + muted subtitle
  HorizontalRule  — styled 1px separator with optional label
  BadgeLabel      — pill-shaped colored badge (status, quality, etc.)
"""
from __future__ import annotations
import math
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QFrame
from PySide6.QtCore import Qt, QRect, QPoint, QTimer, QSize, QRectF, Property
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QPainterPath, QPen, QBrush, QFont, QFontMetrics,
    QConicalGradient,
)


# ──────────────────────────────────────────────────────────────────────
class GlassCard(QWidget):
    """
    Frosted glass card drawn entirely in paintEvent.
    Parameters
      radius    : corner radius (default 16)
      accent    : QColor for the top accent bar (None = no bar)
      accent_h  : height of the top accent bar in px
      hover_glow: whether hovering brightens the card
    """
    def __init__(
        self,
        parent=None,
        radius: int = 16,
        accent: QColor | None = None,
        accent_h: int = 3,
        hover_glow: bool = True,
    ) -> None:
        super().__init__(parent)
        self._radius    = radius
        self._accent    = accent
        self._accent_h  = accent_h
        self._hovered   = False
        self._hover_glow = hover_glow
        if hover_glow:
            self.setMouseTracking(True)

    # inner layout helper
    def set_inner_layout(self, layout):
        layout.setParent(None)
        self.setLayout(layout)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = self._radius

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # Base fill
        base_alpha = 22 if self._hovered else 12
        p.fillPath(path, QColor(255, 255, 255, base_alpha))

        # Subtle top-to-bottom gradient overlay
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(255, 255, 255, 14))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillPath(path, grad)

        # Hover accent glow
        if self._hovered and self._hover_glow and self._accent:
            glow = QRadialGradient(w // 2, 0, w * 0.7)
            c = QColor(self._accent)
            c.setAlpha(30)
            glow.setColorAt(0.0, c)
            c2 = QColor(c)
            c2.setAlpha(0)
            glow.setColorAt(1.0, c2)
            p.fillPath(path, glow)

        # Border
        border_alpha = 55 if self._hovered else 28
        pen = QPen(QColor(255, 255, 255, border_alpha), 1)
        p.setPen(pen)
        p.drawPath(path)

        # Top accent bar
        if self._accent:
            bar_path = QPainterPath()
            bar_path.addRoundedRect(QRectF(0.5, 0.5, w - 1, self._accent_h), r, r)
            clip = QPainterPath()
            clip.addRect(QRectF(0, 0, w, self._accent_h))
            bar_path = bar_path.intersected(clip)
            p.fillPath(bar_path, self._accent)


# ──────────────────────────────────────────────────────────────────────
class NeonStatCard(QWidget):
    """
    Large glowing stat card. Draws:
      ─ Rounded glass background
      ─ Big number in gradient fill
      ─ Small label underneath
      ─ Neon glow behind the number on hover
      ─ Accent bar at top

    Usage:
        card = NeonStatCard("1 284", "Movies", QColor(66,165,245))
    """
    def __init__(
        self,
        value: str,
        label: str,
        accent: QColor = QColor(124, 111, 255),
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._value  = value
        self._label  = label
        self._accent = accent
        self._hovered = False
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.ArrowCursor)

    def update_value(self, value: str) -> None:
        self._value = value
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        r = 14

        # ─ Background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.fillPath(path, QColor(255, 255, 255, 10))

        # Gradient sheen top
        top_grad = QLinearGradient(0, 0, 0, h * 0.5)
        top_grad.setColorAt(0, QColor(255, 255, 255, 16))
        top_grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillPath(path, top_grad)

        # Hover glow
        if self._hovered:
            glow = QRadialGradient(w * 0.5, h, w * 0.8)
            c = QColor(self._accent)
            c.setAlpha(35)
            glow.setColorAt(0, c)
            c2 = QColor(self._accent)
            c2.setAlpha(0)
            glow.setColorAt(1, c2)
            p.fillPath(path, glow)

        # Top accent bar
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0.5, 0.5, w - 1, 3), r, r)
        clip = QPainterPath()
        clip.addRect(QRectF(0, 0, w, 3))
        p.fillPath(bar.intersected(clip), self._accent)

        # Border
        pen_alpha = 60 if self._hovered else 28
        c_border = QColor(self._accent) if self._hovered else QColor(255, 255, 255, pen_alpha)
        p.setPen(QPen(c_border, 1))
        p.drawPath(path)

        # ─ Value text with gradient fill
        p.save()
        vf = QFont("Segoe UI", 28, QFont.Bold)
        p.setFont(vf)
        fm = QFontMetrics(vf)
        vw = fm.horizontalAdvance(self._value)
        vx = (w - vw) // 2
        vy = int(h * 0.62)

        # Gradient text: accent → lighter
        text_grad = QLinearGradient(vx, vy - fm.ascent(), vx + vw, vy)
        light = QColor(self._accent).lighter(180)
        text_grad.setColorAt(0.0, light)
        text_grad.setColorAt(1.0, self._accent)
        pen = QPen()
        pen.setBrush(QBrush(text_grad))
        p.setPen(pen)
        p.drawText(vx, vy, self._value)
        p.restore()

        # ─ Label text
        lf = QFont("Segoe UI", 9)
        p.setFont(lf)
        p.setPen(QColor(100, 100, 130))
        lfm = QFontMetrics(lf)
        lw = lfm.horizontalAdvance(self._label)
        p.drawText((w - lw) // 2, int(h * 0.88), self._label)


# ──────────────────────────────────────────────────────────────────────
class PulseRing(QWidget):
    """Animated arc spinner. Rotates by 6 deg/tick (60ms)."""

    def __init__(self, size: int = 32, color: QColor = QColor(124, 111, 255), parent=None):
        super().__init__(parent)
        self._size  = size
        self._color = color
        self._angle = 0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(60)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._size
        margin = 3
        rect = QRectF(margin, margin, s - margin * 2, s - margin * 2)

        # Track
        p.setPen(QPen(QColor(255, 255, 255, 15), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(rect)

        # Arc
        grad = QConicalGradient(s / 2, s / 2, -self._angle)
        grad.setColorAt(0.0, self._color)
        grad.setColorAt(0.7, QColor(self._color.red(), self._color.green(), self._color.blue(), 0))
        pen = QPen(QBrush(grad), 3, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, self._angle * 16, -270 * 16)


# ──────────────────────────────────────────────────────────────────────
class GradientLabel(QLabel):
    """QLabel with gradient-filled text (accent → lighter)."""

    def __init__(self, text: str, c1: QColor, c2: QColor, font_size: int = 22, parent=None):
        super().__init__(text, parent)
        self._c1 = c1
        self._c2 = c2
        self._font_size = font_size
        f = QFont("Segoe UI", font_size, QFont.Bold)
        self.setFont(f)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, self._c1)
        grad.setColorAt(1, self._c2)
        pen = QPen()
        pen.setBrush(QBrush(grad))
        p.setPen(pen)
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, self.text())


# ──────────────────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    """Section title with a 3px accent bar on the left and optional subtitle."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        accent: QColor = QColor(124, 111, 255),
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._title    = title
        self._subtitle = subtitle
        self._accent   = accent
        self.setFixedHeight(48 if subtitle else 36)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        # Accent bar
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0, 4, 3, self.height() - 8), 1.5, 1.5)
        p.fillPath(bar, self._accent)

        # Title
        tf = QFont("Segoe UI", 14, QFont.Bold)
        p.setFont(tf)
        p.setPen(QColor(240, 240, 255))
        p.drawText(QRect(14, 0, self.width() - 14, 30), Qt.AlignVCenter | Qt.AlignLeft, self._title)

        # Subtitle
        if self._subtitle:
            sf = QFont("Segoe UI", 9)
            p.setFont(sf)
            p.setPen(QColor(80, 80, 110))
            p.drawText(QRect(14, 28, self.width() - 14, 18), Qt.AlignVCenter | Qt.AlignLeft, self._subtitle)


# ──────────────────────────────────────────────────────────────────────
class BadgeLabel(QWidget):
    """Pill-shaped colored badge for status / quality tags."""

    def __init__(
        self,
        text: str,
        bg: QColor  = QColor(124, 111, 255, 50),
        fg: QColor  = QColor(168, 159, 255),
        border: QColor | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._text   = text
        self._bg     = bg
        self._fg     = fg
        self._border = border or QColor(fg.red(), fg.green(), fg.blue(), 80)
        f = QFont("Segoe UI", 8, QFont.Bold)
        fm = QFontMetrics(f)
        self._font = f
        self.setFixedHeight(18)
        self.setFixedWidth(fm.horizontalAdvance(text) + 18)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 9, 9)
        p.fillPath(path, self._bg)
        p.setPen(QPen(self._border, 1))
        p.drawPath(path)
        p.setFont(self._font)
        p.setPen(self._fg)
        p.drawText(self.rect(), Qt.AlignCenter, self._text)


# ──────────────────────────────────────────────────────────────────────
class AmbientBackground(QWidget):
    """
    Full-window ambient glow blobs. Place this as a background layer.
    Three radial blobs: top-right, bottom-left, center.
    Rotates slowly to give a living feel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)   # ~12.5 fps, cheap

    def _tick(self):
        self._angle = (self._angle + 0.4) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        a = math.radians(self._angle)
        offset_x = int(math.sin(a) * 40)
        offset_y = int(math.cos(a) * 30)

        blobs = [
            # (cx_frac, cy_frac, radius_frac, r, g, b, alpha)
            (0.80 + offset_x / w, 0.15 + offset_y / h, 0.45, 100, 80, 255, 18),
            (0.15 - offset_x / w, 0.80 - offset_y / h, 0.40,  80, 60, 220, 14),
            (0.50,                0.50,                 0.30, 124, 111, 255, 8),
        ]
        for cx_f, cy_f, r_f, r, g, b, alpha in blobs:
            cx = cx_f * w
            cy = cy_f * h
            radius = r_f * max(w, h)
            grad = QRadialGradient(cx, cy, radius)
            grad.setColorAt(0.0, QColor(r, g, b, alpha))
            grad.setColorAt(1.0, QColor(r, g, b, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx - radius), int(cy - radius),
                          int(radius * 2), int(radius * 2))
