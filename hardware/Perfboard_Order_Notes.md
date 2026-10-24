# Perf-board build: kit-first parts review and Digi-Key order

| Field | Value |
|---|---|
| Date | 2026-10-24 |
| Upload file | [digikey_phase1_2_order.csv](digikey_phase1_2_order.csv) (cart as checked out: [digikey_cart_2026-10-24.csv](digikey_cart_2026-10-24.csv)) (8 lines) |
| Spec this derives from | [Hardware_Map](../Hardware_Map.md) (Phases 1 and 2, section 7) |
| Kit list | [f26partskit.pdf](../reference/f26partskit.pdf) (Fall 2026 parts kit, 8/24/2026) |
| Status | **Not yet ordered.** Digi-Key stock comes from cached web pages, not live; check the cart before paying. `VERIFY:` = check on the live site or datasheet |
| Assumption | The class board used the kit parts the way the course BOM says (U1 40-pin, U3 and U7 20-pin, U4 28-pin, U6 16-pin sockets; reset, PSEN, INT0 buttons; LED driver; two 10 uF used) |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed by the student |


## 0. USB-MIDI: KB2040 bridge (decided 2026-10-24)

The Adafruit KB2040 (RP2040, native USB) replaces the mio, the DIN jacks, the 6N138 opto and its diode. It plugs into the PC by USB-C and shows up as a class-compliant MIDI device; firmware (CircuitPython `usb_midi` + `busio.UART`) forwards bytes between USB and its UART.

| KB2040 pin | Connect to | Note |
|---|---|---|
| RX (D1) | 8051 TXD (P3.1) through a divider: 1 k in series, 2.2 k to GND | KB2040 pins are 3.3 V and **not** 5 V tolerant |
| TX (D0) | RXD jumper "bridge" position -> 8051 RXD (P3.0) | 3.3 V high should meet the 8051's input-high level, `VERIFY:` data sheet |
| GND | common GND | |
| 5 V / 3.3 V | **not connected** | KB2040 is powered from USB; do not join rails |

- **Preferred instead of the divider: SparkFun bidirectional logic level converter** (BSS138 MOSFETs with 10 k pull-ups, which you have). `HV` = 8051 board +5 V, `LV` = KB2040 3V3 pin (a reference only; the rails are still not joined), GND common. Channel 1: HV1 <- 8051 TXD, LV1 -> KB2040 RX. Channel 2: LV2 <- KB2040 TX, HV2 -> RXD jumper. Its 10 k pull-up also strengthens the 8051's weak port high. Fine for 31,250 and 115,200 baud.
- **TXB0104 (also on hand): not recommended here.** It needs strong push-pull drivers, and the 8051's port pins are only weakly driven high, so the 8051 -> KB2040 direction may not switch reliably.
- RXD jumper (3-pin): KB2040 TX / 8051 RXD / MAX232 R1OUT (PC and FLIP).
- MAX232 T1 still sees TXD, so the PC terminal shows the MIDI traffic; harmless.
- Baud: 31,250 real MIDI (CircuitPython parses it) or 115,200 with 4-byte USB-MIDI packets from the 8051. Pick one before writing firmware.
- Ask the TA that a dev board doing only the USB link is acceptable.

## 1. Kit part -> use in this project

| Kit item | Use here |
|---|---|
| AT89C51RC2, 74LS373, SPLD, MAX232, DE-9, 7805 + heat sink, power jack, crystal, 27 pF | Already on the class board, unchanged |
| 16x4 LCD (HD44780 compatible) | The display. The kit's **14-contact** socket strip suggests a **14-pin interface (no backlight pins)**: wire DB0-DB7, RS, R/W, E, V0, VDD, VSS and skip `LED+`/`LED-`. This partly answers the open LCD item; `VERIFY:` against the module (continuity and the Lab 4 handout) |
| 24C16 serial EEPROM (DIP-8) | **Preset store, replaces the 24LC256.** 2 KB is plenty. Differences: 1-byte word address, the chip occupies **I2C 0x50-0x57** (A0-A2 are ignored), 16-byte pages, tie `WP` (pin 7) low |
| 5.1K resistors x2 | **SDA and SCL pull-ups** (replaces 3.3 k). Fine at 100 kHz for a bus of a few boards. `INT_N` pull-up: 10 k from the lab |
| Potentiometer | LCD contrast (`V0`) |
| 330 ohm x5 | Status LED, spare |
| LEDs (2 red, 2 green) | Status and power indicators |
| 2N2907 / 2N2222 | Status LED driver (same circuit as the class board's `Q1`), and a transistor inverter on `RST` to make the 273's `/MR` |
| 74LS374 | Optional motor direction latch in place of the 273 (see 2); otherwise a spare |
| PCF8574 (DIP-16) | **Phase 3 button board.** One in the kit, enough for one button board |
| Wire-wrap sockets left over: 20-pin x2, 16-pin x2, 14-pin x2, 8-pin x1 | 20-pin: direction latch and button buffer. 16-pin: MCP3008 and the PCF8574. 14-pin: U9 74HC125. 8-pin: 24C16 |
| Pin strips (2 x 36), 14-contact socket strip | Headers on the perf boards, LCD mating strip |
| Pushbuttons | 3 are used by the class board; 1 spare. You still need 8 for the panel |
| 0.1 uF, 1 uF, 4.7 uF, 10 uF, 47 uF, 27 pF | Bypass (0.1 uF; also from the lab), 47 uF for the perf-side 5 V bulk. Non-polarized caps and resistors come from the lab, so none are in the order |
| 4.7K SIP-10 | Already the P0 pull-up bank (class board R4) |
| MCP4802 SPI DAC | Not used |

## 2. Design changes from using the kit parts

1. **Direction latch = 74HCT273 (recommended), with the kit's 2N2222 as the reset inverter.** `RST` -> 10 k -> base of the 2N2222; emitter to GND; collector to `/MR` with a 10 k pull-up to +5 V. While the 8051 is in reset the 273 clears, so both motor inputs are low (brake). This is why one CD74HCT273E is in the order.
   - **Kit-only option: 74LS374.** It has no clear pin, so it powers up with random outputs. Pins: 1 `/OC`, 2 Q0, 3 D0, 4 D1, 5 Q1, 6 Q2, 7 D2, 8 D3, 9 Q3, 10 GND, 11 CLK, 12 Q4, 13 D4, 14 D5, 15 Q5, 16 Q6, 17 D6, 18 D7, 19 Q7, 20 VCC (differs from the 273 at pins 1, 6, 7, 16, 17). Put a 10 k pull-down on each of the six `INx` lines, and hold `/OC` high at power-up with a 4.7 uF from `/OC` to +5 V and 10 k from `/OC` to GND (about 50-100 ms hold-off, `VERIFY:` on the bench); firmware writes `0x00` first thing. A manual reset does **not** re-disable the outputs in this scheme, so the last direction can persist for the few milliseconds of a reset, with the enable pins high. Acceptable only if you are willing to tolerate a brief motor twitch on reset.
2. **No 74HC04.** The status LED uses the class board's PNP driver circuit and the 273 reset uses the 2N2222 inverter above.
3. **EEPROM 24C16.** Update the I2C driver: 1-byte word address; the device address carries the upper 3 address bits (0x50 + block).
4. **LCD header = 14 pins**, backlight omitted unless the module has pads for it. Contrast from the kit pot.
5. **Button pull-ups = eight discrete 10 k** resistors from the lab, no SIP. A 10 nF per button is optional.
6. **Power**: use the kit 7805 and heat sink via the class board's +5 V rail for the perf boards if the lab adapter is 9 V (about 1.6 W at 400 mA). Keep the motor rail on the separate PD module with the PTC, TVS and 470 uF. If the 7805 runs too hot, add a drop-in switching module such as the RECOM R-78E5.0-1.0 (Digi-Key 945-2201-ND); it is not in the order.

## 3. What is still in the order

Sockets and tactile buttons are **not** ordered: you have spares. Count what you need: 8 tactile switches; DIP sockets for U8 (8-pin), U11 (16), U12 and U13 (16 each), U9 (14), U14 and U16 (20 each), the EEPROM (8) and, in Phase 3, the PCF8574 (16). Add them back to the cart (On Shore ED08DT, ED16DT, Omron B3F-1000) if you come up short.

| Item | Why it is not in the kit |
|---|---|
| MCP3008-I/P x2 | fader ADC |
| SN74HCT244N x2 | panel button buffer (no 244/245 in the kit) |
| CD74HCT273E x2 | direction latch with a defined reset (1 + 1 spare) |
| 10 uF x2, 470 uF x2 | reference filter, motor bulk |
| RHEF200 (Digi-Key RHEF200HF-ND), P6KE15A | motor rail protection |
| 1x40 male header | wiring |

Removed from the first version of the order because the kit or lab has them: 24LC256, 74HC04, all resistors, ceramic caps, trimmer, LEDs, SIP, 1x16 female header, and the 5 V module.

Still needed later (Phase 3, not in this order): PCF8591P for the pot board, 4-position DIP switches, 6 mm tactiles for the button board, RJ45 jacks (1 on the main board in Phase 2, 2 per daughter board) and short straight-through patch cables (section 3d).


## 3a. Using your TB6612FNG for motors 1 and 2

Yes, it fits: 1.2 A continuous per channel (more than the L293D's 0.6 A), about 0.5 V drop instead of 2-3 V, logic 2.7-5.5 V, `VM` 4.5-13.5 V (the 12 V PD module is in range, `VERIFY:` the actual PD voltage stays under 13.5 V). It is SSOP-24, so use it on a breakout board. One breakout drives two motors; the third motor still needs a second driver (L293D in the order, or another TB6612 breakout).

| TB6612 pin | Connect to |
|---|---|
| `VM` | motor rail (12 V) with the 470 uF bulk close by |
| `VCC` | +5 V |
| `GND` (all) | GND |
| `PWMA` / `PWMB` | `PWM0_EN` / `PWM1_EN` (U9 buffer outputs, as before) |
| `AIN1`, `AIN2` | latch Q0, Q1 (motor 0) |
| `BIN1`, `BIN2` | latch Q2, Q3 (motor 1) |
| `STBY` | latch **Q6** with a 10 k pull-down: the driver is in standby (outputs off) after reset until firmware sets the bit |
| `AO1`, `AO2` / `BO1`, `BO2` | motor 0 / motor 1 terminals |

Differences from the L293D wiring:
- **Logic table:** `IN1 = IN2 = 0` is **stop (outputs off, coast)** and `IN1 = IN2 = 1` is **short brake**. Between direction changes use `11` for a brake, then `00` or the new direction. `STBY` low turns everything off.
- **PWM:** `PWMx` is a real PWM input, not an enable. High with `IN1/IN2` set drives; low brakes. Same 10.8 kHz signal works.
- **Pull-downs:** some breakouts put pull-downs on the inputs. Keep the U9 buffers so the weak 8051 pins are not loaded, and `VERIFY:` the breakout schematic for resistor values.
- **Motor terminal caps:** still add 100 nF across each motor.
- **Phase 1:** one fader on the TB6612 channel A is enough; the TB67H420FTG carrier joins in Phase 2 for the third motor.


## 3b. Third motor: Pololu TB67H420FTG carrier (on hand, board marked md35a)

The chip marked "H420FTG" is Toshiba's **TB67H420FTG**; the board is very likely Pololu item #2999 (dual/single brushed DC driver carrier: about 10-47 V, 1.7 A per channel, built-in under-voltage, over-current and over-temperature protection, reverse-voltage protection on the carrier). With the TB6612 (motors 0 and 1) it covers all three motors, so the L293D is removed from the order.

| Carrier pin | Connect to |
|---|---|
| `VIN` / `VM` | 12 V motor rail. **Minimum is about 10 V**, so the PD module must stay at 12 V (9 V is too low) |
| logic `VCC`/`VDD` (if the carrier has one) and GND | +5 V and GND, `VERIFY:` against the Pololu pinout |
| `PWMA` | `PWM2_EN` (U9 buffer output) |
| `INA1`, `INA2` | latch Q4, Q5 (motor 2) |
| `AO1`/`AO2` (motor outputs A) | motor 2 terminals, 100 nF across them |
| `HBMODE` | low = dual-channel mode, `VERIFY:` the carrier's default |
| channel B (`PWMB`, `INB1`, `INB2`) | unused: tie the inputs low |
| error outputs (`LO1`, `LO2`) | optional; leave open or bring to a test pad |

`VERIFY:` before wiring: Pololu's pin names and logic table for this carrier (what both inputs low and both high do), whether its inputs accept 5 V logic, and how its current limit is set (a reference voltage or sense resistors on the board). The fader motor's current is far below its 1.7 A, so it will run cool.


## 3c. PWM buffers: SN74AHC157N (on hand) instead of the 74HC125

The '157 is a quad 2-to-1 multiplexer. With its select pin fixed it is simply four non-inverting push-pull buffers, which is the job the 74HC125 did (MIDI OUT no longer needs a gate now that the KB2040 is the USB link). It is not 3-state, so it can **not** replace the 74HCT244 on the data bus.

| '157 pin | Connect to |
|---|---|
| 1 (S, select) | GND (selects the A inputs) |
| 15 (/G, strobe) | 8051 `RST` net: while the 8051 is in reset, /G is high and all outputs are forced low, so the motor PWM inputs are off |
| 2 (1A) -> 4 (1Y) | P1.3 `PWM0` -> `PWM0_EN` (TB6612 `PWMA`) |
| 5 (2A) -> 7 (2Y) | P1.4 `PWM1` -> `PWM1_EN` (TB6612 `PWMB`) |
| 11 (3A) -> 9 (3Y) | P1.5 `PWM2` -> `PWM2_EN` (TB67H420 `PWMA`) |
| 14 (4A) -> 12 (4Y) | spare: tie 4A to GND |
| 3, 6, 10, 13 (B inputs) | GND |
| 16 / 8 | +5 V / GND, 0.1 uF |

`VERIFY:` pin numbers against the TI data sheet. AHC inputs need about 3.85 V for a high at 5 V; the 8051 pins reach close to 5 V into a CMOS input, and the edge is fast enough for 10.8 kHz PWM, but check the waveform on the scope.


## 3d. Daughter-board bus on RJ45 (decided 2026-10-24, replaces the 2x5 IDC)

One RJ45 jack on the main board (fitted in Phase 2, unplugged until Phase 3) and two per daughter board (bus in and bus out, wired pin-for-pin in parallel). Use standard straight-through patch cables. Each signal shares a twisted pair with a ground:

| RJ45 pin | Signal | T568B pair |
|---|---|---|
| 1 | `SCL` | orange |
| 2 | GND | orange |
| 3 | `SDA` | green |
| 6 | GND | green |
| 4 | +5 V (through `JP_BUS` on the main board) | blue |
| 5 | GND | blue |
| 7 | `BUS_INT_N` | brown |
| 8 | GND | brown |

- Pull-ups stay on the main board only (5.1 k on SDA and SCL, 10 k on `BUS_INT_N`).
- **Label every jack "I2C - NOT ETHERNET".** A PoE cable can carry about 48 V.
- Most PCB RJ45 jacks have staggered pins that do not fit a 0.1" grid; use RJ45 breakout boards or grid-friendly jacks. Unshielded is fine.
- Keep the whole chain short (a few metres at most) at 100 kHz; Cat5 is about 50 pF/m.
- `VERIFY:` with a continuity tester that each patch cable is straight-through (pin 1 to pin 1).
- **Sourcing (2026-10-24):** 5 RJ45 breakout boards ordered: 1 for the main board + 2 each for the pot and button boards. The last board in the chain does not need its bus-out jack, so one can be held as a spare. Cable: Cat 5e on hand.

## 4. Wiring notes for the class board

1. **Pin access**: confirm you can reach U1 pins P0-P3, ALE, `/RD`, `/WR`. If U1's socket has no wire-wrap tails, plug a DIP-40 extender under the chip.
2. **SPLD**: reprogram U7 with the new equations (Hardware_Map section 3.3), then wire-wrap pins 9, 11, 12, 14, 15. Keep the Lab 3 `.jed`.
3. **NVRAM (U4)**: remove it and return it. Nothing here needs external memory.
4. **UART**: lift the wire from MAX232 R1OUT to RXD and route RXD through a 3-pin jumper (MIDI opto output vs MAX232).
5. **Address latch**: take LCD `RS` and `R/W` from the class board 74LS373 outputs Q0 and Q1.
6. **Ground**: common ground between class board, perf boards and the PD module.

## 5. Alternates (not in the upload)

| Need | Alternate | Note |
|---|---|---|
| MCP3008 DIP out of stock | MCP3008-I/SL (SOIC-16) on a SOIC-to-DIP adapter | SMD acceptable to you; adapter not picked |
| L293D too weak for the motors | SN754410NE when back in stock (296-9911-5-ND) | 1 A rating |
| HCT244 out of stock | SN74HC244N (296-1582-5-ND) | stock was 0 |
| 74xx out of stock | Rochester Electronics marketplace listings on Digi-Key, or Mouser | same part, different seller |

## 5a. Open issue: motor starting current vs the 2 A fuse

[Hardware_Map](../Hardware_Map.md) section 3.5 gives the fader (Alps SM100AN-B10K) as a 10 V motor with about **800 mA starting current** (from the team design doc, `VERIFY:` against the datasheet). Three motors starting together draw about 2.4 A, above the **2 A hold** of the RHEF200 PTC in the order, so it may trip. Either stagger motor starts in firmware (planned anyway) or swap to a PTC with about 3 A hold. Both drivers are fine: TB6612 1.2 A continuous (3.2 A peak) and TB67H420 1.7 A per channel. The motor is rated 10 V: keep PWM duty capped from the 12 V rail.

## 6. Before you click buy

- Check each line shows **In Stock**; the upload tool may offer substitutes.
- If a line fails to match, search the manufacturer part number instead.
- Part numbers I could not confirm: `P6KE15A`, `ECA-1EM100`, `EEU-FR1E471` (any 25 V parts of those values work).
- Quantities include one spare of each IC. Shipping and tariffs are not included.
