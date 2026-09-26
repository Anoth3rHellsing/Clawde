"""
Hydration Reminder - Non-intrusive water reminder system.
Shows a 16-bit chat bubble when the user has been idle, reminding them
to drink water. Clawde also takes a sip during this state.
"""

import time
import random


class HydrationReminder:
    """
    Tracks hydration reminder timing. Integrates with StateMachine
    to trigger HYDRATION_REMINDER state and with Renderer for dismiss.
    """

    # Default interval: 45 minutes between reminders
    WATER_INTERVAL = 2700.0
    # How long the reminder stays visible before auto-dismissing
    REMINDER_DURATION = 30.0
    # Randomize interval slightly so it doesn't feel robotic
    INTERVAL_JITTER = 300.0  # ±5 minutes

    def __init__(self, interval: float = None):
        if interval is not None:
            self.WATER_INTERVAL = interval
        self._next_reminder_at = time.time() + self._compute_interval()
        self._reminder_active_since: float | None = None
        self._dismissed = False

    def _compute_interval(self) -> float:
        """Return the base interval plus/minus random jitter."""
        jitter = random.uniform(-self.INTERVAL_JITTER, self.INTERVAL_JITTER)
        return max(60.0, self.WATER_INTERVAL + jitter)

    def should_remind(self, now: float) -> bool:
        """
        Returns True if enough time has passed since last reminder
        and no reminder is currently active.
        """
        if self._reminder_active_since is not None:
            return False
        return now >= self._next_reminder_at

    def activate(self, now: float):
        """Start showing the reminder."""
        self._reminder_active_since = now
        self._dismissed = False

    def acknowledge(self):
        """
        User interacted (click or hover) — dismiss the reminder
        and reset the timer.
        """
        if self._reminder_active_since is not None:
            self._reminder_active_since = None
            self._dismissed = True
            self._next_reminder_at = time.time() + self._compute_interval()

    def tick(self, now: float) -> bool:
        """
        Call each tick. Returns True if the reminder should still be shown.
        Auto-dismisses after REMINDER_DURATION seconds.
        """
        if self._reminder_active_since is None:
            return False

        elapsed = now - self._reminder_active_since
        if elapsed >= self.REMINDER_DURATION:
            # Auto-dismiss: timer ran out without user interaction
            self._reminder_active_since = None
            self._next_reminder_at = now + self._compute_interval()
            return False

        return True

    @property
    def is_active(self) -> bool:
        return self._reminder_active_since is not None

    @property
    def progress(self) -> float:
        """0.0 to 1.0 — how far through the reminder duration we are."""
        if self._reminder_active_since is None:
            return 0.0
        elapsed = time.time() - self._reminder_active_since
        return min(1.0, elapsed / self.REMINDER_DURATION)