"""
Hat System - Dynamic hat selection based on state, time of day, and context.
Each hat is drawn as voxel art on top of Clawde's body by the renderer.
"""

from enum import Enum, auto
from datetime import datetime
from typing import Optional

from .state_machine import ClawdeState
from .context_listener import SystemContext


class HatType(Enum):
    """All possible hats Clawde can wear."""
    NONE = auto()
    SUN_HAT = auto()          # Straw hat for daytime idle
    NIGHT_CAP = auto()        # Sleepy cap for nighttime
    RAIN_HAT = auto()         # Yellow raincoat hood for system errors
    CHEF_HAT = auto()         # Chef toque for text editors
    HARD_HAT = auto()         # Construction helmet for IDEs
    STEALTH_BERET = auto()    # Black beret for Hitman states
    CYBER_VISOR = auto()      # Neon green visor for Cyberpunk
    PARTY_HAT = auto()        # Multicolor cone for dancing/happy
    WATER_DROPLET = auto()    # Blue water drop for hydration reminder
    WALKING_CAP = auto()      # Small cap for walking state


# Maps states to their primary hat. Higher-priority states take precedence
# because get_hat() checks this first before falling back to time-of-day.
STATE_HAT_MAP: dict[ClawdeState, HatType] = {
    ClawdeState.SYSTEM_ERROR: HatType.RAIN_HAT,
    ClawdeState.SYSTEM_UPDATE: HatType.RAIN_HAT,
    ClawdeState.DANCING: HatType.PARTY_HAT,
    ClawdeState.VS_CODE_CODING: HatType.HARD_HAT,
    ClawdeState.VS_CODE_FAST_TYPING: HatType.HARD_HAT,
    ClawdeState.TEXT_EDITOR: HatType.CHEF_HAT,
    ClawdeState.HITMAN_STEALTH: HatType.STEALTH_BERET,
    ClawdeState.HITMAN_ALERT: HatType.STEALTH_BERET,
    ClawdeState.CYBERPUNK_NETRUNNER: HatType.CYBER_VISOR,
    ClawdeState.HYDRATION_REMINDER: HatType.WATER_DROPLET,
    ClawdeState.WALKING: HatType.WALKING_CAP,
}


class HatManager:
    """
    Evaluates current state + context each tick and returns which hat
    Clawde should wear. Stateless — all logic is in get_hat().
    """

    def __init__(self):
        self._manual_hat: Optional[HatType] = None

    def set_manual_hat(self, hat: Optional[HatType]):
        """Set a user-chosen hat override. None = automatic selection."""
        self._manual_hat = hat

    @property
    def manual_hat(self) -> Optional[HatType]:
        return self._manual_hat

    def get_hat(self, state: ClawdeState, stats, ctx: SystemContext) -> HatType:
        """
        Determine the current hat. Priority order:
        1. Manual override chosen from the panel
        2. State-specific hat (from STATE_HAT_MAP)
        3. Happiness-based party hat (happiness > 90)
        4. Time-of-day hat (sun hat during day, night cap at night)
        5. NONE
        """
        # 1. Manual override from the panel
        if self._manual_hat is not None:
            return self._manual_hat

        # 2. State-driven hat
        hat = STATE_HAT_MAP.get(state)
        if hat is not None:
            return hat

        # 2. Party hat from high happiness (only in low-priority states)
        if hasattr(stats, 'happiness') and stats.happiness > 90:
            if state in (ClawdeState.IDLE, ClawdeState.WATCHTOWER):
                return HatType.PARTY_HAT

        # 3. Time-of-day hats (only when idle/watchtower — don't override
        # app-specific states that don't have their own hat)
        if state in (ClawdeState.IDLE, ClawdeState.WATCHTOWER):
            hour = datetime.now().hour
            if 10 <= hour < 18:
                return HatType.SUN_HAT
            elif hour >= 22 or hour < 6:
                return HatType.NIGHT_CAP

        return HatType.NONE