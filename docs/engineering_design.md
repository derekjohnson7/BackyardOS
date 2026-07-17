# BackyardOS Engineering Design Document

## Project Information

**Project:** BackyardOS

**Author:** Derek Johnson

**Respository:** https://github.com/derekjohnson7/BackyardOS

**Current Version:** 0.1

---

# Vision

BackyardOS is a modular IoT platform designed to monitor and analyze 
environmental conditions across a residential property.

The project began after repeated plant loss caused by suspected poor 
drainage and root rot. Rather than relying on guesswork, BackyardOS 
collects environmental data to better understand soil conditions, weather 
patterns, and plant health over time.

The long-term goal is to create an extensible platform capable of 
monitoring an entire property through distributed sensor nodes, historical 
analytics, and intelligent recommendations.

---

# Design Philosophy

BackyardOS is designed around several core principles:

- Solve real problems rather than implementing technology for its own 
sake.
- Build modular components that can evolve independently.
- Collect data once and reuse it for many purposes.
- Design for long-term expansion.
- Document engineering decisions.
- Favor simple, reliable solutions before adding complexity.

---

# Version 0.1 Goal

Version 0.1 demonstrates the complete end-to-end data pipeline.

It will:

- Read one capacitive soil moisture sensor.
- Read one BME280 environmental sensor.
- Connect one ESP32 to WiFi.
- Transmit data to a backend.
- Store readings in a SQLite database.
- Display live readings in a local dashboard.

Completion of Version 0.1 proves the overall architecture before expanding 
to multiple sensor nodes.

---

# Problem Statement

Current residential landscaping decisions are largely based on observation 
and intuition.

Questions such as:

- Why did this plant die?
- Which flower bed drains the slowest?
- Does this area receive enough water?
- How long does soil remain saturated after rainfall?

cannot be answered with objective data.

BackyardOS exists to replace assumptions with measurements.

## Development Environment

### Host System

- macOS

### IDE

- Arduino IDE 2.3.10

### Board Support Package

- Espressif ESP32 Arduino Core

### Development Board

- ESP32 Dev Module (USB-C)

### Hardware Bring-Up Result

- Board: ESP32 Dev Module
- Port: `/dev/cu.usbserial-0001`
- Onboard LED pin: GPIO 2
- Blink test: successful
- LED behavior: blue onboard LED flashes once per second
