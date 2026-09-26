"""
Movement Controller - Autonomous movement system for Clawde.
Handles safehouse return, taskbar walking, and hide-and-seek behind windows.
Only active when the user is NOT dragging Clawde manually.
"""

import time
import random
from enum import Enum, auto
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .context_listener import SystemContext, ActivityLevel


class MovementMode(Enum):
    """Current autonomous movement behavior."""
    SAFEHOUSE = auto()      # Returning to or resting at safehouse
    WALKING = auto()        # Strolling along the taskbar
    HIDING = auto()         # Behind a window (hide-and-seek)
    PAUSED = auto()         # User is dragging; wait until released


class MovementController:
    """
    Computes target position for the renderer each tick.
    Manages transitions between walking, hiding, and returning to safehouse.
    """

    # Safehouse: bottom-left corner of primary screen
    SAFEHOUSE_X = 20
    SAFEHOUSE_Y_OFFSET = 260  # screen_height - this value

    # Walking parameters
    WALK_SPEED = 30.0          # pixels per second
    WALK_MIN_DURATION = 5.0    # seconds before changing direction
    WALK_MAX_DURATION = 15.0   # max walk segment duration
    TASKBAR_Y_OFFSET = 80      # screen_height - this = walking y

    # Hide-and-seek parameters
    HIDE_PROBABILITY = 0.15    # 15% chance on window change
    HIDE_MIN_DURATION = 3.0
    HIDE_MAX_DURATION = 8.0
    HIDE_OFFSET_X = 40         # offset from window edge when hiding
    HIDE_OFFSET_Y = 30

    # Lerp factor for smooth movement (per tick at 20Hz)
    LERP_FACTOR = 0.03
    FAST_LERP = 0.08           # used when returning to safehouse after drag

    def __init__(self):
        screen = QApplication.primaryScreen().geometry()
        self._screen_w = screen.width()
        self._screen_h = screen.height()

        self._mode = MovementMode.SAFEHOUSE
        self._target_x = float(self.SAFEHOUSE_X)
        self._target_y = float(self._screen_h - self.SAFEHOUSE_Y_OFFSET)

        # Walking state
        self._walk_direction = 1  # 1 = right, -1 = left
        self._walk_segment_end = 0.0
        self._last_walk_tick = time.time()

        # Hiding state
        self._hide_ends_at = 0.0
        self._is_hiding = False
        self._last_active_process = ""

        # Drag resume delay — don't snap back instantly after release
        self._drag_released_at: Optional[float] = None
        self._DRAG_RESUME_DELAY = 2.0

    @property
    def is_hiding(self) -> bool:
        """True when Clawde is currently behind a window."""
        return self._mode == MovementMode.HIDING

    @property
    def is_walking(self) -> bool:
        return self._mode == MovementMode.WALKING

    def notify_drag_released(self):
        """Call when user stops dragging to start the resume delay."""
        self._drag_released_at = time.time()
        self._mode = MovementMode.SAFEHOUSE

    def update(
        self,
        ctx: SystemContext,
        current_x: int,
        current_y: int,
        is_dragging: bool,
        state_name: str,
    ) -> tuple[int, int]:
        """
        Compute the next position for the renderer.
        Returns (new_x, new_y) to apply via widget.move().

        Call this every tick from app.py's _tick().
        """
        now = time.time()

        # While dragging, pause all autonomous movement
        if is_dragging:
            self._mode = MovementMode.PAUSED
            self._drag_released_at = None
            return current_x, current_y

        # After drag release, wait before resuming autonomy
        if self._drag_released_at is not None:
            if now - self._drag_released_at < self._DRAG_RESUME_DELAY:
                return current_x, current_y
            self._drag_released_at = None
            self._mode = MovementMode.SAFEHOUSE

        # Check for hide-and-seek trigger (window/process change)
        if (ctx.active_process != self._last_active_process
                and self._last_active_process != ""
                and ctx.active_process != ""
                and self._mode != MovementMode.HIDING):
            if random.random() < self.HIDE_PROBABILITY:
                self._start_hiding(now)

        self._last_active_process = ctx.active_process

        # Update current mode
        if self._mode == MovementMode.HIDING:
            if now >= self._hide_ends_at:
                self._mode = MovementMode.SAFEHOUSE
                self._is_hiding = False
            # Stay put while hiding — no position change
            return current_x, current_y

        elif self._mode == MovementMode.WALKING:
            self._update_walking(now)
            # If walk segment ended, decide next action
            if now >= self._walk_segment_end:
                if random.random() < 0.3:
                    # 30% chance to go back to safehouse after a walk
                    self._mode = MovementMode.SAFEHOUSE
                else:
                    # Change direction and keep walking
                    self._walk_direction *= -1
                    self._walk_segment_end = now + random.uniform(
                        self.WALK_MIN_DURATION, self.WALK_MAX_DURATION
                    )

        elif self._mode == MovementMode.SAFEHOUSE:
            # Decide whether to start walking
            if (state_name in ("IDLE", "WATCHTOWER")
                    and ctx.activity_level == ActivityLevel.IDLE):
                if random.random() < 0.005:  # ~1% per tick ≈ every 2s avg
                    self._start_walking(now)

        # Smooth lerp toward target
        factor = self.FAST_LERP if self._mode == MovementMode.SAFEHOUSE else self.LERP_FACTOR
        new_x = int(current_x + (self._target_x - current_x) * factor)
        new_y = int(current_y + (self._target_y - current_y) * factor)

        return new_x, new_y

    def _start_walking(self, now: float):
        """Begin a taskbar walking segment."""
        self._mode = MovementMode.WALKING
        self._target_y = float(self._screen_h - self.TASKBAR_Y_OFFSET)
        self._walk_direction = random.choice([-1, 1])
        self._walk_segment_end = now + random.uniform(
            self.WALK_MIN_DURATION, self.WALK_MAX_DURATION
        )
        self._last_walk_tick = now

    def _update_walking(self, now: float):
        """Advance the walk target horizontally."""
        dt = now - self._last_walk_tick
        self._last_walk_tick = now

        self._target_x += self._walk_direction * self.WALK_SPEED * dt

        # Clamp to screen bounds with padding
        margin = 20
        if self._target_x < margin:
            self._target_x = float(margin)
            self._walk_direction = 1
        elif self._target_x > self._screen_w - margin - 200:
            self._target_x = float(self._screen_w - margin - 200)
            self._walk_direction = -1

    def _start_hiding(self, now: float):
        """Enter hide-and-seek mode behind the current foreground window."""
        self._mode = MovementMode.HIDING
        self._is_hiding = True
        self._hide_ends_at = now + random.uniform(
            self.HIDE_MIN_DURATION, self.HIDE_MAX_DURATION
        )
        # Target position will be set by app.py based on actual window rect
        # For now, just shift slightly off-screen to the right
        self._target_x = min(
            self._target_x + self.HIDE_OFFSET_X,
            self._screen_w - 100
        )
        self._target_y += self.HIDE_OFFSET_Y

    def refresh_screen_geometry(self):
        """Re-read screen dimensions (e.g., after resolution change)."""
        screen = QApplication.primaryScreen().geometry()
        self._screen_w = screen.width()
        self._screen_h = screen.height()
        # Update safehouse target
        if self._mode == MovementMode.SAFEHOUSE:
            self._target_x = float(self.SAFEHOUSE_X)
            self._target_y = float(self._screen_h - self.SAFEHOUSE_Y_OFFSET)