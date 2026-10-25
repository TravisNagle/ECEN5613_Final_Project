# Final project hardware spec: modular Reaper MIDI control surface

| Field | Value |
|---|---|
| File name | `Hardware_Map.md` |
| Course | ECEN 5613 Embedded System Design, Fall 2026, Final Project |
| Team | Nathan Cohen (analog and control), Travis Nagle (MIDI and interface) |
| Document revision | **Rev 13.5, 2026-10-25: KiCad schematic added; SW1 correction (section 3.9).** Rev 13.4, 2026-10-24: power is one 9 V >= 2 A adapter for logic and motors (section 3.9).** Rev 13.3, 2026-10-24: touch sensors are bare AT42QT1010 chips on SOT-23-6 adapters (section 3.5).** Rev 13.2, 2026-10-24: two-level build, panel vs bottom, joined by a 12-pin and a 10-pin ribbon plus a motor cable (section 3.13).** Rev 13.1, 2026-10-24: hardware fader touch sensing (AT42QT1010 per fader, section 3.5). Rev 13, 2026-10-24: the class dev board is the master board; all new circuits are hand-built (perf board / wire-wrap); no custom PCB. Two motor faders on one TB6612 driver.** Folds in the 2026-10-24 perf-board decisions (KB2040 USB-MIDI, TB6612, 74AHC157, kit 24C16, RJ45 bus). Supersedes Rev 1-12 (history in Appendix B; the Rev 12 PCB draft is in the git history at commit `735803c`) |
| Status | **Concept, nothing built.** `VERIFY:` = datasheet check needed before it is trusted. `(MEASURE)` = bench value to fill in. `OPEN` = decision not yet made, see section 9 |
| Builds on | [class BOM](reference/class_board/kicad_schematic/ECEN5613_Dev_Board_BOM.csv), [Lab 3 memory map](reference/class_board/memory_map_and_xram.md), [lab3.pld](reference/class_board/spld/lab3.pld), PDR [F26_PDR_TravisNagle_NathanCohen.pptx](docs/F26_PDR_TravisNagle_NathanCohen.pptx), spec [f26finalproject_8-24-2026.pdf](docs/f26finalproject_8-24-2026.pdf), fader [datasheet](reference/motor_slider_datasheet.pdf), parts and order record [Perfboard_Order_Notes](hardware/Perfboard_Order_Notes.md) |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed/modified by the students. The course requires AI use to be fully documented in the final report. |

---

## 0. Scope at a glance

| | Rev 12 (dropped) | Rev 13 (current) |
|---|---|---|
| Master board | Custom JLCPCB board `ESD_Main` | **Existing class dev board** (AT89C51RC2, '373, ATF16V8B, MAX232, 7805) with wiring changes (section 2) |
| New circuits | On the PCB, 0805 SMD reflow | **Hand-built** in two levels: panel (perf boards hung under the acrylic) and bottom (class board + perf), section 3.13 |
| Faders | 3, board-mounted, 2x SN754410 | **2**, Terwin SM100, **one TB6612FNG breakout** |
| USB-MIDI | DIN-5 + 6N138 + iConnectivity mio | **Adafruit KB2040** USB-MIDI bridge on the UART, through a level shifter |
| PWM buffer | 74HCT125 | **74AHC157** (on hand), forced low during reset |
| Reset inverter for the '273 | 74HC14 | **2N2222** (kit) |
| Presets | 24LC256 | **24C16** (kit) |
| Daughter bus | IDC 2x5 ribbon | **RJ45** breakouts + straight-through patch cables |
| Daughter boards | `ESD_Pot`, `ESD_Btn` PCBs | Hand-built perf boards, same function |
| Power | 12 V 3 A barrel, P-FET, R-78E | **One 9 V >= 2 A adapter** into the class board jack: 7805 for logic, motor rail tapped after the bridge (section 3.9) |

**Schematic deliverable**: the course requires a complete schematic PDF from a schematic capture tool (KiCad 10), with pin numbers and signal names, even without a PCB. It is in [hardware/kicad/ESD_Final/](hardware/kicad/ESD_Final/) (PDF: [ESD_Final_schematic.pdf](hardware/kicad/ESD_Final/ESD_Final_schematic.pdf)), generated from [hardware/kicad/tools/design.py](hardware/kicad/tools/design.py): a root sheet with the boards and cables, then one sheet per board (class board x3, D-pad board, fader button board, Panel Mounted, button daughter board). Every component has a `Phase` and a `Board` field; net names are the ones in this document. Schematic refs that differ from this document: D-pad ends of the panel cables J30/J31 (J20/J21 here are the class ends), J32/J40 = J23, U9 drawn with the pin-compatible 74LS157 symbol, U10 with the 24LC16 symbol.

---

## 1. Architecture

The **class board** keeps the AT89C51RC2 at 11.0592 MHz, its 74LS373 latch and ATF16V8B decoder. The external bus is used **only for memory-mapped I/O** (no external memory; the NVSRAM goes back to the course). Main-side circuits add **two motorized faders**, the **Lab 4 16x4 character LCD**, **eight panel button inputs** (five navigation, one per fader, one spare), an expression pedal input, a preset EEPROM and the **KB2040 USB-MIDI bridge** to Reaper. **Daughter boards** (pot board, button board) hang on an I2C bus over RJ45 cables, in any order; each has a DIP switch for its I2C address and the master finds them by scanning.

```
  CLASS BOARD (master, existing)                  |  MAIN-SIDE CIRCUITS (panel / bottom split: section 3.13)
                                                  |
  J1 9 V jack -> SW1 -> D1-D4 -> U2 7805 -> +5 V =====> +5 V / GND: logic, LCD, daughters
                                                  |    VM motor rail: bridge output via PTC, TVS, 470 uF (3.9)
  +-----------+ AD0-7  +------+ Q0,Q1 (A0,A1) ------> LCD RS, R/W     +-------------------+
  | U1        |------->| U3   |                   |    LCD_E -------->| LCD1 16x4 HD44780 |
  | AT89C51   |        | '373 |                   |    AD0-7 -------->| 14-pin, no b/light|
  |   RC2     |        +------+                   |                   +-------------------+
  | 11.0592   | A15-A10, /RD, /WR                 |
  |   MHz     |------->+---------+ MOTDIR_CLK -------> U14 '273 latch --> AIN1/2, BIN1/2, STBY --+
  |           |        | U7      | BTN_OE_n ---------> U16 '244 <-- 8 button inputs              |
  |           |        | ATF16V8B| LCD_E              (AD0-7 when read at 0xF800)               |
  |           |        +---------+                    Q2 2N2222: RST -> RST_N (U14 /MR)        v
  | P1.3 CEX0 |--- PWM0 ---> U9 74AHC157 (/G = RST) --- PWM0_EN ---> +----------------+         
  | P1.4 CEX1 |--- PWM1 --->                        --- PWM1_EN ---> | A1 TB6612FNG   |-> FDR1 motor
  |           |                                   |                  | breakout       |-> FDR2 motor
  | P1.2 CS   |                                   |                  +----------------+
  | P1.6 SCK  |---- bit-banged SPI -----------------> U11 MCP3008: CH0 FDR1, CH1 FDR2, CH3 pedal (J13)
  | P1.7 MOSI |                                   |
  | P3.3 MISO |<------------------------------------
  |           |                                   |
  | P3.1 TXD  |--+--> U6 MAX232 T1 -> J4/J5 DB9 (PC, FLIP; existing)
  |           |  +-----------------------------------> A3 level shifter (5 V <-> 3.3 V) --> A2 KB2040 --USB--> PC: Reaper
  | P3.0 RXD  |<-- JP_RX: KB2040 TX (via A3) / MAX232 R1OUT      |                             (MCU control surface)
  | P1.0 DBG  |-----------------------------------> J7 TTL debug (course USB-TTL converter)
  | P1.1 LED  |--> class board R7/Q1/D8 status LED (existing)
  | P3.4 SDA  |<=====================================> U10 24C16 EEPROM @0x50-0x57 (presets)
  | P3.5 SCL  |                                   |   J11 RJ45 bus jack (+5 V via JP_BUS, SDA, SCL, INT_N)
  | P3.2 INT0 |<-- BUS_INT_N (class SW4 also pulls it low; harmless)
  +-----------+                                   |       |
                                                          v  RJ45 patch cables, any order
        +--- POT BOARD (perf, DIP addr n) ---+   +--- BUTTON BOARD (perf, DIP addr n) ---+
        | RJ45 in -> RJ45 out in parallel    |-->| RJ45 in -> RJ45 out in parallel       |--> ...
        | I2C ADC (part OPEN #3), 8 pots     |   | PCF8574 @ 0x20+n, 4 buttons + 4 LEDs  |
        +------------------------------------+   +---------------------------------------+
```

### 1.1 Decisions already made

| Topic | Decision | Why |
|---|---|---|
| Master board | The class dev board, modified by wiring only (section 2) | Per team, 2026-10-24; no PCB order or lead time |
| New hardware | Hand-built on perf boards / wire-wrap | Per team |
| USB-MIDI | KB2040 (RP2040, native USB) as a class-compliant USB-MIDI bridge on the 8051 UART; replaces the mio, DIN jacks and 6N138 | The 8051 has no USB. Ask the TA that a dev board doing only the USB link is acceptable |
| MIDI input scope | Reaper feedback only (no keyboard merge) | One UART |
| External memory | None. Class NVSRAM `U4` removed and returned (course requirement) | LCD keeps its own RAM |
| Presets | 24C16 I2C EEPROM (kit), 0x50-0x57 | Non-volatile, DIP-8, already owned |
| Bus kept for I/O | Class '373 + ATF16V8B | LCD, direction latch and buttons cost no port pins |
| Fader ADC | MCP3008 (10-bit SPI), bit-banged | Keeps fader reads off I2C |
| Motors | **2 faders**, PCA PWM CEX0-1, **one TB6612FNG breakout**, memory-mapped direction latch | Per team: one driver for both motors |
| Touch sensing | **Hardware**: one AT42QT1010 capacitive touch sensor per fader, electrode = the fader's T pin (connected to the metal knob/lever, measured < 10 ohm). `TOUCH1` -> U16 D7 (0xF800), `TOUCH2` -> P1.5 | Per team, 2026-10-24; firmware-only touch inference false-triggers |
| Display | Lab 4 kit Samsung 16x4 character LCD, HD44780-compatible, 14 pins, no backlight | Lab 4 kit part |
| Panel buttons | 5 navigation + 2 per-fader on one 74HCT244; its eighth input carries `TOUCH1` | Works if I2C is hung |
| Daughter boards | Passive pot and button boards; DIP-switch I2C addresses; auto-detect by ACK | Per team |
| Daughter bus | RJ45 breakouts and Cat 5e patch cables (section 3.10) | Decided 2026-10-24 |
| Build split | Two levels: **panel** (acrylic + D-pad board + fader strip: buttons, '244, MCP3008, touch sensors, LCD, faders) and **bottom** (class board + perf: everything else). Joined by J20 (12-pin bus), J21 (10-pin I/O) and J22 (motor) | Per team, 2026-10-24: fewest level-to-level wires; two cables are easy to unplug and leave spares (section 3.13) |
| Crystal | Class board 11.0592 MHz, X1 mode | All Lab 1-4 code; X2 breaks LCD timing (section 3.12) |

### 1.2 Feasibility results that constrain the hardware

| Question | Result |
|---|---|
| 8051 pins | 14 spare (P1.0-P1.7, P3.0-P3.5). **All 14 used** (P1.5 = `TOUCH2`, section 3.2) |
| 31,250 baud | Timer 2 baud generator, 11.0592e6 / (32 x 11) = 31,418 baud, +0.54 % error. Timer 1 cannot (28,800/n) |
| PWM | 2 PCA channels, 8-bit, 10.8 kHz at fosc/4 |
| I2C | Bit-banged, about 60-75 kHz at 12 clk/cycle (MEASURE). Traffic is slow human input only |
| Fader loop | MCP3008 bit-banged about 0.2 ms per channel (MEASURE); 2 faders allow a 500 Hz+ loop |
| X2 mode | **Do not use for LCD traffic.** It halves bus pulses to about 170 ns, below the HD44780 E-pulse minimum (about 230 ns). X1 gives about 440 ns |
| Memory | 256 B IRAM + 1 KB on-chip XRAM (`AUXR = 0x0C`); LCD shadow copy is 64 B (80 B for a 20x4) |

---

## 2. Class board changes (master)

Reference: [`ECEN5613_Dev_Board.kicad_sch`](reference/class_board/kicad_schematic/ECEN5613_Dev_Board.kicad_sch) and its [BOM](reference/class_board/kicad_schematic/ECEN5613_Dev_Board_BOM.csv). Do not edit the files in `reference/`; record the changes in the new schematic.

| Class circuit | Refs | Change |
|---|---|---|
| Power: jack, bridge, 7805, power LED, switch | J1, D1-D4, U2, C1, C2, D5, D6, R1, SW1 | Keep. Replace the course's 9 V / 500 mA adapter with a **9 V >= 2 A** one; tap `VM` at the bridge output (C1 node, before SW1) and add the A1 ground return to the same point (section 3.9) |
| 8051, crystal, reset | U1, Y1, C3-C6, R2, R3, D7, SW2 | Keep. Tap `RST` (U1.9) for Q2 and U9 |
| `/PSEN` bootloader button, `/EA` jumper | R6, SW3, J14 | Keep (J14 jumper to +5 V = internal flash) |
| MAX232 + DB9 | U6, C10-C13, J4, J5 | Keep for FLIP and the PC terminal. **Lift the R1OUT (U6.12) -> RXD wire** and route both through `JP_RX` (section 3.8) |
| P0 pull-ups | R4 (10 k SIP-10) | Keep |
| 74LS373 | U3 | Keep. Q0 (pin 2) = `LCD_RS`, Q1 (pin 5) = `LCD_RW` |
| ATF16V8B | U7 | Reprogram with `spld/final.pld` (section 3.3); wire-wrap new pins 9, 11, 12, 14, 15. Keep the Lab 3 `.jed` |
| NVSRAM | U4 | **Remove and return.** Pins 17, 18 of U7 become unused |
| Status LED | R7, Q1, D8 on P1.1 | Keep as `LED_N` (lit when P1.1 = 0) |
| `/INT0` button | SW4, C15 | Keep or remove; it shares `BUS_INT_N` (pulls it low like a daughter interrupt) |
| Current-measurement jumper | J6 | Keep |

**Pin access**: confirm wire-wrap access to U1 P1, P3, RST and P0 (AD0-AD7 at U3's D inputs or R4), U3 Q0/Q1, and U7. If U1's socket has no wire-wrap tails, plug a DIP-40 extender under the chip. Common ground between the class board, every perf board and the motor supply, joined at one point (section 3.9).

---

## 3. Main-side circuits

Which level each part is built on, and the cables between levels, are in section 3.13.

### 3.1 Parts

| Ref | Part | Package | Function | Phase |
|---|---|---|---|---|
| U9 | SN74AHC157N (on hand) | DIP-16 | PWM buffers, outputs forced low while `RST` is high | P1 |
| U10 | 24C16 (kit) | DIP-8 | Preset EEPROM | P2 |
| U11 | MCP3008-I/P | DIP-16 | Fader and pedal ADC | P1 |
| U14 | CD74HCT273E | DIP-20 | Motor direction latch with `/MR` (HCT: CP comes from the ATF16V8B, VOH min 2.4 V) | P1 |
| U16 | SN74HCT244N | DIP-20 | Reads the 8 button inputs onto AD0-AD7 | P1 |
| Q2 | 2N2222 (kit) | TO-92 | `RST` -> `RST_N` inverter for U14 `/MR` | P1 |
| A1 | TB6612FNG breakout (on hand) | module | H-bridge for both motors | P1 |
| A2 | Adafruit KB2040 (on hand) | module | USB-MIDI bridge | P1 |
| A3 | SparkFun bidirectional logic level converter (BSS138, on hand) | module | 5 V <-> 3.3 V for the KB2040 UART | P1 |
| LCD1 | Samsung 16x4 LCD (Lab 4 kit) | 14-pin single row, kit socket strip | Display | P1 |
| FDR1, FDR2 | Terwin SM100 motor fader | wired | Faders (FDR2 in P2) | P1 / P2 |
| A4, A5 | Microchip AT42QT1010-TSHR touch sensor IC on a SOT-23-6 to DIP adapter (on hand), with its Cs, Rs, bypass and filter parts on the fader strip | SOT-23-6 on adapter | Fader 1 / fader 2 touch | P1 / P2 |

All DIP ICs go in sockets (kit wire-wrap sockets or spares). Spares to keep on hand: ATF16V8B (NRND), MCP3008, '273, '244 (the order includes one spare of each). The kit 74LS374 is a fallback for U14 with weaker reset behavior ([Perfboard_Order_Notes](hardware/Perfboard_Order_Notes.md) section 2).

### 3.2 8051 pin map

| DIP pin | Port | Alt | Net | Connects to |
|---|---|---|---|---|
| 1 | P1.0 | T2 | `DBG_TX` | J7 pin 5 (TTL debug header, section 3.8) |
| 2 | P1.1 | T2EX | `LED_N` | class board R7 -> Q1 base (existing status LED, lit when 0) |
| 3 | P1.2 | ECI | `ADC_CS_N` | U11.10 |
| 4 | P1.3 | CEX0 | `PWM0` | U9.2 (1A) |
| 5 | P1.4 | CEX1 | `PWM1` | U9.5 (2A) |
| 6 | P1.5 | CEX2 | `TOUCH2` | A5 OUT (fader 2 touch, high = touched); plain input, latch written 1. Was `PWM2` in Rev 12 |
| 7 | P1.6 | CEX3 | `ADC_SCK` | U11.13 |
| 8 | P1.7 | CEX4 | `ADC_MOSI` | U11.11 |
| 9 | RST | | `RST` | class reset circuit; Q2 base via 10 k; U9.15 (/G) |
| 10 | P3.0 | RXD | `MIDI_RX` | `JP_RX` pin 2 |
| 11 | P3.1 | TXD | `MIDI_TX` | U6.11 (existing), A3 HV1 |
| 12 | P3.2 | /INT0 | `BUS_INT_N` | J11 pin 7, 10 k pull-up to +5 V; class SW4 |
| 13 | P3.3 | /INT1 | `ADC_MISO` | U11.12 (plain GPIO input) |
| 14 | P3.4 | T0 | `SDA` | J11 pin 3, U10.5, 5.1 k pull-up |
| 15 | P3.5 | T1 | `SCL` | J11 pin 1, U10.6, 5.1 k pull-up |
| 16 | P3.6 | /WR | `WR` | U7.8 (existing) |
| 17 | P3.7 | /RD | `RD` | U7.6 (existing) |
| 18, 19 | | XTAL2, XTAL1 | | class Y1, C5, C6 |
| 20 | | GND | | |
| 21, 22 | P2.0, P2.1 | A8, A9 | | unused |
| 23 | P2.2 | A10 | `A10` | U7.11 (new wire) |
| 24 | P2.3 | A11 | `A11` | U7.9 (new wire) |
| 25-28 | P2.4-P2.7 | A12-A15 | `A12`-`A15` | U7.2-U7.5 (existing) |
| 29 | | /PSEN | `PSEN_N` | class R6/SW3 (bootloader); U7.7 (existing, unused by `final.pld`) |
| 30 | | ALE | `ALE` | U3.11 (existing) |
| 31 | | /EA | `EA_N` | class J14 |
| 39..32 | P0.0..P0.7 | AD0..AD7 | `AD0`..`AD7` | U3 D (existing), R4, U14 D, U16 Y, LCD DB0-7 |
| 40 | | VCC | | +5 V |

Port notes for firmware and wiring:
- **8051 ports are quasi-bidirectional**: a high is only a weak pull-up (guaranteed VOH 2.4 V). Never hang a resistive load to ground directly on a port pin; sinking from +5 V is fine (about 10 mA per pin). That is why PWM goes through U9 and the KB2040 link through A3.
- Timer 2 runs as the UART baud generator, so `EXEN2` must stay 0 (P1.1 is a plain output). Timer 0/1 pins P3.4/P3.5 are plain GPIO (`C/T = 0`).
- Do not disable ALE (`AUXR.0`): U3 needs it for the LCD RS and R/W.

### 3.3 Memory-mapped I/O and SPLD

New file `spld/final.pld` derived from [`lab3.pld`](reference/class_board/spld/lab3.pld); leave the reference copy untouched. Inputs: `A15-A12` (pins 2-5, existing), `RD` (6), `PSEN` (7, existing wire, unused), `WR` (8), `A11` (9, new), `A10` (11, new). Outputs:

```
pin 15 = MOTDIR_CLK;   /* -> U14 CLK, rising edge latches at end of /WR          */
pin 14 = LCD_E;        /* -> LCD E, ACTIVE HIGH during a read or write            */
pin 12 = BTN_OE_n;     /* -> U16 /1OE and /2OE                                    */
pin 16 = VDP_WR_n;     /* optional logic-analyzer trigger, test point only        */

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
| 0xF800-0xFBFF | U16 button buffer | read |
| 0xFC00-0xFFFF (use 0xFFFF) | Virtual debug port (trigger only; A9-A0 do not reach the SPLD, so the whole 1 KB block aliases) | write |
| other | Nothing responds (U4 removed) | |

`MOTDIR_CLK` idles high and rises when `/WR` rises, so data is captured with the 8051's write hold time (about 40 ns). `LCD_E` falls one SPLD delay (tPD <= 15 ns) after `/WR` rises, leaving about 25 ns of data hold at the LCD (HD44780 needs about 10 ns, `VERIFY:`). The old `NVRAM_CS_n`/`NVRAM_OE_n` (pins 17, 18) and `CSPERIPH` (19) are dropped; leave those pins open. `VERIFY:` G16V8 simple-mode pin capabilities for pins 12-16, then compile/simulate in WinCUPL and keep the `.jed`.

### 3.4 Connection tables

See **Appendix A** (every IC and module, pin by pin). It is the authoritative netlist for wiring and for the schematic.

### 3.5 Motor fader channels (x2)

- **Fader**: Terwin SM100 ([datasheet](reference/motor_slider_datasheet.pdf)): 100 mm travel, 10 k linear, residual <= 500 ohm (calibrate min/max in firmware), motor rated **10 V DC**, pot pins 1-2-3 (servo track), touch-sense pin T, motor pins A/B. `VERIFY:` which pot pin is the wiper (the drawing suggests pin 2) with an ohmmeter. Motor current is **not** in the datasheet; the PDR design doc gave about 800 mA starting current for a similar part: **(MEASURE)** stall/start current on the bench.
- **Per channel**: U9 output -> TB6612 `PWMx`; latch outputs -> `xIN1/xIN2`; `xO1/xO2` -> motor A/B with 100 nF across the motor pins; fader wiper -> RC (1 k series, 100 nF to AGND, **1 M** to AGND so an unconnected input does not float) -> MCP3008 channel; track ends to `VREF_F` and AGND; touch pin T -> test point `TOUCHn`.
- **TB6612 logic** (`VERIFY:` against the Toshiba datasheet and the breakout's schematic): `IN1/IN2` = 10 or 01 with `PWM` high drives; `PWM` low = short brake; `IN1 = IN2 = 0` = stop (outputs off, coast); `IN1 = IN2 = 1` = short brake; `STBY` low = everything off. Between direction changes write `11` (brake), then the new direction.
- **Safe state at reset**: three independent locks. U9 `/G` = `RST`, so both `PWMx_EN` are forced low; Q2 holds U14 `/MR` low, so all latch outputs (including `STBY` on Q6) are 0; `STBY` also has a 10 k pull-down. Firmware writes the latch and starts PWM only after init.
- **Motor voltage**: TB6612 `VM` 4.5-13.5 V, about 0.5 V drop. From the 9 V adapter `VM` is about 7.6 V, so the motor sees about 7.1 V, inside its 10 V rating: no PWM cap. With the 12 V upgrade (section 3.9) the motor sees about 10 V; cap PWM at about 95 %.
- **Filtering**: `VREF_F` = +5 V through 100 ohm, 10 uF + 0.1 uF to AGND; MCP3008 `VREF` and `VDD` from it; AGND joins GND at one point near U11.
- **Motor supply** `VM`: see section 3.9. 470 uF bulk near A1, 0.1 uF at A1 `VM`, PTC fuse and TVS at the supply entry.
- **Touch (hardware)**: the SM100's T pin connects to the metal lever and knob (bench check 2026-10-24: under 10 ohm), so the T pin itself is the electrode. Each fader gets a bare AT42QT1010 (A4 for FDR1, A5 for FDR2) on the fader strip, close to the fader's T pin. Values from the Microchip AT42QT1010 datasheet (DS40001946A):
  - SOT-23-6 pins: 1 `OUT`, 2 `VSS`, 3 `SNSK`, 4 `SNS`, 5 `VDD`, 6 `SYNC/MODE`.
  - `VDD` = +5 V through a small RC filter (100 ohm, then 10 uF + 100 nF to GND at the chip): the chip wants supply ripple within +-20 mV and the panel's +5 V comes over J21. The 100 nF must sit right at pins 5 and 2.
  - `SNSK` (pin 3) -> Rs (series resistor for ESD/EMC, start at 4.7 k) -> fader T pin (`FDRn_T`). Sample capacitor **Cs between `SNS` (pin 4) and `SNSK` (pin 3)**: 2-50 nF, a stable X7R (5 %) or PPS film type; start at 10 nF and tune (larger = more sensitive, slower). Keep Cs and Rs at the chip and the T wire short and away from GND and other wires: the load the chip can drive (Cx) is 2-50 pF, and the lever, track and wire all add to it.
  - `SYNC/MODE` (pin 6) -> **GND (low-power mode)**. The maximum on-duration (about 60 s, after which a held touch reads released and the chip recalibrates) is quoted for low-power mode and counts measurement bursts. In fast mode (pin 6 high) bursts are about 20 times more frequent, so a held fader would drop out after a few seconds (estimate). Low-power mode still answers within about 100 ms. `VERIFY:` the hold time on the bench.
  - `OUT` (pin 1) = `TOUCH1` / `TOUCH2`: push-pull, **high while touched**, 2 mA. `TOUCH1` -> U16 2A4 (D7 at 0xF800, so it reads 1 when touched, the opposite of the buttons); `TOUCH2` -> P1.5 (write 1 to the P1.5 latch so the pin is an input).
  - **HeartBeat**: before every burst `OUT` floats for about 15 us. With a pull-up that shows as a false "touched" pulse, so `TOUCH1` has **no** pull-up, and each `OUT` gets **10 nF to GND** to filter the pulse (P1.5's weak internal pull-up cannot charge it in 15 us). Firmware also requires 2-3 matching reads before changing touch state.
  - Power-up: the chip self-calibrates for about 100 ms after power-on (ignore `OUT`, and keep hands off the knobs).
  - Keep each T wire short and away from the motor wires; motor PWM can couple into the electrode. If touch chatters while the motor runs, firmware can ignore touch changes during motor drive, or Cs can be reduced.
- **Expression pedal** (MCP3008 CH3, P2): 1/4" TRS jack `J13` (part `VERIFY:`, not in the order). Brands disagree on the wiring, so tip and ring each go to a 3-pin header with a jumper (`JP_TIP`, `JP_RING`) selecting wiper or reference. Default: tip -> wiper (via the same RC), ring -> `VREF_F` **through 100 ohm** (a short while plugging in cannot pull down the fader reference), sleeve -> AGND.

### 3.6 LCD: Samsung 16x4 (Lab 4 kit module)

The Lab 4 handout names an **Optrex DMC-20434** (20x4, Epson SED1278F controller); the kit module in hand (photo, 2026-10-20) is a **Samsung 16x4** (SMC1640A family), about 87 x 60 mm, mounting holes 82 x 55 mm, a **single row of 14 pins**, **no backlight**. Both are HD44780-compatible with the same 14-pin order. `VERIFY:` count the characters per line at power-up (16 or 20) and set the firmware constant. Electrical and timing data are from the Optrex spec (No.99-0259) and the Epson SED1278 manual, used as the conservative reference. Mate it with the kit's 14-contact socket strip.

| Pin | Signal | Net |
|---|---|---|
| 1 | VSS | GND |
| 2 | VCC | +5 V |
| 3 | VEE (LCD drive) | `LCD_V0`, contrast trimmer wiper between +5 V and GND (10-20 k; the one on hand is 20 k, marked 203) |
| 4 | RS | `LCD_RS` (U3.2, latched `A0`) |
| 5 | R/W | `LCD_RW` (U3.5, latched `A1`) |
| 6 | E | `LCD_E` (U7.14) |
| 7-14 | DB0-DB7 | `AD0`-`AD7` |

- Supply 4.5-5.5 V, ICC about 2.2 mA typical. Contrast: VCC - VEE = 4.3 V typical at 25 C, so VEE is about 0.7 V; a 0-5 V pot is fine.
- **Timing (Optrex spec, VDD 5 V)**: E high >= 230 ns, E cycle >= 500 ns, tAS 40 ns, tAH 10 ns, tDSW 80 ns, tH 10 ns, tDDR <= 160 ns, tDHR >= 5 ns. The 8051 at X1, 11.0592 MHz, gives E high about 440 ns: passes. X2 (about 170 ns) fails.
- **Firmware facts**: keep the geometry in one constant. 16x4: 16 columns, a **64-byte** shadow copy, DDRAM line starts 0x00, 0x40, 0x10, 0x50 (Set-DDRAM 0x80, 0xC0, 0x90, 0xD0). 20x4: 20 columns, 80 bytes, line starts 0x00, 0x40, 0x14, 0x54 (0x80, 0xC0, 0x94, 0xD4). Row 0 = title/transient message, rows 1-2 = one line per fader, row 3 = status; 8 custom CGRAM characters for bars. Power-on: wait >= 30 ms, then the 0x30 / 4.1 ms / 100 us / 40 us init sequence; clear display takes up to about 1.64 ms.

### 3.7 Panel buttons

Seven 6 mm tactile switches (spares on hand) plus one spare input. Each switch goes from its net to GND; each net has a discrete **10 k** pull-up to +5 V and an optional 10 nF to GND.

| U16 bit | Net | Switch | Placement |
|---|---|---|---|
| D0 | `BTN_CENTER` | D-pad center | below the LCD |
| D1 | `BTN_UP` | D-pad up | below the LCD |
| D2 | `BTN_DOWN` | D-pad down | below the LCD |
| D3 | `BTN_LEFT` | D-pad left | below the LCD |
| D4 | `BTN_RIGHT` | D-pad right | below the LCD |
| D5 | `BTN_F1` | fader 1 | next to fader 1 |
| D6 | `BTN_F2` | fader 2 | next to fader 2 |
| D7 | `TOUCH1` | none: A4 OUT (fader 1 touch, **1 = touched**) | was `BTN_F3` in Rev 12; **no pull-up** (HeartBeat pulses), 10 nF to GND instead (section 3.5) |

A bit reads 0 when pressed. U16 is read at 0xF800; `/1OE` and `/2OE` are tied together to `BTN_OE_n`. Firmware polls at about 100 Hz with a 20 ms debounce.

### 3.8 USB-MIDI (KB2040), serial and indicators

- **KB2040 bridge (A2)**: plugs into the PC by USB-C and enumerates as a class-compliant USB-MIDI device; firmware (CircuitPython `usb_midi` + `busio.UART`) forwards bytes between USB and its UART. It is powered from USB; its 5 V / 3.3 V pins are **not** joined to the board rails. **KB2040 pins are 3.3 V and not 5 V tolerant.**
- **Level shifter (A3, SparkFun BSS138)**: `HV` = board +5 V, `LV` = KB2040 3V3 pin (reference only), GND common. Channel 1: HV1 <- `MIDI_TX` (P3.1), LV1 -> KB2040 RX (D1). Channel 2: LV2 <- KB2040 TX (D0), HV2 -> `JP_RX` pin 1 (`KB_TX_5V`). Its 10 k pull-ups also strengthen the 8051's weak port high. Fine at 31,250 and 115,200 baud. (The on-hand TXB0104 is **not** suitable: it needs strong push-pull drivers. A 1 k / 2.2 k divider on TX is the fallback for channel 1 only.)
- **Link baud and framing**: real MIDI at 31,250 baud (CircuitPython parses the stream) or 115,200 baud with 4-byte USB-MIDI packets from the 8051: `OPEN` #4. Pick one before writing firmware.
- **RXD select `JP_RX`** (1x3 header, one jumper): pin 1 = `KB_TX_5V` (A3 HV2), pin 2 = `MIDI_RX` (P3.0), pin 3 = MAX232 R1OUT (U6.12). Jumper 1-2 = MIDI (KB2040), 2-3 = PC / FLIP. Label "KB / 8051 RX / PC".
- **TXD fan-out**: `MIDI_TX` drives both U6 T1IN (existing) and A3, so the PC terminal shows the MIDI traffic; harmless.
- **PC serial** (class J4/J5 DB9 + course USB-RS232 adapter): FLIP bootloading with `JP_RX` in the PC position and SW3 held through reset; also the 115,200-baud Hairless MIDI fallback (README).
- **Debug header `J7`** (1x6, FTDI TTL-232R order): pin 1 GND, pin 5 (cable RXD) = `DBG_TX` (P1.0), others NC. Used with the course USB-TTL converter for the Timer 0 soft-UART debug output. `VERIFY:` the converter's RX tolerates 5 V logic.
- **Status LED**: class board D8 via Q1 on P1.1 (`LED_N`). **Power LED**: class board D6.

### 3.9 Power: one 9 V adapter for logic and motors (decided 2026-10-24)

One **9 V DC, 2 A or more** adapter (2.5-3 A preferred, 2.1 mm plug, either polarity) into the class board jack J1 replaces the course's 9 V / 500 mA adapter and feeds both the logic and the motors.

```
J1 9 V >= 2 A --> SW1 --> D1-D4 bridge --+--> U2 7805 --> +5 V (logic)
                  (1N4003)       |
                                 +--> JP_VM --> PTC F1 --> VM: TVS P6KE15A, 470 uF --> A1 TB6612 VM
board GND (bridge "-" output) ---+------------------------------------------------> A1 GND (star point)
```

| Item | Spec |
|---|---|
| Tap point | `VM` comes from the **bridge "+" output** (`VRECT`, the 7805 input node at C1), not from the jack. Board GND is the bridge "-" output, one diode drop above the adapter's negative pin, so tapping after the bridge keeps a single ground for the TB6612's logic inputs and still accepts either adapter polarity. **SW1 sits before the bridge** (J1 -> SW1 -> D1-D4, per the class board netlist), so it switches the motors too and now carries motor current: `VERIFY:` its rating (>= 2 A) or replace it with a toggle switch rated >= 3 A |
| `VM` voltage | About 9 - 1.4 = **7.6 V**; the motor sees about 7.1 V after the TB6612 (about 0.5 V drop). Inside the motor's 10 V rating, so **no PWM cap** is needed; the faders move somewhat slower than at 10 V (MEASURE travel time) |
| Bridge diodes | D1-D4 (1N4003) now carry motor current too: 1 A continuous, about 30 A surge. Two motors start at about 1.6 A (MEASURE), but only for the fraction of a second a fader moves, so the average stays well under 1 A. Firmware keeps the stall timeout and staggers motor starts. `VERIFY:` diode temperature after a 30-minute run; if they get hot, replace D1-D4 with 3 A diodes (for example 1N5404; check that the thicker leads fit the class board holes) |
| Protection on `VM` | `JP_VM` jumper to isolate, PTC F1 (RHEF200 2 A hold or RHEF300 3 A, both on the order), TVS P6KE15A (12.8 V standoff), 470 uF bulk at A1, 0.1 uF at A1 `VM` |
| +5 V budget (MEASURE) | Class board about 100-150 mA; added logic, MCP3008 and touch sensors about 30 mA; LCD about 3 mA; TB6612 logic a few mA; daughters about 50 mA plus up to 40 mA of LEDs per button board. Total roughly 250-350 mA. 7805 dissipation about (9 - 1.4 - 5) x 0.35 A = 0.9 W: use the kit heat sink |
| Grounds | A1's GND wires straight to the bridge "-" output at C1 (the star point) on its own heavy wire; motor current never runs through class-board logic traces or under U11 / the AGND area |
| Bus isolation | `JP_BUS` in the +5 V line to J11 |
| Decoupling | 0.1 uF at every IC, 10 uF near U11 |

**Upgrade path without rewiring:** a **12 V >= 2 A** adapter in the same jack gives `VM` about 10.6 V and about 10 V at the motor (its rating, full speed). Then the 7805 dissipates about 1.7 W (heat sink required) and firmware should cap PWM at about 95 % for margin. TB6612 (13.5 V max), the TVS, the PTC and the 25 V caps all suit 12 V.

**Rejected:** a separate 12 V motor supply (two plugs); the USB-PD module (not every charger offers 12 V); tapping before the bridge (motor current would still return through a bridge diode, and logic GND would sit a diode drop away from motor GND).

### 3.10 I2C and the RJ45 daughter bus

- Pull-ups on the master side only: **5.1 k** (kit) on `SDA`, `SCL`; **10 k** on `BUS_INT_N`.
- **U10 24C16** (kit): 2 KB, 16-byte pages, **1-byte word address**; the chip answers at **0x50-0x57** (A0-A2 pins are ignored; the block number goes in the device address). Tie pins 1-3 to GND and `WP` (pin 7) to GND; 100 nF.
- **J11**: one RJ45 breakout on the master side (P2, unplugged until P3); two per daughter (bus in and bus out, wired pin-for-pin in parallel). Standard straight-through patch cables. Each signal shares a twisted pair with a ground:

| RJ45 pin | Signal | T568B pair |
|---|---|---|
| 1 | `SCL` | orange |
| 2 | GND | orange |
| 3 | `SDA` | green |
| 6 | GND | green |
| 4 | +5 V (through `JP_BUS` on the master side) | blue |
| 5 | GND | blue |
| 7 | `BUS_INT_N` | brown |
| 8 | GND | brown |

- **Label every jack "I2C - NOT ETHERNET".** A PoE cable can carry about 48 V.
- Keep the whole chain short (a few metres at most) at 100 kHz; Cat 5e is about 50 pF/m. Not hot-plug safe. Bus recovery: 9 SCL clocks then STOP.
- `VERIFY:` with a continuity tester that each patch cable is straight-through (pin 1 to pin 1).
- Sourcing: 5 RJ45 breakout boards ordered 2026-10-24 (1 master + 2 per daughter; the last board in the chain does not need its bus-out jack, so one is a spare). Cat 5e on hand.

### 3.11 Connectors, jumpers, test points

| Ref | Item |
|---|---|
| J7 | TTL debug header 1x6, FTDI order (section 3.8) |
| J10 | LCD connection, kit 14-contact socket strip |
| J11 | RJ45 bus breakout (section 3.10) |
| J13 | TRS expression pedal jack (P2), wired to the D-pad board (MCP3008 CH3) |
| J20 | Panel bus cable, 2x6 shrouded keyed IDC, 12-pin (section 3.13) |
| J21 | Panel I/O cable, 2x5 shrouded keyed IDC, 10-pin (section 3.13) |
| J22 | Motor cable, 4-pin (two twisted pairs) (section 3.13) |
| J23 | Fader strip to D-pad board jumper, 6-pin, panel level only (section 3.13) |
| FDR1, FDR2 | Fader pot (3 pins), touch (T, to A4/A5) and motor (A, B) wiring |
| JP_RX (1x3), JP_VM, JP_BUS, JP_TIP, JP_RING | Jumpers as above |
| TP | `LCD_E`, `MOTDIR_CLK`, `BTN_OE_N`, `VDP_WR_N`, `ADC_CS_N`, `ADC_SCK`, `ADC_MOSI`, `ADC_MISO`, `SDA`, `SCL`, `BUS_INT_N`, `PWM0`, `PWM1`, `PWM0_EN`, `PWM1_EN`, `MIDI_TX`, `MIDI_RX`, `RST`, `RST_N`, `TOUCH1`, `TOUCH2`, `FDR1_T`, `FDR2_T`, `VM`, +5 V, GND x2 |

### 3.12 Crystal and clock

The class board's 11.0592 MHz crystal stays; all Lab 1-4 code uses it.

| | 11.0592 MHz (current) | 16 MHz (only if Y1 can be swapped) |
|---|---|---|
| MIDI 31,250 baud, Timer 2 | reload 11, +0.54 % error (MIDI allows about 1 %) | reload 16, exact |
| PC baud, Timer 2 | 115,200 exact | 38,400 and below; 115,200 not usable |
| PCA 8-bit PWM at fosc/4 | 10.8 kHz | 15.6 kHz (quieter, still audible) |
| /RD, /WR pulse = LCD E high (6 TCLCL - 100 ns) | about 440 ns | about 275 ns (minimum 230 ns: passes) |

**Why not X2 mode**: X2 halves every bus strobe as well as the peripheral clocks, so the LCD E pulse would drop to about 170 ns, below the HD44780 minimum. The main PWM-noise fix is in firmware: drive a motor only while its fader is moving, and set PWM to 0 at the target.

### 3.13 Physical build: two levels and the cables between them

The build has two levels. Parts that serve the panel's own controls go on the panel, so only the bus, the ADC link and the motor leads cross between levels. Each level-to-level connection unplugs, for taking the panel off.

| Level | Board | Parts |
|---|---|---|
| **Panel** (acrylic and what hangs under it) | Acrylic | FDR1, FDR2, LCD1 and its contrast pot ([hardware/panel/](hardware/panel/)) |
| | **D-pad board** (7 x 9 cm perf, 0.4 in standoffs) | 5 D-pad switches, **U16 74HCT244** + the 8 button/touch pull-ups, **U11 MCP3008** + `VREF_F` filter and the wiper RC networks, J13 pedal wiring, J20, J21, J23 |
| | **Fader strip** (2 x 8 cm perf, 0.6 in standoffs) | `BTN_F1`, `BTN_F2` switches, **A4, A5 touch sensors** (the T pins are at the bottom end of each fader, next to the strip, so the electrode wires are about 2 cm), J23 |
| **Bottom** | Class board + perf as needed | U1, U3, U7, U6, power, Q2, U14 '273, U9 74AHC157, A1 TB6612 and the motor supply (PTC, TVS, 470 uF), A2 KB2040 + A3, U10 24C16 + I2C pull-ups, J11 RJ45, J7, `JP_RX`, J22 |

**J20, panel bus (2x6, 12 conductors).** Conductor order on the ribbon = pin order; `LCD_E` sits next to a GND.

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | `AD0` | 2 | `AD1` |
| 3 | `AD2` | 4 | `AD3` |
| 5 | `AD4` | 6 | `AD5` |
| 7 | `AD6` | 8 | `AD7` |
| 9 | `LCD_RS` | 10 | `LCD_RW` |
| 11 | `LCD_E` | 12 | GND |

**J21, panel I/O (2x5, 10 conductors).** `ADC_SCK` sits between GNDs.

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | +5 V | 2 | GND |
| 3 | `BTN_OE_N` | 4 | `TOUCH2` (-> P1.5) |
| 5 | `ADC_SCK` | 6 | GND |
| 7 | `ADC_MOSI` | 8 | `ADC_MISO` |
| 9 | `ADC_CS_N` | 10 | spare |

**J22, motor (4 conductors, two twisted pairs, routed away from J20/J21):** 1 `M0_A`, 2 `M0_B`, 3 `M1_A`, 4 `M1_B`. Use wire rated for the stall current (about 0.8 A per motor, MEASURE).

**J23, fader strip to D-pad board (panel level only, 6 conductors):** 1 +5 V, 2 GND, 3 `BTN_F1`, 4 `BTN_F2`, 5 `TOUCH1`, 6 `TOUCH2` (continues to J21 pin 4).

**Wires that stay on the panel:** each fader's pot (track ends to `VREF_F` and AGND, wiper to its RC on the D-pad board), the LCD (from J20/J21 on the D-pad board), the pedal jack, and J23.

Notes:
- **Count:** 22 conductors in two keyed cables of different sizes, so they cannot be swapped: 17 signals, +5 V, 3 GND, 1 spare (J21 pin 10). Without the split it would be about 34 loose wires.
- **Length:** J20 about 9 in, J21 about 8 in, home-made from 12-conductor ribbon and polarized IDC sockets (keep both under about 30 cm) (parts: [Perfboard_Order_Notes](hardware/Perfboard_Order_Notes.md) section 3e). Each fast signal has a GND beside it, and the 8051 drives the bus strongly during bus cycles; the LCD and the '244 are the only loads at the far end.
- **Power:** the panel draws about 10 mA at +5 V (LCD, '244, MCP3008, two touch sensors); one +5 V conductor is enough.
- **Height:** the D-pad board has about 10 mm between its top and the acrylic. Keep socketed DIPs (about 7-8 mm) away from the plunger shoulders or on the underside, and use right-angle or bottom-side headers for J20/J21/J23. Under the board there is about 2 mm above the class board's NVSRAM socket area; removing U4 and its socket frees that space.
- **Grounds:** AGND joins GND at one point at U11 on the D-pad board; the motor return stays on the bottom level (J22 carries no ground).

---

## 4. Daughter boards (perf)

### 4.1 Common

- Two RJ45 breakouts in parallel (bus in, bus out), pinout as section 3.10; no active parts in the pass-through.
- **DIP switch** (8-position blocks on hand, x4): positions 1-3 are `A0`, `A1`, `A2` of the board's I2C chip, the rest unused (leave open). Each position has a 10 k pull-up to +5 V and the switch to GND (closed = 0). Label the setting table on the board.
- 0.1 uF at each IC, 10 uF at the bus-in jack.

### 4.2 Pot board

| Item | Spec |
|---|---|
| ADC | **Part `OPEN` #3** (8 inputs on I2C, 5 V). Candidates: PCF8591P (DIP-16, 8-bit, 4 inputs, 0x48 + n with 8 addresses; listed in the 10/24 order notes but NXP has discontinued it, so only if one is on hand or in stock); TI ADS7828 (12-bit, 8 inputs, TSSOP-16 on a DIP adapter, 0x48 + n with 4 addresses, `REF` driven from `VREF_P`); ADS7830 (8-bit, same footprint as ADS7828) |
| `VREF_P` | 100 ohm + 10 uF + 0.1 uF from +5 V: pot tops and ADC reference, so readings are ratiometric |
| Pots | 1x3 headers or board-mount pots: `VREF_P`, wiper (through 1 k + 100 nF), GND |

### 4.3 Button board

| Ref | Part | Function |
|---|---|---|
| U1 | PCF8574N (kit, DIP-16) | I2C expander, address 0x20 + n. P0-P3 = SW1-SW4 to GND with 10 k pull-ups; P4-P7 = LED1-LED4, active low, 330 ohm to +5 V; `/INT` (pin 13) -> `BUS_INT_N` |
| SW1-SW4 | 4 x 6 mm tactile | Buttons |
| LED1-LED4 | 4 x LED | Indicators |

The kit has one PCF8574, enough for one button board.

### 4.4 I2C address map

| Family | Chip | 7-bit address | Where |
|---|---|---|---|
| Button board | PCF8574 | 0x20 + n, n = 0-7 | daughter |
| Pot board | ADC per `OPEN` #3 | 0x48 + n | daughter |
| Preset EEPROM | 24C16 | 0x50-0x57 (all 8) | master side |
| Reserved | PCF8574A | 0x38-0x3F | spare |

Same-type boards must use different DIP settings; the master cannot detect a duplicate. Do not put a PCF8574 LCD backpack (0x27) on this bus.

---

## 5. Reaper / MIDI mapping (starting point for firmware)

| Control | MIDI |
|---|---|
| Fader 1-2 position, both directions | Pitch bend ch 1-2, 14-bit (10-bit ADC shifted left 4) |
| Fader touch (A4/A5 touch sensors) | Note 0x68-0x69, velocity 127/0 |
| Per-fader button (programmable) | Default Select/Mute/Solo/Rec notes 0x18/0x10/0x08/0x00 + n; short and long press differ |
| Button board SW1-4 | Rec / Solo / Mute / Select for one strip, or transport (`90 5F`/`5E`/`5D` record/play/stop) |
| Button board LEDs | Follow Reaper Note On velocity |
| Pots, pedal | CC (pedal default CC 11) |

Reaper side: Mackie Control Universal driver on the KB2040's MIDI port. `VERIFY:` no SysEx handshake is mandatory.

---

## 6. UI summary (firmware context)

Up/down select, left/right adjust (auto-repeat after about 500 ms), center confirm, long press saves to the EEPROM or backs out. The two fader buttons run an assigned function stored per preset. Every change shows a transient message on LCD row 0 for about 1.5 s.

---

## 7. Build stages (`Phase` field)

The build is staged so something works at every step. Mark each schematic component with `P1`/`P2`/`P3`.

| Phase | Build | Demo at the end |
|---|---|---|
| **P1: one fader, LCD, USB-MIDI** | Class board changes (U4 out, U7 reprogrammed, `JP_RX`, taps); +5 V distribution; motor supply (9 V >= 2 A adapter, `VM` tap at the bridge output, section 3.9) with PTC/TVS/bulk; A2 KB2040 + A3; U9, Q2, U14, A1, FDR1 + A4 touch sensor; U11 + `VREF_F`; U16 with all 8 pull-ups and `BTN_F1`; LCD; J7 | Fader 1 follows Reaper and moves Reaper's volume; LCD shows the value |
| **P2: rest of the master side** | FDR2 + A5 touch sensor, `BTN_F2`, five nav buttons, U10 24C16 + I2C pull-ups, J11 RJ45 (unplugged), J13 pedal | Two faders, menu, presets survive a power cycle, pedal CC |
| **P3: daughter boards** | Pot board, button board, patch cables | Boards found by scan, chained, any order |

Bring-up tests per phase (summary): P1: power, 8051 alive, bus decode on the logic analyzer, button read, LCD, ADC, motor open loop, closed loop, MIDI to and from Reaper via the KB2040. P2: all buttons, EEPROM and I2C, presets, I2C recovery, both motors, loop budget, UI, full Reaper session, 30-minute run. P3: each daughter alone, both chained, duplicate-address behavior, cable length, integration.

---

## 8. Schedule and parts

Today 10/24. Parts order **not yet placed** (course target was 10/20): order now. Feature freeze 11/30; demo 12/4; physical items returned 12/7 (NVSRAM included); report 12/9. Suggested windows (team to confirm): P1 by 11/8, P2 by 11/22, P3 by 11/29.

Kit mapping, the Digi-Key order and alternates: [hardware/Perfboard_Order_Notes.md](hardware/Perfboard_Order_Notes.md). Still to source: a 9 V >= 2 A barrel adapter (section 3.9), pot-board ADC (`OPEN` #3, deferred), button-board tactiles, TRS jack. Both faders and the DIP switches are on hand.

---

## 9. Open items and risks

**OPEN decisions (agents must not decide)**

| # | Item | Needed for | Default if the team delegates |
|---|---|---|---|
| 1 | ~~Motor rail supply~~ **Closed Rev 13.4**: one 9 V >= 2 A adapter into the class board jack, `VM` tapped at the bridge output (section 3.9) | | |
| 2 | ~~Where the main-side circuits are built~~ **Closed Rev 13.2**: two levels, panel and bottom, joined by J20 (12-pin), J21 (10-pin) and J22 (motor); section 3.13 | | |
| 3 | Pot inputs (section 4.2), deferred to P3. Candidates: (a) an I2C ADC for the chainable pot daughter board (ADS7828 on an adapter, ADS1115 module); (b) no new parts: pots on U11's 5 spare channels (CH2, CH4-CH7) on the panel; (c) no new parts: the spare MCP3008 on the panel sharing U11's SPI lines, chip-select from latch U14 Q4 over J21 pin 10 (8 more inputs) | P3 | (a) ADS7828 on a TSSOP-16 DIP adapter |
| 4 | KB2040 link: 31,250-baud MIDI stream or 115,200-baud USB-MIDI packets | Firmware on both ends | 31,250 (the 8051 code stays real MIDI and the DB9 fallback is unchanged) |
| 5 | ~~Hardware SPI for the MCP3008~~ **Closed Rev 13.1**: P1.5 is now `TOUCH2`; the MCP3008 stays bit-banged | | |
| 6 | Mechanical layout: where the LCD, two faders and buttons are mounted (panel or board), and how | Build | Faders side by side on the right, LCD top left, D-pad below the LCD |

**Risks**

1. **PDR scope change** (PDR: one fader, 74HC165 footswitches, NVRAM presets; now two faders, I2C daughters, KB2040). Confirm with the TAs, including that the KB2040 doing only the USB link is acceptable.
2. **Late parts order** (course target 10/20). Order immediately; most parts are kit or on hand.
3. **Pin budget** is 14 of 14 used; further I/O must use the memory-mapped page or I2C.
4. **X2 mode** breaks LCD timing; stay in X1.
5. **Motor current** not in the fader datasheet: measure before trusting the supply and fuse sizes.
6. **SPLD** edits can break the Lab 3 decode; keep `lab3.pld` and its `.jed`.
7. **Bit-banged SPI + I2C + MIDI** loop budget: measure first.
8. **Single UART** shared by MIDI and the PC bootloader (`JP_RX`).
9. **Hand wiring** of the 8-bit bus to several ICs and across J20: continuity-check every net against Appendix A and section 3.13; keep J20/J21 at 30 cm or less.
10. **DIP-switch duplicates** on daughters are undetectable.
11. **Touch sensing**: motor PWM coupling into the T electrode, power-up calibration with a hand on a knob, and the sensor's maximum on-duration recalibration.
12. **PWM noise**: 10.8 kHz is audible and the course says projects must not make significant noise. Drive motors only while moving.
13. **Parts supply**: ATF16V8B NRND; PCF8591P discontinued (`OPEN` #3).
14. **Pin numbers** in Appendix A are from standard pinouts, not yet checked against each datasheet: `VERIFY:` before wiring.

---

## Appendix A: Netlist for the master side (verify every pin number)

Power pins are not listed unless special; every IC gets +5 V, GND and a 0.1 uF cap at its supply pins. `NC` = no connect. Class-board connections that do not change are marked "existing".

### A.1 U1 AT89C51RC2 (DIP-40, class board)

See section 3.2 (complete).

### A.2 U3 74LS373 (DIP-20, class board, existing)

| Pin | Name | Net |
|---|---|---|
| 1 | /OC | GND |
| 3, 4, 7, 8, 13, 14, 17, 18 | D0..D7 | AD0..AD7 |
| 11 | LE | ALE |
| 2 | Q0 | `LCD_RS` (new tap) |
| 5 | Q1 | `LCD_RW` (new tap) |
| 6, 9, 12, 15, 16, 19 | Q2..Q7 | existing class wiring (A2-A7), unused here |

### A.3 U7 ATF16V8B (DIP-20, class board, reprogrammed)

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | GND (existing) | 11 | `A10` (new) |
| 2 | `A12` | 12 | `BTN_OE_N` (new) |
| 3 | `A13` | 13 | NC |
| 4 | `A14` | 14 | `LCD_E` (new) |
| 5 | `A15` | 15 | `MOTDIR_CLK` (new) |
| 6 | `RD` | 16 | `VDP_WR_N` (test point) |
| 7 | `PSEN_N` (existing, unused) | 17, 18 | NC (were U4 /E, /G) |
| 8 | `WR` | 19 | NC (was `CSPERIPH`) |
| 9 | `A11` (new) | 10 / 20 | GND / VCC |

`VERIFY:` how pin 1 is wired on the class board (GND or a clock input) before reprogramming.

### A.4 U14 74HCT273 (DIP-20)

| Pin | Name | Net |
|---|---|---|
| 1 | /MR | `RST_N` (Q2 collector) |
| 11 | CP | `MOTDIR_CLK` |
| 3, 4, 7, 8, 13, 14, 17, 18 | D0..D7 | AD0..AD7 |
| 2 | Q0 | `M0_IN1` -> A1 `AIN1` |
| 5 | Q1 | `M0_IN2` -> A1 `AIN2` |
| 6 | Q2 | `M1_IN1` -> A1 `BIN1` |
| 9 | Q3 | `M1_IN2` -> A1 `BIN2` |
| 12, 15 | Q4, Q5 | NC (test points; were motor 2) |
| 16 | Q6 | `MOT_STBY` -> A1 `STBY`, 10 k to GND |
| 19 | Q7 | NC (test point) |
| 10 / 20 | GND / VCC | |

### A.5 U16 74HCT244 (DIP-20)

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
| 17 | 2A4 | `TOUCH1` (A4 OUT) | | 3 | 2Y4 | AD7 |

Pins 10 / 20: GND / VCC. Each `BTN_*` net: 10 k to +5 V. `TOUCH1`: no pull-up, 10 nF to GND.

### A.6 Q2 2N2222 reset inverter

`RST` -> 10 k -> base; emitter -> GND; collector = `RST_N` -> U14.1, with 10 k to +5 V. While the 8051 is in reset (`RST` high) U14 is cleared. `VERIFY:` the `RST_N` edge on the scope (`RST` is a slow RC ramp).

### A.7 U9 SN74AHC157N (DIP-16)

| Pin | Name | Net |
|---|---|---|
| 1 | S (select) | GND (selects the A inputs) |
| 15 | /G (strobe) | `RST`: high during reset forces all Y low |
| 2 -> 4 | 1A -> 1Y | `PWM0` -> `PWM0_EN` (A1 `PWMA`) |
| 5 -> 7 | 2A -> 2Y | `PWM1` -> `PWM1_EN` (A1 `PWMB`) |
| 11 -> 9 | 3A -> 3Y | 3A to GND; 3Y NC (was `PWM2`) |
| 14 -> 12 | 4A -> 4Y | 4A to GND; 4Y NC |
| 3, 6, 10, 13 | 1B-4B | GND |
| 16 / 8 | VCC / GND | |

`VERIFY:` pin numbers against the TI datasheet. AHC inputs need about 3.85 V for a high at 5 V; a port pin into a CMOS input reaches close to 5 V, but check the PWM edge on the scope.

### A.8 A1 TB6612FNG breakout (pin names; `VERIFY:` the breakout's labels and any on-board pull-downs)

| Pin | Net |
|---|---|
| `VM` | `VM` (motor rail), 470 uF + 0.1 uF close by |
| `VCC` | +5 V |
| `GND` (all) | GND (motor return, section 3.9) |
| `PWMA` / `PWMB` | `PWM0_EN` / `PWM1_EN` |
| `AIN1`, `AIN2` | `M0_IN1`, `M0_IN2` |
| `BIN1`, `BIN2` | `M1_IN1`, `M1_IN2` |
| `STBY` | `MOT_STBY` |
| `AO1`, `AO2` | `M0_A`, `M0_B` -> FDR1 motor A, B (100 nF across) |
| `BO1`, `BO2` | `M1_A`, `M1_B` -> FDR2 motor A, B (100 nF across) |

### A.9 U11 MCP3008 (DIP-16)

| Pin | Name | Net |
|---|---|---|
| 1 | CH0 | `FADER1_W` (1 k series, 100 nF to AGND, 1 M to AGND) |
| 2 | CH1 | `FADER2_W` (same) |
| 3 | CH2 | 100 k to AGND (unused; was fader 3) |
| 4 | CH3 | `PEDAL_W` (same RC as the faders) |
| 5, 6, 7, 8 | CH4..CH7 | 100 k to AGND each |
| 9 | DGND | GND |
| 10 | /CS | `ADC_CS_N` |
| 11 | DIN | `ADC_MOSI` |
| 12 | DOUT | `ADC_MISO` |
| 13 | CLK | `ADC_SCK` |
| 14 | AGND | AGND (single point to GND at U11) |
| 15 | VREF | `VREF_F` |
| 16 | VDD | `VREF_F` |

`VREF_F` = +5 V through 100 ohm, with 10 uF and 0.1 uF to AGND. FDR1/FDR2 track ends: `VREF_F` and AGND.

### A.10 U6 MAX232 (DIP-16, class board)

Unchanged except pin 12: R1OUT goes to `JP_RX` pin 3 instead of straight to P3.0. T1IN (pin 11) = `MIDI_TX` (existing); T1OUT/R1IN to J4/J5 (existing).

### A.11 A2 KB2040 and A3 level shifter

| From | To | Net |
|---|---|---|
| U1.11 P3.1 | A3 HV1 | `MIDI_TX` |
| A3 LV1 | A2 RX (D1) | `KB_RX_3V3` |
| A2 TX (D0) | A3 LV2 | `KB_TX_3V3` |
| A3 HV2 | `JP_RX` pin 1 | `KB_TX_5V` |
| +5 V | A3 HV | |
| A2 3V3 | A3 LV | reference only |
| GND | A2 GND, A3 GND (both sides) | |
| A2 5 V (VBUS) | NC | do not join rails |

### A.12 U10 24C16 (DIP-8)

| Pin | Net |
|---|---|
| 1, 2, 3 | GND (A0-A2, ignored by the 24C16) |
| 4 | GND |
| 5 | `SDA` |
| 6 | `SCL` |
| 7 | WP = GND (write enabled) |
| 8 | +5 V with 100 nF |

`VERIFY:` the kit part's exact type (24C16 vs 24LC16B) and its WP behavior.

### A.13 LCD1 (J10, 1x14)

`DB0..DB7` = `AD0..AD7`, `RS` = `LCD_RS`, `R/W` = `LCD_RW`, `E` = `LCD_E`, `VDD` = +5 V, `VSS` = GND, `VEE` (pin 3) = contrast pot wiper. Pin order per section 3.6.

### A.14 J11 RJ45 bus (master side)

Pins per section 3.10: 1 `SCL`, 3 `SDA`, 4 +5 V via `JP_BUS`, 7 `BUS_INT_N`, 2/5/6/8 GND. Pull-ups (5.1 k `SDA`/`SCL`, 10 k `BUS_INT_N`) on the master side only.

### A.15 A4, A5 AT42QT1010-TSHR touch sensors (SOT-23-6 pin numbers from the Microchip datasheet DS40001946A; adapter pin mapping `VERIFY:` on the adapter)

| Pin | A4 (fader 1) | A5 (fader 2) |
|---|---|---|
| 5 `VDD` | +5 V via 100 ohm; 10 uF + 100 nF to GND at the chip | same |
| 2 `VSS` | GND | GND |
| 3 `SNSK` | Rs 4.7 k to `FDR1_T` (FDR1 pin T); Cs to pin 4 | Rs 4.7 k to `FDR2_T` (FDR2 pin T); Cs to pin 4 |
| 4 `SNS` | Cs (10 nF X7R, tune 2-50 nF) to pin 3 | same |
| 1 `OUT` | `TOUCH1` -> J23 pin 5 -> U16.17; 10 nF to GND | `TOUCH2` -> J23 pin 6 -> J21 pin 4 -> U1.6 (P1.5); 10 nF to GND |
| 6 `SYNC/MODE` | GND (low-power mode, about 60 s hold limit) | GND |

### A.16 Daughter-board nets

| Board | Chip | Pin connections |
|---|---|---|
| Button | PCF8574N (DIP-16): 1, 2, 3 = A0, A1, A2 from the DIP switch; 4, 5, 6, 7 = P0-P3 (buttons); 9, 10, 11, 12 = P4-P7 (LEDs); 13 = /INT; 14 = SCL; 15 = SDA; 8 = VSS; 16 = VDD | `/INT` -> `BUS_INT_N` |
| Pot | per `OPEN` #3 | 8 (or 4) wipers via RC; reference = `VREF_P`; address pins from the DIP switch; `SDA`, `SCL` |

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
| 11 | Review fixes ([Hardware_Map_Review](docs/archive/Hardware_Map_Review.md)): U14 '273 pin numbers fixed; status LED sinks into P1.1; `VDP_WR_n` narrowed to 0xFC00; HCT for U9/U14, 74HC14 for U15; 1 M wiper pull-downs; 6N138 values; WP pull-up. Decisions: 12 V 3 A barrel, P-FET, R-78E5.0; faders board-mounted with motor cutouts; TTL FTDI-style headers J7/J12 and 2x3 `JP_RX`; socketed crystal (16 MHz evaluation, why not X2); 0805 SMD passives; PCF8591P replaced by ADS7828 (8 pots per board, 4 addresses) |
| 12 | LCD: the Lab 4 kit module is a Samsung 16x4 (87 x 60, 14-pin single row, no backlight; photo-measured), the handout names an Optrex DMC-20434 20x4 with the same pinout and SED1278F controller. Pinout, contrast and timing from the Optrex/Epson specs; `JP_BL` and its resistor removed; firmware geometry constants for 16x4 and 20x4. (2026-10-20: ESD_Main KiCad 10 PCB drafted from this revision; still in the git history at commit `735803c`) |
| 13 | **2026-10-24, scope change: class board as master, hand-built perf boards, no custom PCB.** Two faders (Terwin SM100, not Alps) on one TB6612FNG breakout; PWM2, U13, FDR3 and `BTN_F3` dropped (P1.5 spare, D7 = `BTN_SPARE`, MCP3008 CH2 unused). Perf-board decisions of 10/24 folded in: KB2040 + BSS138 level shifter replace DIN-5/6N138/mio and J12; 74AHC157 (with `/G` = `RST`) replaces the 74HCT125; 2N2222 replaces the 74HC14; kit 24C16 replaces the 24LC256 (WP tied low); RJ45 bus replaces the IDC ribbon; 5.1 k I2C pull-ups; `JP_RX` becomes 1x3 (KB2040 / PC); status LED uses the class board's Q1 driver; `STBY` on latch Q6. Removed: custom-PCB brief (old section 0), footprints, JLC/stencil/0805 rules, 12 V barrel/P-FET/R-78E, socketed crystal. New `OPEN` items: motor supply vs the 9 V class input (#1), build location (#2), pot-board ADC (#3, PCF8591P vs ADS7828), KB2040 link baud (#4), hardware SPI (#5), mechanical layout (#6). Closed: expression pedal kept in P2 |
| 13.1 | 2026-10-24: hardware fader touch. The SM100's T pin connects to the knob (< 10 ohm measured), so each fader gets an AT42QT1010 touch sensor (A4, A5) with T as the electrode. `TOUCH1` takes U16 D7 (was `BTN_SPARE`), `TOUCH2` takes P1.5 (was spare), so all 14 port pins are used and `OPEN` #5 (hardware SPI) is closed. New Appendix A.15; daughter-board nets renumbered A.16 |
| 13.2 | 2026-10-24: physical build in two levels (section 3.13). Panel: D-pad board with U16 '244 and U11 MCP3008, fader strip with F1/F2 and the A4/A5 touch sensors. Bottom: class board and everything else. Cables J20 (2x6 bus), J21 (2x5 I/O, 1 spare), J22 (motor), panel jumper J23. Closes `OPEN` #2 |
| 13.3 | 2026-10-24: touch sensors are bare AT42QT1010-TSHR chips on SOT-23-6 adapters (the SparkFun breakout has its own touch pad). Datasheet pinout and circuit in section 3.5 and A.15: `SYNC/MODE` to GND (low-power mode keeps the about 60 s hold limit), no pull-up on `TOUCH1`, 10 nF HeartBeat filter on each `OUT`, RC-filtered `VDD` |
| 13.4 | 2026-10-24: power decided (closes `OPEN` #1). One 9 V >= 2 A adapter into the class board jack; `VM` tapped at the bridge "+" output before SW1 through `JP_VM`, PTC, TVS and 470 uF; A1 ground to the bridge "-" output. Motor sees about 7.1 V (no PWM cap). 12 V adapter is a drop-in upgrade |
| 13.5 | 2026-10-25: KiCad schematic added (hardware/kicad/ESD_Final, ERC clean, netlist checked against design.py). Correction from the class board netlist: SW1 is before the bridge, so it carries motor current (`VERIFY:` rating or replace) |
