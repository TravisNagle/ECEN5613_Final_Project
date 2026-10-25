# Perf-board build: kit-first parts review and Digi-Key order

| Field | Value |
|---|---|
| Date | 2026-10-24 (trimmed to a parts record on 2026-10-24 when its design content moved into [Hardware_Map](../Hardware_Map.md) Rev 13) |
| Upload file | [digikey_phase1_2_order.csv](digikey_phase1_2_order.csv) (14 lines; touch-sensor chips and panel cable parts added 2026-10-24). The older cart export, **not yet ordered and now out of date**: [digikey_cart_2026-10-24.csv](digikey_cart_2026-10-24.csv) (7 lines, see section 4) |
| Spec this derives from | [Hardware_Map](../Hardware_Map.md) Rev 13 (circuits, pin map, netlist). Design decisions live there, not here |
| Kit list | [f26partskit.pdf](../reference/f26partskit.pdf) (Fall 2026 parts kit, 8/24/2026) |
| Status | **Not yet ordered.** Digi-Key stock comes from cached web pages, not live; check the cart before paying. `VERIFY:` = check on the live site or datasheet |
| Assumption | The class board used the kit parts the way the course BOM says (U1 40-pin, U3 and U7 20-pin, U4 28-pin, U6 16-pin sockets; reset, PSEN, INT0 buttons; LED driver; two 10 uF used) |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed by the student |


## 1. Kit part -> use in this project

| Kit item | Use here |
|---|---|
| AT89C51RC2, 74LS373, SPLD, MAX232, DE-9, 7805 + heat sink, power jack, crystal, 27 pF | Already on the class board, unchanged |
| 16x4 LCD (HD44780 compatible) | The display. The kit's **14-contact** socket strip matches the 14-pin interface (no backlight pins) |
| 24C16 serial EEPROM (DIP-8) | **Preset store** (U10). 1-byte word address, answers at I2C 0x50-0x57, 16-byte pages, `WP` (pin 7) tied low |
| 5.1K resistors x2 | **SDA and SCL pull-ups**. `BUS_INT_N` pull-up: 10 k from the lab |
| Potentiometer | LCD contrast (`V0`) |
| 330 ohm x5 | Button-board LEDs, spare |
| LEDs (2 red, 2 green) | Button-board indicators (the class board already has its status and power LEDs) |
| 2N2222 | Q2, the `RST` -> `RST_N` inverter for the '273 `/MR` |
| 2N2907 | Spare |
| 74LS374 | Fallback for the direction latch (section 2), otherwise a spare |
| PCF8574 (DIP-16) | **Phase 3 button board.** One in the kit, enough for one button board |
| Wire-wrap sockets left over: 20-pin x2, 16-pin x2, 14-pin x2, 8-pin x1 | 20-pin: U14 '273 and U16 '244. 16-pin: U11 MCP3008 and U9 74AHC157 (the PCF8574 needs one more 16-pin). 8-pin: U10 24C16 |
| Pin strips (2 x 36), 14-contact socket strip | Headers on the perf boards, LCD mating strip |
| Pushbuttons | 3 are used by the class board; 1 spare. You still need 7 for the panel and 4 per button board |
| 0.1 uF, 1 uF, 4.7 uF, 10 uF, 47 uF, 27 pF | Bypass (0.1 uF; also from the lab), 47 uF for perf-side 5 V bulk. Non-polarized caps and resistors come from the lab |
| 4.7K SIP-10 | Already the P0 pull-up bank (class board R4) |
| MCP4802 SPI DAC | Not used |

### 1a. Modules and parts on hand (not kit, not ordered)

| Part | Use |
|---|---|
| Adafruit KB2040 | A2, USB-MIDI bridge |
| SparkFun bidirectional logic level converter (BSS138) | A3, 5 V <-> 3.3 V for the KB2040 UART |
| TXB0104 breakout | Not used (needs push-pull drivers; the 8051 high is weak) |
| TB6612FNG breakout | A1, drives both motors |
| Pololu TB67H420FTG carrier (board marked md35a) | **Not needed** with two faders (it was the third-motor driver); spare. Note it needs `VIN` >= about 10 V |
| SN74AHC157N | U9, PWM buffers |
| USB-PD trigger module | Not used (power is one 9 V adapter, Hardware_Map section 3.9) |
| Terwin SM100 motor fader(s) | FDR1, FDR2. `VERIFY:` two are on hand |
| RJ45 breakout boards x5 (ordered 2026-10-24) | Daughter bus. Cat 5e cable on hand |
| 6 mm tactile switches, DIP sockets | Spares, so they are not in the order |

## 2. Kit-only fallback: 74LS374 as the direction latch

The order includes a CD74HCT273E (U14) because it has `/MR`, which clears the latch during reset. The kit's 74LS374 has no clear pin, so it powers up with random outputs.

- Pins: 1 `/OC`, 2 Q0, 3 D0, 4 D1, 5 Q1, 6 Q2, 7 D2, 8 D3, 9 Q3, 10 GND, 11 CLK, 12 Q4, 13 D4, 14 D5, 15 Q5, 16 Q6, 17 D6, 18 D7, 19 Q7, 20 VCC (differs from the 273 at pins 1, 6, 7, 16, 17).
- Put a 10 k pull-down on each motor input line and on `STBY`, and hold `/OC` high at power-up with a 4.7 uF from `/OC` to +5 V and 10 k from `/OC` to GND (about 50-100 ms hold-off, `VERIFY:` on the bench); firmware writes `0x00` first thing.
- A manual reset does **not** re-disable the outputs in this scheme, so the last direction can persist for a few milliseconds. The 74AHC157 still forces PWM low during reset, which limits the effect to a brief twitch at most.

## 3. What is in the order

Sockets and tactile buttons are **not** ordered: you have spares. Count what you need: 7 tactile switches for the panel; DIP sockets for U9 (16), U10 (8), U11 (16), U14 and U16 (20 each) and, in Phase 3, the PCF8574 (16). Add them back to the cart (On Shore ED08DT, ED16DT, Omron B3F-1000) if you come up short.

| Item | Why it is not in the kit |
|---|---|
| MCP3008-I/P x2 | U11 fader and pedal ADC (+1 spare) |
| SN74HCT244N x2 | U16 button buffer (no 244/245 in the kit) (+1 spare) |
| CD74HCT273E x2 | U14 direction latch with a defined reset (+1 spare) |
| 10 uF x2, 470 uF x2 | `VREF_F` filter, motor bulk |
| PTC fuse, P6KE15A TVS | Motor rail protection (section 4) |
| 1x40 male header | Wiring |
| Microchip AT42QT1010-TSHR x3 (Digi-Key AT42QT1010-TSHRCT-ND) | A4, A5 fader touch sensors (+1 spare), on SOT23-6 to DIP adapters already on hand. Bare chip, because the SparkFun 12041 breakout has its own touch pad. Cs (10 nF X7R, plus 4.7 and 22 nF to tune), 4.7 k Rs, 100 ohm + 10 uF supply filter and 10 nF output filter come from the lab parts; Hardware_Map section 3.5 |
| Molex 70246-1201 x2, 70246-1001 x2 | J20 (12-pin) and J21 (10-pin) shrouded keyed headers: one on the D-pad board, one on the bottom level (no spares) |
| Adam Tech FCS-12-SG x2, On Shore 101-106 x2, 3M 3365/12 ribbon x3 ft | Home-made J20 and J21 cables, cut to length (section 3e) |

Removed from the first version of the order because the kit or lab has them: 24LC256, 74HC04, all resistors, ceramic caps, trimmer, LEDs, SIP, 1x16 female header, and the 5 V module.

**Still to source (not in this order):** a **9 V DC, 2 A or more** (2.5-3 A preferred) adapter with a 2.1 mm plug for the class board jack (Hardware_Map section 3.9; the course adapter is only 500 mA); pot-board ADC (`OPEN` #3; the PCF8591P listed here before is discontinued); 4-position DIP switches; tactiles for the button board; a 1/4" TRS jack for the pedal; a second fader if only one is on hand.

## 3e. Panel cables J20 and J21 (Hardware_Map section 3.13)

Home-made cables (team decision 2026-10-24): about half the cost of ready-made Samtec cables (roughly $5-8 against $12-16) and any length.

| Item | Part | Qty | Notes |
|---|---|---|---|
| 12-pin socket (J20) | Adam Tech FCS-12-SG: 2x6, 2.54 mm, IDC, **polarizing key**, gold | 2 | Digi-Key 2026-10-24: about 2,100 in stock, sold singly. (The Assmann AWP 12-7540-T is not sold in single quantities; the AWP 12-8540-T has no key.) |
| 10-pin socket (J21) | On Shore Technology 101-106: 2x5, 2.54 mm, IDC, polarizing key, gold | 2 | Listed on Digi-Key 2026-10-24; `VERIFY:` single-quantity stock. Alternates: Adam Tech FCS-10-SG (same family as the 12-pin, not confirmed) or 3M 89110-0101 (not the -0101HA) |
| Ribbon | 3M 3365/12, 12 conductors, 0.050 in pitch, 28 AWG (Digi-Key 3M157990-100-ND, ordered by the foot) | 3 ft | One ribbon for both cables: for J21 peel 2 conductors off the edge away from the red stripe |
| 12-pin header | Molex 70246-1201 (Digi-Key 23-0702461201-ND): vertical, shrouded, keying slot | 2 | Unchanged |
| 10-pin header | Molex 70246-1001: same family | 2 | Unchanged; `VERIFY:` Digi-Key stock. Alternates: 3M N2510-6002RB (vertical) or 3M D2510-5002-AR (Digi-Key MHE10E-ND, right angle) |

Making the cables:
- **Length:** cut J20 at about 9 in and J21 at about 8 in (team, 2026-10-24), plus about 1/2 in to trim square.
- **Pin 1:** the red stripe is conductor 1. Put it at the socket's pin-1 mark (triangle) at **both** ends, with both sockets facing the same way, so the cable runs pin 1 to pin 1.
- **Pressing:** press each socket squarely in a bench vise (or between two flat boards in a clamp) until the cover latches, then fold the ribbon over and snap on the strain relief if the socket has one.
- **Test** every conductor end to end with a continuity meter, and check that neighbors are not shorted, before plugging in.
- **Height on the D-pad board:** a vertical shrouded header plus the socket is taller than the 10 mm between the D-pad board and the acrylic. Mount J20/J21 on the underside of the D-pad board at an edge with nothing tall below it, or use a right-angle header pointing off the board edge.
- **J22 motor cable and J23 panel jumper:** not in the order; use screw terminals or pin headers and wire already on hand.

## 4. Before you click buy

- **PTC fuse**: the cart export has the **RHEF200** (2 A hold); the upload CSV has the **RHEF300HF-ND** (3 A hold), chosen when there were three motors (about 2.4 A start). With **two** motors (about 1.6 A start, MEASURE) the RHEF200 is enough and trips sooner on a fault; the RHEF300 also works. Pick one and make the cart and the CSV agree.
- The cart export has only the first 7 lines; upload the CSV again (14 lines) rather than reusing the cart.
- The TB6612 runs the motors, so the motor rail must stay at or below 13.5 V (the P6KE15A starts conducting around 14-16 V). Keep PWM duty capped for the 10 V motor.
- Check each line shows **In Stock**; the upload tool may offer substitutes. If a line fails to match, search the manufacturer part number.
- Part numbers I could not confirm: `EEU-FR1E471` (any 25 V parts of those values work). The 10 uF is now the Rubycon 25TWL10MEFC5X11 (Digi-Key 25TWL10MEFC5X11-ND); the Panasonic ECA-1EM100 was out of stock. The TVS uses Digi-Key 4878-P6KE15ACT-ND (P6KE15A).
- Quantities include one spare of each IC; the panel cable sockets and headers have no spares (the 3 ft of ribbon leaves enough to remake a cable). Shipping and tariffs are not included.

## 5. Alternates (not in the upload)

| Need | Alternate | Note |
|---|---|---|
| MCP3008 DIP out of stock | MCP3008-I/SL (SOIC-16) on a SOIC-to-DIP adapter | Adapter not picked |
| HCT244 out of stock | SN74HC244N (296-1582-5-ND) | Stock was 0. HC inputs need about 3.5 V high; the buttons are pulled to 5 V, so it works here |
| HCT273 out of stock | Kit 74LS374 (section 2) | Weaker reset behavior |
| 74xx out of stock | Rochester Electronics marketplace listings on Digi-Key, or Mouser | Same part, different seller |
