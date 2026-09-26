"""
Context Listener - The brain of Clawde.
Continuously monitors system state, active processes, window titles,
mouse/keyboard activity, and fullscreen status.
"""

import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum, auto

import psutil


class ActivityLevel(Enum):
    IDLE = auto()
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    INTENSE = auto()


@dataclass
class SystemContext:
    """Snapshot of the current system context."""
    active_process: str = ""
    window_title: str = ""
    is_fullscreen: bool = False
    mouse_active: bool = False
    keyboard_active: bool = False
    activity_level: ActivityLevel = ActivityLevel.IDLE
    idle_seconds: float = 0.0
    typing_rate: float = 0.0  # keystrokes per second
    timestamp: float = field(default_factory=time.time)

    @property
    def process_lower(self) -> str:
        return self.active_process.lower()

    def matches_process(self, *names: str) -> bool:
        pl = self.process_lower
        return any(n.lower() in pl for n in names)


# ─── Platform-specific window detection ───────────────────────────────

if sys.platform == "win32":
    try:
        import win32gui
        import win32process
        import win32con
        import ctypes
        import ctypes.wintypes

        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False

if sys.platform == "darwin":
    try:
        import Quartz
        from AppKit import NSWorkspace
        HAS_COCOA = True
    except ImportError:
        HAS_COCOA = False
else:
    HAS_COCOA = False


def _get_win32_foreground() -> tuple[str, str]:
    """Return (process_name, window_title) for the foreground window on Windows."""
    if not HAS_WIN32:
        return ("", "")
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return (proc.name(), title)
    except Exception:
        return ("", "")


def _is_win32_fullscreen() -> bool:
    """Check if the foreground window covers the entire screen."""
    if not HAS_WIN32:
        return False
    try:
        hwnd = win32gui.GetForegroundWindow()
        rect = win32gui.GetWindowRect(hwnd)
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        return (rect[0] <= 0 and rect[1] <= 0 and
                rect[2] >= sw and rect[3] >= sh)
    except Exception:
        return False


def _get_cocoa_foreground() -> tuple[str, str]:
    """Return (process_name, window_title) for macOS."""
    if not HAS_COCOA:
        return ("", "")
    try:
        workspace = NSWorkspace.sharedWorkspace()
        app = workspace.frontmostApplication()
        name = app.localizedName() or ""
        # Get window title via Quartz
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        title = ""
        for w in windows:
            owner = w.get("kCGWindowOwnerName", "")
            if owner == name:
                title = w.get("kCGWindowName", "")
                if title:
                    break
        return (name, title)
    except Exception:
        return ("", "")


def _is_cocoa_fullscreen() -> bool:
    """Check fullscreen on macOS."""
    if not HAS_COCOA:
        return False
    try:
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        main_display = Quartz.CGMainDisplayID()
        bounds = Quartz.CGDisplayBounds(main_display)
        dw, dh = int(bounds.size.width), int(bounds.size.height)
        for w in windows:
            b = w.get("kCGWindowBounds", {})
            if (b.get("Width", 0) >= dw and b.get("Height", 0) >= dh
                    and w.get("kCGWindowLayer", 99) == 0):
                return True
        return False
    except Exception:
        return False


# ─── Input activity tracking ──────────────────────────────────────────

class InputTracker:
    """Tracks mouse and keyboard activity using low-level hooks or polling."""

    def __init__(self):
        self._last_mouse_pos: Optional[tuple] = None
        self._last_activity_time: float = time.time()
        self._keystroke_times: list[float] = []
        self._lock = threading.Lock()
        self._mouse_active = False
        self._keyboard_active = False

        if sys.platform == "win32" and HAS_WIN32:
            self._start_win32_hooks()
        else:
            self._start_polling()

    def _start_win32_hooks(self):
        """Install low-level keyboard/mouse hooks on Windows."""
        self._hook_thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._hook_thread.start()

    def _hook_loop(self):
        import ctypes
        import ctypes.wintypes as wt

        WH_KEYBOARD_LL = 13
        WH_MOUSE_LL = 14

        # On 64-bit Python, LPARAM/WPARAM/HOOKPROC must use c_ssize_t
        # to avoid OverflowError when values exceed 32-bit signed range.
        HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,    # LRESULT (return)
            ctypes.c_int,        # nCode
            ctypes.c_ssize_t,    # WPARAM
            ctypes.c_ssize_t,    # LPARAM
        )

        # Properly type CallNextHookEx so 64-bit pointers don't overflow
        ctypes.windll.user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_ssize_t
        ]
        ctypes.windll.user32.CallNextHookEx.restype = ctypes.c_ssize_t

        ctypes.windll.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, ctypes.c_void_p, wt.DWORD
        ]
        ctypes.windll.user32.SetWindowsHookExW.restype = ctypes.c_void_p

        ctypes.windll.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wt.MSG), ctypes.c_void_p, wt.UINT, wt.UINT
        ]
        ctypes.windll.user32.GetMessageW.restype = ctypes.c_int

        def kbd_hook(nCode, wParam, lParam):
            with self._lock:
                self._last_activity_time = time.time()
                self._keyboard_active = True
                self._keystroke_times.append(time.time())
            return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

        def ms_hook(nCode, wParam, lParam):
            with self._lock:
                self._last_activity_time = time.time()
                self._mouse_active = True
            return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._kbd_cb = HOOKPROC(kbd_hook)
        self._ms_cb = HOOKPROC(ms_hook)

        kbd_handle = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._kbd_cb, None, 0
        )
        ms_handle = ctypes.windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._ms_cb, None, 0
        )

        msg = wt.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

    def _start_polling(self):
        """Fallback: poll mouse position for activity detection."""
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while True:
            try:
                if sys.platform == "win32" and HAS_WIN32:
                    pos = win32gui.GetCursorPos()
                else:
                    pos = None
                if pos and pos != self._last_mouse_pos:
                    with self._lock:
                        self._last_activity_time = time.time()
                        self._mouse_active = True
                    self._last_mouse_pos = pos
            except Exception:
                pass
            time.sleep(0.1)

    def get_state(self) -> dict:
        now = time.time()
        with self._lock:
            idle = now - self._last_activity_time
            # Clean old keystrokes (keep last 5 seconds)
            cutoff = now - 5.0
            self._keystroke_times = [t for t in self._keystroke_times if t > cutoff]
            typing_rate = len(self._keystroke_times) / 5.0

            mouse = self._mouse_active
            keyboard = self._keyboard_active
            self._mouse_active = False
            self._keyboard_active = False

        if idle < 2:
            level = ActivityLevel.INTENSE if typing_rate > 5 else ActivityLevel.HIGH
        elif idle < 10:
            level = ActivityLevel.MODERATE
        elif idle < 60:
            level = ActivityLevel.LOW
        else:
            level = ActivityLevel.IDLE

        return {
            "mouse_active": mouse,
            "keyboard_active": keyboard,
            "idle_seconds": idle,
            "typing_rate": typing_rate,
            "activity_level": level,
        }


# ─── Main Context Listener ────────────────────────────────────────────

class ContextListener:
    """
    Continuously polls system context and emits changes via callbacks.
    Thread-safe. Runs its own background thread.
    """

    POLL_INTERVAL = 0.5  # seconds

    def __init__(self):
        self._context = SystemContext()
        self._input = InputTracker()
        self._callbacks: list[Callable[[SystemContext], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def context(self) -> SystemContext:
        with self._lock:
            return self._context

    def on_context_change(self, callback: Callable[[SystemContext], None]):
        self._callbacks.append(callback)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _poll_loop(self):
        while self._running:
            ctx = self._sample()
            with self._lock:
                old = self._context
                self._context = ctx
            if self._changed(old, ctx):
                for cb in self._callbacks:
                    try:
                        cb(ctx)
                    except Exception:
                        pass
            time.sleep(self.POLL_INTERVAL)

    def _sample(self) -> SystemContext:
        # Get foreground process + window
        if sys.platform == "win32":
            proc, title = _get_win32_foreground()
            fullscreen = _is_win32_fullscreen()
        elif sys.platform == "darwin":
            proc, title = _get_cocoa_foreground()
            fullscreen = _is_cocoa_fullscreen()
        else:
            proc, title, fullscreen = "", "", False

        # Get input state
        inp = self._input.get_state()

        return SystemContext(
            active_process=proc,
            window_title=title,
            is_fullscreen=fullscreen,
            mouse_active=inp["mouse_active"],
            keyboard_active=inp["keyboard_active"],
            activity_level=inp["activity_level"],
            idle_seconds=inp["idle_seconds"],
            typing_rate=inp["typing_rate"],
            timestamp=time.time(),
        )

    @staticmethod
    def _changed(old: SystemContext, new: SystemContext) -> bool:
        return (
            old.active_process != new.active_process
            or old.is_fullscreen != new.is_fullscreen
            or old.activity_level != new.activity_level
        )