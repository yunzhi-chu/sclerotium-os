"""STG Neuromodulator — profile-based behavior reconfiguration.

In the lobster STG, the same 30-neuron circuit produces different
motor patterns depending on which neuromodulators are present:
  - Dopamine → enhanced pyloric frequency
  - Serotonin → gastric mill dominance
  - GABA → circuit suppression (sleep-like)
  - Acetylcholine → heightened responsiveness
  - Norepinephrine → alert, focused patterns

In Sclerotium OS, "neuromodulators" are configuration profiles that
reconfigure system behavior without changing the underlying code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Profile(Enum):
    WORK = "work"
    SLEEP = "sleep"
    GAME = "game"
    MEETING = "meeting"
    CREATIVE = "creative"


@dataclass
class ModulationState:
    """What each profile modulates."""
    notification_level: str = "all"      # all | important | none
    evolution_enabled: bool = True
    llm_routing: str = "cheapest"       # cheapest | balanced | best
    scan_frequency: str = "normal"      # high | normal | low | off
    auto_reply_enabled: bool = False
    sandbox_isolation: int = 1          # 1 | 2 | 3
    im_poll_interval: float = 30.0      # seconds
    pyloric_scan_interval: float = 1800.0  # seconds
    gastric_daily_hour: int = 9


# ── Profile definitions (like lobster neuromodulator cocktails) ──────

PROFILES: dict[Profile, ModulationState] = {
    Profile.WORK: ModulationState(
        notification_level="all",
        evolution_enabled=True,
        llm_routing="balanced",
        scan_frequency="normal",
        auto_reply_enabled=False,
        sandbox_isolation=1,
        im_poll_interval=30,
        pyloric_scan_interval=1800,  # 30 min
    ),
    Profile.SLEEP: ModulationState(
        notification_level="none",
        evolution_enabled=False,
        llm_routing="cheapest",
        scan_frequency="off",
        auto_reply_enabled=False,
        sandbox_isolation=1,
        im_poll_interval=300,  # 5 min
        pyloric_scan_interval=3600 * 6,  # 6 hours
    ),
    Profile.GAME: ModulationState(
        notification_level="important",
        evolution_enabled=False,
        llm_routing="cheapest",
        scan_frequency="off",
        auto_reply_enabled=True,
        sandbox_isolation=1,
        im_poll_interval=120,
        pyloric_scan_interval=3600,  # 1 hour
    ),
    Profile.MEETING: ModulationState(
        notification_level="none",
        evolution_enabled=False,
        llm_routing="balanced",
        scan_frequency="low",
        auto_reply_enabled=True,
        sandbox_isolation=2,  # elevated security
        im_poll_interval=60,
        pyloric_scan_interval=3600,
    ),
    Profile.CREATIVE: ModulationState(
        notification_level="important",
        evolution_enabled=True,
        llm_routing="best",
        scan_frequency="high",
        auto_reply_enabled=False,
        sandbox_isolation=1,
        im_poll_interval=30,
        pyloric_scan_interval=600,  # 10 min
    ),
}


class Neuromodulator:
    """Profile-based system behavior reconfiguration.

    Switches between WORK / SLEEP / GAME / MEETING / CREATIVE profiles,
    each applying a different "neuromodulator cocktail" to the system.
    """

    def __init__(self) -> None:
        self._active_profile: Profile = Profile.WORK
        self._state: ModulationState = PROFILES[Profile.WORK]

    @property
    def active_profile(self) -> Profile:
        return self._active_profile

    @property
    def state(self) -> ModulationState:
        return self._state

    def switch(self, profile_name: str) -> dict[str, Any]:
        """Switch to a new profile. Returns changes applied."""
        try:
            profile = Profile(profile_name)
        except ValueError:
            return {"error": f"Invalid profile: {profile_name}. "
                    "Valid: work, sleep, game, meeting, creative"}

        old = self._active_profile
        self._active_profile = profile
        self._state = PROFILES[profile]

        return {
            "active_profile": profile.value,
            "previous_profile": old.value,
            "changes": {
                "notification_level": self._state.notification_level,
                "evolution_enabled": self._state.evolution_enabled,
                "llm_routing": self._state.llm_routing,
                "scan_frequency": self._state.scan_frequency,
                "auto_reply_enabled": self._state.auto_reply_enabled,
                "sandbox_isolation": self._state.sandbox_isolation,
                "im_poll_interval_s": self._state.im_poll_interval,
            },
        }

    def get_profile(self) -> dict[str, Any]:
        """Get current profile state."""
        return {
            "profile": self._active_profile.value,
            "notification_level": self._state.notification_level,
            "evolution_enabled": self._state.evolution_enabled,
            "llm_routing": self._state.llm_routing,
            "scan_frequency": self._state.scan_frequency,
            "auto_reply_enabled": self._state.auto_reply_enabled,
            "sandbox_isolation": self._state.sandbox_isolation,
        }
