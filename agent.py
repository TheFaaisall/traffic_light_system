"""
agent.py
--------
Adaptive timing agent. Its one job: decide how long each phase lasts.

Why an agent and not fixed numbers?
  Real Melbourne traffic lights use the SCATS system (Sydney Coordinated
  Adaptive Traffic System), which adjusts phase durations based on
  measured traffic volume. We simulate that behaviour using time-of-day
  density modelling.

Why a class?
  The agent is a replaceable component. You can swap this rule-based
  version for a sensor-driven one, an LLM-based one, or a trained RL
  model — without touching any other file. The interface stays the same:
    agent.decide_green_duration() -> int
    agent.decide_red_duration()   -> int
"""

from datetime import datetime
from typing import Dict
from config import PEAK_HOURS, TIMING


class AdaptiveTimingAgent:
    """
    Rule-based adaptive traffic timing agent.
    Models Melbourne morning and afternoon peak traffic patterns.
    """

    def __init__(self, timing_config: Dict[str, int] = None):
        self.config = timing_config or TIMING

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    def _get_traffic_density(self) -> float:
        """
        Returns a traffic density score from 0.0 (empty) to 1.0 (peak).

        Inside a peak window:
          Score scales from 0.5 at the edge to 1.0 at the midpoint.
          This reflects how traffic builds toward the peak and eases off.

        Outside peak windows:
          Night (10pm-6am) = 0.1
          Normal daytime   = 0.3
        """
        hour   = datetime.now().hour
        minute = datetime.now().minute
        now    = hour + minute / 60.0   # e.g. 8:30 -> 8.5

        for start, end in PEAK_HOURS:
            if start <= now < end:
                midpoint = (start + end) / 2.0
                # 0.0 = at midpoint (highest density), 1.0 = at edge (lowest in window)
                dist = abs(now - midpoint) / ((end - start) / 2.0)
                return round(1.0 - dist * 0.5, 2)   # range: 0.5 to 1.0

        if hour >= 22 or hour < 6:
            return 0.1
        return 0.3

    def _linear_map(self, density: float, val_min: int, val_max: int) -> int:
        """
        Linearly map a density score [0.0, 1.0] to a duration [val_min, val_max].
        density=0.0 → val_min, density=1.0 → val_max.
        """
        return int(val_min + (val_max - val_min) * density)

    # ----------------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------------

    def decide_green_duration(self) -> int:
        """
        More traffic → longer green.
        More cars need to pass through before the light changes.
        Returns duration in seconds.
        """
        density  = self._get_traffic_density()
        duration = self._linear_map(
            density,
            self.config["green_min"],
            self.config["green_max"]
        )
        print(f"  [Agent] Density={density:.2f}  Green={duration}s")
        return duration

    def decide_red_duration(self) -> int:
        """
        More traffic → longer red.
        The opposing direction also has more cars and needs more time.
        Returns duration in seconds.
        """
        density  = self._get_traffic_density()
        duration = self._linear_map(
            density,
            self.config["red_min"],
            self.config["red_max"]
        )
        print(f"  [Agent] Density={density:.2f}  Red={duration}s")
        return duration
