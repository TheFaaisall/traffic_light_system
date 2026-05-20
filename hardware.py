"""
hardware.py
-----------
The ONLY file that directly touches pyfirmata2.

Responsibilities:
  - Connect to the Arduino and configure all pins
  - Provide raw functions for writing to LEDs and reading the button
  - Provide clean shutdown

Everything above this layer talks in names and logic.
This layer is where names become real electrical signals.
"""

import time
from context import SystemContext
from wrappers import hardware_tool_wrapper
from config import PIN_CONFIG, SIMULATION_MODE, ARDUINO_PORT, DIGIT_KEYS, DIG_OFF


# ----------------------------------------------------------------
# Raw hardware functions (private — prefixed with _)
# These are wrapped below. Do not call them directly.
# ----------------------------------------------------------------

def _set_led(context: SystemContext, pin=None, state: bool = False) -> None:
    """
    Drive an LED pin HIGH (on) or LOW (off).
    In simulation mode, this is a no-op — the display thread
    handles all terminal output.
    """
    if pin is None:
        return
    if not SIMULATION_MODE:
        pin.write(1 if state else 0)


def _read_button(context: SystemContext, pin=None) -> bool:
    """
    Read the pedestrian push button.

    Wiring: button connects pin to GND (active-LOW).
    Pull-up resistor holds pin HIGH when button is not pressed.
    So: pressed = LOW = 0.

    pyfirmata returns None before the first read cycle completes.
    Treat None as not pressed.
    """
    if SIMULATION_MODE:
        return False
    if pin is None:
        return False
    val = pin.read()
    return val == 0 if val is not None else False


# ----------------------------------------------------------------
# Wrapped versions — these are what all other modules import
# ----------------------------------------------------------------

set_led     = hardware_tool_wrapper(_set_led,     pin_keys=("pin",))
read_button = hardware_tool_wrapper(_read_button, pin_keys=("pin",))


# ----------------------------------------------------------------
# Initialisation
# ----------------------------------------------------------------

def init_hardware(context: SystemContext) -> bool:
    """
    Connect to the Arduino and configure all pins.
    Stores pyfirmata pin objects in context.pins under their logical names.
    In simulation mode, stores FakePin objects instead.
    Returns True on success, False on failure.
    """
    if SIMULATION_MODE:
        _init_simulation(context)
        return True

    return _init_real_hardware(context)


def _init_simulation(context: SystemContext) -> None:
    """Create fake pin objects so all other code runs unchanged in sim mode."""

    class FakePin:
        def write(self, val: int) -> None:
            pass
        def read(self) -> int:
            return 1   # 1 = HIGH = button not pressed (active-LOW logic)

    for key in PIN_CONFIG:
        context.pins[key] = FakePin()

    print("  [Init] Simulation mode — no Arduino required")


def _init_real_hardware(context: SystemContext) -> bool:
    """Connect to a real Arduino UNO and configure all pins via pyfirmata2."""
    try:
        import pyfirmata2

        print(f"  [Init] Connecting to Arduino on {ARDUINO_PORT}...")
        board = pyfirmata2.Arduino(ARDUINO_PORT)
        context.board = board

        # Arduino resets when USB connects — wait for it to boot
        time.sleep(2)
        print("  [Init] Arduino connected")

        # Output pins: LEDs, segment pins, digit select pins
        output_keys = [
            "red", "yellow", "green",
            "seg_a", "seg_b", "seg_c", "seg_d",
            "seg_e", "seg_f", "seg_g", "seg_dp",
            "dig_1", "dig_2", "dig_3", "dig_4",
        ]
        for key in output_keys:
            pin_num = PIN_CONFIG[key]
            # "d:N:o" = digital pin N in output mode
            context.pins[key] = board.get_pin(f"d:{pin_num}:o")

        # Input pin: pedestrian button
        btn_num = PIN_CONFIG["button"]
        context.pins["button"] = board.get_pin(f"d:{btn_num}:i")
        board.digital[btn_num].mode = pyfirmata2.INPUT
        board.digital[btn_num].enable_reporting()

        print("  [Init] All pins configured")
        return True

    except Exception as e:
        print(f"  [Init] ERROR: {e}")
        print("  [Init] Check:")
        print(f"         1. Arduino is plugged in")
        print(f"         2. ARDUINO_PORT is '{ARDUINO_PORT}' — correct?")
        print(f"         3. StandardFirmata sketch is uploaded to Arduino")
        print(f"         4. pyfirmata2 is installed: pip install pyfirmata2")
        return False


# ----------------------------------------------------------------
# Shutdown
# ----------------------------------------------------------------

def cleanup_hardware(context: SystemContext) -> None:
    """
    Safe shutdown sequence:
    1. Mark the system as stopped (signals all threads to exit)
    2. Turn all LEDs off
    3. Blank the 7-segment display
    4. Close the serial connection
    """
    print("\n  [Cleanup] Shutting down...")
    context.running = False

    if not SIMULATION_MODE and context.board is not None:
        for key in ["red", "yellow", "green"]:
            if key in context.pins:
                context.pins[key].write(0)
        for dk in DIGIT_KEYS:
            if dk in context.pins:
                context.pins[dk].write(DIG_OFF)
        context.board.exit()

    print("  [Cleanup] All outputs off. Done.")
