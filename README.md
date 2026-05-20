# Adaptive Traffic Light Control System

A real-time embedded systems project built in Python, controlling physical traffic light hardware via an Arduino UNO. Designed and developed as part of my Robotics and Mechatronics Engineering studies at Monash University.

---

## Overview

This project implements a fully functional traffic light controller that runs on physical hardware. Python communicates with the Arduino UNO over USB using the Firmata protocol, giving direct control over all GPIO pins from a high-level software layer. The system manages a complete traffic light sequence, a 4-digit countdown timer displayed on a 7-segment LED display, and a pedestrian crossing request button.

An adaptive timing agent adjusts phase durations based on time-of-day traffic density modelling, reflecting how real-world traffic management systems operate.

---

## Key Features

- Real-time hardware control via Python and the pyfirmata2 serial communication protocol
- Finite state machine managing six traffic phases: Green, Amber, All-Red clearance, Red, Pedestrian Walk, and Pedestrian Flash
- Adaptive AI agent that calculates green and red phase durations based on simulated traffic density, modelled on Melbourne peak-hour patterns
- 4-digit 7-segment LED display with multiplexed refresh at 125Hz for real-time countdown visibility
- Multi-threaded architecture with dedicated threads for display refresh and pedestrian button polling, decoupled from the main control loop
- Simulation mode for full software testing without physical hardware
- Modular tool-wrapper pattern for hardware abstraction, enabling clean separation between logic and physical I/O

---

## Hardware

- Arduino UNO microcontroller
- Red, Yellow, and Green LEDs with current-limiting resistors
- Pedestrian push button with pull-up resistor
- 4-digit 7-segment LED display (common cathode)
- Breadboard and jumper wires

---

## Software Stack

- Python 3
- pyfirmata2 — serial communication with Arduino over USB
- threading — concurrent display refresh and button polling
- dataclasses, enum — typed system state and configuration management

---

## System Architecture

The codebase follows a layered design:

- Configuration layer — all pin mappings and timing constants in one place
- Hardware abstraction layer — tool-wrapper functions resolve logical pin names to physical hardware handles, keeping all hardware-specific code isolated
- State machine layer — TrafficLightController manages phase transitions and enforces the all-red safety clearance gap between phases, consistent with Australian road rules
- AI agent layer — AdaptiveTimingAgent models traffic density from time-of-day data and returns dynamic phase durations each cycle
- Display layer — a background thread multiplexes the 7-segment display independently of the control loop
- Input layer — a background thread polls the pedestrian button at 100ms intervals without blocking the main sequence

---

## Traffic Light Sequence

```
GREEN (adaptive 20-60s) → AMBER (4s) → ALL RED (2s) → RED (adaptive 20-60s)
└── If pedestrian button pressed: PED WALK (15s) → PED FLASH (5s) → repeat
```

The all-red clearance phase is a deliberate design choice aligned with Australian road safety standards, allowing vehicles that entered on a late amber signal to clear the intersection before the next phase begins.

---

## Setup and Installation

1. Upload the StandardFirmata sketch to the Arduino UNO via Arduino IDE (File > Examples > Firmata > StandardFirmata)
2. Install the Python dependency:

```bash
pip install pyfirmata2
```

3. Set your serial port in the configuration at the top of the file:

```python
ARDUINO_PORT = "COM3"        # Windows
ARDUINO_PORT = "/dev/ttyACM0"  # Linux
ARDUINO_PORT = "/dev/cu.usbmodemXXXX"  # macOS
```

4. Update PIN_CONFIG to match your wiring if needed
5. Set SIMULATION_MODE = False to run on real hardware
6. Run:

```bash
python traffic_light_system.py
```

To test without hardware, keep SIMULATION_MODE = True. The full state machine, agent, and countdown logic run in terminal with visual output.

---

## Skills Demonstrated

- Embedded systems design and hardware-software integration
- Real-time control systems and concurrent programming
- Python software architecture and object-oriented design
- Sensor and actuator interfacing via serial communication protocols
- AI-driven adaptive control logic
- Finite state machine implementation
- Applied robotics and mechatronics engineering principles

---

## Background

Built as part of my Bachelor of Engineering (Robotics and Mechatronics, AI specialisation) at Monash University, Melbourne. This project bridges my hardware background with Python-based AI system design, an area I actively develop through both academic and personal projects.
