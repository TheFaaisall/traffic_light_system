"""
display.py
----------
Controls the 4-digit 7-segment LED countdown display.

How a 7-segment display works:
  Each digit has 7 LED segments (a-g) arranged like this:

       a
      ---
  f  |   |  b
      ---      <- g
  e  |   |  c
      ---
       d

  To show a number, we turn specific segments ON.
  Example: digit 7 = segments a, b, c ON → top, top-right, bottom-right.

How multiplexing works:
  The display has 4 digits but only ONE set of segment pins.
  We show one digit at a time, cycling through all 4 faster than
  the human eye can see (>50Hz). The eye perceives all 4 as always ON.

  This file handles that cycle automatically in a background thread.
  All other code needs to do is write to context.current_countdown.
"""

import time
from context import SystemContext
from config import (
    SIMULATION_MODE,
    SEG_PATTERNS, SEGMENT_KEYS, DIGIT_KEYS,
    DIG_ON, DIG_OFF, SEG_ON, SEG_OFF,
)


def display_number(context: SystemContext, number: int) -> None:
    """
    Show a number (0-9999) on the 4-digit 7-segment display.
    Performs one full multiplex cycle across all 4 digits.

    In simulation mode, this is a no-op — terminal output is handled
    by the controller's countdown bar instead.

    Steps per digit:
      1. Turn ALL digit-select pins OFF (prevents ghosting between digits)
      2. Set segment pins to the pattern for this digit's value
      3. Turn ON only this digit's select pin
      4. Hold for 2ms
    Total cycle: 4 digits x 2ms = 8ms = 125Hz refresh rate
    """
    if SIMULATION_MODE:
        return

    number = max(0, min(9999, number))

    # Split into 4 individual digits, left-padded with zeros
    # e.g. 37 → "0037" → [0, 0, 3, 7]
    digits = [int(ch) for ch in f"{number:04d}"]

    for i, digit_val in enumerate(digits):

        # Step 1: blank all digit-selects to prevent ghosting
        for dk in DIGIT_KEYS:
            context.pins[dk].write(DIG_OFF)

        # Step 2: set segment pins for this digit
        pattern = SEG_PATTERNS.get(digit_val, SEG_PATTERNS[' '])
        for seg_idx, seg_key in enumerate(SEGMENT_KEYS):
            context.pins[seg_key].write(
                SEG_ON if pattern[seg_idx] else SEG_OFF
            )

        # Decimal point is not used for countdown — always off
        context.pins["seg_dp"].write(SEG_OFF)

        # Step 3: activate only this digit
        context.pins[DIGIT_KEYS[i]].write(DIG_ON)

        # Step 4: hold 2ms
        time.sleep(0.002)

    # End of cycle — blank all digits for a clean state
    for dk in DIGIT_KEYS:
        context.pins[dk].write(DIG_OFF)


def countdown_display_loop(context: SystemContext) -> None:
    """
    Background thread target.
    Runs continuously while context.running is True.
    Reads context.current_countdown and calls display_number() in a tight loop.

    The main control loop only needs to update context.current_countdown.
    This thread handles all display multiplexing independently.
    """
    while context.running:
        display_number(context, context.current_countdown)
        if SIMULATION_MODE:
            time.sleep(0.05)   # avoid CPU spinning in sim mode
