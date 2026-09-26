"""
Renderer - Draws Clawde using PySide6 QPainter with voxel-style 2D rendering.
Each state has its own draw function producing the character + props + particles.
Uses a simple voxel grid approach: each "pixel" is a small colored square,
giving the retro 3D-printed look from the reference image.
"""

import math
import time
import random
from typing import Optional

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap,
    QPainterPath, QRadialGradient, QLinearGradient, QTransform
)
from PySide6.QtWidgets import QWidget

from .state_machine import ClawdeState, TamagotchiStats
from .hat_system import HatType


# ─── Color Palette ────────────────────────────────────────────────────

ORANGE_BODY = QColor(228, 116, 72)       # Main body orange (matches 3D print)
ORANGE_LIGHT = QColor(240, 140, 95)      # Highlight
ORANGE_DARK = QColor(190, 90, 50)        # Shadow
EYE_BLACK = QColor(15, 15, 20)           # Eyes
EYE_SHINE = QColor(255, 255, 255, 180)   # Eye reflection
BG_TRANSPARENT = QColor(0, 0, 0, 0)

# Prop colors
GLASSES_COLOR = QColor(40, 40, 50)
HEADSET_COLOR = QColor(60, 60, 70)
TACTICAL_GREEN = QColor(80, 100, 60)
SUNGLASSES_COLOR = QColor(30, 30, 35)
CYBERPUNK_GREEN = QColor(0, 255, 100)
PALETTE_COLORS = [
    QColor(220, 50, 50), QColor(50, 120, 220), QColor(220, 200, 50),
    QColor(50, 200, 80), QColor(180, 50, 200), QColor(220, 140, 50),
]
HEART_RED = QColor(230, 60, 80)
BSOD_BLUE = QColor(30, 60, 180)
UPDATE_RING = QColor(80, 140, 220)
PEN_COLOR = QColor(40, 30, 60)
MAGNIFIER_COLOR = QColor(180, 160, 100)
SOFA_COLOR = QColor(100, 80, 140)
CABINET_COLOR = QColor(160, 140, 110)
PHONE_COLOR = QColor(50, 50, 55)
FOOD_COLOR = QColor(180, 120, 60)
ZZZ_COLOR = QColor(180, 200, 255)


class Particle:
    """A simple animated particle (heart, zzz, spark, etc.)."""
    def __init__(self, x: float, y: float, kind: str = "heart"):
        self.x = x
        self.y = y
        self.kind = kind
        self.life = 1.0
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1.5, -0.5)
        self.size = random.uniform(6, 12)

    def update(self, dt: float):
        self.x += self.vx
        self.y += self.vy
        self.life -= dt * 0.8
        if self.kind == "zzz":
            self.vy = -0.3
            self.vx = 0.2

    @property
    def alive(self) -> bool:
        return self.life > 0


class ClawdeRenderer(QWidget):
    """
    Transparent overlay widget that renders Clawde.
    Always-on-top, click-through by default, interactive on hover.
    """

    VOXEL_SIZE = 4  # Size of each voxel "pixel"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._state = ClawdeState.IDLE
        self._stats = TamagotchiStats()
        self._time = 0.0
        self._last_frame = time.time()
        self._particles: list[Particle] = []
        self._breath_phase = 0.0
        self._blink_timer = 0.0
        self._is_blinking = False
        self._drag_offset = QPointF(0, 0)
        self._is_dragging = False
        self._is_hovered = False
        self._color_shift = 0.0  # For photoshop state

        # Hat and hiding systems
        self._current_hat = HatType.NONE
        self._is_hiding = False

        # Animation frame counters
        self._anim_frame = 0
        self._anim_timer = 0.0

        # Sizing
        self._char_width = 80
        self._char_height = 90
        self.resize(200, 220)

        # Frame timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

        # Position: bottom-right of screen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 220, screen.height() - 260)

    def set_state(self, state: ClawdeState, stats: TamagotchiStats):
        self._state = state
        self._stats = stats

    def set_hat(self, hat: HatType):
        """Set the current hat to draw on top of Clawde's head."""
        self._current_hat = hat

    def set_hiding(self, hiding: bool):
        """Set whether Clawde is currently hiding behind a window."""
        if self._is_hiding != hiding:
            self._is_hiding = hiding
            # Toggle WindowStaysOnTopHint: off when hiding, on otherwise
            flags = self.windowFlags()
            if hiding:
                self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            else:
                self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.show()  # Required after changing window flags

    def _tick(self):
        now = time.time()
        dt = now - self._last_frame
        self._last_frame = now
        self._time += dt
        self._breath_phase += dt * 2.0
        self._anim_timer += dt
        self._color_shift += dt * 0.5

        # Blink logic
        self._blink_timer -= dt
        if self._blink_timer <= 0:
            if self._is_blinking:
                self._is_blinking = False
                self._blink_timer = random.uniform(2.0, 5.0)
            else:
                self._is_blinking = True
                self._blink_timer = 0.15

        # Update particles
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if p.alive]

        # Spawn particles based on state
        self._spawn_particles(dt)

        # Animation frame
        if self._anim_timer > 0.1:
            self._anim_frame += 1
            self._anim_timer = 0.0

        self.update()

    def _spawn_particles(self, dt: float):
        if self._state == ClawdeState.BEING_PETTED:
            if random.random() < dt * 8:
                cx = self.width() / 2 + random.uniform(-20, 20)
                cy = self.height() / 2 - 20
                self._particles.append(Particle(cx, cy, "heart"))
        elif self._state == ClawdeState.RANDOM_YAWN:
            # Sleepy zzz's drift up during a yawn — reuses the old sleep
            # particle effect now that hunger/sleep stats are gone.
            if random.random() < dt * 2:
                cx = self.width() / 2 + 25
                cy = self.height() / 2 - 30
                self._particles.append(Particle(cx, cy, "zzz"))
        elif self._state == ClawdeState.DANCING:
            if random.random() < dt * 6:
                cx = self.width() / 2 + random.uniform(-30, 30)
                cy = self.height() / 2 + random.uniform(-20, 20)
                self._particles.append(Particle(cx, cy, "spark"))
        elif self._state == ClawdeState.VS_CODE_FAST_TYPING:
            if random.random() < dt * 4:
                cx = self.width() / 2 + random.uniform(-25, 25)
                cy = self.height() / 2 - 10
                self._particles.append(Particle(cx, cy, "spark"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # Voxel look = no AA

        # Clear
        painter.fillRect(self.rect(), BG_TRANSPARENT)

        # Draw based on current state
        method_name = self._STATE_DRAW_MAP.get(self._state, "_draw_idle")
        draw_fn = getattr(self, method_name, self._draw_idle)
        body_info = draw_fn(painter)

        # Draw hat on top of the body (if any)
        if body_info and self._current_hat != HatType.NONE:
            head_rect = body_info.get("head")
            if head_rect:
                self._draw_hat(painter, head_rect)

        # Draw hydration bubble overlay when in HYDRATION_REMINDER state
        if self._state == ClawdeState.HYDRATION_REMINDER and body_info:
            self._draw_hydration_bubble(painter, body_info)

        # Draw particles on top
        self._draw_particles(painter)

        painter.end()

    # ─── Voxel Drawing Helpers ────────────────────────────────────────

    def _voxel(self, painter: QPainter, x: int, y: int, color: QColor, size: int = None):
        """Draw a single voxel block."""
        s = size or self.VOXEL_SIZE
        painter.fillRect(x, y, s, s, color)

    def _voxel_rect(self, painter: QPainter, x: int, y: int, w: int, h: int, color: QColor):
        """Draw a rectangle of voxels."""
        s = self.VOXEL_SIZE
        for vx in range(0, w, s):
            for vy in range(0, h, s):
                painter.fillRect(x + vx, y + vy, s, s, color)

    def _draw_body(self, painter: QPainter, cx: int, cy: int, breath_offset: float = 0.0):
        """
        Draw Clawde faithful to the reference: a single wide rectangular
        orange block with two square black eyes, short side arms, and
        four stubby legs underneath. No separate head/torso split.
        """
        s = self.VOXEL_SIZE
        by = int(cy + breath_offset)

        # Main body — one wide rectangle (the whole character is basically this)
        body_w, body_h = 56, 40
        bx = cx - body_w // 2
        body_y = by - body_h // 2
        self._voxel_rect(painter, bx, body_y, body_w, body_h, ORANGE_BODY)
        # Top highlight strip
        self._voxel_rect(painter, bx + s, body_y + s, body_w - 2*s, s, ORANGE_LIGHT)
        # Bottom shadow strip
        self._voxel_rect(painter, bx + s, body_y + body_h - s, body_w - 2*s, s, ORANGE_DARK)

        # Side arms — short nubs sticking out left and right, vertically centered
        arm_w, arm_h = 10, 14
        arm_y = body_y + (body_h - arm_h) // 2
        # Left arm
        self._voxel_rect(painter, bx - arm_w, arm_y, arm_w, arm_h, ORANGE_BODY)
        self._voxel_rect(painter, bx - arm_w, arm_y + arm_h - s, arm_w, s, ORANGE_DARK)
        # Right arm
        self._voxel_rect(painter, bx + body_w, arm_y, arm_w, arm_h, ORANGE_BODY)
        self._voxel_rect(painter, bx + body_w, arm_y + arm_h - s, arm_w, s, ORANGE_DARK)

        # Eyes — two simple black squares, upper-center of the body
        eye_size = 8
        eye_y = body_y + 10
        eye_gap = 8  # space between the two eyes
        left_eye_x = cx - eye_gap - eye_size
        right_eye_x = cx + eye_gap
        if not self._is_blinking:
            self._voxel_rect(painter, left_eye_x, eye_y, eye_size, eye_size, EYE_BLACK)
            self._voxel_rect(painter, right_eye_x, eye_y, eye_size, eye_size, EYE_BLACK)
            # Tiny shine pixel in each eye
            painter.fillRect(left_eye_x + 1, eye_y + 1, 2, 2, EYE_SHINE)
            painter.fillRect(right_eye_x + 1, eye_y + 1, 2, 2, EYE_SHINE)
        else:
            # Closed eyes — thin horizontal line
            painter.fillRect(left_eye_x, eye_y + eye_size // 2, eye_size, 2, EYE_BLACK)
            painter.fillRect(right_eye_x, eye_y + eye_size // 2, eye_size, 2, EYE_BLACK)

        # Four stubby legs underneath, evenly spaced
        leg_w, leg_h = 8, 12
        leg_y = body_y + body_h
        # Positions: 4 legs spread across the body width
        leg_positions = [
            bx + 6,
            bx + 6 + leg_w + 6,
            bx + body_w - 6 - leg_w - 6 - leg_w,
            bx + body_w - 6 - leg_w,
        ]
        for lx in leg_positions:
            self._voxel_rect(painter, lx, leg_y, leg_w, leg_h, ORANGE_BODY)
            self._voxel_rect(painter, lx, leg_y + leg_h - s, leg_w, s, ORANGE_DARK)

        # Return part coordinates for hat placement and hydration bubble
        return {
            "head": (bx, body_y, body_w, body_h),
            "left_eye": (left_eye_x, eye_y, eye_size, eye_size),
            "right_eye": (right_eye_x, eye_y, eye_size, eye_size),
            "left_arm": (bx - arm_w, arm_y, arm_w, arm_h),
            "right_arm": (bx + body_w, arm_y, arm_w, arm_h),
        }

    def _draw_particles(self, painter: QPainter):
        for p in self._particles:
            alpha = int(p.life * 255)
            if p.kind == "heart":
                color = QColor(HEART_RED.red(), HEART_RED.green(), HEART_RED.blue(), alpha)
                self._draw_heart(painter, int(p.x), int(p.y), int(p.size), color)
            elif p.kind == "zzz":
                color = QColor(ZZZ_COLOR.red(), ZZZ_COLOR.green(), ZZZ_COLOR.blue(), alpha)
                font = QFont("Consolas", int(p.size))
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(color)
                painter.drawText(int(p.x), int(p.y), "Z")
            elif p.kind == "spark":
                color = QColor(255, 220, 100, alpha)
                painter.fillRect(int(p.x), int(p.y), 3, 3, color)

    def _draw_heart(self, painter: QPainter, x: int, y: int, size: int, color: QColor):
        s = size / 2
        path = QPainterPath()
        path.moveTo(x, y + s * 0.3)
        path.cubicTo(x, y, x - s, y, x - s, y + s * 0.3)
        path.cubicTo(x - s, y + s * 0.7, x, y + s, x, y + s * 1.2)
        path.cubicTo(x, y + s, x + s, y + s * 0.7, x + s, y + s * 0.3)
        path.cubicTo(x + s, y, x, y, x, y + s * 0.3)
        painter.fillPath(path, color)

    # ─── Hat Drawing ──────────────────────────────────────────────────

    def _draw_hat(self, painter: QPainter, head_rect: tuple):
        """Draw the current hat on top of Clawde's head/body block."""
        bx, by, bw, bh = head_rect
        s = self.VOXEL_SIZE
        hat_x = bx + bw // 2  # center horizontally on body

        if self._current_hat == HatType.SUN_HAT:
            # Straw hat: wide brim + dome
            brim_w, brim_h = bw + 16, 6
            self._voxel_rect(painter, hat_x - brim_w // 2, by - brim_h, brim_w, brim_h, QColor(230, 200, 80))
            dome_w, dome_h = 24, 12
            self._voxel_rect(painter, hat_x - dome_w // 2, by - brim_h - dome_h, dome_w, dome_h, QColor(210, 180, 60))
            # Band
            self._voxel_rect(painter, hat_x - dome_w // 2, by - brim_h - 4, dome_w, 4, QColor(180, 60, 60))

        elif self._current_hat == HatType.NIGHT_CAP:
            # Sleepy cap: rounded top with star
            cap_w, cap_h = 28, 16
            self._voxel_rect(painter, hat_x - cap_w // 2, by - cap_h, cap_w, cap_h, QColor(70, 70, 160))
            # Star on top
            self._voxel_rect(painter, hat_x - 3, by - cap_h - 6, 6, 6, QColor(255, 255, 100))
            # Brim fold
            self._voxel_rect(painter, hat_x - cap_w // 2 - 2, by - 4, cap_w + 4, 4, QColor(90, 90, 180))

        elif self._current_hat == HatType.RAIN_HAT:
            # Yellow raincoat hood
            hood_w, hood_h = bw + 8, 20
            self._voxel_rect(painter, hat_x - hood_w // 2, by - hood_h + 4, hood_w, hood_h, QColor(240, 220, 40))
            # Darker edge
            self._voxel_rect(painter, hat_x - hood_w // 2, by - hood_h + 4, hood_w, s, QColor(200, 180, 20))

        elif self._current_hat == HatType.CHEF_HAT:
            # Tall white toque
            base_w, base_h = 24, 6
            top_w, top_h = 20, 20
            self._voxel_rect(painter, hat_x - base_w // 2, by - base_h, base_w, base_h, QColor(240, 240, 240))
            self._voxel_rect(painter, hat_x - top_w // 2, by - base_h - top_h, top_w, top_h, QColor(255, 255, 255))
            # Shadow line
            self._voxel_rect(painter, hat_x - top_w // 2 + s, by - base_h - top_h + s, top_w - 2*s, s, QColor(220, 220, 220))

        elif self._current_hat == HatType.HARD_HAT:
            # Construction helmet
            helm_w, helm_h = bw + 4, 14
            self._voxel_rect(painter, hat_x - helm_w // 2, by - helm_h + 2, helm_w, helm_h, QColor(240, 200, 20))
            # Front brim
            self._voxel_rect(painter, hat_x - helm_w // 2 - 4, by - 4, helm_w + 8, 4, QColor(220, 180, 10))
            # Ridge on top
            self._voxel_rect(painter, hat_x - 3, by - helm_h - 2, 6, 4, QColor(200, 160, 10))

        elif self._current_hat == HatType.STEALTH_BERET:
            # Black tactical beret
            beret_w, beret_h = 30, 10
            self._voxel_rect(painter, hat_x - beret_w // 2 + 4, by - beret_h, beret_w, beret_h, QColor(30, 30, 35))
            # Slight tilt to right
            self._voxel_rect(painter, hat_x + 6, by - beret_h + 2, 8, beret_h - 2, QColor(40, 40, 45))

        elif self._current_hat == HatType.CYBER_VISOR:
            # Neon green visor across eyes
            visor_w, visor_h = bw + 6, 8
            eye_y = by + 10
            color = QColor(0, 255, 100)
            self._voxel_rect(painter, hat_x - visor_w // 2, eye_y - 2, visor_w, visor_h, color)
            # Glow effect — lighter center
            self._voxel_rect(painter, hat_x - visor_w // 4, eye_y, visor_w // 2, visor_h - 4, QColor(100, 255, 180))

        elif self._current_hat == HatType.PARTY_HAT:
            # Multicolor cone
            cone_w, cone_h = 20, 24
            colors = [QColor(255, 80, 80), QColor(80, 255, 80), QColor(80, 80, 255), QColor(255, 255, 80)]
            stripe_h = cone_h // len(colors)
            for i, color in enumerate(colors):
                sw = cone_w - i * 4
                sy = by - cone_h + i * stripe_h
                self._voxel_rect(painter, hat_x - sw // 2, sy, sw, stripe_h, color)
            # Pom-pom on top
            self._voxel_rect(painter, hat_x - 3, by - cone_h - 4, 6, 6, QColor(255, 200, 50))

        elif self._current_hat == HatType.WATER_DROPLET:
            # Blue water drop sitting on head
            drop_size = 12
            dx = hat_x - drop_size // 2
            dy = by - drop_size - 2
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(60, 140, 255))
            painter.drawEllipse(dx, dy, drop_size, drop_size)
            # Shine
            painter.fillRect(dx + 2, dy + 2, 3, 3, QColor(180, 220, 255))

        elif self._current_hat == HatType.WALKING_CAP:
            # Small baseball cap
            cap_w, cap_h = 26, 8
            self._voxel_rect(painter, hat_x - cap_w // 2, by - cap_h, cap_w, cap_h, QColor(60, 100, 180))
            # Visor
            self._voxel_rect(painter, hat_x + 2, by - 4, 18, 4, QColor(50, 80, 150))

    # ─── Hydration Bubble ─────────────────────────────────────────────

    def _draw_hydration_bubble(self, painter: QPainter, body_info: dict):
        """Draw a 16-bit style chat bubble reminding the user to drink water."""
        bx, by, bw, bh = body_info["head"]

        # Bubble dimensions
        bubble_w, bubble_h = 120, 36
        bubble_x = bx + bw + 8
        bubble_y = by - bubble_h + 4

        # Pixel-art border (black outline)
        painter.setPen(Qt.NoPen)
        painter.fillRect(bubble_x - 2, bubble_y - 2, bubble_w + 4, bubble_h + 4, QColor(0, 0, 0))
        # White fill
        painter.fillRect(bubble_x, bubble_y, bubble_w, bubble_h, QColor(255, 255, 255))
        # Tail (small triangle pointing left toward Clawde)
        tail_pts = [
            QPoint(bubble_x, bubble_y + bubble_h // 2 - 4),
            QPoint(bubble_x - 6, bubble_y + bubble_h // 2),
            QPoint(bubble_x, bubble_y + bubble_h // 2 + 4),
        ]
        painter.setBrush(QColor(255, 255, 255))
        painter.drawPolygon(tail_pts)
        # Tail border
        painter.setPen(QColor(0, 0, 0))
        painter.drawLine(tail_pts[0], tail_pts[1])
        painter.drawLine(tail_pts[1], tail_pts[2])

        # Text
        font = QFont("Consolas", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(30, 80, 180))
        text_rect = QRect(bubble_x + 6, bubble_y + 4, bubble_w - 12, bubble_h - 8)
        painter.drawText(text_rect, Qt.AlignCenter, "💧 Toma agua!")

        # Small water glass next to Clawde's arm
        if "right_arm" in body_info:
            ax, ay, aw, ah = body_info["right_arm"]
            glass_x = ax + aw + 2
            glass_y = ay + 2
            # Glass body
            painter.fillRect(glass_x, glass_y, 8, 12, QColor(180, 220, 255))
            # Water inside
            painter.fillRect(glass_x + 1, glass_y + 4, 6, 7, QColor(60, 140, 255))
            # Rim
            painter.fillRect(glass_x - 1, glass_y, 10, 2, QColor(200, 230, 255))

    # ─── State-specific Draw Functions ────────────────────────────────

    def _draw_idle(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        breath = math.sin(self._breath_phase) * 2
        return self._draw_body(painter, cx, cy, breath)

    def _draw_watchtower(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)
        # Looking around — shift the eye shine left/right so Clawde appears
        # to be scanning. The shine is a single 2x2 pixel; we fully repaint
        # each eye black first (covering the default shine drawn by
        # _draw_body), then drop exactly one shine pixel back inside the
        # eye at the shifted position. This avoids the old bug where a
        # second shine pixel stacked on top of the first and looked like
        # extra eyes above the real ones.
        if not self._is_blinking and "left_eye" in parts:
            look_x = int(math.sin(self._time * 0.6) * 2)
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            # Repaint both eyes solid black to erase any prior shine
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            # One shine pixel per eye, clamped strictly inside the eye box
            sx_l = max(lx, min(lx + lw - 2, lx + 1 + look_x))
            sy_l = ly + 1
            sx_r = max(rx, min(rx + rw - 2, rx + 1 + look_x))
            sy_r = ry + 1
            painter.fillRect(sx_l, sy_l, 2, 2, EYE_SHINE)
            painter.fillRect(sx_r, sy_r, 2, 2, EYE_SHINE)

    def _draw_sleeping(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 20
        s = self.VOXEL_SIZE
        # Lying down — rotated body
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-75)
        painter.translate(-cx, -cy)
        breath = math.sin(self._breath_phase * 0.5) * 3
        body_info = self._draw_body(painter, cx, cy, breath)
        painter.restore()

        # Dream bubble
        bx, by = cx + 30, cy - 50
        bubble_alpha = int((math.sin(self._time * 2) * 0.3 + 0.7) * 200)
        bubble_color = QColor(200, 220, 255, bubble_alpha)
        painter.setPen(QPen(bubble_color, 1))
        painter.setBrush(QColor(220, 235, 255, bubble_alpha // 2))
        painter.drawEllipse(bx, by, 30, 25)
        # Data packet icon inside
        painter.fillRect(bx + 8, by + 8, 14, 10, QColor(100, 180, 255, bubble_alpha))
        painter.fillRect(bx + 10, by + 10, 4, 2, QColor(255, 255, 255, bubble_alpha))
        painter.fillRect(bx + 16, by + 10, 4, 2, QColor(255, 255, 255, bubble_alpha))

    def _draw_hungry(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase * 1.5) * 2
        parts = self._draw_body(painter, cx, cy, breath)

        # Empty bowl below
        bowl_x = cx - 15
        bowl_y = cy + 40
        s = self.VOXEL_SIZE
        self._voxel_rect(painter, bowl_x, bowl_y, 30, 8, QColor(180, 180, 190))
        self._voxel_rect(painter, bowl_x + s, bowl_y + s*2, 28 - 2*s, 4, QColor(140, 140, 150))
        # Sad mouth
        hx, hy, hw, hh = parts["head"]
        painter.setPen(QPen(EYE_BLACK, 2))
        painter.drawArc(hx + hw//2 - 6, hy + 20, 12, 8, 0, -180 * 16)

    def _draw_dancing(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Bouncy dance
        bounce = abs(math.sin(self._time * 6)) * 8
        sway = math.sin(self._time * 4) * 5
        parts = self._draw_body(painter, int(cx + sway), int(cy - bounce))

        # Disco sparkles around
        for i in range(3):
            angle = self._time * 3 + i * 2.1
            sx = cx + int(math.cos(angle) * 40)
            sy = cy + int(math.sin(angle) * 30) - 10
            c = PALETTE_COLORS[i % len(PALETTE_COLORS)]
            c.setAlpha(180)
            painter.fillRect(sx, sy, 4, 4, c)

    def _draw_being_petted(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Gentle squish
        squish = math.sin(self._time * 3) * 2
        parts = self._draw_body(painter, cx, int(cy + squish))

        # Happy closed eyes override
        hx, hy, hw, hh = parts["head"]
        painter.fillRect(hx + 10, hy + 14, 8, 2, EYE_BLACK)
        painter.fillRect(hx + hw - 18, hy + 14, 8, 2, EYE_BLACK)
        # Smile
        painter.setPen(QPen(EYE_BLACK, 2))
        painter.drawArc(hx + hw//2 - 6, hy + 18, 12, 8, 180 * 16, -180 * 16)

    def _draw_being_dragged(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Flailing — rapid rotation wobble
        wobble = math.sin(self._time * 15) * 10
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(wobble)
        painter.translate(-cx, -cy)
        body_info = self._draw_body(painter, cx, cy)
        painter.restore()

        # Stretch marks / speed lines
        for i in range(4):
            ly = cy - 20 + i * 12
            painter.fillRect(cx - 50, ly, 15, 2, QColor(255, 255, 255, 100))
            painter.fillRect(cx + 35, ly, 15, 2, QColor(255, 255, 255, 100))

    def _draw_system_error(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # BSOD background
        painter.fillRect(10, 10, self.width() - 20, self.height() - 20, BSOD_BLUE)
        # Fallen Clawde
        painter.save()
        painter.translate(cx, cy + 15)
        painter.rotate(90)
        painter.translate(-cx, -(cy + 15))
        body_info = self._draw_body(painter, cx, cy + 15)
        painter.restore()
        # Error text
        font = QFont("Consolas", 7)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 30, ":(")
        painter.drawText(20, 50, "CLAWDE_CRASH")

    def _draw_system_update(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        body_info = self._draw_body(painter, cx, cy)
        # Spinning update ring
        painter.setPen(QPen(UPDATE_RING, 3))
        start_angle = int(self._time * 200) % 360
        painter.drawArc(cx - 35, cy - 45, 70, 70, start_angle * 16, 270 * 16)
        # Percentage text
        pct = int((self._time * 10) % 100)
        font = QFont("Consolas", 8)
        painter.setFont(font)
        painter.setPen(UPDATE_RING)
        painter.drawText(cx - 12, cy + 50, f"{pct}%")

    def _draw_vscode_coding(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Glasses
        hx, hy, hw, hh = parts["head"]
        painter.setPen(QPen(GLASSES_COLOR, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(hx + 6, hy + 8, 14, 10)
        painter.drawRect(hx + hw - 20, hy + 8, 14, 10)
        painter.drawLine(hx + 20, hy + 13, hx + hw - 20, hy + 13)

        # Step stool below
        stool_y = cy + 38
        self._voxel_rect(painter, cx - 18, stool_y, 36, 6, QColor(140, 120, 90))
        self._voxel_rect(painter, cx - 14, stool_y + 6, 28, 6, QColor(120, 100, 70))

        # Holographic code board
        board_x = cx + 30
        board_y = cy - 50
        board_alpha = int((math.sin(self._time * 2) * 0.2 + 0.6) * 255)
        board_color = QColor(100, 200, 255, board_alpha // 2)
        painter.fillRect(board_x, board_y, 50, 40, board_color)
        painter.setPen(QPen(QColor(100, 200, 255, board_alpha), 1))
        painter.drawRect(board_x, board_y, 50, 40)
        # Code lines
        font = QFont("Consolas", 5)
        painter.setFont(font)
        painter.setPen(QColor(200, 255, 200, board_alpha))
        lines = ["def clawde():", "  while True:", "    be_cute()"]
        for i, line in enumerate(lines):
            painter.drawText(board_x + 3, board_y + 10 + i * 10, line)

    def _draw_vscode_fast_typing(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        # Excited bouncing
        bounce = abs(math.sin(self._time * 8)) * 5
        parts = self._draw_body(painter, cx, int(cy - bounce))

        # Glasses
        hx, hy, hw, hh = parts["head"]
        painter.setPen(QPen(GLASSES_COLOR, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(hx + 6, hy + 8, 14, 10)
        painter.drawRect(hx + hw - 20, hy + 8, 14, 10)

        # Clapping hands indicator
        clap = math.sin(self._time * 10) > 0
        if clap:
            painter.fillRect(cx - 5, cy - 5, 10, 6, ORANGE_LIGHT)

        # Speed lines
        for i in range(3):
            ly = cy - 30 + i * 15
            alpha = int((math.sin(self._time * 5 + i) * 0.5 + 0.5) * 150)
            painter.fillRect(cx - 55, ly, 20, 2, QColor(255, 220, 100, alpha))

    def _draw_discord_chat(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Headset
        hx, hy, hw, hh = parts["head"]
        painter.setPen(QPen(HEADSET_COLOR, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(hx - 2, hy - 4, hw + 4, 20, 0, 180 * 16)
        # Ear cups
        self._voxel_rect(painter, hx - 6, hy + 6, 8, 10, HEADSET_COLOR)
        self._voxel_rect(painter, hx + hw - 2, hy + 6, 8, 10, HEADSET_COLOR)
        # Mic boom
        painter.setPen(QPen(HEADSET_COLOR, 2))
        painter.drawLine(hx - 2, hy + 16, hx - 8, hy + 26)
        painter.fillRect(hx - 10, hy + 24, 6, 4, QColor(80, 80, 90))

        # Mini sofa behind
        sofa_y = cy + 20
        self._voxel_rect(painter, cx - 30, sofa_y, 60, 12, SOFA_COLOR)
        self._voxel_rect(painter, cx - 32, sofa_y - 8, 8, 20, SOFA_COLOR)
        self._voxel_rect(painter, cx + 24, sofa_y - 8, 8, 20, SOFA_COLOR)

        # Speech bubble
        bub_x, bub_y = cx + 25, cy - 55
        painter.setPen(QPen(QColor(200, 200, 210), 1))
        painter.setBrush(QColor(240, 240, 245, 220))
        painter.drawRoundedRect(bub_x, bub_y, 40, 25, 5, 5)
        # Discord icon (simplified)
        painter.fillRect(bub_x + 8, bub_y + 6, 10, 8, QColor(88, 101, 242))
        painter.fillRect(bub_x + 22, bub_y + 6, 10, 8, QColor(88, 101, 242))
        # Bubble tail
        path = QPainterPath()
        path.moveTo(bub_x + 5, bub_y + 25)
        path.lineTo(bub_x - 5, bub_y + 35)
        path.lineTo(bub_x + 15, bub_y + 25)
        painter.fillPath(path, QColor(240, 240, 245, 220))

    def _draw_file_explorer(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        body_info = self._draw_body(painter, cx, cy, breath)

        # Mini filing cabinet
        cab_x = cx - 45
        cab_y = cy - 20
        self._voxel_rect(painter, cab_x, cab_y, 30, 50, CABINET_COLOR)
        # Drawers
        for i in range(3):
            dy = cab_y + 4 + i * 16
            self._voxel_rect(painter, cab_x + 3, dy, 24, 12, QColor(180, 160, 130))
            # Handle
            self._voxel_rect(painter, cab_x + 12, dy + 4, 6, 3, QColor(120, 100, 80))
        # Open drawer with papers
        open_y = cab_y + 20
        self._voxel_rect(painter, cab_x - 8, open_y, 30, 12, QColor(180, 160, 130))
        # Papers sticking out
        self._voxel_rect(painter, cab_x - 5, open_y - 4, 12, 6, QColor(240, 240, 230))
        self._voxel_rect(painter, cab_x + 2, open_y - 6, 10, 6, QColor(230, 235, 245))

    def _draw_web_browser(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Giant magnifying glass
        mg_x = cx + 20
        mg_y = cy - 30
        painter.setPen(QPen(MAGNIFIER_COLOR, 3))
        painter.setBrush(QColor(200, 220, 255, 80))
        painter.drawEllipse(mg_x, mg_y, 28, 28)
        # Handle
        painter.setPen(QPen(QColor(140, 120, 80), 4))
        painter.drawLine(mg_x + 22, mg_y + 22, mg_x + 35, mg_y + 38)

        # Conveyor belt below
        belt_y = cy + 42
        self._voxel_rect(painter, cx - 50, belt_y, 100, 6, QColor(100, 100, 110))
        # Belt movement indicators
        offset = int(self._time * 20) % 12
        for i in range(-4, 5):
            bx = cx - 48 + i * 12 + offset
            if -50 < bx - cx < 50:
                painter.fillRect(bx, belt_y + 1, 6, 4, QColor(80, 80, 90))

    def _draw_social_media(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Mini phone in hand
        ph_x = cx + 15
        ph_y = cy - 15
        self._voxel_rect(painter, ph_x, ph_y, 16, 24, PHONE_COLOR)
        # Screen
        screen_color = PALETTE_COLORS[int(self._time * 2) % len(PALETTE_COLORS)]
        screen_color.setAlpha(200)
        self._voxel_rect(painter, ph_x + 2, ph_y + 3, 12, 16, screen_color)

        # Shock/laugh face — alternating
        hx, hy, hw, hh = parts["head"]
        if int(self._time * 2) % 2 == 0:
            # Shock — O mouth
            painter.setPen(QPen(EYE_BLACK, 2))
            painter.setBrush(EYE_BLACK)
            painter.drawEllipse(hx + hw//2 - 4, hy + 20, 8, 8)
        else:
            # Laugh — wide smile
            painter.setPen(QPen(EYE_BLACK, 2))
            painter.drawArc(hx + hw//2 - 8, hy + 18, 16, 10, 180 * 16, -180 * 16)

    def _draw_photoshop_creating(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5

        # Color-shifting body
        shift = self._color_shift
        r = int(ORANGE_BODY.red() + math.sin(shift) * 40)
        g = int(ORANGE_BODY.green() + math.sin(shift + 2) * 40)
        b = int(ORANGE_BODY.blue() + math.sin(shift + 4) * 40)
        shifted_orange = QColor(max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))

        # Draw body with shifted color
        s = self.VOXEL_SIZE
        by = int(cy + breath)
        head_w, head_h = 48, 32
        hx = cx - head_w // 2
        hy = by - 40
        self._voxel_rect(painter, hx, hy, head_w, head_h, shifted_orange)
        # Eyes
        if not self._is_blinking:
            self._voxel_rect(painter, hx + 10, hy + 10, 8, 8, EYE_BLACK)
            self._voxel_rect(painter, hx + head_w - 18, hy + 10, 8, 8, EYE_BLACK)
        body_w, body_h = 40, 28
        bx = cx - body_w // 2
        body_y = hy + head_h
        self._voxel_rect(painter, bx, body_y, body_w, body_h, shifted_orange)
        # Arms
        self._voxel_rect(painter, bx - 12, body_y + 8, 8, 20, shifted_orange)
        self._voxel_rect(painter, bx + body_w + 4, body_y + 8, 8, 20, shifted_orange)
        # Legs
        leg_y = body_y + body_h
        self._voxel_rect(painter, bx + 4, leg_y, 12, 16, shifted_orange)
        self._voxel_rect(painter, bx + body_w - 16, leg_y, 12, 16, shifted_orange)

        # Paint palette
        pal_x = cx - 50
        pal_y = cy - 10
        painter.setPen(QPen(QColor(160, 140, 110), 1))
        painter.setBrush(QColor(200, 180, 150))
        painter.drawEllipse(pal_x, pal_y, 25, 20)
        # Color dots on palette
        for i, c in enumerate(PALETTE_COLORS[:4]):
            dx = pal_x + 5 + (i % 2) * 12
            dy = pal_y + 4 + (i // 2) * 8
            painter.fillRect(dx, dy, 5, 5, c)

        # Brush
        br_x = cx + 25
        br_y = cy - 25
        painter.setPen(QPen(QColor(140, 100, 60), 3))
        painter.drawLine(br_x, br_y, br_x + 15, br_y + 20)
        # Brush tip
        tip_color = PALETTE_COLORS[int(self._time) % len(PALETTE_COLORS)]
        painter.fillRect(br_x + 13, br_y + 18, 6, 8, tip_color)

    def _draw_text_editor(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Giant fountain pen
        pen_x = cx + 20
        pen_y = cy - 40
        painter.save()
        painter.translate(pen_x + 5, pen_y + 25)
        painter.rotate(30)
        painter.translate(-(pen_x + 5), -(pen_y + 25))
        # Pen body
        self._voxel_rect(painter, pen_x, pen_y, 8, 40, PEN_COLOR)
        # Pen nib
        path = QPainterPath()
        path.moveTo(pen_x, pen_y + 40)
        path.lineTo(pen_x + 4, pen_y + 52)
        path.lineTo(pen_x + 8, pen_y + 40)
        painter.fillPath(path, QColor(200, 180, 100))
        # Ink drop
        if int(self._time * 3) % 2 == 0:
            painter.fillRect(pen_x + 3, pen_y + 52, 3, 3, QColor(30, 30, 80))
        painter.restore()

    def _draw_fullscreen_watching(self, painter: QPainter):
        # Sitting in corner, looking up attentively. With the new single-block
        # body we must NOT draw a second pair of eyes on top of the ones
        # _draw_body already painted (that produced the "4 eyes" look). Instead
        # we repaint each eye solid black and drop the shine pixel near the top
        # of the eye so Clawde appears to be gazing upward, plus an occasional
        # nod by shifting the whole shine row down a pixel.
        cx, cy = self.width() // 2, self.height() // 2 + 15
        breath = math.sin(self._breath_phase * 0.8) * 1
        parts = self._draw_body(painter, cx, cy, breath)

        nod = 1 if math.sin(self._time * 0.3) > 0.5 else 0
        if not self._is_blinking and "left_eye" in parts:
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            # Erase the default eyes/shine drawn by _draw_body
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            # Shine near the top of each eye => looking up; +nod for the dip
            painter.fillRect(lx + 1, ly + nod, 2, 2, EYE_SHINE)
            painter.fillRect(rx + 1, ry + nod, 2, 2, EYE_SHINE)

    def _draw_hitman_stealth(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Prone position
        painter.save()
        painter.translate(cx, cy + 10)
        painter.rotate(-80)
        painter.translate(-cx, -(cy + 10))
        parts = self._draw_body(painter, cx, cy + 10)
        painter.restore()

        # Tactical vest overlay
        s = self.VOXEL_SIZE
        self._voxel_rect(painter, cx - 16, cy - 8, 32, 20, TACTICAL_GREEN)
        # Vest pockets
        self._voxel_rect(painter, cx - 12, cy - 4, 8, 6, QColor(60, 80, 45))
        self._voxel_rect(painter, cx + 4, cy - 4, 8, 6, QColor(60, 80, 45))

        # Sunglasses
        hx = cx - 24
        hy = cy - 38
        self._voxel_rect(painter, hx + 8, hy + 10, 12, 6, SUNGLASSES_COLOR)
        self._voxel_rect(painter, hx + 28, hy + 10, 12, 6, SUNGLASSES_COLOR)
        painter.setPen(QPen(SUNGLASSES_COLOR, 2))
        painter.drawLine(hx + 20, hy + 13, hx + 28, hy + 13)

        # Binoculars
        bin_x = cx + 20
        bin_y = cy - 30
        self._voxel_rect(painter, bin_x, bin_y, 8, 12, QColor(50, 50, 55))
        self._voxel_rect(painter, bin_x + 10, bin_y, 8, 12, QColor(50, 50, 55))
        self._voxel_rect(painter, bin_x + 8, bin_y + 2, 2, 8, QColor(50, 50, 55))

    def _draw_hitman_alert(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 15
        # Cowering / masonry pose
        squish = math.sin(self._time * 4) * 3
        parts = self._draw_body(painter, cx, int(cy + squish))

        # Tactical vest
        self._voxel_rect(painter, cx - 16, cy - 8, 32, 20, TACTICAL_GREEN)

        # Sunglasses
        hx, hy, hw, hh = parts["head"]
        self._voxel_rect(painter, hx + 8, hy + 10, 12, 6, SUNGLASSES_COLOR)
        self._voxel_rect(painter, hx + hw - 20, hy + 10, 12, 6, SUNGLASSES_COLOR)

        # "Don't see me" hands over face
        self._voxel_rect(painter, hx + 4, hy + 6, hw - 8, 14, ORANGE_BODY)

        # Alert indicator
        alert_alpha = int((math.sin(self._time * 6) * 0.5 + 0.5) * 255)
        painter.setPen(QPen(QColor(255, 50, 50, alert_alpha), 2))
        painter.drawText(cx - 8, cy - 55, "!")

    def _draw_cyberpunk_netrunner(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 5
        breath = math.sin(self._breath_phase) * 1.5
        parts = self._draw_body(painter, cx, cy, breath)

        # Green floating panels
        for i in range(3):
            px = cx - 60 + i * 45
            py = cy - 55 + int(math.sin(self._time * 2 + i) * 5)
            alpha = int((math.sin(self._time + i) * 0.3 + 0.7) * 200)
            panel_color = QColor(0, 255, 100, alpha // 3)
            border_color = QColor(0, 255, 100, alpha)
            painter.fillRect(px, py, 35, 25, panel_color)
            painter.setPen(QPen(border_color, 1))
            painter.drawRect(px, py, 35, 25)
            # Matrix text
            font = QFont("Consolas", 4)
            painter.setFont(font)
            painter.setPen(border_color)
            chars = "01" * 10
            offset = int(self._time * 5 + i * 3) % len(chars)
            painter.drawText(px + 2, py + 8, chars[offset:offset+8])
            painter.drawText(px + 2, py + 16, chars[offset+3:offset+11])

        # Cables from head
        hx, hy, hw, hh = parts["head"]
        painter.setPen(QPen(CYBERPUNK_GREEN, 1))
        for i in range(3):
            cable_end_x = cx - 40 + i * 40
            cable_end_y = cy - 55 + int(math.sin(self._time * 2 + i) * 5) + 25
            path = QPainterPath()
            path.moveTo(hx + hw // 2, hy)
            path.cubicTo(
                hx + hw // 2, hy - 15,
                cable_end_x, cable_end_y - 15,
                cable_end_x, cable_end_y
            )
            painter.drawPath(path)

    # ─── New Dynamic State Draw Functions ─────────────────────────────

    def _draw_hydration_reminder(self, painter: QPainter):
        """Clawde holding a glass of water with a gentle idle pose."""
        cx, cy = self.width() // 2, self.height() // 2 + 10
        breath = math.sin(self._breath_phase) * 1.5
        return self._draw_body(painter, cx, cy, breath)

    def _draw_walking(self, painter: QPainter):
        """Clawde strolling with alternating leg animation."""
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Walking bob: slight vertical oscillation
        walk_phase = time.time() * 4.0
        bounce = abs(math.sin(walk_phase)) * 3
        body_info = self._draw_body(painter, cx, int(cy - bounce))

        # Override leg positions for walking animation
        s = self.VOXEL_SIZE
        leg_w, leg_h = s * 2, s * 3
        leg_y = cy + 20 - bounce
        left_offset = math.sin(walk_phase) * 6
        right_offset = math.sin(walk_phase + math.pi) * 6

        # Redraw legs at animated positions (overwrite static ones)
        bg_color = QColor(0, 0, 0, 0)
        left_leg_x = cx - 18 + int(left_offset)
        right_leg_x = cx + 6 + int(right_offset)
        # Clear old leg area and draw new positions
        painter.fillRect(cx - 24, leg_y - 2, 48, leg_h + 4, bg_color)
        self._voxel_rect(painter, left_leg_x, leg_y, leg_w, leg_h, ORANGE_BODY)
        self._voxel_rect(painter, left_leg_x, leg_y + leg_h - s, leg_w, s, ORANGE_DARK)
        self._voxel_rect(painter, right_leg_x, leg_y, leg_w, leg_h, ORANGE_BODY)
        self._voxel_rect(painter, right_leg_x, leg_y + leg_h - s, leg_w, s, ORANGE_DARK)

        # Small dust particles at feet
        if int(walk_phase * 10) % 8 == 0:
            dust_x = cx + random.randint(-20, 20)
            dust_y = leg_y + leg_h + 2
            painter.fillRect(dust_x, dust_y, s, s, QColor(180, 170, 150, 120))

        return body_info

    # ─── State → Draw Method Name Map ─────────────────────────────────

    _STATE_DRAW_MAP = {
        ClawdeState.IDLE: "_draw_idle",
        ClawdeState.WATCHTOWER: "_draw_watchtower",
        ClawdeState.DANCING: "_draw_dancing",
        ClawdeState.BEING_PETTED: "_draw_being_petted",
        ClawdeState.BEING_DRAGGED: "_draw_being_dragged",
        ClawdeState.SYSTEM_ERROR: "_draw_system_error",
        ClawdeState.SYSTEM_UPDATE: "_draw_system_update",
        ClawdeState.VS_CODE_CODING: "_draw_vscode_coding",
        ClawdeState.VS_CODE_FAST_TYPING: "_draw_vscode_fast_typing",
        ClawdeState.DISCORD_CHAT: "_draw_discord_chat",
        ClawdeState.FILE_EXPLORER: "_draw_file_explorer",
        ClawdeState.WEB_BROWSER: "_draw_web_browser",
        ClawdeState.SOCIAL_MEDIA: "_draw_social_media",
        ClawdeState.PHOTOSHOP_CREATING: "_draw_photoshop_creating",
        ClawdeState.TEXT_EDITOR: "_draw_text_editor",
        ClawdeState.FULLSCREEN_WATCHING: "_draw_fullscreen_watching",
        ClawdeState.HITMAN_STEALTH: "_draw_hitman_stealth",
        ClawdeState.HITMAN_ALERT: "_draw_hitman_alert",
        ClawdeState.CYBERPUNK_NETRUNNER: "_draw_cyberpunk_netrunner",
        # Random self behaviors
        ClawdeState.RANDOM_SNEEZE: "_draw_random_sneeze",
        ClawdeState.RANDOM_WAVE: "_draw_random_wave",
        ClawdeState.RANDOM_STRETCH: "_draw_random_stretch",
        ClawdeState.RANDOM_BUG: "_draw_random_bug",
        ClawdeState.RANDOM_EXERCISE: "_draw_random_exercise",
        ClawdeState.RANDOM_YAWN: "_draw_random_yawn",
        ClawdeState.RANDOM_SPIN: "_draw_random_spin",
        ClawdeState.RANDOM_THINK: "_draw_random_think",
        # New dynamic states
        ClawdeState.HYDRATION_REMINDER: "_draw_hydration_reminder",
        ClawdeState.WALKING: "_draw_walking",
    }

    # ─── Random Self-Behavior Animations ──────────────────────────────
    # These play on their own when the user is idle, so Clawde feels alive
    # even when nothing specific is happening. Each one is short (2-4s) and
    # returns to idle/watchtower automatically via the state machine timer.

    def _draw_random_sneeze(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Quick forward lunge then recoil. The whole body shifts forward
        # (down-right) for the first half of the animation, then snaps back.
        t = self._time % 2.0
        if t < 0.6:
            lunge = math.sin(t / 0.6 * math.pi) * 6
        else:
            lunge = 0
        parts = self._draw_body(painter, int(cx + lunge), int(cy + lunge * 0.5))
        # Sneeze burst: a few pixels spraying out in front during the lunge
        if 0.3 < t < 0.8:
            for i in range(4):
                sx = cx + 30 + i * 4 + int(lunge)
                sy = cy - 5 + (i % 2) * 6
                alpha = int((1 - (t - 0.3) / 0.5) * 200)
                painter.fillRect(sx, sy, 3, 3, QColor(220, 220, 230, alpha))
        # Squinted eyes during the sneeze
        if not self._is_blinking and "left_eye" in parts and t < 0.8:
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            # Thin closed-eye lines
            painter.fillRect(lx, ly + lh // 2, lw, 2, EYE_BLACK)
            painter.fillRect(rx, ry + rh // 2, rw, 2, EYE_BLACK)

    def _draw_random_wave(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        parts = self._draw_body(painter, cx, cy)
        # Raise the right arm and wiggle it side to side. We repaint the
        # right arm nub higher up and oscillate its x position.
        if "right_arm" in parts:
            ax, ay, aw, ah = parts["right_arm"]
            # Erase the default arm
            self._voxel_rect(painter, ax, ay, aw, ah, BG_TRANSPARENT)
            # Raised arm position, wiggling
            wiggle = int(math.sin(self._time * 8) * 3)
            raised_y = ay - 18
            raised_x = ax + wiggle
            self._voxel_rect(painter, raised_x, raised_y, aw, ah, ORANGE_BODY)
            self._voxel_rect(painter, raised_x, raised_y + ah - self.VOXEL_SIZE,
                             aw, self.VOXEL_SIZE, ORANGE_DARK)
            # Little wave lines above the hand
            for i in range(2):
                lx = raised_x - 4 + i * 10 + wiggle
                ly = raised_y - 6
                alpha = int((math.sin(self._time * 6 + i) * 0.5 + 0.5) * 180)
                painter.fillRect(lx, ly, 4, 2, QColor(255, 220, 120, alpha))

    def _draw_random_stretch(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Body elongates vertically then settles. We scale the breath offset
        # into a bigger vertical stretch for the first half.
        t = self._time % 2.5
        stretch = math.sin(min(t, 1.25) / 1.25 * math.pi) * 6
        parts = self._draw_body(painter, cx, int(cy - stretch))
        # Arms reach outward during the stretch
        if "left_arm" in parts and "right_arm" in parts:
            lax, lay, law, lah = parts["left_arm"]
            rax, ray, raw, rah = parts["right_arm"]
            reach = int(stretch * 0.8)
            # Repaint arms pushed outward
            self._voxel_rect(painter, lax, lay, law, lah, BG_TRANSPARENT)
            self._voxel_rect(painter, rax, ray, raw, rah, BG_TRANSPARENT)
            self._voxel_rect(painter, lax - reach, lay, law, lah, ORANGE_BODY)
            self._voxel_rect(painter, rax + reach, ray, raw, rah, ORANGE_BODY)

    def _draw_random_bug(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        parts = self._draw_body(painter, cx, cy)
        # An imaginary bug zips around above Clawde; the eyes track it.
        bug_x = cx + int(math.sin(self._time * 3) * 35)
        bug_y = cy - 45 + int(math.cos(self._time * 4) * 8)
        # Bug body
        painter.fillRect(bug_x, bug_y, 5, 3, QColor(40, 40, 45))
        # Wings flutter
        wing_up = math.sin(self._time * 20) > 0
        wy = bug_y - 2 if wing_up else bug_y + 3
        painter.fillRect(bug_x - 2, wy, 3, 2, QColor(180, 200, 220, 160))
        painter.fillRect(bug_x + 4, wy, 3, 2, QColor(180, 200, 220, 160))
        # Eyes follow the bug horizontally
        if not self._is_blinking and "left_eye" in parts:
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            # Shine tracks toward the bug, clamped inside each eye
            dir_x = 2 if bug_x > cx else -1
            sx_l = max(lx, min(lx + lw - 2, lx + 1 + dir_x))
            sx_r = max(rx, min(rx + rw - 2, rx + 1 + dir_x))
            painter.fillRect(sx_l, ly + 1, 2, 2, EYE_SHINE)
            painter.fillRect(sx_r, ry + 1, 2, 2, EYE_SHINE)

    def _draw_random_exercise(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # Little jumping jacks: bounce up and down, arms flap out on the up.
        bounce = abs(math.sin(self._time * 7)) * 8
        arms_out = math.sin(self._time * 7) > 0
        parts = self._draw_body(painter, cx, int(cy - bounce))
        if arms_out and "left_arm" in parts and "right_arm" in parts:
            lax, lay, law, lah = parts["left_arm"]
            rax, ray, raw, rah = parts["right_arm"]
            self._voxel_rect(painter, lax, lay, law, lah, BG_TRANSPARENT)
            self._voxel_rect(painter, rax, ray, raw, rah, BG_TRANSPARENT)
            # Arms raised diagonally
            self._voxel_rect(painter, lax - 6, lay - 8, law, lah, ORANGE_BODY)
            self._voxel_rect(painter, rax + 6, ray - 8, raw, rah, ORANGE_BODY)
        # Sweat drop
        if bounce > 4:
            sx = cx + 26
            sy = cy - 30 + int(bounce)
            painter.fillRect(sx, sy, 3, 4, QColor(120, 180, 230, 200))

    def _draw_random_yawn(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        parts = self._draw_body(painter, cx, cy)
        # Big open mouth (a dark oval) below the eyes, plus sleepy half eyes.
        if "left_eye" in parts:
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            # Half-closed sleepy eyes
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            painter.fillRect(lx, ly + lh // 2, lw, 2, ORANGE_BODY)
            painter.fillRect(rx, ry + rh // 2, rw, 2, ORANGE_BODY)
        # Open mouth
        t = self._time % 2.5
        openness = math.sin(min(t, 1.25) / 1.25 * math.pi)
        mouth_w = int(10 * openness) + 4
        mouth_h = int(8 * openness) + 2
        mx = cx - mouth_w // 2
        my = cy + 2
        painter.setPen(QPen(EYE_BLACK, 1))
        painter.setBrush(EYE_BLACK)
        painter.drawEllipse(mx, my, mouth_w, mouth_h)

    def _draw_random_spin(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        # One full rotation over ~2 seconds, with motion blur lines.
        t = self._time % 2.0
        angle = (t / 2.0) * 360
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.translate(-cx, -cy)
        body_info = self._draw_body(painter, cx, cy)
        painter.restore()
        # Spin swoosh arcs
        for i in range(3):
            a = int(angle + i * 40) % 360
            alpha = int((math.sin(self._time * 5 + i) * 0.5 + 0.5) * 140)
            painter.setPen(QPen(QColor(255, 200, 120, alpha), 2))
            painter.drawArc(cx - 38, cy - 38, 76, 76, a * 16, 30 * 16)

    def _draw_random_think(self, painter: QPainter):
        cx, cy = self.width() // 2, self.height() // 2 + 10
        parts = self._draw_body(painter, cx, cy)
        # Eyes look up-and-to-one-side; a floating "?" bobs above.
        if not self._is_blinking and "left_eye" in parts:
            lx, ly, lw, lh = parts["left_eye"]
            rx, ry, rw, rh = parts["right_eye"]
            self._voxel_rect(painter, lx, ly, lw, lh, EYE_BLACK)
            self._voxel_rect(painter, rx, ry, rw, rh, EYE_BLACK)
            # Shine up-right => thinking gaze
            painter.fillRect(min(lx + lw - 2, lx + 3), ly + 1, 2, 2, EYE_SHINE)
            painter.fillRect(min(rx + rw - 2, rx + 3), ry + 1, 2, 2, EYE_SHINE)
        # Bobbing question mark
        bob = math.sin(self._time * 3) * 3
        qx = cx + 22
        qy = cy - 42 + int(bob)
        font = QFont("Segoe UI", 12, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(200, 210, 255))
        painter.drawText(qx, qy, "?")

    # ─── Mouse Interaction ────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Dismiss hydration reminder on click
            if self._state == ClawdeState.HYDRATION_REMINDER and hasattr(self, '_hydration_ack_callback'):
                self._hydration_ack_callback()
            self._drag_offset = event.globalPosition() - self.frameGeometry().topLeft()
            self._is_dragging = False
            self._press_time = time.time()
            self._is_petted = True

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # If moved more than 5px from press point, it's a drag not a pet
            delta = event.globalPosition() - self._drag_offset - QPointF(0, 0)
            dist = (delta.x()**2 + delta.y()**2) ** 0.5
            if dist > 5 or self._is_dragging:
                self._is_dragging = True
                self._is_petted = False
                new_pos = event.globalPosition() - self._drag_offset
                self.move(int(new_pos.x()), int(new_pos.y()))

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._is_petted = False

    def set_hydration_ack_callback(self, callback):
        """Register a callable to invoke when user dismisses hydration reminder."""
        self._hydration_ack_callback = callback

    def enterEvent(self, event):
        self._is_hovered = True
        # Dismiss hydration reminder on hover
        if self._state == ClawdeState.HYDRATION_REMINDER and hasattr(self, '_hydration_ack_callback'):
            self._hydration_ack_callback()

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_petted = False

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @property
    def is_petted(self) -> bool:
        """True when user is holding click without dragging (petting)."""
        return getattr(self, '_is_petted', False) and not self._is_dragging

    @property
    def is_hovered(self) -> bool:
        return self._is_hovered