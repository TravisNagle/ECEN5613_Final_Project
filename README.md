# (WIP) MIDI Foot Controller for Reaper

**ECEN 5613 Embedded System Design · Fall 2026 Final Project**
Travis Nagle & Nathan Cohen

An 8051-based MIDI foot controller with a motorized fader that stays in sync with the DAW. It lets a musician record, play and mix in Reaper without taking their hands off their instrument.

> **Hardware status (2026-10-20):** the design has grown since the PDR. The authoritative hardware spec is [Hardware_Map.md](Hardware_Map.md) (Rev 12): three board-mounted motorized faders, a 16x4 LCD on the memory-mapped bus, eight panel buttons, a preset EEPROM, I2C daughter boards, and a custom main PCB (KiCad 10, JLCPCB). The hardware sections below (footswitches, '165, single fader, NVRAM presets, pin map) describe the PDR design and are kept for reference until they are updated.

## Documents

| File | What it is |
|---|---|
| [Hardware_Map.md](Hardware_Map.md) | **Authoritative hardware spec (Rev 12)** and hand-off brief for KiCad capture/layout |
| [Hardware_Map_Review.md](Hardware_Map_Review.md) | Design review of Rev 10; its fixes are folded into Rev 11-12 |
| [F26_PDR_TravisNagle_NathanCohen.pptx](F26_PDR_TravisNagle_NathanCohen.pptx) | Preliminary design review slides (10/19) |
| [MIDI-Controller.pdf](MIDI-Controller.pdf) | PDR-era design document (single fader; fader specs) |
| [f26finalproject_8-24-2026.pdf](f26finalproject_8-24-2026.pdf) | Course final-project specification |
| [reference/](reference/) | Read-only copies of the class dev board (KiCad project, BOM, Lab 3 SPLD, memory map) and the fader datasheet |
| [kicad/](kicad/) | Main-board KiCad project (`ESD_Main`), project libraries and generator scripts |
| [AGENTS.md](AGENTS.md) | Rules and conventions for AI agents working in this repo |

---

## Features

- **Footswitch transport control:** four footswitches send Mackie Control commands (record, play, stop, previous/next marker) or user-assigned MIDI CC/notes.
- **Expression pedal:** TRS pedal → 10-bit ADC → averaged, calibrated MIDI CC 0–127 with hysteresis.
- **Motorized fader, synced both ways:** moving the fader changes Reaper's track volume, and Reaper's automation moves the fader. A touch message prevents fighting.
- **MIDI IN merge:** opto-isolated MIDI input. External gear (e.g. a keyboard) plays through, merged with the controller's own messages, with filtering and loop prevention.
- **LCD presets:** status display and a preset editor driven by the footswitches. Presets are stored in battery-backed NVRAM with a checksum.
- **No drivers or plugins:** standard 5-pin MIDI plus Reaper's built-in Mackie Control Universal support.

---

## System Overview

```
 Footswitches ──► 74HC165 ─┐
 Pedal + fader ─► MCP3008 ─┤                         ┌─► 74HC125 ─► MIDI OUT ─► USB-MIDI ─► Reaper
                           ├─► AT89C51RC2 (8051) ────┤
 MIDI IN ─► 6N138 opto ────┘   11.0592 MHz           ├─► SN754410 H-bridge ─► fader motor (12 V USB-PD)
                               bq4011 NVRAM          ├─► MAX232 ch2 ─► DB9 #2 (debug, soft UART)
                               LCD (Lab 4)           └─► MAX232 ch1 ─► DB9 #1 (FLIP / fallback)
```

New hardware lives on a **daughter board** connected to the Lab 1–3 8051 board by a ribbon cable (9 port pins, TXD, RXD, +5 V, GND).

### Pin Map

| Pin | Function |
|---|---|
| P1.0 | MCP3008 /CS + 74HC165 SH/LD |
| P1.2 | 74HC165 QH |
| P1.3 (CEX0) | PCA PWM → H-bridge enable |
| P1.4 | Motor DIR_A |
| P1.5 / P1.6 / P1.7 | Hardware SPI: MISO / SCK / MOSI (SSDIS = 1) |
| P3.4 | Motor DIR_B |
| P3.5 | Soft-UART debug TX → MAX232 T2IN |
| P3.0 / P3.1 | Hardware UART: MIDI (RXD via jumper: MIDI IN / PC) |
| P3.2, P3.3 | Reserved for Lab 4 |
| P1.1 | Existing LED |

### Memory Map

| Range | Use |
|---|---|
| 0x0000–0x03FF | On-chip XRAM |
| 0x7F00–0x7FFF | Preset storage in the bq4011 NVRAM |

---

## Firmware Architecture

Interrupts only move bytes and set flags; all real work runs in a cooperative main loop.

| Interrupt / hardware | Job |
|---|---|
| UART (Timer 2, 31,250 baud) | MIDI RX into a 32-byte ring buffer; TX from a ring buffer |
| Timer 0, mode 2 (high priority) | Soft-UART debug TX at 9,600 baud |
| Timer 1, mode 1 | 1 ms system tick |
| PCA | 8-bit hardware PWM at 10.8 kHz for the motor (no CPU cost) |

| Main-loop module | Job |
|---|---|
| MIDI parser | Status/data state machine, running status, real-time bytes |
| Merge + filter | Interleave local messages at message boundaries; filter table; loop prevention |
| Switch scan | 200 Hz '165 read, 20 ms debounce → Mackie transport notes / CC |
| Pedal | 200 Hz, 8-sample average, calibration, hysteresis → CC 11 |
| Fader control | 1 kHz PD loop, deadband brake, 1 s stall timeout |
| MCU link | 14-bit pitch bend both ways; touch notes |
| Presets + LCD | NVRAM records with checksum; long-press edit menu |

### Worst-Case CPU Budget (X1, 11.0592 MHz)

Full-speed MIDI in both directions (3,125 B/s each way) plus the 1 kHz fader loop, debug output off. Cycle counts come from representative SDCC code run in the s51 simulator.

| Task | CPU |
|---|---|
| MIDI RX/TX interrupts | 25% |
| Parser / merge | 21% |
| Fader loop | 24% |
| Pedal + switches | 12% |
| Tick, scheduler, LCD | 4% |
| **Spare** | **14%** |

Debug output adds about 39% and is used for bring-up only. X2 mode doubles CPU headroom if needed.

---

## Mackie Control Messages Used

| Message | Meaning |
|---|---|
| `90 5F 7F` | Record |
| `90 5E 7F` | Play |
| `90 5D 7F` | Stop |
| `90 5B 7F` / `90 5C 7F` | Previous / next marker |
| `E0 ll mm` | Fader 1 position (14-bit, both directions) |
| `90 68 7F` / `90 68 00` | Fader 1 touch / release |
| `B0 0B vv` | Expression pedal (CC 11, plain MIDI mode) |

---

## Setup

### Hardware
1. Connect the controller's MIDI OUT and MIDI IN to a class-compliant USB-MIDI interface (e.g. iConnectivity mio).
2. Plug the interface into the PC.
3. Connect the 12 V USB-PD supply for the fader motor.

### Reaper
1. **Options → Preferences → Audio → MIDI Devices:** confirm the interface appears.
2. **Preferences → Control/OSC/Web → Add → Mackie Control Universal:** set the MIDI input and output to the interface.
3. Optional: assign the pedal to any plugin parameter with **Param → Learn** in the FX window.

### Fallback (if USB-MIDI fails)
MIDI bytes go out DB9 #1 at 115,200 baud → USB-serial adapter → [Hairless MIDI](https://projectgus.github.io/hairless-midiserial/) → [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) → Reaper.

---

## Building and Flashing

> Firmware is in progress; these steps will be finalized with the first build.

```bash
cd firmware
sdcc -mmcs51 --model-small main.c
packihx main.ihx > main.hex
```

Flash `main.hex` with Atmel FLIP over DB9 #1 (RXD jumper in **PC** position, PSEN switch held at reset to enter the bootloader).

---

## Milestones

| | Milestone | Owner | Target |
|---|---|---|---|
| M1 | MIDI OUT: Timer 2 UART, 74HC125 driver | Both | 11/1 |
| M2 | Debug port + footswitches | Travis | 11/8 |
| M3 | Expression pedal via MCP3008 | Nathan | 11/8 |
| M4 | MIDI IN, merge, filter | Travis | 11/22 |
| M5 | LCD, presets, menu | Travis | 11/29 |
| M6 | Motorized fader, PD loop, MCU link | Nathan | 11/29 |
| M7 | Stretch: tempo sync or second fader | Both | If ahead |

Feature freeze **11/30** · Demo **12/4**

---

## Repository Layout

```
Hardware_Map.md   hardware spec (start here), plus review, PDR deck and course spec at the root
kicad/            ESD_Main KiCad 10 project, lib/ (ESD + class symbols/footprints), tools/ (generators)
reference/        class dev board and datasheets, read-only: copy, do not edit
firmware/         8051 C source (SDCC)
hardware/         hardware notes (KiCad projects currently live in kicad/)
docs/             PDR slides, datasheets, references
tools/            test scripts (MIDI-OX configs, benchmarks)
```

---

## References

- Atmel AT89C51RB2/RC2 Datasheet (doc4180), Errata (doc4181), 8051 Hardware Manual (doc4316)
- [MIDI 1.0 Electrical Specification (CA-033)](https://midi.org/wp-content/uploads/wpforo/default_attachments/1709416667-ca33-MIDI-10-Electrical-Specification-Update.pdf)
- [Summary of MIDI 1.0 Messages](https://midi.org/summary-of-midi-1-0-messages)
- [REAPER Mackie Control source (`csurf_mcu.cpp`)](https://github.com/justinfrankel/reaper-sdk/blob/main/reaper-plugins/reaper_csurf/csurf_mcu.cpp)
- TI [SN74HC165](https://www.ti.com/lit/ds/symlink/sn74hc165.pdf), [SN74HC125](https://www.ti.com/lit/ds/symlink/sn74hc125.pdf), [SN754410](https://www.ti.com/lit/ds/symlink/sn754410.pdf), [MAX232](https://www.ti.com/lit/ds/symlink/max232.pdf), [bq4011](https://www.ti.com/lit/ds/symlink/bq4011.pdf)
- [Microchip MCP3008](https://ww1.microchip.com/downloads/en/DeviceDoc/21295d.pdf)

## AI use

Parts of the hardware documents and KiCad generators were drafted with AI assistance (Anthropic Claude) and reviewed by the team. The course requires AI use to be fully documented in the final report.
