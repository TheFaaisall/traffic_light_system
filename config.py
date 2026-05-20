"""
config.py
---------
Single source of truth for every constant in the system.
If you rewire the board, change a timing, or switch display type —
this is the ONLY file you touch.
"""

from typing import Dict

# ------------------------------------------------------------------
# Runtime mode
# ------------------------------------------------------------------

SIMULATION_MODE = True       # True = run in terminal, no Arduino needed
                             # False = real hardware via pyfirmata2

ARDUINO_PORT = "COM3"        # Windows: "COM3"
                             # Mac:     "/dev/cu.usbmodemXXXX"
                             # Linux:   "/dev/ttyACM0"

# ------------------------------------------------------------------
# Pin mapping
# Each key = logical name used throughout the code.
# Each value = Arduino digital pin number.
# Analog pins A0-A5 on Arduino UNO = digital pins 14-19.
# ------------------------------------------------------------------

PIN_CONFIG: Dict[str, int] = {
    # Traffic light LEDs
    "red"   : 2,
    "yellow": 3,
    "green" : 4,

    # Pedestrian push button (active-LOW with pull-up resistor to 5V)
    "button": 5,

    # 7-segment display — one pin per segment
    "seg_a" : 6,
    "seg_b" : 7,
    "seg_c" : 8,
    "seg_d" : 9,
    "seg_e" : 10,
    "seg_f" : 11,
    "seg_g" : 12,
    "seg_dp": 13,

    # 7-segment display — digit select pins (left to right)
    # A0=14, A1=15, A2=16, A3=17 on Arduino UNO
    "dig_1" : 14,
    "dig_2" : 15,
    "dig_3" : 16,
    "dig_4" : 17,
}

# ------------------------------------------------------------------
# 7-segment display type
# Common cathode  → digit select LOW=ON,  segment HIGH=ON  (most common)
# Common anode    → digit select HIGH=ON, segment LOW=ON
# ------------------------------------------------------------------

DISPLAY_COMMON_CATHODE = True

# Derived from above — used in display.py to avoid repeating this logic
DIG_ON  = 0 if DISPLAY_COMMON_CATHODE else 1
DIG_OFF = 1 if DISPLAY_COMMON_CATHODE else 0
SEG_ON  = 1 if DISPLAY_COMMON_CATHODE else 0
SEG_OFF = 0 if DISPLAY_COMMON_CATHODE else 1

# ------------------------------------------------------------------
# Traffic light timing (all values in seconds)
# ------------------------------------------------------------------

TIMING: Dict[str, int] = {
    "green_min"         : 20,   # shortest green phase allowed
    "green_max"         : 60,   # longest green phase allowed
    "green_default"     : 30,   # baseline if agent is unavailable
    "amber"             : 4,    # fixed — Australian road rules
    "red_min"           : 20,
    "red_max"           : 60,
    "all_red_clearance" : 2,    # safety gap between phases
    "ped_walk"          : 15,   # pedestrian walk signal duration
    "ped_flash"         : 5,    # pedestrian flashing warning duration
    "ped_red_cap"       : 10,   # max red wait when pedestrian is queued
}

# ------------------------------------------------------------------
# Melbourne peak hours (24-hour format): list of (start, end) tuples
# ------------------------------------------------------------------

PEAK_HOURS = [
    (7, 9),    # morning peak
    (16, 18),  # afternoon peak
]

# ------------------------------------------------------------------
# 7-segment display segment patterns
# Index order: [a, b, c, d, e, f, g]
# 1 = segment ON, 0 = segment OFF
# ------------------------------------------------------------------

SEG_PATTERNS: Dict = {
    0: [1, 1, 1, 1, 1, 1, 0],
    1: [0, 1, 1, 0, 0, 0, 0],
    2: [1, 1, 0, 1, 1, 0, 1],
    3: [1, 1, 1, 1, 0, 0, 1],
    4: [0, 1, 1, 0, 0, 1, 1],
    5: [1, 0, 1, 1, 0, 1, 1],
    6: [1, 0, 1, 1, 1, 1, 1],
    7: [1, 1, 1, 0, 0, 0, 0],
    8: [1, 1, 1, 1, 1, 1, 1],
    9: [1, 1, 1, 1, 0, 1, 1],
    ' ': [0, 0, 0, 0, 0, 0, 0],  # blank
}

# Segment pin key names in order a-g — must match SEG_PATTERNS index order
SEGMENT_KEYS = ["seg_a", "seg_b", "seg_c", "seg_d", "seg_e", "seg_f", "seg_g"]

# Digit select key names, left to right
DIGIT_KEYS = ["dig_1", "dig_2", "dig_3", "dig_4"]
