"""
main.py
-------
Entry point. Wires all modules together and starts the system.

This file does not contain any logic.
Its only job is to:
  1. Create the shared context
  2. Initialise hardware
  3. Instantiate the agent and controller
  4. Start background threads
  5. Run the main loop
  6. Clean up on exit

If you want to understand what the system does, start here.
Then follow the imports into each module.

Module dependency map:
  main.py
  |-- config.py       (constants — no dependencies)
  |-- context.py      (SystemContext, TrafficState — no dependencies)
  |-- hardware.py     (pin I/O — imports config, context, wrappers)
  |-- wrappers.py     (tool wrappers — imports context)
  |-- display.py      (7-seg display — imports config, context)
  |-- agent.py        (timing agent — imports config)
  |-- controller.py   (state machine — imports context, hardware, agent, config)
  |-- button.py       (button polling — imports context, hardware)
"""

import threading
from context import SystemContext
from hardware import init_hardware, cleanup_hardware
from display import countdown_display_loop
from agent import AdaptiveTimingAgent
from controller import TrafficLightController
from button import pedestrian_button_listener
from config import SIMULATION_MODE, TIMING


def main() -> None:
    print()
    print("=" * 55)
    print("   Melbourne Traffic Light System")
    print("   Python + pyfirmata2 + Arduino UNO")
    if SIMULATION_MODE:
        print("   SIMULATION MODE — no Arduino needed")
    print("=" * 55)

    # Step 1: Shared context — the single source of runtime state
    context = SystemContext()

    # Step 2: Connect to hardware (or set up fake pins in sim mode)
    if not init_hardware(context):
        print("  Aborting — hardware initialisation failed.")
        return

    # Step 3: AI timing agent
    agent = AdaptiveTimingAgent(TIMING)

    # Step 4: Traffic light controller (state machine)
    controller = TrafficLightController(context, agent)

    # Step 5: Background thread — drives 7-segment display continuously
    # daemon=True: this thread exits automatically when main() returns
    display_thread = threading.Thread(
        target=countdown_display_loop,
        args=(context,),
        name="DisplayThread",
        daemon=True,
    )
    display_thread.start()

    # Step 6: Background thread — polls pedestrian button every 100ms
    button_thread = threading.Thread(
        target=pedestrian_button_listener,
        args=(context,),
        name="ButtonThread",
        daemon=True,
    )
    button_thread.start()

    # Step 7: Main loop — runs one complete cycle per iteration
    try:
        print("\n  System running. Press Ctrl+C to stop.\n")
        cycle = 0
        while True:
            cycle += 1
            print(f"\n  -- Cycle {cycle} " + "-" * 38)
            controller.run_cycle()

    except KeyboardInterrupt:
        print("\n\n  Stopped by user.")

    finally:
        cleanup_hardware(context)


if __name__ == "__main__":
    main()
