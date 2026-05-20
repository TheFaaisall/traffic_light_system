"""
context.py
----------
Defines the two core types that every module in this project imports:

  TrafficState  — enum of all possible traffic light states
  SystemContext — shared memory object passed through every function

Every module reads from and writes to ONE SystemContext instance.
This is how threads and components stay in sync without globals.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional


class TrafficState(Enum):
    """
    All possible states the traffic light system can be in.
    Using Enum instead of strings:
    - Typos throw an error immediately (TrafficState.GREEM fails at import)
    - IDE autocomplete works
    - Comparisons are unambiguous
    """
    GREEN     = auto()   # vehicles go
    AMBER     = auto()   # vehicles slow — warning
    ALL_RED   = auto()   # safety clearance gap, nobody moves
    RED       = auto()   # vehicles stop
    PED_WALK  = auto()   # pedestrian crossing active
    PED_FLASH = auto()   # pedestrian flashing warning


@dataclass
class SystemContext:
    """
    The shared brain of the entire system.

    Every module receives this object and reads/writes to it.
    No module holds its own state — all state lives here.
    This makes the system predictable: one place to inspect,
    one place to debug.

    Attributes:
        vars      -- general-purpose key-value store for logic data
        board     -- pyfirmata2 Arduino board object (None in sim mode)
        pins      -- maps logical pin names ("red") to pyfirmata pin objects
        state     -- current traffic light phase
        ped_requested  -- True when pedestrian button has been pressed
        current_countdown -- the number currently shown on the display
        running   -- set to False to stop all background threads cleanly
    """
    vars             : Dict[str, Any] = field(default_factory=dict)
    board            : Optional[Any]  = None
    pins             : Dict[str, Any] = field(default_factory=dict)

    state            : TrafficState = TrafficState.RED
    ped_requested    : bool = False
    current_countdown: int  = 0
    running          : bool = True

    def get(self, key: str) -> Any:
        """Read a value from the general variable store."""
        return self.vars.get(key)

    def set(self, key: str, value: Any) -> None:
        """Write a value to the general variable store."""
        self.vars[key] = value
