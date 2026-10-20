# Final project hardware spec: modular Reaper MIDI control surface (KiCad 10 hand-off)

| Field | Value |
|---|---|
| File name | `Hardware_Map.md` |
| Course | ECEN 5613 Embedded System Design, Fall 2026, Final Project |
| Team | Nathan Cohen (analog and control), Travis Nagle (MIDI and interface) |
| Document revision | **Rev 12, 2026-10-20: LCD is the Lab 4 Samsung 16x4, 14-pin, no backlight (section 3.6).** Rev 11, 2026-10-19: review fixes folded in ([Hardware_Map_Review](Hardware_Map_Review.md)), faders board-mounted, 12 V barrel supply, TTL serial headers, socketed crystal.** Supersedes Rev 1-10 (history in Appendix B) |
| Status | **Concept, nothing built, simulated or fabricated.** `VERIFY:` = datasheet check needed before it is trusted. `(MEASURE)` = bench value to fill in. `OPEN` = decision not yet made, see section 9 |
| Builds on | [class BOM](reference/class_board/kicad_schematic/ECEN5613_Dev_Board_BOM.csv), [Lab 3 memory map](reference/class_board/memory_map_and_xram.md), [lab3.pld](reference/class_board/spld/lab3.pld), PDR [F26_PDR_TravisNagle_NathanCohen.pptx](F26_PDR_TravisNagle_NathanCohen.pptx), spec [f26finalproject_8-24-2026.pdf](f26finalproject_8-24-2026.pdf), design doc [MIDI-Controller.pdf](MIDI-Controller.pdf). Class-board files are copies from Nathan's Lab 3 work, see [reference/](reference/) |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed/modified by the student. The course requires AI use to be fully documented in the final report. |

---

## 0. Brief for the layout agent (read first)

**Task**: capture schematics and lay out three KiCad 10 projects from this document:

| Project | Purpose | Notes |
|---|---|---|
| `ESD_Main` | Master board: AT89C51RC2, bus logic, MIDI, 3 motor faders, LCD, 8 panel buttons, I2C master | Sections 3, 5 and Appendix A are authoritative |
| `ESD_Btn` | Daughter: 4 buttons + 4 LEDs on I2C | Section 4.3 |
| `ESD_Pot` | Daughter: 8 potentiometer inputs on I2C (ADS7828, SMD) | Section 4.2 |

**Starting point**: the course board project [`reference/class_board/kicad_schematic/`](reference/class_board/kicad_schematic/) (KiCad 10.0, `ECEN5613_Dev_Board.kicad_sch`, local symbol library `ECEN5613.kicad_sym` with `8051`, `74LS373`, `GAL16V8`, `MAX232`, etc.). Copy it into `kicad/ESD_Main/`, do not edit the reference copy. Reuse the power, reset, crystal, MAX232/DB9, `/EA` jumper and bootloader (`SW3`) circuits; delete the NVSRAM (`U4`) and the LED driver (`Q1`/`D8`).

**Rules**
1. **Do not modify anything under `reference/`** (read-only copies of the class board). New KiCad projects go in `kicad/ESD_Main/`, `kicad/ESD_Btn/`, `kicad/ESD_Pot/`, with a shared project-local library in `kicad/lib/`; ask before creating them. See [AGENTS.md](AGENTS.md).
2. **Every pin number in Appendix A was written from standard JEDEC pinouts, not from datasheets.** Verify each against the datasheet (or the KiCad library symbol) and report any mismatch before routing. ERC must be clean.
3. **Do not decide the items marked `OPEN` (section 9).** Build the rest, leave a clearly labeled placeholder for them, and list what you assumed.
4. **ICs**: DIP in a socket wherever the DIP part is in production, so ICs can be swapped (project goal). Where only SMD is available (pot-board ADC), use a leaded package (SOIC/TSSOP/MSOP), never BGA or no-lead. **Passives**: 0805 SMD for resistors and ceramic caps (the team has a reflow oven; order a JLC stencil); electrolytics THT radial; resistor networks THT SIP. Assembly order: reflow SMD first, then hand-solder THT.
5. Use KiCad standard footprints where one exists; add custom ones only when needed, in a project-local library.
6. Net names are the ones in this document, in upper case, active-low suffix `_N` (the CUPL signal names in section 3.3 use a lowercase `_n` for the same nets). Add a `Phase` field (P1/P2/P3) to every component (section 7).
7. Sheet structure for `ESD_Main`: Power, MCU + bus (8051, 373, SPLD), Memory-mapped I/O (latch, button buffer, LCD), MIDI + serial, Fader channel (hierarchical, 3 instances), I2C + bus connector. Keep sheets uncluttered with pin numbers and net names visible (the course requires a readable PDF schematic).
8. PCB: 2-layer, 1.6 mm, ground pour both sides, four M3 mounting holes, silkscreen reference designators, polarity marks, pin-1 marks, phase tags, and arrows on the D-pad. If routing needs 4 layers, stop and ask.

**Deliverables**: three KiCad projects; schematic PDFs; BOM CSV per board with columns `Ref, Value, Footprint, Phase, Manufacturer PN, Supplier, Supplier URL, Qty, Unit cost`; Gerbers + drill + zip; netlist cross-check against Appendix A; list of assumptions and mismatches.

**Stop and ask the user** about: LCD header pin order, the fader mechanical drawing (footprint and motor cutout, section 3.5), panel layout, board outline size (section 9).

---

## 1. Architecture

The **main board** carries the AT89C51RC2 at 11.0592 MHz. The 8051's external bus (74LS373 latch + ATF16V8 SPLD) is kept **only for memory-mapped I/O**: no external memory is fitted. It supplies MIDI IN/OUT for Reaper, **three motorized faders**, the **Lab 4 16x4 character LCD**, **eight panel buttons** (five navigation under the LCD, one under each fader), an I2C master with a preset EEPROM, and a ribbon connector for daughter boards. **Daughter boards** are passive input boards (pot board, button board) on a 10-pin I2C ribbon, in any order and any number; each has a DIP switch for its I2C address and the main board finds them by scanning.

```
                              MAIN BOARD (ESD_Main)
+---------------------------------------------------------------------------------------+
| 12 V 3 A barrel ----+--> VM (+12 V motor rail) --> SN754410 x2, bulk caps             |
|                     +--> 5 V (R-78E5.0 switcher) --> logic, LCD, daughters             |
|                                                                                       |
| +----------+ AD[7:0]   +------+  latched A[1:0] = RS, R/W                             |
| |   U1     |---------->| U3   |-------------------------+                             |
| | AT89C51  |           |'373  |                         |                             |
| |   RC2    |           +------+                         v                             |
| | 11.0592  | A[15:10]  +---------+  LCD_E (0xF400) +----------------+                 |
| |   MHz    |---------->| U7      |---------------->| 16x4 ASCII LCD |                 |
| |          | /RD /WR   | ATF16V8 |                 | HD44780 (Lab 4)|                 |
| |          |---------->| decode  |                 | DB0-7 = AD bus |                 |
| |          |           +--+---+--+                 +----------------+                 |
| |          |              |   |  MOTDIR_CLK (0xF000)                                  |
| |          |              |   +---------> U14 74HCT273 dir latch -+                   |
| |          |              |               (IN1/IN2 x3, /MR=!RST)  |                   |
| |          |              |  BTN_OE_n (0xF800)                    v                   |
| |          |              +--> U16 74HC244 <-- 8 buttons    +-------------+           |
| |          |                   (5 nav + F1-3)               | U12 SN754410|-> motor 0 |
| | P1.3 CEX0|----------------- PWM0 ------------------------>| (M0, M1)    |-> motor 1 |
| | P1.4 CEX1|----------------- PWM1 ------------------------>|             |           |
| | P1.5 CEX2|----------------- PWM2 ------------------------>| U13 SN754410|-> motor 2 |
| |          |                                                +-------------+           |
| |          |   3 motor fader wipers --+                                               |
| |          |                          v                                               |
| | P1.2 CS  |                 +-------------------+                                    |
| | P1.6 SCK |<-- bit-banged ->| U11 MCP3008 ADC   |                                    |
| | P1.7 MOSI|      SPI        | CH0-2 faders      |                                    |
| | P3.3 MISO|                 | CH3 exp. pedal    |                                    |
| |          |                 +-------------------+                                    |
| | P3.0 RXD |<-- JP_RX 2x3 ---+-- U8 6N138 <-- DIN-5 IN  <-- MIDI cable ---+           |
| |          |                 +-- MAX232 R1 <-- DB9 (PC / FLIP)           |            |
| |          |                 +-- J12 TTL (USB-UART cable, PC / FLIP)     |            |
| | P3.1 TXD |--> U9 74HCT125 -> DIN-5 OUT --> MIDI cable ------+         |             |
| |          |--> MAX232 T1 --> DB9, and J12 TTL                 |         |            |
| | P1.0 DBG |--> J7 TTL debug header (USB-UART cable)           |         |            |
| | P1.1 LED |--< status LED (sinks from +5 V)                   |         |            |
| |          |                                                   |         |            |
| | P3.4 SDA |<===+====+==> U10 24LC256 EEPROM @0x50 (presets)   |         |            |
| | P3.5 SCL |<===+    |                                         |         |            |
| | P3.2 INT0|<-- BUS_INT_N                                      |         |            |
| +----------+    |                                              |         |            |
+---------------------------------------------------------------------------------------+
      | BUS connector J11 (IDC 2x5: 5V GND SDA SCL INT_N RSVD)    |         |
      |                                                   v         v
      |                                         +--------------------+
      |                                         | iConnectivity mio  |
      |                                         | MIDI OUT   MIDI IN |
      |                                         +---------+----------+
      |                                                   | USB
      |                                                   v
      |                                      PC: Reaper (MCU control surface)
      v    ribbon, straight pass-through, any order, any number
        +---- POT BOARD (DIP addr n) ---+   +---- BUTTON BOARD (DIP addr n) ---+
        | BUS_IN -> BUS_OUT in parallel |-->| BUS_IN -> BUS_OUT in parallel    |--> ...
        | ADS7828 ADC @ 0x48+n, 8 pots  |   | PCF8574 @ 0x20+n                 |
        | DIP switch sets A1:A0         |   | 4 buttons + 4 LEDs, INT -> INT_N |
        +-------------------------------+   +----------------------------------+
```

### 1.1 Decisions already made

| Topic | Decision | Why |
|---|---|---|
| USB-MIDI | UART MIDI at 31,250 baud, DIN-5 IN and OUT, into an iConnectivity mio (two DIN ports, read as 1 IN + 1 OUT) | The 8051 has no USB. The mio is class-compliant. `VERIFY:` model and port labels on the unit |
| MIDI input scope | Reaper feedback only; the PDR's keyboard merge/filter is dropped | One MIDI IN |
| External memory | **None.** Class NVSRAM removed (it must be returned); no SRAM | The LCD keeps its own RAM, so no frame buffer is needed |
| Presets | 24LC256 I2C EEPROM at 0x50 | Non-volatile, DIP-8, user keeps it |
| Bus kept for I/O | 74LS373 + ATF16V8 stay | All 14 spare port pins are used; LCD, motor latch and buttons cost no pins |
| Fader ADC | MCP3008 (10-bit SPI), bit-banged | Takes load off I2C and gives 10 bits |
| Motors | 3 faders on the main board, PCA PWM CEX0-2, SN754410, memory-mapped direction latch | Per user |
| Touch sensing | Firmware only | The faders have no touch hardware |
| Daughter boards | Passive pot and button boards; DIP-switch I2C addresses; auto-detect by ACK | Per user |
| Display | Lab 4 kit Samsung 16x4 character LCD (handout: Optrex DMC-20434 20x4, SED1278F), HD44780-compatible, 14 pins, no backlight | Lab 4 kit part; dimensions from photo, VERIFY |
| Panel buttons | 5 navigation + 3 per-fader on one 74HC244 | User interface; works if I2C is hung |
| Build order | Three population phases on one PCB spin (section 7) | Per user |
| Power | 12 V 3 A DC barrel adapter; no USB-PD | 12 V is optional in USB-PD; three faders draw about 2.4 A at start |
| Fader mounting | On the main PCB; motor passes through a routed cutout | Per user |
| 5 V regulator | Recom R-78E5.0-1.0 switching module (LM7805 fits the same holes) | A 7805 at 12 V would dissipate 3.5 W |
| Debug / PC serial | 6-pin FTDI-style TTL headers (`J7` debug, `J12` PC/MIDI TTL); MAX232 + DB9 `J5` kept for the class adapter | Board edge space, no second DB9, cable is the team's own |
| Crystal | HC-49 crystal in a socket, 11.0592 MHz default, 16 MHz to evaluate (section 3.12) | Allows a PWM-noise / baud experiment without desoldering |
| Assembly | DIP ICs in sockets, 0805 SMD passives reflowed, PCBs from JLCPCB | Team has a reflow oven |

### 1.2 Feasibility results that constrain the hardware

| Question | Result |
|---|---|
| 8051 pins | 14 spare (P1.0-P1.7, P3.0-P3.5). All are used (section 3.2) |
| 31,250 baud | Timer 2 baud generator, 11.0592e6 / (32 x 11) = 31,418 baud, +0.54 % error. Timer 1 cannot (28,800/n) |
| PWM | 3 PCA channels, 8-bit, 10.8 kHz at fosc/4 |
| I2C | Bit-banged, about 60-75 kHz at 12 clk/cycle (MEASURE). Traffic is slow human input only |
| Fader loop | MCP3008 bit-banged about 0.2 ms per channel (MEASURE); 250-500 Hz loop for 3 faders. The PDR's 1 kHz loop is too heavy |
| X2 mode | **Do not use for LCD traffic.** It halves bus pulses to about 170 ns, below the HD44780 E-pulse minimum (about 230 ns). X1 gives about 440 ns |
| Memory | 256 B IRAM + 1 KB on-chip XRAM (`AUXR = 0x0C`); LCD shadow copy is 64 B (80 B for a 20x4) |

---

## 2. Reference points on the existing course board

Reuse these circuits from [`ECEN5613_Dev_Board.kicad_sch`](reference/class_board/kicad_schematic/ECEN5613_Dev_Board.kicad_sch) unchanged unless noted:

| Circuit | Class refs | Change |
|---|---|---|
| Barrel jack, bridge, LM7805, C1/C2, D5, power LED, power switch | J1, D1-D4, U2, C1, C2, D5, D6, R1, SW1 | Drop the bridge (DC only); U2 becomes the R-78E module; keep SW1; see section 3.9 |
| 8051, crystal, load caps, bypass, reset (R2, R3, C3, D7, SW2) | U1, Y1, C5, C6, C4, ... | Keep. Y1 goes in a socket (section 3.12). Tap `RST` for U15 |
| `/PSEN` bootloader button | R6, SW3 | Keep |
| `/EA` select | J14 | Keep, jumper to +5 V = internal flash |
| MAX232 + DB9 | U6, C10-C13, J4, J5 | Keep channel 1; channel 2 unused (debug moves to TTL header `J7`) |
| P0 pull-up bank | R4 (10 k SIP-10) | Keep (AD0-AD7 float between bus cycles) |
| 74LS373, ATF16V8 | U3, U7 | Keep; U7 gets new equations (section 3.3) |
| Remove | U4 (NVSRAM), Q1/D8/R5/R7 (LED driver), SW4 `/INT0` button (optional footprint, DNP), J6 | |

---

## 3. Main board (ESD_Main)

### 3.1 ICs (all DIP, all socketed)

| Ref | Part | Package | Function | Phase |
|---|---|---|---|---|
| U1 | AT89C51RC2 | DIP-40, machined-pin socket | MCU | P1 |
| U2 | Recom R-78E5.0-1.0 (LM7805 alternative in the same holes) | 3-pin SIP, 2.54 mm (TO-220 pinout Vin/GND/Vout) | 5 V logic rail | P1 |
| U3 | SN74LS373N (TI) or 74HCT373 | DIP-20 | ALE address latch; only Q0, Q1 used (LCD RS, R/W) | P1 |
| U6 | MAX232 | DIP-16 | PC serial (ch1); ch2 unused | P1 |
| U7 | ATF16V8B-15PU | DIP-20 | I/O decode, 3 outputs (section 3.3) | P1 |
| U8 | 6N138 | DIP-8 | MIDI IN opto | P1 |
| U9 | 74HCT125 | DIP-14 | MIDI OUT driver + 3 PWM buffers (HCT: inputs come from quasi-bidirectional port pins, VOH min 2.4 V) | P1 |
| U10 | 24LC256-I/P | DIP-8 | Preset EEPROM | P2 |
| U11 | MCP3008-I/P | DIP-16 | Fader and pedal ADC | P1 |
| U12 | SN754410NE | DIP-16 | H-bridge, motors 0 and 1 | P1 |
| U13 | SN754410NE | DIP-16 | H-bridge, motor 2 | P2 |
| U14 | 74HCT273 | DIP-20 | Motor direction latch (has /MR). HCT: CP comes from the ATF16V8B (VOH min 2.4 V) | P1 |
| U15 | 74HC14 | DIP-14 | Schmitt RST inverter for U14 /MR (`RST` is a slow RC ramp); 5 gates spare | P1 |
| U16 | 74HC244 | DIP-20 | Reads the 8 panel buttons | P1 |
| LCD1 | Samsung 16x4 LCD (Lab 4 kit; handout: Optrex DMC-20434) | 14-pin single-row header | Display | P1 |

Buy duplicates of cheap course parts (74LS373, MAX232, ATF16V8B) so only the 8051 might need to move from the course board (`VERIFY:` with TA whether it must be returned). **Supply notes (2026-10-19 search, re-check)**: ATF16V8B is NRND, buy 2-3 spares; SN754410NE is out of stock at DigiKey US, order from Mouser; the L293D is pin-compatible but rated 0.6 A, below the fader's 0.8 A start current (bench use only); 6N138 stock is patchy (Lite-On 6N138M), buy spares.

### 3.2 8051 pin map

| DIP pin | Port | Alt | Net | Connects to |
|---|---|---|---|---|
| 1 | P1.0 | T2 | `DBG_TX` | J7.5 (TTL debug header, section 3.8) |
| 2 | P1.1 | T2EX | `LED_N` | status LED cathode; +5 V -> 330 ohm -> LED anode (lit when P1.1 = 0) |
| 3 | P1.2 | ECI | `ADC_CS_N` | U11.10 |
| 4 | P1.3 | CEX0 | `PWM0` | U9.5 |
| 5 | P1.4 | CEX1 | `PWM1` | U9.9 |
| 6 | P1.5 | CEX2 | `PWM2` | U9.12 |
| 7 | P1.6 | CEX3 | `ADC_SCK` | U11.13 |
| 8 | P1.7 | CEX4 | `ADC_MOSI` | U11.11 |
| 9 | RST | | `RST` | class reset circuit, U15.1 |
| 10 | P3.0 | RXD | `MIDI_RX` | JP_RX pins 2, 4, 6 |
| 11 | P3.1 | TXD | `MIDI_TX` | U9.2, U6.11, J12.5 |
| 12 | P3.2 | /INT0 | `BUS_INT_N` | J11.7, 10 k pull-up to +5 V |
| 13 | P3.3 | /INT1 | `ADC_MISO` | U11.12 (plain GPIO input) |
| 14 | P3.4 | T0 | `SDA` | J11.3, U10.5, 3.3 k pull-up |
| 15 | P3.5 | T1 | `SCL` | J11.5, U10.6, 3.3 k pull-up |
| 16 | P3.6 | /WR | `WR` | U7.8 |
| 17 | P3.7 | /RD | `RD` | U7.6 |
| 18, 19 | | XTAL2, XTAL1 | | Y1 (HC-49 in socket) + 27 pF x2 |
| 20 | | GND | | |
| 21, 22 | P2.0, P2.1 | A8, A9 | | unconnected (test pads) |
| 23 | P2.2 | A10 | `A10` | U7.11 |
| 24 | P2.3 | A11 | `A11` | U7.9 |
| 25 | P2.4 | A12 | `A12` | U7.2 |
| 26 | P2.5 | A13 | `A13` | U7.3 |
| 27 | P2.6 | A14 | `A14` | U7.4 |
| 28 | P2.7 | A15 | `A15` | U7.5 |
| 29 | | /PSEN | `PSEN_N` | R6 1 k -> SW3 -> GND (bootloader); **not** to U7 |
| 30 | | ALE | `ALE` | U3.11 |
| 31 | | /EA | `EA_N` | J14 (jumper to +5 V = internal flash) |
| 39..32 | P0.0..P0.7 | AD0..AD7 | `AD0`..`AD7` | U3 D, U14 D, U16 Y outputs, LCD DB0-7, R4 pull-ups |
| 40 | | VCC | | +5 V, 0.1 uF |

Port notes for firmware and layout:
- **8051 ports are quasi-bidirectional**: a high is only a weak pull-up (guaranteed VOH 2.4 V). Never hang a resistive load to ground (a pull-down below about 100 k, an LED to ground) directly on a port pin; sinking from +5 V is fine (about 10 mA per pin). That is why PWM goes through the U9 buffers and the status LED sinks into P1.1.
- Timer 2 runs as the UART baud generator, so `EXEN2` must stay 0 (P1.1 is a plain output). Timer 0/1 pins P3.4/P3.5 are plain GPIO (`C/T = 0`).
- Do not disable ALE (`AUXR.0`): U3 needs it for the LCD RS and R/W.

### 3.3 Memory-mapped I/O and SPLD

New file `spld/final.pld` derived from [`lab3.pld`](reference/class_board/spld/lab3.pld); leave the reference copy untouched. Inputs: `A15-A12` (pins 2-5), `A11` (9), `A10` (11), `RD` (6), `WR` (8). Outputs:

```
pin 15 = MOTDIR_CLK;   /* -> U14 CLK, rising edge latches at end of /WR          */
pin 14 = LCD_E;        /* -> LCD E, ACTIVE HIGH during a read or write            */
pin 12 = BTN_OE_n;     /* -> U16 /1OE and /2OE                                    */
pin 16 = VDP_WR_n;     /* optional logic-analyzer trigger, test pad only          */

MOTDIR_CLK = WR # !(A15 & A14 & A13 & A12 & !A11 & !A10); /* write 0xF000-0xF3FF */
LCD_E      = (A15 & A14 & A13 & A12 & !A11 & A10) & !(RD & WR); /* 0xF400-0xF7FF */
BTN_OE_n   = RD # !(A15 & A14 & A13 & A12 & A11 & !A10);  /* read  0xF800-0xFBFF */
VDP_WR_n   = WR # !(A15 & A14 & A13 & A12 & A11 & A10);  /* write 0xFC00-0xFFFF */
```

| XRAM address | Device | Access |
|---|---|---|
| 0x0000-0x03FF | On-chip XRAM (`AUXR = 0x0C`), no bus cycle | |
| 0xF000-0xF3FF | U14 motor direction latch | write |
| 0xF400-0xF7FF | LCD: +0 command write, +1 data write, +2 busy/address read, +3 data read (`A1` = R/W, `A0` = RS) | read/write |
| 0xF800-0xFBFF | U16 panel button buffer | read |
| 0xFC00-0xFFFF (use 0xFFFF) | Virtual debug port (trigger only; A9-A0 do not reach the SPLD, so the whole 1 KB block aliases) | write |
| other | Nothing responds | |

`MOTDIR_CLK` idles high and rises when `/WR` rises, so data is captured with the 8051's write hold time (about 40 ns). `LCD_E` falls one SPLD delay (tPD <= 15 ns) after `/WR` rises, leaving about 25 ns of data hold at the LCD (HD44780 needs about 10 ns, `VERIFY:`). Unused U7 inputs (pins 1, 7) tie to GND; unused outputs left open. `VERIFY:` G16V8 pin capabilities, then compile/simulate in WinCUPL and keep the `.jed`.

### 3.4 Connection tables

See **Appendix A** (every IC, pin by pin). It is the authoritative netlist for the layout agent.

### 3.5 Motor fader channels (x3)

- **Per channel**: U9 buffer -> SN754410 `EN`; latch outputs -> `1A/2A` (or `3A/4A`); `Y` outputs -> motor terminals; fader wiper -> RC (1 k series, 100 nF to AGND, **1 M** to AGND so an unpopulated input does not float; 100 k would load the 10 k wiper by up to about 2.4 %) -> MCP3008 channel; fader track ends to filtered 5 V (`VREF_F`) and AGND.
- **Safe state at reset**: the 8051 pins are high at reset, so the U9 buffers enable the bridges, but U14 is cleared to `00` (both inputs low = brake), so the motors do not move. Firmware should drive the PWM pins low early. The 10 k pull-down on each `EN` only matters if U9 is absent or unpowered.
- **Direction**: write `00` or `11` between forward and reverse, never straight through.
- **Filtering**: `VREF_F` = 5 V through 100 ohm and 10 uF; MCP3008 `VREF` and `VDD` from it; single-point connection of AGND to GND near U11.
- **Motor supply** `VM`: 470 uF bulk at the rail, **47-100 uF electrolytic + 0.1 uF at each SN754410 `VCC2`**, 100 nF across each motor terminal pair, PTC fuse. TVS on `VM`.
- **Fader part** (from the team's design doc [MIDI-Controller.pdf](MIDI-Controller.pdf), OCR, `VERIFY:` against the real datasheet): Alps SM100AN-B10K, 100 mm travel, 10 k linear (B), about 500 ohm end residual (calibrate min/max), motor 10 V rated (6-11 V), **about 800 mA starting current**, about 200 mm/s. With about 2.6 V SN754410 drop the motor sees about 9.4 V from 12 V. At 0.8 A per channel the SN754410 (1 A) has little margin: firmware should stagger motor starts and use a stall timeout.
- **Fader mounting: on the main PCB.** Each fader is a footprint in the project-local library, drawn from the fader's mechanical drawing (`VERIFY:` with the real part and calipers): pot and touch pins, motor terminals and mounting tabs as plated holes, plus a **routed cutout on `Edge.Cuts` for the motor body**, which hangs below the pot through the board. Keep a 1 mm copper keep-out around the cutout; JLC routes internal cutouts with a 2 mm end mill, so draw corner radii of 1 mm or more (or add relief notches if the motor can is square). Pot terminals connect straight to `VREF_F`, `FADERn_W` (through the RC) and AGND; motor terminals to `Mn_A`/`Mn_B`; the touch terminal (if present) to a test pad `TOUCHn`. No fader headers. The faders, LCD and buttons are on the top side, so **the PCB is the front panel**: keep tall parts (electrolytics, R-78E, DB9, DIN jacks) out of the knob travel area. Standoffs must be longer than the motor protrusion below the board (MEASURE).
- **Touch**: firmware only (wiper motion not explained by the drive). The touch terminal goes to a test pad for later use; no port pin is free.
- **Expression pedal** (MCP3008 CH3, P2): TRS jack `J13` (Neutrik NMJ6HCD2). Brands disagree on the wiring, so tip and ring each go through a 3-pad solder jumper (`SJ1`, `SJ2`) selecting wiper or reference. Default: tip -> wiper (via the same RC), ring -> `VREF_F` **through 100 ohm** (so a short while plugging in cannot pull down the fader reference), sleeve -> AGND.

### 3.6 LCD: Samsung 16x4 (Lab 4 kit module)

The Lab 4 handout names an **Optrex DMC-20434** (20x4, Epson SED1278F controller), but the kit module in hand (photo, 2026-10-20) is a **Samsung 16x4** (SMC1640A family): about 87 x 60 mm, mounting holes 82 x 55 mm (2.5 mm in from the edges), a **single row of 14 pins** with pin 1 at 10.0 mm from the left edge and 2.5 mm from the top, about a 65 mm viewing window, **no backlight**. Both modules are HD44780-compatible with the same 14-pin order, so the wiring below fits either; the board footprint (`ESD:LCD_16x4_Samsung_87x60_Header1x14`) fits the Samsung outline. `VERIFY:` outline, hole and pin-1 positions with a ruler before fab (photo accuracy about 0.5 mm), and count the characters at power-up (16 or 20 per line). Electrical and timing data below are from the Optrex DMC-20434 spec (No.99-0259) and the Epson SED1278 manual, used as the conservative reference.

| Pin | Signal | Net |
|---|---|---|
| 1 | VSS | GND |
| 2 | VCC | +5 V |
| 3 | VEE (LCD drive) | `LCD_V0`, 10 k trimmer wiper between +5 V and GND |
| 4 | RS | `LCD_RS` (U3.2, latched `A0`) |
| 5 | R/W | `LCD_RW` (U3.5, latched `A1`) |
| 6 | E | `LCD_E` (U7.14) |
| 7-14 | DB0-DB7 | `AD0`-`AD7` |

- Supply 4.5-5.5 V, ICC about 2.2 mA typical (4 mA max). Contrast: VCC - VEE = 4.3 V typical at 25 C (4.0-4.6 V), so VEE is about 0.7 V; a 0-5 V trimmer is fine and no negative supply is needed.
- **Timing (Optrex module spec, VDD 5 V)**: E high >= 230 ns, E cycle >= 500 ns, tAS 40 ns, tAH 10 ns, tDSW 80 ns, tH 10 ns, tDDR <= 160 ns, tDHR >= 5 ns. The 8051 at X1 gives E high about 440 ns (11.0592 MHz) or about 275 ns (16 MHz): both pass. X2 (about 170 ns) fails.
- **Firmware facts**: keep the geometry in one constant. 16x4 (Samsung module in hand): 16 columns, a **64-byte** shadow copy, DDRAM line starts 0x00, 0x40, 0x10, 0x50 (Set-DDRAM 0x80, 0xC0, 0x90, 0xD0). 20x4 (Optrex DMC-20434): 20 columns, 80 bytes, line starts 0x00, 0x40, 0x14, 0x54 (0x80, 0xC0, 0x94, 0xD4). Row 0 = title/transient message, rows 1-3 = one line per fader; 8 custom CGRAM characters for bars. Power-on: wait >= 30 ms, then the 0x30 / 4.1 ms / 100 us / 40 us init sequence; clear display takes up to about 1.64 ms.

### 3.7 Panel buttons

Eight 6 mm THT tactile switches (or one 5-way navigation switch plus three tactiles; `VERIFY:` footprint and stock). Each switch goes from its net to GND; each net has a 10 k pull-up to +5 V (one 9-pin bussed SIP, 8 resistors) and a footprint for 10 nF to GND.

| U16 bit | Net | Switch | Placement |
|---|---|---|---|
| D0 | `BTN_CENTER` | D-pad center | below the LCD |
| D1 | `BTN_UP` | D-pad up | below the LCD |
| D2 | `BTN_DOWN` | D-pad down | below the LCD |
| D3 | `BTN_LEFT` | D-pad left | below the LCD |
| D4 | `BTN_RIGHT` | D-pad right | below the LCD |
| D5 | `BTN_F1` | fader 1 | directly below fader 1 |
| D6 | `BTN_F2` | fader 2 | directly below fader 2 |
| D7 | `BTN_F3` | fader 3 | directly below fader 3 |

A bit reads 0 when pressed. U16 is read at 0xF800; `/1OE` and `/2OE` are tied together to `BTN_OE_n`. Firmware polls at about 100 Hz with a 20 ms debounce.

### 3.8 MIDI, serial and indicators

- **MIDI OUT** (`J9`, DIN-5): +5 V -> 220 ohm -> pin 4; U9.3 -> 220 ohm -> pin 5; pin 2 -> GND. The non-inverting buffer is correct: UART idle high = no current; UART low = current on. `VERIFY:` sink current against the 74HC125 data sheet (about 5 mA).
- **MIDI IN** (`J8`, DIN-5): pin 4 -> 220 ohm -> U8.2; pin 5 -> U8.3; 1N4148 across U8.2-U8.3 (cathode on U8.2); pin 2 unconnected. U8: pin 8 +5 V with 100 nF, pin 5 GND, pin 6 output with **470 ohm** pull-up to +5 V (1 k also works), pin 7 **10 k to GND** (footprint, populate if the falling edge is slow on the scope). The opto inverts the LED drive, but LED on = MIDI line low = output low, so the output follows the UART level (logically non-inverting), which is what RXD needs.
- **RXD select** `JP_RX` (2x3 header, one jumper): odd pins are sources, even pins are all `MIDI_RX` (P3.0). Pair 1-2 = U8.6 (MIDI), pair 3-4 = U6.12 (DB9 PC / FLIP), pair 5-6 = J12.4 (TTL PC / FLIP). Silkscreen "MIDI / DB9 / TTL". Only one source can drive P3.0 at a time.
- **TTL serial headers**: two 1x6 2.54 mm right-angle headers in the FTDI TTL-232R pin order, so a standard **5 V** USB-UART cable (FTDI TTL-232R-5V, or a CP2102/CH340 adapter set to 5 V) plugs straight in. Names are from the cable's side: cable TXD (pin 4) is an output into the board, cable RXD (pin 5) is an input from the board.

| Pin | Cable signal | `J12` PC / MIDI TTL | `J7` debug |
|---|---|---|---|
| 1 | GND (black) | GND | GND |
| 2 | CTS | NC | NC |
| 3 | VCC (+5 V from USB) | NC (pad + solder jumper `SJ3`, open: do not back-power the board from USB) | NC |
| 4 | TXD (cable output) | `JP_RX` pin 5 | NC |
| 5 | RXD (cable input) | `MIDI_TX` (TXD, P3.1) | `DBG_TX` (P1.0) |
| 6 | RTS | NC | NC |

  `J12` replaces both the DB9 and the class USB-RS232 adapter for FLIP bootloading and the "MIDI over serial" fallback (Hairless MIDI); `J7` carries the Timer 0 soft-UART debug output. Silkscreen "GND" at pin 1 on both.
- **PC serial** `J5` (DB9 female, via 9-pin header `J4` like the class board): pin 2 <- U6.14 (T1OUT), pin 3 -> U6.13 (R1IN), pin 5 GND. Kept for the class adapter; may be DNP if the TTL cable is used.
- **Status LED**: +5 V -> 330 ohm -> LED anode, cathode -> P1.1 (`LED_N`); lit when P1.1 = 0, off at reset. **Power LED** as on the class board.

### 3.9 Power

| Item | Spec |
|---|---|
| Input | `J1` 2.1 mm barrel jack (center positive), **12 V 3 A DC adapter** (no USB-PD). Then power switch `SW1`, then PTC fuse `F1` (about 3 A hold), then reverse-polarity protection with a **P-FET** (drain to the jack, source to the load, gate to GND through 10 k, 12 V zener gate-source; for example a SOT-23 or DPAK P-FET with Vds at least -20 V, Rds(on) under 50 mohm, `VERIFY:` part). TVS (SMBJ15A) across `VM` |
| `VM` | Fused 12 V to U12/U13 `VCC2` only; jumper `JP_VM` (or a 2-pin header rated 3 A) to isolate; 470 uF bulk + 47-100 uF at each driver |
| +5 V | **Recom R-78E5.0-1.0** (1 A, 8-28 V in, about $4). Use one 3-hole 2.54 mm footprint (Vin, GND, Vout) plus a heat-sink hole so an LM7805 can drop in as a backup; keep the class board's input/output caps |
| Budget (MEASURE) | 5 V: core about 150 mA; SN754410 logic about 20-60 mA each (`VERIFY:`); LCD about 20-100 mA; daughters; total up to about 500-600 mA (fine for the 1 A R-78E). 12 V: three faders starting together about 2.4 A, plus about 0.3 A for the R-78E input, so a 3 A adapter |
| Grounds | Motor current returns from the SN754410 GND pins straight to the power-entry star point and never runs under U11 or the AGND area. SN754410 GND pins 4, 5, 12, 13 sit on a large copper pour on both layers with stitching vias (these pins are the heat sink) |
| Isolation | `JP_BUS` in the +5 V line to `J11` |
| Decoupling | 0.1 uF at every IC, 10 uF near U1 and U11 |

### 3.10 I2C and daughter-board connector

- Pull-ups on the main board only: **3.3 k** on `SDA`, `SCL`; **10 k** on `BUS_INT_N`.
- **U10 24LC256**: A0-A2 GND, `WP` 10 k pull-up to +5 V plus jumper `JP_WP` to GND (jumper on = write enabled, off = protected; WP never floats), 100 nF.
- **J11** (IDC 2x5, 2.54 mm, shrouded, keyed): the ribbon connector below. BUS_IN and BUS_OUT on a daughter are wired in parallel with no active parts.

| Pin | Signal | | Pin | Signal |
|---|---|---|---|---|
| 1 | +5 V (via `JP_BUS`) | | 2 | GND |
| 3 | `SDA` | | 4 | GND |
| 5 | `SCL` | | 6 | GND |
| 7 | `BUS_INT_N` | | 8 | GND |
| 9 | `RSVD` | | 10 | GND |

- Capacitance: about 50 pF per board plus about 50 pF/m of ribbon (rough). Plan 4-6 boards at 100 kHz. Not hot-plug safe. Bus recovery: 9 SCL clocks then STOP.

### 3.11 Connectors, jumpers, test points, board

| Ref | Item |
|---|---|
| J1 | Barrel jack |
| J4/J5 | Class-board 9-pin header + DB9 (PC) |
| J7 | TTL debug header 1x6, FTDI order (section 3.8) |
| J8 / J9 | DIN-5 MIDI IN / OUT (Same Sky SDS-50J) |
| J10 | LCD header, 1x14 single row (pin 1 at left) |
| J11 | Bus IDC 2x5 |
| J12 | TTL PC / MIDI header 1x6, FTDI order (section 3.8) |
| J13 | TRS expression pedal (P2), Neutrik NMJ6HCD2 |
| J14 | `/EA` select 1x3 |
| FDR1-FDR3 | Board-mounted motor faders with motor cutouts (section 3.5); replaces the Rev 10 headers J15-J20 |
| Y1 | HC-49 crystal in a socket (section 3.12) |
| SW1 | Power switch (class board part) |
| JP_VM, JP_BUS, JP_RX (2x3), JP_WP | Jumpers as above |
| SJ1, SJ2, SJ3 | Solder jumpers: pedal tip/ring select; J12 +5 V (open) |
| TP | `LCD_E`, `MOTDIR_CLK`, `BTN_OE_n`, `VDP_WR_n`, `ADC_CS_N`, `ADC_SCK`, `ADC_MOSI`, `ADC_MISO`, `SDA`, `SCL`, `BUS_INT_N`, `PWM0`-`PWM2`, `MIDI_TX`, `MIDI_RX`, `RST`, `ALE`, `TOUCH1`-`TOUCH3`, `VM`, +5 V, GND x2 |
| Board | 2-layer, size OPEN. Board-mounted 100 mm faders (body about 128 mm, `VERIFY:`) + a 16x4 LCD (87 x 60 mm) make it larger than 100 x 100 mm, which leaves JLC's cheapest price tier (still about $10-30 for 5). Four or more M3 holes, standoffs longer than the motor protrusion |

### 3.12 Crystal (socketed)

"Socketed" means Y1 plugs into two machined-pin receptacles (cut from a round-pin SIP socket strip, 4.88 mm HC-49 pitch) instead of being soldered, so the crystal can be swapped in seconds. The 27 pF load caps stay soldered; they suit both frequencies.

| | 11.0592 MHz (default, all Lab 1-4 code) | 16 MHz (to evaluate) |
|---|---|---|
| MIDI 31,250 baud, Timer 2 | reload 11, +0.54 % error (MIDI allows about 1 %) | reload 16, **exact** |
| PC baud, Timer 2 | 115,200 exact | 38,400 and below, 0.16 % error (115,200 not usable) |
| PCA 8-bit PWM at fosc/4 | 10.8 kHz | 15.6 kHz (quieter, still audible) |
| /RD, /WR pulse = LCD E high time (6 TCLCL - 100 ns) | about 440 ns | about 275 ns (module minimum 230 ns: passes) |
| Firmware change | none | recompute Timer 0 soft-UART and delay constants |

**Why not X2 mode**: X2 halves every bus strobe as well as the peripheral clocks, so at 11.0592 MHz the LCD E pulse would drop to about 170 ns, below the HD44780 minimum. That would mean an LCD that works on some modules and fails on others. A faster crystal in X1 is limited by the same E-pulse rule; 16 MHz is about the ceiling (18.432 MHz gives about 225 ns). The main noise fix is in firmware anyway: drive the motor only while the fader is moving (about 0.5 s per move), and set PWM to 0 at the target.

---

## 4. Daughter boards

### 4.1 Common

- Two IDC 2x5 connectors in parallel (`J1` BUS_IN, `J2` BUS_OUT), pinout as section 3.10; no active parts in the pass-through.
- **4-position DIP switch** `SW1` (DIP-8 footprint): positions 1-3 are `A0`, `A1`, `A2` of the board's I2C chip, position 4 spare. On the pot board only positions 1-2 are used (ADS7828 has `A0`, `A1`); positions 3-4 are spare. Each position has a 10 k pull-up to +5 V and the switch to GND (closed = 0). Silkscreen the setting table (000 = 0 ... 111 = 7; pot board 00 = 0 ... 11 = 3).
- 0.1 uF at each IC, 10 uF at the connector.

### 4.2 Pot board (ESD_Pot)

| Ref | Part | Function |
|---|---|---|
| U1 | **TI ADS7828** (12-bit, 8-channel I2C ADC, TSSOP-16, SMD reflow); the ADS7830 (8-bit) has the same footprint and pinout and is a drop-in fallback | Address 0x48 + n, n = 0-3 from `A0`/`A1` (4 pot boards maximum). CH0-CH7 = 8 pot inputs, each through 1 k and 100 nF; `COM` to GND (single-ended); **`REF` driven by `VREF_P`** (filtered +5 V, the same node as the pot tops, so readings are ratiometric) and firmware keeps the internal reference off (command byte PD1 = 0); 0.1 uF + 10 uF at `VDD` |
| `VREF_P` | 100 ohm + 10 uF + 0.1 uF from +5 V | Pot and ADC reference, as on the main board |
| J3-J10 | 1x3 pot headers (2.54 mm) | `VREF_P`, wiper, GND. Optionally add a 9 mm board-mount pot footprint (e.g. Bourns PTV09A) in parallel with each header |

Why the PCF8591P was replaced: NXP no longer makes it and the SO-16 PCF8591T has no stock. TI lists the ADS7828, ADS7830, ADS1015 and ADS1115 as Active (ti.com, 2026-10-19). The ADS7830 showed 0 stock at DigiKey with a backorder that day, so `VERIFY:` live stock of whichever is ordered. The ADS7828 was chosen for 8 channels, 5 V operation, and 12 bits for the same price class. If more than 4 pot boards are ever needed, the alternative is an ATtiny1616 (SOIC-20) as an I2C target ADC with a firmware-set address (8+ addresses, UPDI programming, extra firmware). `VERIFY:` all ADS7828 pin numbers against the TI datasheet; Appendix A.14 lists functions only.

### 4.3 Button board (ESD_Btn)

| Ref | Part | Function |
|---|---|---|
| U1 | PCF8574N (DIP-16) | I2C expander, address 0x20 + n. P0-P3 = SW2-SW5 to GND with 10 k pull-ups (+ optional 100 nF); P4-P7 = LED1-LED4, active low, 330 ohm to +5 V; `INT` (pin 13) -> `BUS_INT_N` |
| SW2-SW5 | 4 x 6 mm tactile | Buttons |
| D1-D4 | 4 x LED | Indicators |

### 4.4 I2C address map

| Family | Chip | 7-bit address | Where |
|---|---|---|---|
| Button board | PCF8574 | 0x20 + n | daughter, `n` = DIP setting 0-7 |
| Pot board | ADS7828 | 0x48 + n, n = 0-3 | daughter (0x4C-0x4F unused) |
| Preset EEPROM | 24LC256 | 0x50 | main board (reserve 0x50-0x57) |
| Reserved | PCF8574A | 0x38-0x3F | spare |

Same-type boards must use different DIP settings; the master cannot detect a duplicate. Do not put a PCF8574 LCD backpack (0x27) on this bus.

---

## 5. Reaper / MIDI mapping (starting point for firmware)

| Control | MIDI |
|---|---|
| Fader 1-3 position, both directions | Pitch bend ch 1-3, 14-bit (10-bit ADC shifted left 4) |
| Fader touch (firmware-inferred) | Note 0x68-0x6A, velocity 127/0 |
| Per-fader button (programmable) | Default Select/Mute/Solo/Rec notes 0x18/0x10/0x08/0x00 + n; short and long press differ |
| Button board SW1-4 | Rec / Solo / Mute / Select for one strip |
| Button board LEDs | Follow Reaper Note On velocity |
| Pots, pedal | CC |

Reaper side: Mackie Control Universal driver. `VERIFY:` no SysEx handshake is mandatory.

---

## 6. UI summary (firmware context)

Up/down select, left/right adjust (auto-repeat after about 500 ms), center confirm, long press saves to the EEPROM or backs out. The three fader buttons run an assigned function stored per preset. Every change shows a transient message on LCD row 0 for about 1.5 s.

---

## 7. Phased population (design-for-phasing is a layout requirement)

One PCB spin, populated in three phases. Mark each component with `P1`/`P2`/`P3` in the schematic field and silkscreen.

| Phase | Populate | Leave empty (DNP) |
|---|---|---|
| **P1: one fader, its button, LCD, MIDI** | All SMD passives (one reflow pass), power, `VM` and bulk, U1, Y1 + socket, reset, SW1, SW3, J14, R4, U3, U7 (final equations), U6 + J5, J7, J12, U8, U9, J8, J9, JP_RX, U11, U12, U14, U15, U16, button pull-up SIP, **BTN_F1**, **FDR1**, LCD header, I2C pull-ups, status/power LEDs, test points | U13, U10, J11, J13, nav switches, BTN_F2, BTN_F3, FDR2, FDR3 |
| **P2: rest of the master board** | U13, U10, J11 (unplugged), J13 pedal jack, nav switches, BTN_F2, BTN_F3, FDR2, FDR3, extra bulk | none |
| **P3: daughter boards** | ESD_Pot, ESD_Btn, ribbon cables | none |

Layout rules for this:
- SMD passives for P2 parts can be reflowed in P1 (they are harmless without their IC); the P2 step is then THT only.
- No floating nets in an empty section: 10 k pull-down on every motor `EN`, 1 M pull-down on every fader/pedal MCP3008 input and 100 k on CH4-CH7, pull-ups on all 8 U16 inputs, and the empty `U13` socket must not load any net (U13 inputs are tied to GND by the board, but its sockets pins connect only to nets that are valid with the part absent).
- Jumpers to isolate `VM`, bus +5 V and the RXD source.
- Decoupling caps next to each socket, populated with that IC.
- Program the SPLD once with all three equations in P1.

Bring-up tests per phase (firmware team, summarized): P1: power, 8051 alive, bus decode on the logic analyzer, button read, LCD, ADC, motor open loop, closed loop, MIDI OUT, MIDI IN. P2: eight buttons, EEPROM and I2C, presets, I2C recovery, three motors, loop budget, UI, full Reaper session, 30-minute run. P3: each daughter alone, both chained, duplicate address behavior, cable length, integration.

---

## 8. Schedule and parts

Today 10/19; parts order target 10/20; feature freeze 11/30; demo 12/4. A PCB order around 10/27-11/1 with express shipping lands about 11/10 (MEASURE against the real ship date). Suggested windows: P1 11/10-11/16, P2 11/17-11/22, P3 11/23-11/30. Until boards arrive, develop P1 firmware on the course board plus a breadboard. If P1 slips by more than a few days, fall back to the main board alone (PDR M1-M6 scope).

Parts to add to the 10/20 order (`VERIFY:` stock and quantities): MCP3008-I/P, SN754410NE x2 (+1 spare, Mouser), 74HCT273, 74HC244, 74HC14, 74HCT125, 6N138 (+spare), 24LC256-I/P, ADS7828IPW x2-3 (pot board, section 4.2), PCF8574N, 4-position DIP switches (DIP-8), tactile switches (8 for the main board plus 4 per button board), 9-pin 10 k SIP, DIP sockets (8/14/16/20/40, machined for U1), round-pin socket strip (crystal), 16 MHz HC-49 crystal (evaluation), DIN-5 jacks x2 (SDS-50J), TRS jack (NMJ6HCD2), 2x5 IDC headers/sockets and ribbon, 1x6 right-angle headers x2, a 5 V USB-UART cable (FTDI TTL-232R-5V or equivalent, team-owned), 3 motor faders (2 more of the on-hand part), pots, **12 V 3 A barrel adapter**, R-78E5.0-1.0, P-FET + zener, SMBJ15A TVS, 3 A PTC, 0805 passive kit, spare 74LS373 / MAX232 / **ATF16V8B x2-3 (NRND)**, Samsung 16x4 LCD (Lab 4 kit part). JLC order: main + two daughter PCBs, **plus a stencil** for each board with SMD parts.

---

## 9. Open items and risks

**OPEN decisions (agent must not decide)**

| # | Item | Needed for | Default if the user delegates |
|---|---|---|---|
| 1 | LCD mechanical: confirm the photo-derived outline (87 x 60), holes (82 x 55) and pin 1 (10.0, 2.5) with a ruler; confirm 16 vs 20 characters at power-up | Footprint check before fab | Ruler measurement |
| 2 | Fader mechanical drawing: pin positions, mounting tabs, motor-body outline and protrusion below the board (board mounting is decided) | FDR footprint, cutout, standoff length | Measure the on-hand fader with calipers and confirm against the Alps drawing before routing |
| 3 | Mechanical layout: relative positions of the LCD, three faders and eight buttons (the PCB is the front panel) | Placement | Faders side by side on the right, LCD top left, D-pad below the LCD, fader buttons below each fader |
| 4 | ~~5 V source~~ **Closed Rev 11**: R-78E5.0-1.0, LM7805-compatible holes | | |
| 5 | Expression pedal kept in P2 or deferred | J13 | Keep footprint, DNP |
| 6 | Board outline | PCB | Smallest that fits the faders and LCD; ask before exceeding about 200 x 150 mm |
| 7 | ~~Pot-board ADC~~ **Closed Rev 11**: ADS7828 (section 4.2) | | |

**Risks**

1. **PDR scope change** (PDR: one fader, 74HC165 footswitches; now three faders, I2C daughters). Agreed with Travis and being worked through with the TAs (2026-10-19).
2. **Pin budget is 100 % used.** Further I/O must use the memory-mapped page.
3. **X2 mode** breaks LCD timing; stay in X1 for LCD traffic.
4. **Three motors at once**: supply budget, regulator heat, `VM` noise on the wiper ADC.
5. **SPLD** edits can break the Lab 3 decode; keep `lab3.pld` and its `.jed`.
6. **Bit-banged SPI + I2C + MIDI parser** loop budget: measure first.
7. **Single UART** shared by MIDI and the PC bootloader.
8. **DIP-switch duplicates** on daughters are undetectable.
9. **Software touch detection** can false-trigger on vibration.
10. **Pin numbers** in Appendix A were reviewed against standard pinouts in Rev 11 (one error fixed in A.4) but not yet against the KiCad symbols and the exact datasheets.
11. **PWM noise**: 10.8 kHz is audible and the course says projects must not make significant noise. Mitigation: drive motors only while moving; optional 16 MHz crystal (section 3.12).
12. **Parts supply**: ATF16V8B NRND, SN754410NE and 6N138 stock thin; PCF8591P obsolete (replaced by ADS7828). Order on 10/20 with spares.
13. **Motor current margin**: about 0.8 A start per fader against the SN754410's 1 A per channel; stagger starts, stall timeout.

---

## Appendix A: Netlist for ESD_Main (verify every pin number)

Power pins (VCC/GND) are not listed unless special; every IC gets +5 V, GND and a 0.1 uF cap at its supply pins. `NC` = no connect. `X` = column intentionally empty.

### A.1 U1 AT89C51RC2 (DIP-40)

See section 3.2 (complete).

### A.2 U3 74LS373 (DIP-20)

| Pin | Name | Net |
|---|---|---|
| 1 | /OC | GND |
| 3, 4, 7, 8, 13, 14, 17, 18 | D0..D7 | AD0..AD7 |
| 11 | LE | ALE |
| 2 | Q0 | `LCD_RS` |
| 5 | Q1 | `LCD_RW` |
| 6, 9, 12, 15, 16, 19 | Q2..Q7 | NC |
| 10 / 20 | GND / VCC | |

### A.3 U7 ATF16V8B (DIP-20)

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | GND | 11 | `A10` |
| 2 | `A12` | 12 | `BTN_OE_N` |
| 3 | `A13` | 13 | NC |
| 4 | `A14` | 14 | `LCD_E` |
| 5 | `A15` | 15 | `MOTDIR_CLK` |
| 6 | `RD` | 16 | `VDP_WR_N` (test pad) |
| 7 | GND | 17, 18, 19 | NC |
| 8 | `WR` | 10 / 20 | GND / VCC |
| 9 | `A11` | | |

### A.4 U14 74HCT273 (DIP-20)

Rev 11 fix: the Rev 10 table had D2/D6 and Q2/Q6 swapped. The '273 pinout matches the '373.

| Pin | Name | Net |
|---|---|---|
| 1 | /MR | `RST_N` (U15.2) |
| 11 | CP | `MOTDIR_CLK` |
| 3, 4, 7, 8, 13, 14, 17, 18 | D0..D7 | AD0..AD7 |
| 2 | Q0 | `M0_IN1` |
| 5 | Q1 | `M0_IN2` |
| 6 | Q2 | `M1_IN1` |
| 9 | Q3 | `M1_IN2` |
| 12 | Q4 | `M2_IN1` |
| 15 | Q5 | `M2_IN2` |
| 16, 19 | Q6, Q7 | NC (test pads) |
| 10 / 20 | GND / VCC | |

### A.5 U16 74HC244 (DIP-20)

| Pin | Name | Net | | Pin | Name | Net |
|---|---|---|---|---|---|---|
| 1 | /1OE | `BTN_OE_N` | | 19 | /2OE | `BTN_OE_N` |
| 2 | 1A1 | `BTN_CENTER` | | 18 | 1Y1 | AD0 |
| 4 | 1A2 | `BTN_UP` | | 16 | 1Y2 | AD1 |
| 6 | 1A3 | `BTN_DOWN` | | 14 | 1Y3 | AD2 |
| 8 | 1A4 | `BTN_LEFT` | | 12 | 1Y4 | AD3 |
| 11 | 2A1 | `BTN_RIGHT` | | 9 | 2Y1 | AD4 |
| 13 | 2A2 | `BTN_F1` | | 7 | 2Y2 | AD5 |
| 15 | 2A3 | `BTN_F2` | | 5 | 2Y3 | AD6 |
| 17 | 2A4 | `BTN_F3` | | 3 | 2Y4 | AD7 |

Pins 10 / 20: GND / VCC.

### A.6 U15 74HC14 (DIP-14, Schmitt inverter, same pinout as '04)

| Gate | In | Out | Use |
|---|---|---|---|
| 1 | pin 1 = `RST` | pin 2 = `RST_N` | U14 /MR |
| 2-6 | pins 3, 5, 9, 11, 13 | GND | unused inputs tied low; outputs (4, 6, 8, 10, 12) NC (pin 4 to a test pad as a spare) |

The status LED no longer uses U15: +5 V -> 330 ohm -> LED -> P1.1 (`LED_N`).

Pins 7 / 14: GND / VCC.

### A.7 U9 74HCT125 (DIP-14)

| Gate | /OE | A (in) | Y (out) | Use |
|---|---|---|---|---|
| A | 1 -> GND | 2 = `MIDI_TX` | 3 -> J9 pin 5 via 220 ohm | MIDI OUT |
| B | 4 -> GND | 5 = `PWM0` | 6 = `PWM0_EN` -> U12.1 | motor 0 enable |
| C | 10 -> GND | 9 = `PWM1` | 8 = `PWM1_EN` -> U12.9 | motor 1 enable |
| D | 13 -> GND | 12 = `PWM2` | 11 = `PWM2_EN` -> U13.1 | motor 2 enable |

Pins 7 / 14: GND / VCC.

### A.8 U12 and U13 SN754410NE (DIP-16)

| Pin | Name | U12 | U13 |
|---|---|---|---|
| 1 | 1,2EN | `PWM0_EN` (10 k to GND) | `PWM2_EN` (10 k to GND) |
| 2 | 1A | `M0_IN1` | `M2_IN1` |
| 3 | 1Y | `M0_A` -> FDR1 motor | `M2_A` -> FDR3 motor |
| 4, 5, 12, 13 | GND | GND | GND |
| 6 | 2Y | `M0_B` -> FDR1 motor | `M2_B` -> FDR3 motor |
| 7 | 2A | `M0_IN2` | `M2_IN2` |
| 8 | VCC2 | `VM` | `VM` |
| 9 | 3,4EN | `PWM1_EN` (10 k to GND) | GND |
| 10 | 3A | `M1_IN1` | GND |
| 11 | 3Y | `M1_A` -> FDR2 motor | NC |
| 14 | 4Y | `M1_B` -> FDR2 motor | NC |
| 15 | 4A | `M1_IN2` | GND |
| 16 | VCC1 | +5 V | +5 V |

100 nF across each motor terminal pair; 0.1 uF at VCC1 and VCC2.

### A.9 U11 MCP3008 (DIP-16)

| Pin | Name | Net |
|---|---|---|
| 1 | CH0 | `FADER1_W` (1 k series, 100 nF to AGND, 1 M to AGND) |
| 2 | CH1 | `FADER2_W` (same) |
| 3 | CH2 | `FADER3_W` (same) |
| 4 | CH3 | `PEDAL_W` (same) |
| 5, 6, 7, 8 | CH4..CH7 | 100 k to AGND each (or tie to AGND) |
| 9 | DGND | GND |
| 10 | /CS | `ADC_CS_N` |
| 11 | DIN | `ADC_MOSI` |
| 12 | DOUT | `ADC_MISO` |
| 13 | CLK | `ADC_SCK` |
| 14 | AGND | AGND (single-point to GND at U11) |
| 15 | VREF | `VREF_F` |
| 16 | VDD | `VREF_F` |

`VREF_F` = +5 V through 100 ohm, with 10 uF and 0.1 uF to AGND.

### A.10 U6 MAX232 (DIP-16)

Class-board charge-pump circuit (C10-C13, 1 uF) unchanged.

| Pin | Name | Net |
|---|---|---|
| 11 | T1IN | `MIDI_TX` |
| 12 | R1OUT | JP_RX pin 3 |
| 11 | T1IN (also) | `MIDI_TX` is shared with U9.2 and J12.5 |
| 14 | T1OUT | J5 pin 2 (via J4) |
| 13 | R1IN | J5 pin 3 (via J4) |
| 10 | T2IN | +5 V (unused, held idle) |
| 9 | R2OUT | NC |
| 7 | T2OUT | NC |
| 8 | R2IN | NC (internal pull-down) |

### A.11 U8 6N138 (DIP-8)

| Pin | Net |
|---|---|
| 1, 4 | NC |
| 2 | LED anode: from J8 pin 4 via 220 ohm; 1N4148 cathode |
| 3 | LED cathode: J8 pin 5; 1N4148 anode |
| 5 | GND |
| 6 | `MIDI_RX_OPTO` -> JP_RX pin 1; 470 ohm pull-up to +5 V |
| 7 | 10 k to GND (footprint; populate if the edge is slow) |
| 8 | +5 V with 100 nF |

### A.12 U10 24LC256 (DIP-8)

| Pin | Net |
|---|---|
| 1, 2, 3 | A0, A1, A2 = GND |
| 4 | GND |
| 5 | `SDA` |
| 6 | `SCL` |
| 7 | WP: 10 k to +5 V, `JP_WP` to GND |
| 8 | +5 V with 100 nF |

### A.13 LCD header J10 (1x14, Samsung 16x4 / Optrex order)

Net list only: `DB0..DB7` = `AD0..AD7`, `RS` = `LCD_RS`, `R/W` = `LCD_RW`, `E` = `LCD_E`, `VDD` = +5 V, `VSS` = GND, `VEE` (pin 3) = trimmer wiper. Pin order per section 3.6 (Optrex spec); no backlight pins.

### A.14 Daughter-board nets

| Board | Chip | Pin connections |
|---|---|---|
| ESD_Btn | PCF8574N (DIP-16): 1,2,3 = A0,A1,A2 from SW1; 4,5,6,7 = P0-P3 (buttons); 9,10,11,12 = P4-P7 (LEDs); 13 = /INT; 14 = SCL; 15 = SDA; 8 = VSS; 16 = VDD | `INT` -> `BUS_INT_N` |
| ESD_Pot | ADS7828 (TSSOP-16), **pin numbers from the TI datasheet (`VERIFY:`)**: CH0-CH7 = pot wipers via RC; COM = GND; REF = `VREF_P`; A0, A1 = SW1 positions 1, 2; SDA; SCL; GND; +VDD = +5 V | No interrupt output |

---

## Appendix B: Revision history

| Rev | Change |
|---|---|
| 1 | Daughter boards with fader + I2C ADC + address-chain adder + PWM barrel-shift |
| 2 | 3 motor faders moved onto the main board; passive daughters; DIP-switch I2C addresses |
| 3 | Touch firmware-only; USB-MIDI fixed as DIN into iConnectivity mio |
| 4 | Independent of class-board pinout; memory-mapped character LCD |
| 5-6 | NVSRAM removed; graphic LCD with SRAM frame buffer (later dropped) |
| 7 | Navigation buttons through a 74HC244 |
| 8 | Lab 4 16x4 ASCII LCD; SRAM dropped; no external memory |
| 9 | Phased population; three per-fader buttons |
| 10 | Review and clean-up for KiCad hand-off: PWM buffered through spare 74HC125 gates (quasi-bidirectional port fix), LED through U15, Appendix A netlist, brief for the layout agent, `OPEN` list |
| 11 | Review fixes ([Hardware_Map_Review](Hardware_Map_Review.md)): U14 '273 pin numbers fixed; status LED sinks into P1.1; `VDP_WR_n` narrowed to 0xFC00; HCT for U9/U14, 74HC14 for U15; 1 M wiper pull-downs; 6N138 values; WP pull-up. Decisions: 12 V 3 A barrel, P-FET, R-78E5.0; faders board-mounted with motor cutouts; TTL FTDI-style headers J7/J12 and 2x3 `JP_RX`; socketed crystal (16 MHz evaluation, why not X2); 0805 SMD passives; PCF8591P replaced by ADS7828 (8 pots per board, 4 addresses) |
| 12 | LCD: the Lab 4 kit module is a Samsung 16x4 (87 x 60, 14-pin single row, no backlight; photo-measured), the handout names an Optrex DMC-20434 20x4 with the same pinout and SED1278F controller. Pinout, contrast and timing from the Optrex/Epson specs; `JP_BL` and its resistor removed; firmware geometry constants for 16x4 and 20x4 |
