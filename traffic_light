"""
=====================================================================
  Melbourne Traffic Light System — Full Python Controller
  Hardware : Arduino UNO + Breadboard
  Interface: pyfirmata2 (Python → USB → Arduino)
  Author   : Faisal | Monash University Robotics & Mechatronics

  BEFORE RUNNING:
  1. Open Arduino IDE
  2. File → Examples → Firmata → StandardFirmata
  3. Upload that sketch to your Arduino UNO
  4. pip install pyfirmata2
  5. Set ARDUINO_PORT below to your port
     Windows → "COM3"  (check Device Manager)
     Mac     → "/dev/cu.usbmodemXXXX"
     Linux   → "/dev/ttyACM0"
=====================================================================
"""

import time
import threading
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable

# ------------------------------------------------------------------
# Toggle this to True if you want to test without Arduino plugged in.
# It prints everything to terminal instead of driving real hardware.
# ------------------------------------------------------------------
SIMULATION_MODE = True   # ← change to False for real hardware

# =====================================================================
# --- Configuration ---
# Change pin numbers here to match YOUR wiring on the breadboard.
# =====================================================================

ARDUINO_PORT = "COM3"   # ← CHANGE THIS to your port

# Each key = a logical name, each value = the Arduino digital pin number.
# Analog pins A0-A5 on Arduino UNO map to digital pins 14-19.
PIN_CONFIG: Dict[str, int] = {
    # Traffic light LEDs
    "red"   : 2,
    "yellow": 3,
    "green" : 4,

    # Pedestrian push button (wired with a pull-up resistor to 5V)
    "button": 5,

    # 7-segment display — individual segment pins (a through g + decimal point)
    "seg_a" : 6,
    "seg_b" : 7,
    "seg_c" : 8,
    "seg_d" : 9,
    "seg_e" : 10,
    "seg_f" : 11,
    "seg_g" : 12,
    "seg_dp": 13,

    # 7-segment display — digit select pins (one per digit, left to right)
    # These go to A0, A1, A2, A3 on the Arduino UNO
    "dig_1" : 14,   # leftmost digit
    "dig_2" : 15,
    "dig_3" : 16,
    "dig_4" : 17,   # rightmost digit
}

# Is your 7-segment display common cathode or common anode?
# Common cathode  → digit select LOW = ON,  segment HIGH = ON   (most common)
# Common anode    → digit select HIGH = ON, segment LOW = ON
DISPLAY_COMMON_CATHODE = True   # ← change if your display is common anode

# Melbourne-standard traffic timing (in seconds)
TIMING: Dict[str, int] = {
    "green_min"         : 20,   # shortest green allowed
    "green_max"         : 60,   # longest green allowed
    "green_default"     : 30,   # baseline green
    "amber"             : 4,    # always fixed — Australian road rules
    "red_min"           : 20,
    "red_max"           : 60,
    "all_red_clearance" : 2,    # safety all-red gap between phases
    "ped_walk"          : 15,   # pedestrian walk time
    "ped_flash"         : 5,    # pedestrian flashing warning time
}

# Melbourne peak hours (24-hour format): (start_hour, end_hour)
PEAK_HOURS = [(7, 9), (16, 18)]


# =====================================================================
# --- Traffic States ---
# An Enum is used here because it gives each state a name AND
# makes comparisons readable (state == TrafficState.GREEN vs state == 2).
# =====================================================================

class TrafficState(Enum):
    GREEN     = auto()   # vehicles go
    AMBER     = auto()   # vehicles slow down — warning
    ALL_RED   = auto()   # safety clearance — nobody moves
    RED       = auto()   # vehicles stop
    PED_WALK  = auto()   # pedestrian crossing (solid walk signal)
    PED_FLASH = auto()   # pedestrian flashing (hurry up warning)


# =====================================================================
# --- System Context ---
# This is the central "brain" / shared memory of the whole system.
# Every tool, every thread, every component reads and writes to this
# ONE object — that way nothing is isolated or disconnected.
#
# Why a dataclass?
# Clean, typed, auto-generates __init__. No boilerplate.
# =====================================================================

@dataclass
class SystemContext:
    vars  : Dict[str, Any] = field(default_factory=dict)   # general key-value store
    board : Optional[Any]  = None                           # pyfirmata board object
    pins  : Dict[str, Any] = field(default_factory=dict)   # name → pin object

    state           : TrafficState = TrafficState.RED
    ped_requested   : bool = False   # set to True when button is pressed
    current_countdown: int = 0       # display thread reads this every 2ms
    running         : bool = True    # set to False to stop all threads

    def get(self, key: str) -> Any:
        """Read a value from the general variable store."""
        return self.vars.get(key)

    def set(self, key: str, value: Any):
        """Write a value to the general variable store."""
        self.vars[key] = value


# =====================================================================
# --- Tool Wrappers ---
# These sit between the caller and the actual hardware function.
# The caller passes a pin NAME (string like "red"),
# the wrapper resolves it to the actual pyfirmata pin object,
# then calls the underlying function.
#
# Why this pattern?
# - Decouples logic from hardware — you can test without real pins.
# - Mirrors the symbolic execution pattern in your example code.
# - Makes the call sites clean and readable.
# =====================================================================

def tool_wrapper(fn: Callable) -> Callable:
    """
    Basic wrapper.
    Resolves any string argument that exists in context.vars
    to its actual value before calling fn.

    Example:
        context.set("MY_PIN", some_pin_object)
        tool_wrapper(fn)(context, pin="MY_PIN")
        → fn receives the actual pin object
    """
    def wrapped(context: SystemContext, **args) -> Any:
        resolved = {}
        for k, v in args.items():
            # If the value is a string AND it exists in context.vars → resolve it
            if isinstance(v, str) and v in context.vars:
                resolved[k] = context.get(v)
            else:
                resolved[k] = v
        return fn(context=context, **resolved)
    return wrapped


def hardware_tool_wrapper(fn: Callable, pin_keys: tuple = ("pin",)) -> Callable:
    """
    Advanced wrapper specifically for hardware pin calls.
    Resolves pin NAME strings (like "red", "seg_a") to the actual
    pyfirmata pin objects stored in context.pins.

    Why separate from tool_wrapper?
    Because pins live in context.pins (not context.vars).
    The two stores serve different purposes — vars = logic data, pins = hardware handles.
    """
    def wrapped(context: SystemContext, **args) -> Any:
        resolved = {}
        for k, v in args.items():
            if k in pin_keys and isinstance(v, str) and v in context.pins:
                # This arg is a pin name → swap it for the actual pin object
                resolved[k] = context.pins[v]
            elif isinstance(v, str) and v in context.vars:
                # This arg is a context variable → resolve it
                resolved[k] = context.get(v)
            else:
                resolved[k] = v
        return fn(context=context, **resolved)
    return wrapped


# =====================================================================
# --- Hardware Layer (raw functions) ---
# These are the ONLY functions that directly touch pyfirmata.
# Everything above this layer speaks in names and logic, not pins.
# =====================================================================

def _set_led(context: SystemContext, pin=None, state: bool = False):
    """
    Drive an LED pin HIGH (on) or LOW (off).
    pyfirmata pin.write() accepts 0 or 1.
    """
    if pin is not None:
        if SIMULATION_MODE:
            pass   # sim mode: display thread handles visual output
        else:
            pin.write(1 if state else 0)


def _read_button(context: SystemContext, pin=None) -> bool:
    """
    Read the pedestrian push button.
    Button is wired active-LOW (pressed = 0V = logic 0).
    pyfirmata returns None before the first reading — treat that as not pressed.
    """
    if SIMULATION_MODE:
        return False   # sim mode: button never pressed (you can manually set ped_requested)
    if pin is not None:
        val = pin.read()
        return val == 0 if val is not None else False
    return False


def _set_segment_pin(context: SystemContext, pin=None, state: bool = False):
    """Drive a single 7-segment display pin HIGH or LOW."""
    if pin is not None and not SIMULATION_MODE:
        pin.write(1 if state else 0)


# Apply wrappers — these are the versions used everywhere else in the code
set_led         = hardware_tool_wrapper(_set_led,         pin_keys=("pin",))
read_button     = hardware_tool_wrapper(_read_button,     pin_keys=("pin",))
set_segment_pin = hardware_tool_wrapper(_set_segment_pin, pin_keys=("pin",))


# =====================================================================
# --- Seven-Segment Display Controller ---
# A 4-digit 7-segment display works by MULTIPLEXING:
# you show one digit at a time, cycling through all 4 so fast
# (>50Hz) that your eye sees them all lit simultaneously.
#
# Each digit has 7 segments (a-g) arranged like this:
#
#    ─ a ─
#   |     |
#   f     b
#   |     |
#    ─ g ─
#   |     |
#   e     c
#   |     |
#    ─ d ─   · dp
#
# To show a digit, we set which of a-g are ON.
# =====================================================================

# Lookup table: digit → which segments [a,b,c,d,e,f,g] are ON (1) or OFF (0)
SEG_PATTERNS: Dict[Any, list] = {
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
    ' ': [0, 0, 0, 0, 0, 0, 0],  # blank (all off)
}

# Key names in the order a, b, c, d, e, f, g (must match SEG_PATTERNS order)
SEGMENT_KEYS = ["seg_a", "seg_b", "seg_c", "seg_d", "seg_e", "seg_f", "seg_g"]

# Digit select key names, left to right
DIGIT_KEYS = ["dig_1", "dig_2", "dig_3", "dig_4"]

# For common cathode: ON = 0 (LOW), OFF = 1 (HIGH)
# For common anode:   ON = 1 (HIGH), OFF = 0 (LOW)
DIG_ON  = 0 if DISPLAY_COMMON_CATHODE else 1
DIG_OFF = 1 if DISPLAY_COMMON_CATHODE else 0
SEG_ON  = 1 if DISPLAY_COMMON_CATHODE else 0
SEG_OFF = 0 if DISPLAY_COMMON_CATHODE else 1


def display_number(context: SystemContext, number: int):
    """
    Show a number (0-9999) on the 4-digit 7-segment display.
    This function multiplexes all 4 digits in a single call.

    Steps:
    1. Split number into 4 individual digits (pad with leading zeros)
    2. For each digit:
       a. Turn ALL digit-selects OFF first (prevents ghosting / bleed)
       b. Set the segment pins for this digit's pattern
       c. Turn ON only this digit's select pin
       d. Hold for 2ms (gives ~125Hz refresh rate across 4 digits)
    3. Turn all digits off at the end
    """
    if SIMULATION_MODE:
        # In simulation, just print to terminal — no pin writes
        return

    # Clamp number to valid range
    number = max(0, min(9999, number))

    # Build 4-digit array, e.g. 37 → [0, 0, 3, 7]
    s = f"{number:04d}"
    digits = [int(ch) for ch in s]

    for i, digit_val in enumerate(digits):
        # Step a: turn all digit-selects OFF
        for dk in DIGIT_KEYS:
            context.pins[dk].write(DIG_OFF)

        # Step b: set segment pins for this digit
        pattern = SEG_PATTERNS.get(digit_val, SEG_PATTERNS[' '])
        for seg_idx, seg_key in enumerate(SEGMENT_KEYS):
            context.pins[seg_key].write(SEG_ON if pattern[seg_idx] else SEG_OFF)

        # Decimal point always off (we don't use it for countdown)
        context.pins["seg_dp"].write(SEG_OFF)

        # Step c: turn on ONLY this digit's select
        context.pins[DIGIT_KEYS[i]].write(DIG_ON)

        # Step d: hold 2ms — 4 digits × 2ms = 8ms cycle = 125Hz refresh
        time.sleep(0.002)

    # Clean up: turn all digit-selects off
    for dk in DIGIT_KEYS:
        context.pins[dk].write(DIG_OFF)


def countdown_display_loop(context: SystemContext):
    """
    Background thread — runs forever while context.running is True.
    Reads context.current_countdown and drives the 7-segment display.
    The main logic only needs to update context.current_countdown;
    this thread handles all the hardware multiplexing automatically.
    """
    while context.running:
        display_number(context, context.current_countdown)
        # In simulation mode, sleep a bit to avoid busy-looping
        if SIMULATION_MODE:
            time.sleep(0.05)


# =====================================================================
# --- Adaptive Timing AI Agent ---
# This agent's ONE job: decide how long each phase should last.
#
# Why an agent and not hardcoded numbers?
# Because real Melbourne traffic lights adapt.
# VicRoads SCATS system adjusts timing based on traffic density.
# We simulate that with time-of-day rules.
#
# You can upgrade this later to:
# - Read a PIR sensor for car count
# - Call an LLM for complex decisions
# - Use a trained RL model
# Without changing anything else in the code.
# =====================================================================

class AdaptiveTimingAgent:
    """
    Rule-based AI agent for adaptive traffic light timing.
    Simulates Melbourne peak-hour traffic patterns.
    """

    def __init__(self, timing_config: Dict[str, int]):
        self.config = timing_config

    # -- Internal helper ------------------------------------------------

    def _get_traffic_density(self) -> float:
        """
        Returns a traffic density score: 0.0 (empty road) to 1.0 (gridlock).
        Logic:
        - Inside a peak window → score 0.5–1.0 based on distance from midpoint
        - Night time (10pm–6am) → score 0.1
        - Normal daytime → score 0.3
        """
        hour   = datetime.now().hour
        minute = datetime.now().minute
        now    = hour + minute / 60.0   # e.g. 8:30am → 8.5

        for start, end in PEAK_HOURS:
            if start <= now < end:
                midpoint = (start + end) / 2.0
                # How far from the peak mid (0.0 = at midpoint, 1.0 = at edge)
                dist = abs(now - midpoint) / ((end - start) / 2.0)
                # Score: 1.0 at midpoint, 0.5 at edge
                return round(1.0 - dist * 0.5, 2)

        if hour >= 22 or hour < 6:
            return 0.1
        return 0.3

    # -- Public interface -----------------------------------------------

    def decide_green_duration(self) -> int:
        """
        More traffic → longer green (more cars need to pass through).
        Linearly maps density [0.0 → 1.0] to [green_min → green_max].
        """
        density  = self._get_traffic_density()
        min_g    = self.config["green_min"]
        max_g    = self.config["green_max"]
        duration = int(min_g + (max_g - min_g) * density)
        print(f"  [Agent] Density={density:.2f} → Green={duration}s")
        return duration

    def decide_red_duration(self) -> int:
        """
        More traffic → longer red (opposing direction also has more cars).
        Same linear mapping.
        """
        density  = self._get_traffic_density()
        min_r    = self.config["red_min"]
        max_r    = self.config["red_max"]
        duration = int(min_r + (max_r - min_r) * density)
        print(f"  [Agent] Density={density:.2f} → Red={duration}s")
        return duration


# =====================================================================
# --- Traffic Light State Machine ---
# Controls all state transitions and sequences.
#
# One full cycle:
#   GREEN → AMBER → ALL_RED → RED → [optional: PED_WALK → PED_FLASH] → repeat
#
# Why ALL_RED between AMBER and RED?
# Australian road rules require an all-red clearance gap so any car
# that ran a late amber clears the intersection before the next green.
# =====================================================================

class TrafficLightController:

    def __init__(self, context: SystemContext, agent: AdaptiveTimingAgent):
        self.ctx   = context
        self.agent = agent

    # -- Internal helpers -----------------------------------------------

    def _set_lights(self, red: bool, yellow: bool, green: bool):
        """Set all 3 LEDs in one call. Cleaner than calling set_led 3 times separately."""
        set_led(self.ctx, pin="red",    state=red)
        set_led(self.ctx, pin="yellow", state=yellow)
        set_led(self.ctx, pin="green",  state=green)

    def _run_countdown(self, seconds: int):
        """
        Count down from `seconds` to 0, one tick per second.
        Writes to context.current_countdown so the display thread
        picks it up without any extra code here.
        Also prints a terminal status bar in simulation mode.
        """
        for remaining in range(seconds, -1, -1):
            if not self.ctx.running:
                return   # stop if system is shutting down
            self.ctx.current_countdown = remaining

            if SIMULATION_MODE:
                # Simple terminal visual for simulation
                state_name  = self.ctx.state.name.ljust(10)
                bar_filled  = "█" * remaining
                bar_empty   = "░" * (seconds - remaining)
                print(f"\r  [{state_name}] {remaining:3d}s  {bar_filled}{bar_empty}", end="", flush=True)

            time.sleep(1)

        if SIMULATION_MODE:
            print()   # newline after countdown bar ends

    def _enter_phase(self, state: TrafficState, duration: int,
                     red: bool, yellow: bool, green: bool):
        """
        Enter a single traffic light phase:
        1. Update system state (so anything watching context.state can react)
        2. Set the LED outputs
        3. Run the countdown for this phase's duration
        """
        self.ctx.state = state
        self._set_lights(red=red, yellow=yellow, green=green)

        if SIMULATION_MODE:
            r = "🔴" if red    else "⚫"
            y = "🟡" if yellow else "⚫"
            g = "🟢" if green  else "⚫"
            print(f"\n  {r} {y} {g}  → {state.name} phase ({duration}s)")

        self._run_countdown(duration)

    # -- Public interface -----------------------------------------------

    def run_cycle(self):
        """
        Run one complete traffic light cycle.
        Called in a loop from main() — each call is one full cycle.

        Sequence:
          1. GREEN   — duration from agent
          2. AMBER   — fixed 4s (Australian road rule)
          3. ALL_RED — fixed 2s safety clearance
          4. RED     — duration from agent (shortened if pedestrian waiting)
          5. PED_WALK  — only if button was pressed
          6. PED_FLASH — pedestrian warning flash, then cycle repeats
        """
        # Ask the agent how long green and red should be this cycle
        green_duration = self.agent.decide_green_duration()
        red_duration   = self.agent.decide_red_duration()

        # ── Phase 1: GREEN ──────────────────────────────────────────────
        self._enter_phase(
            TrafficState.GREEN, green_duration,
            red=False, yellow=False, green=True
        )

        # ── Phase 2: AMBER ──────────────────────────────────────────────
        self._enter_phase(
            TrafficState.AMBER, TIMING["amber"],
            red=False, yellow=True, green=False
        )

        # ── Phase 3: ALL RED (clearance) ────────────────────────────────
        self._enter_phase(
            TrafficState.ALL_RED, TIMING["all_red_clearance"],
            red=True, yellow=False, green=False
        )

        # ── Phase 4: RED ────────────────────────────────────────────────
        if self.ctx.ped_requested:
            # If pedestrian is waiting, shorten the red wait
            # (they've already been waiting since they pressed the button)
            red_wait = min(10, red_duration)
        else:
            red_wait = red_duration

        self._enter_phase(
            TrafficState.RED, red_wait,
            red=True, yellow=False, green=False
        )

        # ── Phase 5 & 6: Pedestrian crossing (only if button was pressed) ─
        if self.ctx.ped_requested:
            self.ctx.ped_requested = False   # clear the flag for next cycle
            print("\n  🚶 Pedestrian crossing ACTIVE")

            # Walk phase — pedestrian can cross safely
            self._enter_phase(
                TrafficState.PED_WALK, TIMING["ped_walk"],
                red=True, yellow=False, green=False
            )

            # Flash phase — flash yellow to warn pedestrian to hurry
            self.ctx.state = TrafficState.PED_FLASH
            for i in range(TIMING["ped_flash"], 0, -1):
                if not self.ctx.running:
                    return
                self.ctx.current_countdown = i

                # Flash: yellow ON for 0.5s, then OFF for 0.5s
                self._set_lights(red=True, yellow=True,  green=False)
                time.sleep(0.5)
                self._set_lights(red=True, yellow=False, green=False)
                time.sleep(0.5)

                if SIMULATION_MODE:
                    print(f"\r  [PED_FLASH ] {i:3d}s  flashing...", end="", flush=True)

            if SIMULATION_MODE:
                print("\n  🚶 Pedestrian crossing COMPLETE")


# =====================================================================
# --- Pedestrian Button Listener ---
# Runs in its own background thread so it never blocks the main loop.
#
# Why poll instead of interrupt?
# pyfirmata doesn't support hardware interrupts from Python.
# Polling every 100ms is fast enough — humans press buttons for ~200–500ms.
# CPU cost is negligible.
# =====================================================================

def pedestrian_button_listener(context: SystemContext):
    """
    Polls the pedestrian push button every 100ms.
    When pressed, sets context.ped_requested = True.
    Only sets the flag once per cycle (ignores held button / repeat presses).
    """
    print("  [Button] Pedestrian listener started")
    while context.running:
        pressed = read_button(context, pin="button")
        if pressed and not context.ped_requested:
            print("\n  [Button] 🔔 Pedestrian crossing requested!")
            context.ped_requested = True
        time.sleep(0.1)   # 100ms polling interval


# =====================================================================
# --- Hardware Initialisation ---
# =====================================================================

def init_hardware(context: SystemContext) -> bool:
    """
    Connect to the Arduino via pyfirmata2.
    Create a pin object for every entry in PIN_CONFIG.
    Store them in context.pins under the same logical name.
    Returns True on success, False on failure.
    """
    if SIMULATION_MODE:
        # In sim mode, create fake pin objects that do nothing
        class FakePin:
            def write(self, val): pass
            def read(self): return 1   # 1 = not pressed (active-LOW button)

        for key in PIN_CONFIG:
            context.pins[key] = FakePin()
        print("  [Init] SIMULATION MODE — no Arduino required ✓")
        return True

    try:
        import pyfirmata2

        print(f"  [Init] Connecting to Arduino on {ARDUINO_PORT}...")
        board = pyfirmata2.Arduino(ARDUINO_PORT)

        # pyfirmata2 automatically starts its internal iterator thread.
        # No manual util.Iterator needed (unlike older pyfirmata).
        context.board = board

        # Wait for Arduino to boot after USB connection resets it
        time.sleep(2)
        print("  [Init] Arduino connected ✓")

        # --- Set up OUTPUT pins (LEDs, segments, digit selects) ---
        output_keys = [
            "red", "yellow", "green",
            "seg_a", "seg_b", "seg_c", "seg_d", "seg_e", "seg_f", "seg_g", "seg_dp",
            "dig_1", "dig_2", "dig_3", "dig_4",
        ]
        for key in output_keys:
            pin_num = PIN_CONFIG[key]
            # "d:N:o" = digital pin N, output mode
            context.pins[key] = board.get_pin(f"d:{pin_num}:o")

        # --- Set up INPUT pin for pedestrian button ---
        btn_num = PIN_CONFIG["button"]
        context.pins["button"] = board.get_pin(f"d:{btn_num}:i")
        # Enable pull-up so the pin reads HIGH when button is not pressed
        board.digital[btn_num].mode = pyfirmata2.INPUT
        board.digital[btn_num].enable_reporting()

        print("  [Init] All pins configured ✓")
        return True

    except Exception as e:
        print(f"  [Init] ERROR: {e}")
        print("  [Init] Checklist:")
        print(f"         1. Is Arduino plugged in?")
        print(f"         2. Is ARDUINO_PORT = '{ARDUINO_PORT}' correct?")
        print(f"         3. Is StandardFirmata sketch uploaded to the Arduino?")
        print(f"         4. Run: pip install pyfirmata2")
        return False


def cleanup_hardware(context: SystemContext):
    """
    Safe shutdown:
    - Turn all LEDs off
    - Turn all 7-segment digits off
    - Close serial connection
    """
    print("\n  [Cleanup] Shutting down hardware...")
    context.running = False

    if not SIMULATION_MODE and context.board is not None:
        for key in ["red", "yellow", "green"]:
            if key in context.pins:
                context.pins[key].write(0)
        for dk in DIGIT_KEYS:
            if dk in context.pins:
                context.pins[dk].write(DIG_OFF)
        context.board.exit()

    print("  [Cleanup] Done. All lights off. ✓")


# =====================================================================
# --- Main Entry Point ---
# =====================================================================

def main():
    print()
    print("=" * 55)
    print("   Melbourne Traffic Light System")
    print("   Python + pyfirmata2 + Arduino UNO")
    if SIMULATION_MODE:
        print("   *** SIMULATION MODE (no Arduino needed) ***")
    print("=" * 55)

    # 1. Create shared context (the 'brain' of the whole system)
    context = SystemContext()

    # 2. Connect to hardware (or enter sim mode)
    if not init_hardware(context):
        print("  Aborting — hardware init failed.")
        return

    # 3. Create the AI timing agent
    agent = AdaptiveTimingAgent(TIMING)

    # 4. Create the traffic light controller
    controller = TrafficLightController(context, agent)

    # 5. Start 7-segment display background thread
    #    daemon=True means this thread dies automatically when main() exits
    display_thread = threading.Thread(
        target=countdown_display_loop,
        args=(context,),
        name="DisplayThread",
        daemon=True
    )
    display_thread.start()

    # 6. Start pedestrian button listener thread
    button_thread = threading.Thread(
        target=pedestrian_button_listener,
        args=(context,),
        name="ButtonThread",
        daemon=True
    )
    button_thread.start()

    # 7. Run the traffic light loop forever until Ctrl+C
    try:
        print("\n  System running. Press Ctrl+C to stop.")
        print("  (In sim mode: set context.ped_requested=True to test pedestrian crossing)\n")
        cycle = 0
        while True:
            cycle += 1
            print(f"\n  ── Cycle {cycle} ──────────────────────────────")
            controller.run_cycle()

    except KeyboardInterrupt:
        print("\n\n  Stopped by user.")

    finally:
        cleanup_hardware(context)


if __name__ == "__main__":
    main()
