# Embedded Clock Radio

A custom embedded clock radio built around the Raspberry Pi Pico W, featuring FM radio playback, alarm functionality, an OLED user interface, rotary encoder controls, a custom 4-layer PCB, and a 3D-printed enclosure.

This project was completed for **ECE 299 at the University of Victoria** as a two-person engineering design project.

## Project Overview

The goal of this project was to design and build a fully integrated clock radio using a Raspberry Pi Pico W running MicroPython.

The system combines embedded firmware, analog audio circuitry, PCB design, user-interface development, and mechanical enclosure design into a single working device.

### Key Features

- FM radio tuning and playback
- 12-hour and 24-hour time display
- Configurable alarm functionality
- Snooze and alarm cancellation
- OLED user interface
- Rotary encoder control for volume and radio tuning
- RDS station and track information
- Custom 4-layer PCB
- LM386-based audio amplification
- Custom 3D-printed enclosure

## Hardware

The clock radio is built around the following components:

- Raspberry Pi Pico W (RP2040)
- RDA5807M FM radio receiver
- SSD1306 1.3" OLED display
- LM386 audio amplifier
- 2 W, 8 Ω speaker
- 2 rotary encoders
- Push buttons
- Custom 4-layer PCB

## Communication Interfaces

- **I²C** — communication with the RDA5807M FM receiver
- **SPI** — communication with the SSD1306 OLED display
- **GPIO** — rotary encoders and push-button inputs

## PCB Design

The PCB was designed in **KiCad** as a compact 4-layer board.

The design separated power, ground, digital control, and analog audio signals across multiple layers to improve routing and reduce interference.

The board was fabricated externally and manually assembled using both SMD and through-hole components.

### PCB Highlights

- 4-layer PCB layout
- Dedicated power and ground routing
- Mixed analog and digital circuitry
- RDA5807M radio integration
- LM386 audio amplifier stage
- Raspberry Pi Pico W integration
- Test points for debugging and validation

## Firmware

The system firmware was written in **MicroPython** and runs on the Raspberry Pi Pico W.

The firmware handles:

- Real-time clock functionality
- FM radio tuning
- Volume control
- Alarm configuration
- Snooze and cancellation
- Rotary encoder input
- OLED menu navigation
- RDS station and song information

The main firmware and supporting drivers are located in the [`firmware`](firmware) directory.

## Testing and Debugging

The design was initially prototyped and validated on a breadboard before being transferred to the custom PCB.

Testing and debugging included:

- Oscilloscope measurements
- Power-supply noise reduction
- Rotary encoder debouncing
- FM tuning and audio testing
- OLED display troubleshooting
- PCB rework after identifying display pin-mapping issues
- Full hardware and firmware integration testing

## Enclosure Design

The enclosure was designed in **SolidWorks** and 3D printed in PLA.

The enclosure includes:

- OLED display opening
- Rotary encoder controls
- Speaker opening
- USB/power access
- Internal PCB mounting features
- Animal-themed exterior design

Design files are available in the [`enclosure`](enclosure) directory.

## Repository Structure

```text
embedded-clock-radio/
├── firmware/
│   ├── radio.py
│   ├── ssd1306.py
│   ├── rotary.py
│   ├── rotary_irq_rp2.py
│   └── development/
├── hardware/
│   ├── kicad/
│   └── gerbers/
├── enclosure/
├── images/
├── docs/
│   └── ECE299 Final Report.pdf
└── README.md
```

## My Contributions

This project was completed by a two-person team.
My primary contributions included:

- Leading the schematic and PCB design in KiCad
- Designing the 4-layer PCB layout
- Testing FM tuning, audio output, and OLED feedback
- Designing the enclosure in SolidWorks
- Developing UI functionality for time setting and display formatting
- Hardware debugging, testing, and final system integration

Technologies Used

- KiCad
- SolidWorks
- MicroPython
- Raspberry Pi Pico W
- RP2040
- I²C
- SPI
- Soldering
- Oscilloscope testing
- PCB design
- 3D printing

## Documentation

The full project report contains additional details on the design process, PCB development, testing, and project decisions.

[View the ECE 299 Final Report](docs/ECE299 Final Report.pdf)