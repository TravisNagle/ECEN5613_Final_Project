# ECEN 5613 Final Project: Reaper MIDI control surface

Travis Nagle and Nathan Cohen, ECEN 5613 Embedded System Design, Fall 2026.

An AT89C51RC2 (8051) control surface for Reaper: three motorized faders, a 16x4 character LCD (Lab 4 Samsung module), eight panel buttons, DIN MIDI IN/OUT (into an iConnectivity mio), a preset EEPROM, and I2C daughter boards for extra pots and buttons. PCBs are made in KiCad 10, fabricated by JLCPCB and assembled by the team.

**Status:** concept. Nothing is built, simulated or fabricated yet.

## Documents

| File | What it is |
|---|---|
| [Hardware_Map.md](Hardware_Map.md) | **Authoritative hardware spec (Rev 12)** and hand-off brief for KiCad capture/layout. Start here |
| [Hardware_Map_Review.md](Hardware_Map_Review.md) | Design review of Rev 10; its fixes are folded into Rev 11 |
| [F26_PDR_TravisNagle_NathanCohen.pptx](F26_PDR_TravisNagle_NathanCohen.pptx) | Preliminary design review slides (10/19) |
| [MIDI-Controller.pdf](MIDI-Controller.pdf) | PDR-era design document (single fader; fader specs) |
| [f26finalproject_8-24-2026.pdf](f26finalproject_8-24-2026.pdf) | Course final-project specification |
| [reference/](reference/) | Read-only copies of the class development board (KiCad project, BOM, Lab 3 SPLD, memory map) |

## Layout

```
Hardware_Map.md           spec (start here)
reference/class_board/    class dev board, read-only: copy, do not edit
  kicad_schematic/        KiCad 10 project + ECEN5613.kicad_sym + BOM + Lab 2 schematic PDF
  spld/lab3.pld           Lab 3 WinCUPL decode (base for spld/final.pld)
  memory_map_and_xram.md  Lab 3 memory map notes
kicad/                    (planned) ESD_Main, ESD_Btn, ESD_Pot projects + shared lib/
spld/                     (planned) final.pld, .si, .jed
firmware/                 (planned) SDCC sources
```

## Key dates

Parts order 10/20; PCB order about 10/27-11/1; feature freeze 11/30; demo 12/4; course parts returned 12/7; report 12/9.

## AI use

Parts of these documents were drafted with AI assistance (Anthropic Claude) and reviewed by the team. The course requires AI use to be fully documented in the final report.
