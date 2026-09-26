"""
Main Application - Wires together ContextListener, StateMachine,
ClawdeRenderer, and TamagotchiPanel into a running desktop overlay.
"""

import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from .context_listener import ContextListener
from .state_machine import StateMachine, ClawdeState
from .renderer import ClawdeRenderer
from .tamagotchi_panel import TamagotchiPanel
from .hat_system import HatManager
from .integration_loader import IntegrationLoader
from .movement import MovementController


class ClawdeApp:
    """
    Main controller that connects all subsystems:
    - ContextListener polls system state in a background thread
    - StateMachine evaluates context + tamagotchi stats each tick
    - ClawdeRenderer draws the character overlay
    - TamagotchiPanel shows stats and feed button
    """

    TICK_INTERVAL_MS = 50  # 20 Hz logic tick

    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        # Subsystems
        self._listener = ContextListener()
        self._state_machine = StateMachine()
        self._renderer = ClawdeRenderer()
        self._panel = TamagotchiPanel()
        self._hat_manager = HatManager()
        self._integration_loader = IntegrationLoader()
        self._movement = MovementController()
        self._was_dragging = False

        # Load external integrations and inject into state machine / hat manager
        self._integration_loader.load_all()
        proc_map = self._integration_loader.get_process_map()
        title_kws = self._integration_loader.get_title_keywords()
        if proc_map or title_kws:
            self._state_machine.register_integration_mappings(proc_map, title_kws)
            print(f"[App] Injected {len(proc_map)} process + {len(title_kws)} title integration(s)")

        # Connect hydration dismiss callback from renderer to state machine
        self._renderer.set_hydration_ack_callback(
            self._state_machine.acknowledge_hydration
        )

        # Connect manual hat selection from the panel to the hat manager
        self._panel.set_hat_callback(self._hat_manager.set_manual_hat)

        # Logic timer
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(self.TICK_INTERVAL_MS)

        self._last_tick = time.time()

    def run(self):
        """Start everything and enter the Qt event loop."""
        # Start context listener background thread
        self._listener.start()

        # Show overlays
        self._renderer.show()
        self._panel.show()

        import io, sys as _sys
        if hasattr(_sys.stdout, 'reconfigure'):
            try: _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception: pass
        print("Clawde is alive!")
        print("  - Hover over Clawde to interact")
        print("  - Drag to reposition")
        print("  - Use the panel to feed")
        print("  - Close this terminal to quit")

        exit_code = self._app.exec()

        # Cleanup
        self._listener.stop()
        return exit_code

    def _tick(self):
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        # Get current context
        ctx = self._listener.context

        # Update interaction states from renderer
        self._state_machine.set_petted(self._renderer.is_petted)
        self._state_machine.set_dragged(self._renderer.is_dragging)

        # Tick state machine
        new_state, changed = self._state_machine.tick(ctx)

        # Compute hat for current state (manual override takes precedence)
        hat = self._hat_manager.get_hat(new_state, self._state_machine.stats, ctx)
        self._renderer.set_hat(hat)

        # Update renderer
        self._renderer.set_state(new_state, self._state_machine.stats)

        # Autonomous movement (only when not being dragged)
        rx = self._renderer.x()
        ry = self._renderer.y()
        new_x, new_y = self._movement.update(
            ctx, rx, ry, self._renderer.is_dragging, new_state.name
        )
        if (new_x != rx or new_y != ry) and not self._renderer.is_dragging:
            self._renderer.move(new_x, new_y)

        # Notify movement controller when drag ends
        if hasattr(self, '_was_dragging') and self._was_dragging and not self._renderer.is_dragging:
            self._movement.notify_drag_released()
        self._was_dragging = self._renderer.is_dragging

        # Update panel
        self._panel.update_stats(self._state_machine.stats, new_state)
        self._panel.tick(dt)

        # Keep panel near renderer
        self._position_panel()

    def _position_panel(self):
        """Keep the tamagotchi panel just below the renderer, centered."""
        rx = self._renderer.x()
        ry = self._renderer.y()
        rw = self._renderer.width()
        pw = self._panel.width()
        target_x = rx + (rw - pw) // 2
        target_y = ry + self._renderer.height() + 2

        # Smooth lerp toward target
        cx = self._panel.x()
        cy = self._panel.y()
        nx = int(cx + (target_x - cx) * 0.1)
        ny = int(cy + (target_y - cy) * 0.1)
        self._panel.move(nx, ny)