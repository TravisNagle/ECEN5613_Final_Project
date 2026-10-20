# Review of Hardware_Map Rev 10 (2026-10-19)

> **Status 2026-10-19: folded into [Hardware_Map](Hardware_Map.md) Rev 11.** Kept as the record of the review.

Review of [Hardware_Map](Hardware_Map.md) before KiCad 10 capture. Drafted with AI assistance (Anthropic Claude). Pinouts were checked against standard datasheet pinouts from memory; part availability came from a web search (prices and stock **not verified on live distributor pages**, re-check before ordering).

**Verdict:** the architecture works. The bus decode, LCD timing at X1, MIDI circuits, MAX232, MCP3008, SN754410, 74HC244/125/04, 74LS373, 24LC256 and PCF8574 pin tables are correct. There is **one netlist error**, **one logic-polarity error** and **one part you cannot buy** (PCF8591P). Several smaller changes are recommended.

---

## 1. Errors (fix before layout)

| # | Where | Problem | Fix |
|---|---|---|---|
| E1 | A.4 U14 74HC273 | Pin numbers wrong. The '273 pinout is the same as the '373: D0-D7 = **3, 4, 7, 8, 13, 14, 17, 18**; Q0-Q7 = **2, 5, 6, 9, 12, 15, 16, 19**. The table lists D on 6 and 16 (those are Q2, Q6) and Q2 = 7, Q6 = 17 (those are D2, D6) | Q2 (`M1_IN1`) = pin 6, Q6 = pin 16 (NC/test pad), D2 = 7, D6 = 17 |
| E2 | 3.8, A.6 status LED | As drawn, P1.1 -> inverter -> 330 ohm -> LED -> GND lights the LED when P1.1 is **low**, not high | Simplest: drop the inverter for the LED and wire +5 V -> 330 ohm -> LED -> P1.1 (8051 pins sink 10 mA; LED off at reset, lit when P1.1 = 0). Or keep the inverter and change the text |
| E3 | 3.3 `VDP_WR_n` | The equation fires on every write to 0xF000-0xFFFF (motor latch and LCD too), not only 0xFFFF | `VDP_WR_n = WR # !(A15 & A14 & A13 & A12 & A11 & A10);` = 0xFC00-0xFFFF (A9-A0 never reach the SPLD) |
| E4 | 3.8 text | "U8 output is inverting": the opto inverts the LED drive, but LED on = MIDI line low = output low, so it is **logically non-inverting**. The circuit is right, the wording is not | Wording only |

## 2. Parts problems (from availability search, re-verify)

| Part | Status | Action |
|---|---|---|
| **PCF8591P** (pot board) | **Obsolete** (NXP no longer manufactured). PCF8591T SO-16 has 0 stock / 52-week lead time | Redesign the pot board, see Q3 below. Recommended: **TI ADS7830** (8-ch 8-bit I2C, TSSOP-16, 4 addresses 0x48-0x4B). 8 pots per board instead of 4 |
| ATF16V8B-15PU | NRND, thin stock | Buy 2-3 spares in the 10/20 order |
| SN754410NE | Out of stock at DigiKey US (18 wk); Mouser reportedly has stock | Order now from Mouser. **L293D is pin-compatible** (DIP-16, internal diodes), but at 600 mA it is below the fader's 800 mA start current: bench-test only |
| 6N138 | Stock patchy (Lite-On 6N138M is the usual buyable one) | Order early; spares |
| 74LS373 | onsemi version obsolete; TI SN74LS373N available | Or 74HCT373 (same pinout) |
| PCF8574AN | Thin | Stay with PCF8574N (active, about $2.30) |
| 12 V USB-PD | 12 V is **not** a mandatory PD fixed voltage; many chargers skip it (the PDR's risk 4 already noted this) | Use a plain 12 V 3 A barrel adapter as the primary supply; PD trigger optional |

Buyable: AT89C51RC2-3CSUM ($9.40), 24LC256-I/P ($1.16), MCP3008-I/P ($3.20), Recom R-78E5.0-1.0 ($4, 1 A, 8-28 V in), Same Sky SDS-50J DIN ($1.75), Neutrik NMJ6HCD2 TRS ($2.50). The HC logic parts were not checked: confirm DIP stock for each.

## 3. Recommended design changes

**Logic levels**
1. **U14 -> 74HCT273.** Its CP comes from the ATF16V8B, whose guaranteed VOH is only 2.4 V; a 74HC input needs 3.5 V. HCT has TTL thresholds (2.0 V). Same pinout.
2. **U9 -> 74HCT125.** Inputs come from 8051 quasi-bidirectional pins (guaranteed VOH 2.4 V). It works with HC at no load, but HCT removes the doubt.
3. **U15 -> 74HC14** (Schmitt, same pinout as '04). `RST` is a slow RC ramp, and a non-Schmitt input can oscillate on it. If E2 is fixed by sinking the LED from P1.1, U15 has one used gate.

**Analog**
4. **MCP3008 pull-downs:** 100 k on a fader wiper (10 k pot) gives up to about 2.4 % (about 25 LSB) error at mid-travel. Use **1 M** on the fader/pedal channels, or place it DNP when the fader is fitted. 100 k is fine on CH4-CH7.
5. **6N138 values** (fill the `VERIFY:`): pin 6 pull-up **470 ohm to 1 k**, pin 7 **10 k to GND** (footprint, may be DNP). This is the usual MIDI-spec circuit.
6. **Expression pedal:** brands disagree on tip = wiper or ring = wiper. Add two 3-pad solder jumpers to swap tip/ring, and put **100 ohm in series** with the `VREF_F` feed to the jack so a plug-in short does not pull down the fader reference.
7. **Fader touch track:** many Alps motor faders have a touch-sense terminal. Check yours; if it has one, bring it to a 1-pin header or test pad (no port pin is free, but it costs nothing to keep).

**Motor and power**
8. **PWM noise:** 10.8 kHz is audible, and the spec says projects "must not make significant noise". Fit the crystal in an **HC-49 socket** so you can test alternatives. **16 MHz** gives exact 31,250 baud (Timer 2 reload 16), PCA PWM 15.6 kHz, and a /RD pulse of 275 ns (still above the 230 ns E minimum, but measure it). The cost is that the Lab 1-4 code assumes 11.0592 MHz. Test one fader on the course board early to decide.
9. **SN754410 heat:** put a large copper pour on GND pins 4, 5, 12, 13 on both layers with vias. Add 47-100 uF at each `VCC2`, not only at the rail.
10. **Grounds:** route motor return current straight from the drivers to the power input (star point) so it never runs under U11 or the AGND area.
11. **Reverse polarity:** use a **P-FET** (for example a TO-220 or SOT-23 P-FET with Vgs zener). A Schottky drops about 0.5 V and dissipates 0.75 W at 1.5 A.
12. **5 V:** populate the **R-78E5.0-1.0** by default. A 7805 at 12 V and 0.5 A dissipates 3.5 W. TO-220 and the R-78 both use 2.54 mm pitch, so one 3-hole footprint (plus a heat-sink hole) serves both.
13. **Supply current:** your design doc ([MIDI-Controller.pdf](MIDI-Controller.pdf), OCR'd) gives the on-hand fader (Alps SM100AN-B10K, 100 mm) as a 10 V motor, 6-11 V range, about **800 mA starting current**. Three faders starting together is about 2.4 A on `VM`, plus about 0.5 A of logic. Size the adapter at **12 V, 3 A** and `F1` at about 3 A hold, and add firmware that staggers motor starts. At 0.8 A per channel the SN754410 (1 A) has little margin and the L293D fallback (0.6 A) has none.
14. **Power switch:** the class board's `SW1` is missing from the BOM. Add a power switch, or document that the barrel plug is the switch.

**Misc**
15. **24LC256 WP:** do not leave it floating when `JP_WP` is open. Add 10 k to +5 V, so the jumper on = write enabled and the jumper off = protected.
16. **Debug port:** a second DB9 takes about 30 x 12 mm of board edge. Use a 1x6 FTDI-style TTL header for `DBG_TX` (a USB-TTL cable), and leave MAX232 ch2 + `J7` as DNP footprints. The course USB-RS232 adapter must be returned by 12/7 anyway.
17. **Board cost:** JLC's cheap tier is at most 100 x 100 mm. The main board (three 100 mm faders if board-mounted, about 128 mm long each) will exceed that. It is still cheap (about $10-25 for 5), but plan for it. Both daughters should fit within 100 x 100.
18. **SMD vs THT:** the spec says to order DIP where possible and to avoid BGA and no-lead packages; SOIC/TSSOP are allowed. Keep all ICs DIP and socketed. Passives can be THT, or 1206/0805 SMD if you have a fine tip and flux. Only the pot-board ADC (if ADS7830) has to be SMD; order a JLC stencil only if you go SMD on the passives.

## 4. Questions for you

1. **Soldering tools:** do you have hot air or a fine tip + flux? This decides SMD passives and the TSSOP ADS7830.
2. **Fader:** your design doc names the Alps SM100AN-B10K as on hand. Are all three that part? Board-mounted (fixes the board length and layout) or panel-mounted on flying leads?
3. **Pot board ADC:** ADS7830 (SMD, 8 pots, 4 addresses), ADS1115 (4 ch, 16-bit, MSOP-10, 4 addresses), or drop the I2C ADC and use an MCP3008-I/P (DIP) on the daughter with a shared SPI bus? That last option needs more ribbon wires and chip selects, so it is not recommended.
4. **Power:** OK with a 12 V 3 A barrel adapter as the primary supply?
5. **Debug:** TTL header instead of the second DB9?
6. **Crystal:** socket it and evaluate 16 MHz, or stay at 11.0592 MHz?
7. **Scope:** the PDR promised footswitches (74HC165) and MIDI merge with 1 fader; the new design drops both and adds 2 faders + daughters. Has Travis agreed, and does the TA need a heads-up?
8. Should I fold these fixes into `Hardware_Map.md` as **Rev 11**?
