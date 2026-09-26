"""
State Machine - Manages Clawde's behavioral states with priority system.
Each state maps to a specific animation set. Higher priority states
override lower ones (e.g., Hitman stealth > Discord chat).

Tamagotchi hunger/sleep mechanics have been removed per user request.
Instead, Clawde has a pool of random "self behaviors" it performs on its
own when idle — sneezing, waving, stretching, chasing an imaginary bug,
etc. — so it feels alive even when the user isn't doing anything specific.
"""

from enum import Enum, auto
from dataclasses import dataclass
import time
import random

from .context_listener import SystemContext, ActivityLevel
from .hydration import HydrationReminder


class ClawdeState(Enum):
    """All possible states for Clawde, ordered by default priority."""
    # Forced interaction states (highest priority)
    SYSTEM_ERROR = auto()       # Blue screen voxel crash
    SYSTEM_UPDATE = auto()      # Trapped in update ring
    DANCING = auto()            # Happy dance choreography
    BEING_PETTED = auto()       # Purring with heart particles
    BEING_DRAGGED = auto()      # Flailing limbs, liquid voxel

    # Random self behaviors (medium-high priority, triggered by timer)
    RANDOM_SNEEZE = auto()      # Quick sneeze animation
    RANDOM_WAVE = auto()        # Waves hello to the user
    RANDOM_STRETCH = auto()     # Stretches arms/legs
    RANDOM_BUG = auto()         # Chases an imaginary bug
    RANDOM_EXERCISE = auto()    # Does little jumping jacks
    RANDOM_YAWN = auto()        # Big yawn
    RANDOM_SPIN = auto()        # Spins around once
    RANDOM_THINK = auto()       # Thinking pose with floating "?"

    # App-specific states (medium priority)
    HITMAN_STEALTH = auto()     # Tactical vest, binoculars, prone
    HITMAN_ALERT = auto()       # "Don't see me" masonry pose
    CYBERPUNK_NETRUNNER = auto() # Green floating panels, matrix cables
    VS_CODE_CODING = auto()     # Glasses, step-stool, holographic board
    VS_CODE_FAST_TYPING = auto() # Clapping, excited
    DISCORD_CHAT = auto()       # Mini-sofa, headset, speech bubble
    FILE_EXPLORER = auto()      # Peeking into mini filing cabinet
    WEB_BROWSER = auto()        # Giant magnifying glass, conveyor belt
    SOCIAL_MEDIA = auto()       # Mini-phone, shock/laugh faces
    PHOTOSHOP_CREATING = auto() # Palette, brush, color-changing surface
    TEXT_EDITOR = auto()        # Giant fountain pen
    FULLSCREEN_WATCHING = auto() # Sitting corner, nodding attentively

    # New dynamic states
    HYDRATION_REMINDER = auto() # Water bubble + sipping animation
    WALKING = auto()            # Strolling along the taskbar

    # Default states (lowest priority)
    WATCHTOWER = auto()         # Observing, looking around
    IDLE = auto()               # Gentle breathing, blinking


# Priority map: higher number = higher priority
STATE_PRIORITY = {
    ClawdeState.SYSTEM_ERROR: 100,
    ClawdeState.SYSTEM_UPDATE: 95,
    ClawdeState.BEING_DRAGGED: 90,
    ClawdeState.BEING_PETTED: 85,
    ClawdeState.DANCING: 70,
    # Random behaviors sit above app states so they play out fully,
    # but below forced interactions.
    ClawdeState.RANDOM_SNEEZE: 68,
    ClawdeState.RANDOM_WAVE: 68,
    ClawdeState.RANDOM_STRETCH: 68,
    ClawdeState.RANDOM_BUG: 68,
    ClawdeState.RANDOM_EXERCISE: 68,
    ClawdeState.RANDOM_YAWN: 68,
    ClawdeState.RANDOM_SPIN: 68,
    ClawdeState.RANDOM_THINK: 68,
    ClawdeState.HITMAN_ALERT: 65,
    ClawdeState.HITMAN_STEALTH: 60,
    ClawdeState.CYBERPUNK_NETRUNNER: 55,
    ClawdeState.VS_CODE_FAST_TYPING: 52,
    ClawdeState.VS_CODE_CODING: 50,
    ClawdeState.DISCORD_CHAT: 45,
    ClawdeState.FILE_EXPLORER: 40,
    ClawdeState.WEB_BROWSER: 38,
    ClawdeState.SOCIAL_MEDIA: 36,
    ClawdeState.PHOTOSHOP_CREATING: 34,
    ClawdeState.TEXT_EDITOR: 32,
    ClawdeState.FULLSCREEN_WATCHING: 30,
    ClawdeState.HYDRATION_REMINDER: 67,
    ClawdeState.WALKING: 5,
    ClawdeState.WATCHTOWER: 10,
    ClawdeState.IDLE: 0,
}


# All random self-behavior states, used to pick one at random.
RANDOM_BEHAVIORS = [
    ClawdeState.RANDOM_SNEEZE,
    ClawdeState.RANDOM_WAVE,
    ClawdeState.RANDOM_STRETCH,
    ClawdeState.RANDOM_BUG,
    ClawdeState.RANDOM_EXERCISE,
    ClawdeState.RANDOM_YAWN,
    ClawdeState.RANDOM_SPIN,
    ClawdeState.RANDOM_THINK,
]

# How long each random behavior lasts before returning to idle/watchtower.
RANDOM_BEHAVIOR_DURATION = {
    ClawdeState.RANDOM_SNEEZE: 2.0,
    ClawdeState.RANDOM_WAVE: 3.0,
    ClawdeState.RANDOM_STRETCH: 2.5,
    ClawdeState.RANDOM_BUG: 4.0,
    ClawdeState.RANDOM_EXERCISE: 3.5,
    ClawdeState.RANDOM_YAWN: 2.5,
    ClawdeState.RANDOM_SPIN: 2.0,
    ClawdeState.RANDOM_THINK: 3.5,
}


@dataclass
class TamagotchiStats:
    """
    Lightweight stats — hunger and energy were removed. Happiness remains
    as a simple mood value that rises when petted and slowly drifts back
    to neutral, used only to occasionally trigger a happy dance.
    """
    happiness: float = 60.0   # 0 = sad, 100 = ecstatic

    HAPPINESS_DECAY_RATE = 0.05   # per second, drifts toward neutral (50)
    HAPPINESS_NEUTRAL = 50.0

    def update(self, dt: float):
        # Drift toward neutral rather than decaying to zero
        if self.happiness > self.HAPPINESS_NEUTRAL:
            self.happiness = max(self.HAPPINESS_NEUTRAL,
                                 self.happiness - self.HAPPINESS_DECAY_RATE * dt)
        elif self.happiness < self.HAPPINESS_NEUTRAL:
            self.happiness = min(self.HAPPINESS_NEUTRAL,
                                 self.happiness + self.HAPPINESS_DECAY_RATE * dt)

    def pet(self, amount: float = 15.0):
        self.happiness = min(100, self.happiness + amount)

    @property
    def is_happy(self) -> bool:
        return self.happiness > 80


# ─── Process → State mapping ─────────────────────────────────────────
# Keys are lowercased; matching uses substring containment so variants
# like "hitman3.exe", "hitman 3.exe", or launcher wrappers still match.

PROCESS_STATE_MAP: dict[str, ClawdeState] = {
    # IDEs
    "code.exe": ClawdeState.VS_CODE_CODING,
    "code": ClawdeState.VS_CODE_CODING,
    "pycharm.exe": ClawdeState.VS_CODE_CODING,
    "pycharm64.exe": ClawdeState.VS_CODE_CODING,
    "idea64.exe": ClawdeState.VS_CODE_CODING,
    "sublime_text.exe": ClawdeState.VS_CODE_CODING,
    "notepad++.exe": ClawdeState.TEXT_EDITOR,
    "notepad.exe": ClawdeState.TEXT_EDITOR,
    "wordpad.exe": ClawdeState.TEXT_EDITOR,
    "winword.exe": ClawdeState.TEXT_EDITOR,

    # Communication
    "discord.exe": ClawdeState.DISCORD_CHAT,
    "slack.exe": ClawdeState.DISCORD_CHAT,
    "teams.exe": ClawdeState.DISCORD_CHAT,

    # File management
    "explorer.exe": ClawdeState.FILE_EXPLORER,
    "finder": ClawdeState.FILE_EXPLORER,

    # Browsers
    "chrome.exe": ClawdeState.WEB_BROWSER,
    "msedge.exe": ClawdeState.WEB_BROWSER,
    "firefox.exe": ClawdeState.WEB_BROWSER,
    "brave.exe": ClawdeState.WEB_BROWSER,
    "opera.exe": ClawdeState.WEB_BROWSER,

    # Creative tools
    "photoshop.exe": ClawdeState.PHOTOSHOP_CREATING,
    "blender.exe": ClawdeState.PHOTOSHOP_CREATING,
    "gimp-2.10.exe": ClawdeState.PHOTOSHOP_CREATING,

    # Games — Hitman 3 ships under several executable names across
    # Steam/Epic/GOG, so we list the known variants. Matching is by
    # substring, so "hitman" alone also catches future variants.
    "hitman3.exe": ClawdeState.HITMAN_STEALTH,
    "hitman 3.exe": ClawdeState.HITMAN_STEALTH,
    "hitmaniii.exe": ClawdeState.HITMAN_STEALTH,
    "hitman.exe": ClawdeState.HITMAN_STEALTH,
    "cyberpunk2077.exe": ClawdeState.CYBERPUNK_NETRUNNER,
}

# Window-title keywords that also map to states. This is the fallback for
# games/apps whose foreground process name doesn't match (e.g. a launcher
# is in front, or the exe has an unexpected name). Hitman's window title
# reliably contains "hitman".
TITLE_KEYWORD_STATES: list[tuple[str, ClawdeState]] = [
    ("hitman", ClawdeState.HITMAN_STEALTH),
    ("cyberpunk", ClawdeState.CYBERPUNK_NETRUNNER),
    ("netrunner", ClawdeState.CYBERPUNK_NETRUNNER),
]

# Social media detection via window title keywords
SOCIAL_KEYWORDS = ["twitter", "x.com", "instagram", "facebook", "tiktok", "reddit"]


def _match_process(process_lower: str) -> "ClawdeState | None":
    """Return a mapped state if any key is contained in the process name."""
    for key, state in PROCESS_STATE_MAP.items():
        if key in process_lower:
            return state
    return None


def _match_title(title_lower: str) -> "ClawdeState | None":
    """Return a mapped state if any title keyword is present."""
    for kw, state in TITLE_KEYWORD_STATES:
        if kw in title_lower:
            return state
    return None


class StateMachine:
    """
    Evaluates context each tick and determines the current ClawdeState
    using a priority system. Also drives random self-behaviors on a
    timer when the user is idle or in a low-priority state.
    """

    # Integration-injected mappings (populated at runtime by IntegrationLoader)
    _integration_process_map: dict[str, tuple[str, int]] = {}
    _integration_title_keywords: list[tuple[str, str, int]] = []

    @classmethod
    def register_integration_mappings(
        cls,
        process_map: dict[str, tuple[str, int]],
        title_keywords: list[tuple[str, str, int]],
    ):
        """
        Inject integration-defined process and title mappings.
        Called once at startup by ClawdeApp after loading integrations.

        process_map: {process_name_lower: (custom_state_name, priority)}
        title_keywords: [(keyword_lower, custom_state_name, priority)]
        """
        cls._integration_process_map = dict(process_map)
        cls._integration_title_keywords = list(title_keywords)

    @staticmethod
    def _match_integration_process(process_lower: str) -> "str | None":
        """Return custom state name from integration process map, or None."""
        for key, (state_name, _priority) in StateMachine._integration_process_map.items():
            if key in process_lower:
                return state_name
        return None

    @staticmethod
    def _match_integration_title(title_lower: str) -> "str | None":
        """Return custom state name from integration title keywords, or None."""
        for kw, state_name, _priority in StateMachine._integration_title_keywords:
            if kw in title_lower:
                return state_name
        return None

    # Random behavior scheduling: wait between MIN and MAX seconds, then
    # play one behavior for its fixed duration.
    RANDOM_INTERVAL_MIN = 12.0
    RANDOM_INTERVAL_MAX = 30.0

    def __init__(self):
        self.stats = TamagotchiStats()
        self._current_state = ClawdeState.IDLE
        self._state_entered_at = time.time()
        self._is_being_petted = False
        self._is_being_dragged = False
        self._system_error = False
        self._system_update = False
        self._last_update = time.time()
        self._happy_dance_cooldown = 0.0

        # Random behavior scheduler
        self._next_random_at = time.time() + random.uniform(
            self.RANDOM_INTERVAL_MIN, self.RANDOM_INTERVAL_MAX
        )
        self._active_random: "ClawdeState | None" = None
        self._random_ends_at = 0.0

        # Hydration reminder system
        self._hydration = HydrationReminder()

    @property
    def hydration(self) -> HydrationReminder:
        """Expose hydration reminder for external dismiss (renderer events)."""
        return self._hydration

    def acknowledge_hydration(self):
        """Call when user clicks/hovers during HYDRATION_REMINDER to dismiss."""
        self._hydration.acknowledge()

    @property
    def current_state(self) -> ClawdeState:
        return self._current_state

    @property
    def state_duration(self) -> float:
        return time.time() - self._state_entered_at

    def set_petted(self, active: bool):
        self._is_being_petted = active
        if active:
            self.stats.pet(5.0)

    def set_dragged(self, active: bool):
        self._is_being_dragged = active

    def set_system_error(self, active: bool):
        self._system_error = active

    def set_system_update(self, active: bool):
        self._system_update = active

    def tick(self, ctx: SystemContext) -> tuple[ClawdeState, bool]:
        """
        Evaluate current context and return (new_state, changed).
        Call this every frame or at regular intervals.
        """
        now = time.time()
        dt = now - self._last_update
        self._last_update = now

        # Update mood
        self.stats.update(dt)

        # Decrease happy dance cooldown
        self._happy_dance_cooldown = max(0, self._happy_dance_cooldown - dt)

        # Expire an active random behavior when its duration elapses
        if self._active_random is not None and now >= self._random_ends_at:
            self._active_random = None
            self._next_random_at = now + random.uniform(
                self.RANDOM_INTERVAL_MIN, self.RANDOM_INTERVAL_MAX
            )

        # Determine candidate state
        candidate = self._evaluate(ctx, now)

        # Only transition if candidate has higher or equal priority,
        # or if we've been in current state for a while
        candidate_pri = STATE_PRIORITY.get(candidate, 0)
        current_pri = STATE_PRIORITY.get(self._current_state, 0)

        should_switch = (
            candidate_pri > current_pri
            or (candidate_pri == current_pri and candidate != self._current_state)
            or self.state_duration > 30.0  # re-evaluate after 30s
        )

        changed = False
        if should_switch and candidate != self._current_state:
            self._current_state = candidate
            self._state_entered_at = now
            changed = True

        return self._current_state, changed

    def _evaluate(self, ctx: SystemContext, now: float) -> ClawdeState:
        # Highest priority: forced states
        if self._system_error:
            return ClawdeState.SYSTEM_ERROR
        if self._system_update:
            return ClawdeState.SYSTEM_UPDATE
        if self._is_being_dragged:
            return ClawdeState.BEING_DRAGGED
        if self._is_being_petted:
            return ClawdeState.BEING_PETTED

        # Happy dance from high mood (kept as a fun reaction)
        if self.stats.is_happy and self._happy_dance_cooldown <= 0:
            self._happy_dance_cooldown = 60.0
            return ClawdeState.DANCING

        # Fullscreen → watching (games, video). Checked before process/title
        # mapping so a fullscreen Hitman still gets its stealth state below
        # only when not fullscreen; when fullscreen we prefer the game state
        # if one matches, otherwise the watching pose.
        fullscreen = ctx.is_fullscreen

        # Check window title for social media
        title_lower = ctx.window_title.lower()
        for kw in SOCIAL_KEYWORDS:
            if kw in title_lower:
                return ClawdeState.SOCIAL_MEDIA

        # Title-keyword mapping (catches Hitman/Cyberpunk even if the
        # foreground process name is a launcher or wrapper).
        title_state = _match_title(title_lower)

        # Process-based mapping (substring match)
        process_state = _match_process(ctx.process_lower)

        # Prefer a specific game/app state over the generic fullscreen pose.
        game_or_app = title_state or process_state
        if game_or_app is not None:
            # Special case: fast typing in IDE
            if game_or_app == ClawdeState.VS_CODE_CODING and ctx.typing_rate > 5:
                return ClawdeState.VS_CODE_FAST_TYPING
            return game_or_app

        # Integration-defined states (evaluated after built-in maps)
        int_title_state = self._match_integration_title(title_lower)
        int_process_state = self._match_integration_process(ctx.process_lower)
        int_state = int_title_state or int_process_state
        if int_state is not None:
            return int_state

        if fullscreen:
            return ClawdeState.FULLSCREEN_WATCHING

        # Random self-behaviors: only when the user is fairly idle and we're
        # not already committed to a higher-priority app state. This is what
        # makes Clawde "do its own thing" when nothing specific is happening.
        if (self._active_random is not None
                and ctx.activity_level in (ActivityLevel.IDLE, ActivityLevel.LOW)):
            return self._active_random

        if (now >= self._next_random_at
                and ctx.activity_level in (ActivityLevel.IDLE, ActivityLevel.LOW)):
            self._active_random = random.choice(RANDOM_BEHAVIORS)
            self._random_ends_at = now + RANDOM_BEHAVIOR_DURATION[self._active_random]
            return self._active_random

        # Hydration reminder: only when idle/low and timer has elapsed
        if self._hydration.should_remind(now):
            if ctx.activity_level in (ActivityLevel.IDLE, ActivityLevel.LOW):
                self._hydration.activate(now)
                return ClawdeState.HYDRATION_REMINDER
        if self._hydration.is_active:
            still_showing = self._hydration.tick(now)
            if still_showing:
                return ClawdeState.HYDRATION_REMINDER
            # Reminder expired this tick — fall through to normal states

        # Default states based on activity
        if ctx.activity_level in (ActivityLevel.MODERATE, ActivityLevel.HIGH, ActivityLevel.INTENSE):
            return ClawdeState.WATCHTOWER

        return ClawdeState.IDLE