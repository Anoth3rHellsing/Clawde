"""
Integration Loader - Scans clawde_integrations/active/*.json at startup,
validates each file, and exposes process/title mappings for StateMachine.
"""

import json
import os
from pathlib import Path
from typing import Optional


# Directory relative to project root
_INTEGRATIONS_DIR = Path(__file__).resolve().parent.parent / "clawde_integrations" / "active"


class IntegrationConfig:
    """Parsed and validated integration entry."""

    __slots__ = (
        "name", "integration_id", "process_match", "title_keywords",
        "on_activate_state", "on_activate_priority", "on_activate_hat",
        "on_activate_bubble", "on_idle_after_seconds", "on_idle_after_state",
        "on_pet_bubble", "on_drag_bubble", "preferred_zone", "hide_probability",
    )

    def __init__(self):
        self.name: str = ""
        self.integration_id: str = ""
        self.process_match: list[str] = []
        self.title_keywords: list[str] = []
        self.on_activate_state: str = ""
        self.on_activate_priority: int = 50
        self.on_activate_hat: Optional[str] = None
        self.on_activate_bubble: Optional[str] = None
        self.on_idle_after_seconds: int = 300
        self.on_idle_after_state: str = "IDLE"
        self.on_pet_bubble: Optional[str] = None
        self.on_drag_bubble: Optional[str] = None
        self.preferred_zone: str = "safehouse"
        self.hide_probability: float = 0.15


def _validate_and_parse(filepath: Path) -> Optional[IntegrationConfig]:
    """Parse a single JSON file. Returns None if invalid."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[IntegrationLoader] Skipping {filepath.name}: {exc}")
        return None

    if not isinstance(data, dict):
        print(f"[IntegrationLoader] Skipping {filepath.name}: root is not an object")
        return None

    cfg = IntegrationConfig()
    cfg.integration_id = filepath.stem.upper()

    # Required fields
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        print(f"[IntegrationLoader] Skipping {filepath.name}: missing or empty 'name'")
        return None
    cfg.name = name[:64]

    proc = data.get("process_match")
    if not isinstance(proc, list) or len(proc) == 0:
        print(f"[IntegrationLoader] Skipping {filepath.name}: 'process_match' must be non-empty array")
        return None
    cfg.process_match = [str(p).lower() for p in proc if isinstance(p, str) and p.strip()]
    if not cfg.process_match:
        print(f"[IntegrationLoader] Skipping {filepath.name}: no valid entries in 'process_match'")
        return None

    # Optional: title_keywords
    tk = data.get("title_keywords")
    if isinstance(tk, list):
        cfg.title_keywords = [str(k).lower() for k in tk if isinstance(k, str) and k.strip()]

    # States
    states = data.get("states", {})
    if isinstance(states, dict):
        on_act = states.get("on_activate", {})
        if isinstance(on_act, dict):
            state_name = on_act.get("state", "")
            if isinstance(state_name, str) and state_name.strip():
                # Prefix with integration ID to avoid collisions
                cfg.on_activate_state = f"{cfg.integration_id}_{state_name.upper()}"
            pri = on_act.get("priority", 50)
            if isinstance(pri, (int, float)):
                cfg.on_activate_priority = max(1, min(99, int(pri)))
            hat = on_act.get("hat")
            if isinstance(hat, str) and hat.strip():
                cfg.on_activate_hat = hat.upper()
            bubble = on_act.get("bubble_text")
            if isinstance(bubble, str):
                cfg.on_activate_bubble = bubble

        on_idle = states.get("on_idle_after", {})
        if isinstance(on_idle, dict):
            secs = on_idle.get("seconds", 300)
            if isinstance(secs, (int, float)):
                cfg.on_idle_after_seconds = max(30, min(3600, int(secs)))
            idle_state = on_idle.get("state", "IDLE")
            if isinstance(idle_state, str):
                cfg.on_idle_after_state = idle_state.upper()

    # Interactions
    interactions = data.get("interactions", {})
    if isinstance(interactions, dict):
        on_pet = interactions.get("on_pet", {})
        if isinstance(on_pet, dict):
            bt = on_pet.get("bubble_text")
            if isinstance(bt, str):
                cfg.on_pet_bubble = bt
        on_drag = interactions.get("on_drag", {})
        if isinstance(on_drag, dict):
            bt = on_drag.get("bubble_text")
            if isinstance(bt, str):
                cfg.on_drag_bubble = bt

    # Movement
    movement = data.get("movement", {})
    if isinstance(movement, dict):
        zone = movement.get("preferred_zone")
        if isinstance(zone, str) and zone in ("taskbar", "safehouse", "window"):
            cfg.preferred_zone = zone
        hp = movement.get("hide_probability")
        if isinstance(hp, (int, float)):
            cfg.hide_probability = max(0.0, min(1.0, float(hp)))

    return cfg


class IntegrationLoader:
    """
    Loads all valid integration configs from clawde_integrations/active/.
    Call load_all() once at app startup.
    """

    def __init__(self):
        self._configs: list[IntegrationConfig] = []

    def load_all(self) -> list[IntegrationConfig]:
        """Scan active/ directory, parse and validate each JSON file."""
        self._configs.clear()

        if not _INTEGRATIONS_DIR.is_dir():
            print(f"[IntegrationLoader] Directory not found: {_INTEGRATIONS_DIR}")
            return self._configs

        files = sorted(_INTEGRATIONS_DIR.glob("*.json"))
        for fp in files:
            cfg = _validate_and_parse(fp)
            if cfg is not None:
                self._configs.append(cfg)
                print(f"[IntegrationLoader] Loaded: {cfg.name} ({fp.name})")

        print(f"[IntegrationLoader] Total integrations loaded: {len(self._configs)}")
        return self._configs

    @property
    def configs(self) -> list[IntegrationConfig]:
        return list(self._configs)

    def get_process_map(self) -> dict[str, tuple[str, int]]:
        """
        Returns {process_name_lower: (custom_state_name, priority)}.
        First match wins (alphabetical file order).
        """
        result: dict[str, tuple[str, int]] = {}
        for cfg in self._configs:
            if not cfg.on_activate_state:
                continue
            for proc in cfg.process_match:
                if proc not in result:
                    result[proc] = (cfg.on_activate_state, cfg.on_activate_priority)
        return result

    def get_title_keywords(self) -> list[tuple[str, str, int]]:
        """
        Returns [(keyword_lower, custom_state_name, priority)].
        """
        result: list[tuple[str, str, int]] = []
        for cfg in self._configs:
            if not cfg.on_activate_state:
                continue
            for kw in cfg.title_keywords:
                result.append((kw, cfg.on_activate_state, cfg.on_activate_priority))
        return result

    def get_hat_overrides(self) -> dict[str, str]:
        """
        Returns {custom_state_name: hat_type_string}.
        """
        result: dict[str, str] = {}
        for cfg in self._configs:
            if cfg.on_activate_state and cfg.on_activate_hat:
                result[cfg.on_activate_state] = cfg.on_activate_hat
        return result

    def get_bubble_overrides(self) -> dict[str, str]:
        """
        Returns {custom_state_name: bubble_text}.
        """
        result: dict[str, str] = {}
        for cfg in self._configs:
            if cfg.on_activate_state and cfg.on_activate_bubble:
                result[cfg.on_activate_state] = cfg.on_activate_bubble
        return result