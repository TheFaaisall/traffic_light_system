"""
controller.py
-------------
Traffic light state machine. Manages all phase transitions.

One full cycle:
  GREEN -> AMBER -> ALL_RED -> RED -> [PED_WALK -> PED_FLASH] -> repeat

Why ALL_RED between AMBER and RED?
  Australian road rules require a clearance gap after amber.
  Any car that entered on a late amber must clear the intersection
  before the opposing direction gets a green.

The controller does not talk to hardware directly.
It calls set_led() from hardware.py, which handles the actual pin writes.
The controller only knows about states and timing.
"""

import time
from context import SystemContext, TrafficState
from hardware import set_led
from agent import AdaptiveTimingAgent
from config import TIMING, SIMULATION_MODE


class TrafficLightController:

    def __init__(self, context: SystemContext, agent: AdaptiveTimingAgent):
        self.ctx   = context
        self.agent = agent

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _set_lights(self, red: bool, yellow: bool, green: bool) -> None:
        """Set all three LEDs in one call."""
        set_led(self.ctx, pin="red",    state=red)
        set_led(self.ctx, pin="yellow", state=yellow)
        set_led(self.ctx, pin="green",  state=green)

    def _run_countdown(self, seconds: int) -> None:
        """
        Count down from `seconds` to 0, one tick per second.
        Writes to context.current_countdown each tick so the
        display thread picks it up without any extra wiring here.

        Checks context.running each tick — exits early if the
        system is shutting down.
        """
        for remaining in range(seconds, -1, -1):
            if not self.ctx.running:
                return
            self.ctx.current_countdown = remaining

            if SIMULATION_MODE:
                state_label = self.ctx.state.name.ljust(10)
                filled      = "|" * remaining
                empty       = "-" * (seconds - remaining)
                print(
                    f"\r  [{state_label}] {remaining:3d}s  {filled}{empty}",
                    end="", flush=True
                )

            time.sleep(1)

        if SIMULATION_MODE:
            print()   # newline after countdown bar completes

    def _enter_phase(
        self,
        state: TrafficState,
        duration: int,
        red: bool,
        yellow: bool,
        green: bool,
    ) -> None:
        """
        Enter a single traffic light phase.
          1. Update system state in context
          2. Set LED outputs
          3. Run countdown for this phase's duration
        """
        self.ctx.state = state
        self._set_lights(red=red, yellow=yellow, green=green)

        if SIMULATION_MODE:
            r = "[R]" if red    else "[ ]"
            y = "[Y]" if yellow else "[ ]"
            g = "[G]" if green  else "[ ]"
            print(f"\n  {r} {y} {g}  {state.name}  ({duration}s)")

        self._run_countdown(duration)

    def _run_pedestrian_crossing(self) -> None:
        """
        Pedestrian crossing sequence — runs only when button was pressed.
          1. Walk phase: pedestrian crosses safely, all vehicle lights red
          2. Flash phase: yellow flashes to warn pedestrian to hurry
        """
        self.ctx.ped_requested = False
        print("\n  [Ped] Walk signal active")

        # Walk phase
        self._enter_phase(
            TrafficState.PED_WALK,
            TIMING["ped_walk"],
            red=True, yellow=False, green=False
        )

        # Flash phase: alternate yellow on/off each 0.5s
        self.ctx.state = TrafficState.PED_FLASH
        for i in range(TIMING["ped_flash"], 0, -1):
            if not self.ctx.running:
                return
            self.ctx.current_countdown = i

            self._set_lights(red=True, yellow=True,  green=False)
            time.sleep(0.5)
            self._set_lights(red=True, yellow=False, green=False)
            time.sleep(0.5)

            if SIMULATION_MODE:
                print(f"\r  [PED_FLASH  ] {i:3d}s  flashing", end="", flush=True)

        if SIMULATION_MODE:
            print("\n  [Ped] Crossing complete")

    # ----------------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------------

    def run_cycle(self) -> None:
        """
        Run one complete traffic light cycle.
        Called repeatedly from main.py's infinite loop.

        Phase order:
          1. GREEN   — adaptive duration from agent
          2. AMBER   — fixed 4s (Australian road rule)
          3. ALL_RED — fixed 2s safety clearance
          4. RED     — adaptive duration (capped if pedestrian is waiting)
          5. PED_WALK + PED_FLASH — only if button was pressed
        """
        green_duration = self.agent.decide_green_duration()
        red_duration   = self.agent.decide_red_duration()

        # Phase 1: GREEN
        self._enter_phase(
            TrafficState.GREEN, green_duration,
            red=False, yellow=False, green=True
        )

        # Phase 2: AMBER
        self._enter_phase(
            TrafficState.AMBER, TIMING["amber"],
            red=False, yellow=True, green=False
        )

        # Phase 3: ALL RED clearance
        self._enter_phase(
            TrafficState.ALL_RED, TIMING["all_red_clearance"],
            red=True, yellow=False, green=False
        )

        # Phase 4: RED
        # If pedestrian is waiting, cap red wait so they don't wait too long
        red_wait = (
            min(TIMING["ped_red_cap"], red_duration)
            if self.ctx.ped_requested
            else red_duration
        )
        self._enter_phase(
            TrafficState.RED, red_wait,
            red=True, yellow=False, green=False
        )

        # Phase 5 + 6: Pedestrian crossing (conditional)
        if self.ctx.ped_requested:
            self._run_pedestrian_crossing()
