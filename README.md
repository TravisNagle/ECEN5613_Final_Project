# (WIP) Modular MIDI Control Surface for Reaper

**ECEN 5613 Embedded System Design · Fall 2026 Final Project**
Travis Nagle & Nathan Cohen

An 8051-based MIDI control surface for Reaper. Two motorized faders stay in sync with the DAW, a 16x4 LCD and panel buttons edit presets, and plug-in I2C daughter boards add pots and buttons.

> **Status (2026-10-24):** design phase, nothing built yet. The master board is the **existing class dev board**, and every new circuit is **hand-built on perf boards** (no custom PCB). The authoritative hardware spec is [Hardware_Map.md](Hardware_Map.md) **Rev 13**; open decisions are in its section 9. The PDR (10/19) described a foot controller with one fader. The changes since then are in Hardware_Map Appendix B.

## Documents

| File | What it is |
|---|---|
| [Hardware_Map.md](Hardware_Map.md) | **Authoritative hardware spec (Rev 13)**: architecture, class-board changes, pin map, memory map, netlist (Appendix A), build stages, open items |
| [hardware/Perfboard_Order_Notes.md](hardware/Perfboard_Order_Notes.md) | Kit parts mapping, on-hand modules, Digi-Key order (not yet placed) and alternates |
| [docs/f26finalproject_8-24-2026.pdf](docs/f26finalproject_8-24-2026.pdf) | Course final-project specification (deliverables, report and submission rules) |
| [docs/F26_PDR_TravisNagle_NathanCohen.pptx](docs/F26_PDR_TravisNagle_NathanCohen.pptx) | Preliminary design review slides (10/19) |
| [docs/MIDI-Controller.pdf](docs/MIDI-Controller.pdf) | PDR-era design document (single fader) |
| [docs/archive/](docs/archive/) | Superseded documents (Rev 10 review of the dropped PCB design) |
| [reference/](reference/) | Read-only: class dev board KiCad project, BOM, Lab 3 SPLD and memory map; fader datasheet; parts-kit list |
| [AGENTS.md](AGENTS.md) | Rules and conventions for AI agents working in this repo |

The custom-PCB draft (`kicad/ESD_Main`, Rev 12) was removed on 2026-10-24. It is still in the git history at commit `735803c`.

---

## Features

- **Two motorized faders, synced both ways:** moving a fader changes Reaper's track volume, and Reaper's automation moves the fader. A capacitive touch sensor on each fader knob tells the firmware when a hand is on it, so the motor never fights the user.
- **USB-MIDI with no drivers:** the 8051 UART talks to a KB2040 acting as a class-compliant USB-MIDI device; Reaper uses its built-in Mackie Control Universal support.
- **LCD and panel buttons:** 16x4 character LCD on the memory-mapped bus, a five-way D-pad and one button per fader for menus and presets.
- **Presets:** stored in a 24C16 I2C EEPROM.
- **Expression pedal:** TRS input on the fader ADC, sent as a MIDI CC.
- **Daughter boards:** pot and button boards on an I2C bus over RJ45 cables, in any order; the master finds them by address scan.

---

## System Overview

```
                 +---------------- class dev board (master) ----------------+
 9 V adapter --> | AT89C51RC2 @ 11.0592 MHz, '373 latch, ATF16V8B decode,   |
                 | MAX232 + DB9 (FLIP / PC), 7805                           |
                 +---+-----------------+----------------+-------------+-----+
                     | AD bus + decode | PCA PWM, SPI   | UART        | I2C
                     v                 v                v             v
              LCD 16x4,          TB6612 -> 2 faders  KB2040 USB-MIDI  24C16 presets,
              '273 dir latch,    MCP3008 ADC         (level shifter)  RJ45 bus -> pot / button
              '244 buttons       (faders, pedal)         |                daughter boards
                                                         v
                                                PC: Reaper (Mackie Control)
```

Full block diagram, pin map and memory map: [Hardware_Map.md](Hardware_Map.md) sections 1-3.

| XRAM address | Device |
|---|---|
| 0x0000-0x03FF | On-chip XRAM |
| 0xF000 | Motor direction latch (write) |
| 0xF400-0xF403 | LCD (command / data / busy / data read) |
| 0xF800 | Button buffer (read) |
| 0xFFFF | Virtual debug port (logic-analyzer trigger) |

---

## Firmware Architecture

Interrupts only move bytes and set flags; all real work runs in a cooperative main loop.

| Interrupt / hardware | Job |
|---|---|
| UART (Timer 2) | Link to the KB2040: RX into a ring buffer, TX from a ring buffer. 31,250 baud MIDI or 115,200 baud packets (Hardware_Map `OPEN` #4) |
| Timer 0, mode 2 (high priority) | Soft-UART debug TX at 9,600 baud on P1.0 |
| Timer 1, mode 1 | 1 ms system tick |
| PCA | 8-bit hardware PWM at 10.8 kHz for two motors (no CPU cost) |

| Main-loop module | Job |
|---|---|
| MIDI parser | Status/data state machine, running status, real-time bytes (Reaper feedback only) |
| Button scan | Read 0xF800 at about 100 Hz, 20 ms debounce, short and long press |
| Fader control | MCP3008 reads, PD loop at 250-500 Hz, deadband brake, stall timeout, staggered starts |
| MCU link | 14-bit pitch bend both ways; touch notes from the knob touch sensors (0xF800 bit 7, P1.5) |
| Pedal | Averaging, calibration, hysteresis -> CC 11 |
| LCD + UI | Shadow copy, menu, transient messages |
| Presets | 24C16 records with checksum |
| I2C daughters | Address scan, PCF8574 buttons/LEDs, pot ADC reads, bus recovery |

The PDR's CPU budget (single fader, 1 kHz loop, MIDI merge) no longer applies. Re-measure the budget on hardware.

---

## Mackie Control Messages Used

| Message | Meaning |
|---|---|
| `E0 ll mm` / `E1 ll mm` | Fader 1 / 2 position (14-bit, both directions) |
| `90 68 7F` / `90 68 00` | Fader 1 touch / release (fader 2: note `69`) |
| `90 18+n`, `10+n`, `08+n`, `00+n` | Select / Mute / Solo / Rec for strip n |
| `90 5F 7F` / `90 5E 7F` / `90 5D 7F` | Record / Play / Stop |
| `B0 0B vv` | Expression pedal (CC 11) |

Starting point only; the full mapping is in Hardware_Map section 5.

---

## Setup

### Hardware
1. Power everything from one **9 V, 2 A or more** adapter in the class board jack; it feeds the logic and the fader motors (Hardware_Map section 3.9).
2. Plug the KB2040 into the PC by USB-C. It shows up as a USB-MIDI device.
3. Set `JP_RX` to **KB** for normal use, or **PC** for FLIP and the DB9 terminal.

### Reaper
1. **Options → Preferences → Audio → MIDI Devices:** confirm the KB2040 appears; enable its input and output.
2. **Preferences → Control/OSC/Web → Add → Mackie Control Universal:** set the MIDI input and output to the KB2040.
3. Optional: assign the pedal to any plugin parameter with **Param → Learn** in the FX window.

### Fallback (if the USB-MIDI bridge fails)
MIDI bytes go out the class board DB9 at 115,200 baud → USB-RS232 adapter → [Hairless MIDI](https://projectgus.github.io/hairless-midiserial/) → [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) → Reaper.

---

## Building and Flashing

> Firmware is not written yet; these steps will be finalized with the first build.

```bash
cd firmware
sdcc -mmcs51 --model-large main.c
packihx main.ihx > main.hex
```

Flash `main.hex` with Atmel FLIP over the class board DB9 (`JP_RX` in the **PC** position; hold the PSEN button through reset to enter the bootloader). The KB2040 runs a CircuitPython bridge script (to be added under `firmware/`).

---

## Milestones

Rebased from the PDR milestones for the Rev 13 scope; the team still needs to confirm owners and dates.

| | Milestone | Owner | Target | Phase |
|---|---|---|---|---|
| M1 | MIDI link: Timer 2 UART, KB2040 bridge, Reaper receives notes | Both | 11/1 | P1 |
| M2 | Debug port, panel buttons via the '244 | Travis | 11/8 | P1 |
| M3 | MCP3008: fader positions and pedal as CC | Nathan | 11/8 | P1 |
| M4 | MIDI from Reaper: parser, MCU feedback | Travis | 11/22 | P1 |
| M5 | LCD, presets (24C16), menu | Travis | 11/29 | P1-P2 |
| M6 | Motorized faders: TB6612, PD loop, MCU link (2 faders) | Nathan | 11/29 | P1-P2 |
| M7 | I2C daughter boards (pot, button) over RJ45 | Both | 11/29 | P3 |
| M8 | Stretch: MIDI clock tempo sync | Both | If ahead | |

Feature freeze **11/30** · Demo **12/4** · Return kit items (including the NVSRAM) **12/7** · Report **12/9**

---

## Repository Layout

```
Hardware_Map.md   hardware spec (start here)
hardware/         parts and order notes, Digi-Key CSVs; (planned) KiCad schematic-only project
spld/             (planned) final.pld, its simulation input and .jed
firmware/         8051 C source (SDCC) and the KB2040 bridge script
tools/            test scripts (MIDI-OX configs, benchmarks)
docs/             course spec, PDR deck, design doc; archive/ for superseded documents
reference/        class dev board, fader datasheet, parts kit; read-only: copy, do not edit
```

---

## References

- Atmel AT89C51RB2/RC2 Datasheet (doc4180), Errata (doc4181), 8051 Hardware Manual (doc4316)
- [MIDI 1.0 Electrical Specification (CA-033)](https://midi.org/wp-content/uploads/wpforo/default_attachments/1709416667-ca33-MIDI-10-Electrical-Specification-Update.pdf)
- [Summary of MIDI 1.0 Messages](https://midi.org/summary-of-midi-1-0-messages)
- [REAPER Mackie Control source (`csurf_mcu.cpp`)](https://github.com/justinfrankel/reaper-sdk/blob/main/reaper-plugins/reaper_csurf/csurf_mcu.cpp)
- [Microchip MCP3008](https://ww1.microchip.com/downloads/en/DeviceDoc/21295d.pdf), Toshiba TB6612FNG, TI [SN74AHC157](https://www.ti.com/lit/ds/symlink/sn74ahc157.pdf), [SN74HCT244](https://www.ti.com/lit/ds/symlink/sn74hct244.pdf), [CD74HCT273](https://www.ti.com/lit/ds/symlink/cd74hct273.pdf), [MAX232](https://www.ti.com/lit/ds/symlink/max232.pdf), NXP PCF8574
- [Adafruit KB2040](https://learn.adafruit.com/adafruit-kb2040), CircuitPython `usb_midi`
- Terwin SM100 motor fader: [reference/motor_slider_datasheet.pdf](reference/motor_slider_datasheet.pdf)

## AI use

Parts of the hardware documents were drafted with AI assistance (Anthropic Claude) and reviewed by the team. The course requires AI use to be fully documented in the final report, and AI may not be used to write report text.
