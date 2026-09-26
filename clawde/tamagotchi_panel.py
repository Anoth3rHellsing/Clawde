"""
Tamagotchi Panel - Minimalist side panel showing Clawde's current state
and a single mood indicator. Hunger/Energy bars and the Feed button were
removed per user request; the panel now just reflects what Clawde is
doing and how happy it is.
"""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QLinearGradient, QBrush
)
from PySide6.QtWidgets import QWidget, QApplication

from .state_machine import TamagotchiStats, ClawdeState
from .hat_system import HatType

# Cycle order for the panel's hat selector (None = automatic)
HAT_CYCLE = [
    None,
    HatType.NONE,
    HatType.SUN_HAT,
    HatType.NIGHT_CAP,
    HatType.RAIN_HAT,
    HatType.CHEF_HAT,
    HatType.HARD_HAT,
    HatType.STEALTH_BERET,
    HatType.CYBER_VISOR,
    HatType.PARTY_HAT,
    HatType.WATER_DROPLET,
    HatType.WALKING_CAP,
]

HAT_LABELS = {
    None: "Auto",
    HatType.NONE: "No hat",
    HatType.SUN_HAT: "Sun hat",
    HatType.NIGHT_CAP: "Night cap",
    HatType.RAIN_HAT: "Rain hood",
    HatType.CHEF_HAT: "Chef hat",
    HatType.HARD_HAT: "Hard hat",
    HatType.STEALTH_BERET: "Beret",
    HatType.CYBER_VISOR: "Cyber visor",
    HatType.PARTY_HAT: "Party hat",
    HatType.WATER_DROPLET: "Water drop",
    HatType.WALKING_CAP: "Walking cap",
}


# ─── Colors ──────────────────────────────────────────────────────────
PANEL_BG = QColor(25, 25, 30, 210)
PANEL_BORDER = QColor(60, 60, 70)
BAR_BG = QColor(50, 50, 55)
HAPPINESS_COLOR = QColor(220, 80, 120)
TEXT_COLOR = QColor(200, 200, 210)
STATE_TEXT_COLOR = QColor(180, 200, 255)
COLLAPSE_COLOR = QColor(120, 120, 130)


STATE_NAMES = {
    ClawdeState.IDLE: "Idle",
    ClawdeState.WATCHTOWER: "Watching around",
    ClawdeState.DANCING: "Dancing!",
    ClawdeState.BEING_PETTED: "Purring~",
    ClawdeState.BEING_DRAGGED: "Wheee!",
    ClawdeState.SYSTEM_ERROR: "BSOD!",
    ClawdeState.SYSTEM_UPDATE: "Updating...",
    ClawdeState.VS_CODE_CODING: "Coding along",
    ClawdeState.VS_CODE_FAST_TYPING: "Fast typing!",
    ClawdeState.DISCORD_CHAT: "Chatting",
    ClawdeState.FILE_EXPLORER: "Browsing files",
    ClawdeState.WEB_BROWSER: "Surfing the web",
    ClawdeState.SOCIAL_MEDIA: "Scrolling feeds",
    ClawdeState.PHOTOSHOP_CREATING: "Making art",
    ClawdeState.TEXT_EDITOR: "Writing",
    ClawdeState.FULLSCREEN_WATCHING: "Watching",
    ClawdeState.HITMAN_STEALTH: "Going stealth",
    ClawdeState.HITMAN_ALERT: "ALERT!",
    ClawdeState.CYBERPUNK_NETRUNNER: "Netrunning",
    ClawdeState.RANDOM_SNEEZE: "Achoo!",
    ClawdeState.RANDOM_WAVE: "Waving hi",
    ClawdeState.RANDOM_STRETCH: "Stretching",
    ClawdeState.RANDOM_BUG: "Chasing a bug",
    ClawdeState.RANDOM_EXERCISE: "Working out",
    ClawdeState.RANDOM_YAWN: "Yawning",
    ClawdeState.RANDOM_SPIN: "Spinning",
    ClawdeState.RANDOM_THINK: "Thinking...",
}


class TamagotchiPanel(QWidget):
    """
    Compact status panel that floats near Clawde. Shows the current
    state name and a single mood bar. Collapsible.
    """
    PANEL_W = 160
    PANEL_H_COLLAPSED = 24
    PANEL_H_EXPANDED = 96

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._stats = TamagotchiStats()
        self._state = ClawdeState.IDLE
        self._collapsed = False
        self._collapse_hover = False
        self._hat_index = 0  # 0 = Auto (automatic selection)
        self._hat_callback = None

        self.resize(self.PANEL_W, self.PANEL_H_EXPANDED)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 390, screen.height() - 200)

        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.update())
        self._timer.start(100)

    def update_stats(self, stats: TamagotchiStats, state: ClawdeState):
        self._stats = stats
        self._state = state

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        h = self.PANEL_H_COLLAPSED if self._collapsed else self.PANEL_H_EXPANDED
        self.resize(self.PANEL_W, h)

    def tick(self, dt: float):
        # No cooldowns to track anymore; kept for API compatibility.
        pass

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        # Background
        p.setPen(QPen(PANEL_BORDER, 1))
        p.setBrush(PANEL_BG)
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # Collapse toggle
        p.setPen(QPen(COLLAPSE_COLOR, 1))
        arrow = "▼" if not self._collapsed else "▲"
        font_small = QFont("Segoe UI", 7)
        p.setFont(font_small)
        p.drawText(w - 18, 16, arrow)

        # State name
        state_name = STATE_NAMES.get(self._state, "Unknown")
        font_state = QFont("Segoe UI", 8, QFont.Bold)
        p.setFont(font_state)
        p.setPen(STATE_TEXT_COLOR)
        p.drawText(10, 16, state_name)

        if self._collapsed:
            p.end()
            return

        # Single mood bar
        bar_x = 10
        bar_w = w - 20
        bar_h = 10
        font_label = QFont("Segoe UI", 7)
        p.setFont(font_label)

        p.setPen(TEXT_COLOR)
        p.drawText(bar_x, 28, "Mood")

        by = 32
        p.setPen(Qt.NoPen)
        p.setBrush(BAR_BG)
        p.drawRoundedRect(bar_x, by, bar_w, bar_h, 3, 3)

        fill_ratio = max(0.0, min(1.0, self._stats.happiness / 100.0))
        fill_w = int(bar_w * fill_ratio)
        if fill_w > 0:
            grad = QLinearGradient(bar_x, by, bar_x + fill_w, by)
            c1 = QColor(HAPPINESS_COLOR)
            c2 = QColor(HAPPINESS_COLOR.lighter(130))
            grad.setColorAt(0, c1)
            grad.setColorAt(1, c2)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(bar_x, by, fill_w, bar_h, 3, 3)

        p.setPen(TEXT_COLOR)
        p.drawText(bar_x + bar_w - 28, 28, f"{int(self._stats.happiness)}%")

        # Hat selector row — click to cycle through hats
        hat = HAT_CYCLE[self._hat_index]
        label = HAT_LABELS.get(hat, "?")
        font_hat = QFont("Segoe UI", 7)
        p.setFont(font_hat)
        p.setPen(QPen(QColor(140, 140, 150), 1))
        p.setBrush(QColor(40, 40, 48))
        self._hat_btn_rect = QRectF(bar_x, 46, bar_w, 18)
        p.drawRoundedRect(self._hat_btn_rect, 4, 4)
        p.setPen(QColor(220, 220, 230))
        p.drawText(self._hat_btn_rect, Qt.AlignCenter, f"🎩 {label}")

        self._collapse_btn_rect = QRectF(w - 22, 0, 22, 20)
        p.end()

    def set_hat_callback(self, callback):
        """Register a callable invoked with the chosen HatType (or None)."""
        self._hat_callback = callback

    def _cycle_hat(self):
        self._hat_index = (self._hat_index + 1) % len(HAT_CYCLE)
        if self._hat_callback:
            self._hat_callback(HAT_CYCLE[self._hat_index])

    def mousePressEvent(self, event):
        pos = event.position()
        if hasattr(self, '_collapse_btn_rect') and self._collapse_btn_rect.contains(pos):
            self.toggle_collapse()
        elif (hasattr(self, '_hat_btn_rect')
              and not self._collapsed
              and self._hat_btn_rect.contains(pos)):
            self._cycle_hat()

    def mouseMoveEvent(self, event):
        pos = event.position()
        self._collapse_hover = (
            hasattr(self, '_collapse_btn_rect')
            and self._collapse_btn_rect.contains(pos)
        )
        self.update()