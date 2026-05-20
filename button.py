"""
button.py
---------
Pedestrian button listener. Runs in its own background thread.

Why a separate thread?
  The main loop is blocked inside time.sleep() during each phase countdown.
  If the button listener ran in the same thread, button presses during
  a countdown would be missed entirely.
  A background thread polls independently, so no press is lost.

Why poll instead of hardware interrupt?
  pyfirmata does not expose Arduino interrupt pins to Python.
  Polling at 100ms is sufficient — a human button press lasts 200-500ms,
  so we will always catch it within one or two polls.
  CPU cost at 100ms polling is negligible.
"""

import time
from context import SystemContext
from hardware import read_button


def pedestrian_button_listener(context: SystemContext) -> None:
    """
    Polls the pedestrian push button every 100ms.
    Sets context.ped_requested = True on first press.
    Ignores further presses once the flag is already set
    (one request per cycle is enough).

    Exits cleanly when context.running becomes False.
    """
    print("  [Button] Pedestrian listener active")

    while context.running:
        pressed = read_button(context, pin="button")

        if pressed and not context.ped_requested:
            print("\n  [Button] Pedestrian crossing requested")
            context.ped_requested = True

        time.sleep(0.1)   # 100ms polling interval
