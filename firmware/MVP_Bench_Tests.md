# MVP bench tests: 8051 to Reaper over MIDI

| Field | Value |
|---|---|
| File name | `MVP_Bench_Tests.md` |
| Course | ECEN 5613 Embedded System Design, Fall 2026, Final Project |
| Revision | 2, 2026-11-02: firmware requirement noted on every test. 1, 2026-11-02: first draft |
| Covers | The MVP firmware in [src/](src/) (revision 1) and the KB2040 bridge [kb2040/code.py](kb2040/code.py) |
| Hardware spec | [Hardware_Map.md](../Hardware_Map.md) Rev 13.5; net and pin names below are from its Appendix A and the schematic source [design.py](../hardware/kicad/tools/design.py) |
| Status | **DRAFTED.** No test has been run yet |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed by the student. This is a working procedure, not report text |

The MVP is send-only: SW4 on the class board alternates Reaper's Play and Stop, and fader 1 sets track 1's volume, both as Mackie Control (MCU) messages over the KB2040. It needs no SPLD, LCD, button buffer or motor. These tests take the board from powered-off checks to a 30-minute run with Reaper.

## How to use this file

- Run the stages **in order** and stop at the first failure. Each stage relies on the ones before it.
- Every test has **Setup**, **Steps**, **Pass** and **If it fails**. "Pass" is the only acceptance criterion; anything else is a fail.
- The **Firmware** line under each test says whether it needs the MVP flashed into U1 (the 8051), the bridge on the KB2040, both, or neither:

| Stage | 8051 MVP on U1 | KB2040 bridge |
|---|---|---|
| A. Power off | Not needed | Not needed |
| B. Power on | Not needed (any program, or a blank chip) | Not needed |
| C. Build and flash | C2 flashes it | Not needed |
| D. 8051 alone | Required | Not needed |
| E. KB2040 alone | Not needed | Loaded in E2; required from E3 on |
| F. 8051 to PC | Required from F2 on (F1: not needed) | Required |
| G. Calibration | Required; G2 re-flashes the calibrated build | Required |
| H. Reaper | Calibrated build required from H2 on (H1: not needed) | Required |
| I. Endurance | Calibrated build required | Required for I1-I2; not needed for I3 |

- Write every measured value in the [results log](#results-log) at the end, with the date and your initials. Values marked `(MEASURE)` also belong in Hardware_Map.
- Pin references are `U1.11` = U1 pin 11. Schematic connector names are used for the panel cables: **J21** is the class-board end of the 10-pin ribbon and **J31** is the D-pad-board end (Hardware_Map calls both ends J21).

## Equipment and files

| Item | Use |
|---|---|
| 9 V DC, 2 A or more adapter, 2.1 mm plug | Board power (the course's 500 mA adapter also works for the MVP, since the motors stay off) |
| Digital multimeter | Continuity, resistance, voltages, board current |
| LogicPort logic analyzer (course kit) | UART bytes, SPI waveforms, timing |
| Oscilloscope (optional) | Signal levels and edges at the level shifter |
| USB-RS232 adapter and DB9 cable (course kit) | FLIP bootloading |
| USB-C cable | KB2040 to the PC |
| Jumper wire, female-female | KB2040 loopback test (E4) |
| PC software | SDCC 4.6.0 and `make`, Atmel FLIP, MIDI-OX, Reaper, a serial terminal (PuTTY or similar) |
| Files | `build/main.hex` from `make` in `firmware/`; `kb2040/code.py`; the CircuitPython `.uf2` for the Adafruit KB2040 from circuitpython.org |

### Jumper and cable settings for all MVP tests

| Ref | Name | Setting | Why |
|---|---|---|---|
| JP1 | `JP_VM` | **Removed** (except test I4) | Disconnects the motor supply, so the faders cannot move whatever the firmware does |
| JP3 | `JP_BUS` | Removed | No daughter boards in the MVP |
| J11 | RJ45 bus | Nothing plugged in | `BUS_INT_N` is shared with SW4 |
| JP2 | `JP_RX` | 2-3 (PC) for flashing, 1-2 (KB) for everything else | Selects what drives P3.0 |
| J14 | /EA select | 2-3 (+5 V) | Run from internal flash |
| J6 | Current jumper | Installed, or an ammeter across it in B1 | Board current measurement |
| J21/J31 | 10-pin ribbon | Plugged in, pin 1 to pin 1 | Carries +5 V, GND and the ADC SPI lines to the D-pad board |
| J34 | Fader pots | FDR1 connected | Fader 1 wiper to MCP3008 CH0 |

### LogicPort channel plan

| Channel | Net | Pin |
|---|---|---|
| D0 | `MIDI_TX` | U1.11 (P3.1) |
| D1 | `MIDI_RX` | U1.10 (P3.0) |
| D2 | `ADC_CS_N` | U1.3 (P1.2) |
| D3 | `ADC_SCK` | U1.7 (P1.6) |
| D4 | `ADC_MOSI` | U1.8 (P1.7) |
| D5 | `ADC_MISO` | U1.13 (P3.3) |
| D6 | `LED_N` | U1.2 (P1.1) |
| D7 | `BUS_INT_N` (SW4) | U1.12 (P3.2) |
| GND | GND | any board ground |

Serial decode for D0 and D1: asynchronous, 31,250 baud, 8 data bits, no parity, 1 stop bit, idle high. The 8051 actually runs at 31,418 baud (+0.54 %), which decodes correctly at 31,250.

---

## Stage A: Power-off checks

The board is unplugged for every test in this stage. Remove U1 from its socket only if a reading below is confusing; otherwise leave the ICs in.

### A1. Visual inspection

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged, good light, magnifier.

**Steps:**
1. Check every socketed IC is seated, with pin 1 matching the socket's notch: U1, U3, U6, U7, U9, U11 (D-pad board), U14, U16 (D-pad board).
2. Check U4 (NVSRAM) is removed (Hardware_Map section 2). Note whether U7 holds the Lab 3 image or `final.pld`.
3. Check the A3 level shifter's HV side faces the 5 V wiring and its LV side faces the KB2040.
4. Check the KB2040's 5 V/RAW pin has no wire on it.
5. Check the J21/J31 ribbon's red stripe is at pin 1 on both ends.
6. Look for solder bridges, loose wire-wrap, and stray wire clippings on both levels.

**Pass:** All six checks hold. Record U7's image in the log.

**If it fails:** Fix before going on. A reversed IC must be checked for damage after correction.

### A2. Supply rails are not shorted

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged, DMM on resistance.

**Steps:** Measure from each net to its ground, then reverse the probes and measure again:

| Net | Measure at | To | Pass |
|---|---|---|---|
| +5 V | U1.40 | U1.20 (GND) | More than 100 ohm both ways |
| `VRECT` | U2 pin 1 (7805 input) | GND | More than 1 kohm |
| `VM` | A1 `VM` | GND | Open or more than 10 kohm (JP_VM removed) |
| `VREF_F` | U11.16 | U11.14 (GNDA) | More than 100 ohm |
| +5 V to `VREF_F` | U1.40 | U11.16 | About 100 ohm (R32) |
| GND to GNDA | U1.20 | U11.14 | Under 1 ohm (NT1 tie) |

**Pass:** Every row in range.

**If it fails:** Find the short before applying power; a short on +5 V is usually a solder bridge or a reversed electrolytic cap.

### A3. Continuity: MIDI link

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged, DMM on continuity. Remove the `JP_RX` jumper for this test.

**Steps:** Check each pair beeps (under 1 ohm):

| Net | From | To |
|---|---|---|
| `MIDI_TX` | U1.11 | U6.11 (MAX232 T1IN) |
| `MIDI_TX` | U1.11 | A3 HV1 |
| `KB_RX_3V3` | A3 LV1 | KB2040 D1 (RX) |
| `KB_TX_3V3` | KB2040 D0 (TX) | A3 LV2 |
| `KB_TX_5V` | A3 HV2 | JP2 pin 1 |
| `MIDI_RX` | JP2 pin 2 | U1.10 |
| `PC_RX` | JP2 pin 3 | U6.12 (MAX232 R1OUT) |
| +5 V | A3 HV | U1.40 |
| `KB_3V3` | A3 LV | KB2040 3V3 |
| GND | A3 GND (both sides) | U1.20 |
| GND | KB2040 GND | U1.20 |

**Pass:** All pairs connected.

**If it fails:** Re-wire against Hardware_Map A.11 and A.10.

### A4. Isolation: things that must not be connected

**Firmware:** Not needed. The board is unpowered.

**Setup:** As A3 (`JP_RX` jumper still removed).

**Steps:** Check each pair does **not** beep:

| From | To | Why |
|---|---|---|
| U6.12 (R1OUT) | U1.10 (P3.0) | The original class-board wire must be lifted, or the MAX232 fights the KB2040 |
| KB2040 5 V/RAW | U1.40 (+5 V) | The KB2040 is USB-powered; joining the rails back-feeds the PC's USB port |
| KB2040 3V3 | U1.40 (+5 V) | Would put 5 V on the RP2040 |
| KB2040 D0, D1 | U1.11, U1.10 directly | KB2040 pins are not 5 V tolerant; they must go through A3 |
| U1.11 | U1.10 | TX and RX must not be shorted |

**Pass:** No pair connected.

**If it fails:** Stop. Fix the wiring; a 5 V connection to a KB2040 pin can destroy it.

Put the `JP_RX` jumper back on 1-2 after this test.

### A5. Continuity: ADC and fader 1

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged, ribbon J21-J31 and J34 connected.

**Steps:**

| Net | From | To |
|---|---|---|
| `ADC_CS_N` | U1.3 | U11.10 (via J21/J31 pin 9) |
| `ADC_SCK` | U1.7 | U11.13 (via J21/J31 pin 5) |
| `ADC_MOSI` | U1.8 | U11.11 (via J21/J31 pin 7) |
| `ADC_MISO` | U1.13 | U11.12 (via J21/J31 pin 8) |
| +5 V | U1.40 | J31 pin 1 |
| GND | U1.20 | J31 pins 2 and 6 |
| `VREF_F` | U11.15 (VREF) | U11.16 (VDD) |
| `VREF_F` | U11.16 | J34 pin 1, then FDR1 pin 1 |
| `FADER1_W` | J34 pin 2 | FDR1 wiper pin (see A6) |
| GNDA | J34 pin 4 | FDR1 pin 3 and U11.14 |
| `FADER1_ADC` | U11.1 (CH0) | R33 (1 k), R34 (1 M) and C33 (100 nF) junction |

Also check the ribbon: no two neighboring pins of J31 are connected to each other (except pins 2 and 6, both GND).

**Pass:** All pairs connected; no neighbor shorts on the ribbon.

**If it fails:** Re-press or replace the ribbon connector, or fix the wire.

### A6. Fader 1 pot and wiper pin (`VERIFY:` in Hardware_Map 3.5)

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged. Unplug FDR1 from J34 so the board does not load the readings.

**Steps:**
1. Measure FDR1 pin 1 to pin 3: record it.
2. Put the knob at the bottom of its travel (the end nearest you as mounted). Measure pin 2 to pin 3 and pin 2 to pin 1.
3. Move the knob to the top. Measure the same two.
4. Move it to the middle. Measure the same two.
5. Reconnect FDR1 to J34.

**Pass:**
- Pin 1 to pin 3 is 8-12 kohm (10 kohm plus or minus 20 %).
- Pin 2 to pin 3 changes smoothly with travel, from under 500 ohm at one end to near the full value at the other (the datasheet allows up to 500 ohm residual at each end). This confirms pin 2 is the wiper.
- Record which end gives the low pin 2 to pin 3 value. Pin 3 is GNDA, so that end reads low on the ADC. If it is the **top** end, the firmware needs `FADER_INVERT 1` (set in G2).

**If it fails:** If pin 2 does not track the knob, find the pin that does and fix J34's wiring to match. Record the result in Hardware_Map.

### A7. Continuity: SW4, LED, reset and motor-off nets

**Firmware:** Not needed. The board is unpowered.

**Setup:** Board unplugged.

**Steps:**

| Net | From | To | Pass |
|---|---|---|---|
| `BUS_INT_N` | U1.12 | SW4 | Connected |
| `BUS_INT_N` | U1.12 | GND with SW4 pressed | Connected only while pressed |
| `BUS_INT_N` pull-up | U1.12 | U1.40 | About 10 kohm (R13) |
| `LED_N` | U1.2 | R7 (4.7 k) | Connected |
| `PWM0` | U1.4 | U9.2 | Connected |
| `PWM1` | U1.5 | U9.5 | Connected |
| `PWM0_EN` | U9.4 | A1 `PWMA` | Connected |
| `PWM1_EN` | U9.7 | A1 `PWMB` | Connected |
| `RST` | U1.9 | U9.15 (/G) | Connected |
| `RST` | U1.9 | R9, Q2 base side | Connected |
| `RST_N` | Q2 collector | U14.1 (/MR) | Connected |
| `MOT_STBY` | U14.16 | A1 `STBY` | Connected |
| `MOT_STBY` | A1 `STBY` | GND | About 10 kohm (R8) |
| U9 select | U9.1 | GND | Connected |

**Pass:** Every row as stated.

**If it fails:** Fix against Hardware_Map A.4, A.6 and A.7.

---

## Stage B: Power on

The KB2040 stays unplugged from USB in this stage.

### B1. First power and board current

**Firmware:** Not needed. Any program in U1, or a blank chip, is fine.

**Setup:** All jumpers per the [table](#jumper-and-cable-settings-for-all-mvp-tests), except J6: remove the J6 jumper and connect the DMM (current, 2 A range first) across J6's two pins. SW1 off. Plug in the adapter.

**Steps:**
1. Turn SW1 on. Watch D6 (power LED) and the DMM.
2. If the current is under 1 A, switch the DMM to a lower range and read it.
3. After 1 minute, touch the 7805 (U2) heat sink.
4. Turn SW1 off, put the J6 jumper back.

**Pass:** D6 lights. Current is steady and below 350 mA; Hardware_Map 3.9 puts the class board alone at 100-150 mA (record it, `(MEASURE)`). The 7805 is warm at most.

**If it fails:** Above 350 mA or rising: turn off at once and look for a reversed IC or a short. D6 dark: check the adapter, SW1 and J6.

### B2. Rail voltages

**Firmware:** Not needed. Any program in U1, or a blank chip, is fine.

**Setup:** SW1 on, J6 jumper in. DMM on DC volts, negative probe on U1.20.

**Steps and pass:**

| Net | Measure at | Pass |
|---|---|---|
| `VRECT` | U2 pin 1 | 7-11 V with a 9 V adapter (record it); must be below 13.5 V, the TB6612's limit |
| +5 V | U1.40 | 4.75-5.25 V |
| +5 V | A3 HV | Same as U1.40 within 0.05 V |
| +5 V at the panel | J31 pin 1 | Within 0.1 V of U1.40 |
| `VREF_F` | U11.16 (negative probe on U11.14) | 4.8-5.0 V (a little under +5 V because of R32) |
| `VM` | A1 `VM` | Under 0.5 V (JP_VM removed) |

**If it fails:** Low +5 V with high current: a short. `VRECT` above 13.5 V: use a different adapter before installing JP_VM. Low panel +5 V: ribbon or connector problem.

### B3. Reset circuit and the motor-off path

**Firmware:** Not needed. Any program in U1, or a blank chip, is fine.

**Setup:** As B2. Whatever program is in U1's flash may be running; that is fine.

**Steps:**
1. Measure `RST` (U1.9): record it.
2. Hold SW2 (reset) and measure `RST` again.
3. Still holding SW2, measure `RST_N` (U14.1), `PWM0_EN` (U9.4) and `PWM1_EN` (U9.7).
4. Release SW2 and measure `RST_N` again.
5. Measure `MOT_STBY` at A1 `STBY`.

**Pass:**
- `RST` under 0.3 V when running, above 3.5 V while SW2 is held.
- While SW2 is held: `RST_N` under 0.4 V, and both `PWM0_EN` and `PWM1_EN` under 0.4 V (U9 forced low by `RST` on /G).
- After release: `RST_N` above 4.5 V.
- `MOT_STBY` under 0.4 V.

**If it fails:** `RST_N` stuck: check Q2's pin order (E-B-C) and R9/R10. `PWM_EN` not low in reset: check U9.15 is on `RST`. `MOT_STBY` high: check R8, and note that U14 may hold random data if U7 is not running `final.pld`; the MVP firmware's PWM-low setting (D2) is the protection in that case.

---

## Stage C: Build and flash

### C1. Build

**Firmware:** Not needed. This test builds it on the PC.

**Setup:** PC, a shell in `firmware/`.

**Steps:**
1. Run `make clean`, then `make`.
2. Open `build/main.mem` and note the sizes.

**Pass:** No warnings or errors; the last line is `packihx: ... OK`; `build/main.hex` exists. `main.mem` shows EXTERNAL RAM under 1024 bytes and ROM under 32768 bytes (2026-11-02 build: 175 bytes and about 1.7 KB).

**If it fails:** Check `sdcc --version` reports 4.6.0 and that `sdcc` and `packihx` are on PATH.

### C2. Flash with FLIP

**Firmware:** This test flashes the MVP into U1. Everything from D1 on needs it.

**Setup:** SW1 off. `JP_RX` on **2-3 (PC)**. DB9 cable from J5 to the USB-RS232 adapter. KB2040 USB unplugged.

**Steps:**
1. Turn SW1 on.
2. Hold SW3 (PSEN). Press and release SW2 (reset). Release SW3. The 8051 is now in its bootloader.
3. In FLIP: select device AT89C51RC2, RS232, the adapter's COM port and the baud rate you used in the labs, then connect.
4. Load `build/main.hex`. Tick Erase, Blank Check, Program and Verify. Run.
5. Turn SW1 off. Move `JP_RX` to **1-2 (KB)**.

**Pass:** FLIP connects and reports a successful verify.

**If it fails:** FLIP will not connect: repeat step 2 (SW3 must be held while SW2 is released), check `JP_RX` is on 2-3, check the COM port. Verify fails: re-flash once; if it fails again, check U1 is seated and J14 is on 2-3.

---

## Stage D: The 8051 on its own

KB2040 USB still unplugged. `JP_RX` on 1-2. The KB2040 side being unpowered is safe: A3's LV side then has no supply and does not back-feed the KB2040.

### D1. Heartbeat LED: firmware and 1 ms tick are running

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** SW1 on. LogicPort D6 on `LED_N` (U1.2).

**Steps:**
1. Watch D8 (status LED).
2. Capture 10 s on the LogicPort and measure the period of `LED_N`.

**Pass:** D8 blinks steadily, about 0.5 s on and 0.5 s off. The measured period is 1.000-1.025 s (the tick is reloaded in software and runs 1-2 % slow; record it).

**If it fails:** No blink: the program is not running. Check J14 is on 2-3, re-check C2's verify, and check `RST` is low (B3). Blinks at a very different rate: the crystal is not 11.0592 MHz or X2 mode is set.

### D2. Motor PWM pins held low

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** As D1.

**Steps:** Measure U1.4 (P1.3), U1.5 (P1.4), U9.4 (`PWM0_EN`) and U9.7 (`PWM1_EN`).

**Pass:** All four under 0.4 V.

**If it fails:** If U1.4/U1.5 are high, the firmware's `PWM0 = 0; PWM1 = 0;` in `main()` is not running; re-check D1 and the flashed file. Do not install JP_VM until this passes.

### D3. Start-up MIDI burst, baud rate and framing

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** LogicPort D0 on `MIDI_TX` (U1.11), async decode at 31,250 baud. Trigger on the first falling edge of D0. Fader 1 resting anywhere.

**Steps:**
1. Arm the LogicPort, then press and release SW2 (reset).
2. Measure the width of one bit (the start bit of the first byte).
3. Read the decoded bytes in the first 300 ms after reset.
4. Measure the time from the first byte to the last byte of the burst.

**Pass:**
- The line idles high (about 5 V) between bytes.
- One bit is 31.8 us (31.5-32.1 us).
- The decoded bytes, in order, are `90 68 7F` (touch on), then `E0 ll mm` (fader position), then about 250 ms later `90 68 00` (touch off). Nothing else.
- `ll` and `mm` are both 0x00-0x7F. The 14-bit value is `mm x 128 + ll`; with the default calibration it divides by 16 to about the ADC reading.

**If it fails:** Wrong bit width: Timer 2 reload or crystal. Framing errors: check the decode settings (8-N-1). No bytes at all but D1 passes: check `T2CON`, `SCON` and that U1.11 is not loaded down (A3 or MAX232 wiring).

### D4. SW4 sends Play and Stop

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** As D3, trigger on the first falling edge of D0 after arming.

**Steps:**
1. Press SW4 and hold it 1 s, then release. Capture.
2. Repeat three more times.
3. Tap SW4 quickly (about 5 taps per second) ten times. Capture.
4. Hold SW4 for 5 s.

**Pass:**
- Press 1 sends `90 5E 7F` (Play), its release `90 5E 00`.
- Press 2 sends `90 5D 7F` (Stop), its release `90 5D 00`. Presses 3 and 4 repeat this pattern.
- Each press gives exactly one 3-byte message and each release exactly one; the 5 s hold sends nothing after the press message.
- Ten quick taps give ten press/release pairs (taps shorter than 20 ms may be ignored by design).
- The press message starts 20-25 ms after `BUS_INT_N` (LogicPort D7) goes low (the debounce time).

**If it fails:** No message: check `BUS_INT_N` goes low when pressed (D7). Doubled messages: contact bounce longer than 20 ms; raise `SW4_DEBOUNCE_MS` in [src/main.c](src/main.c).

### D5. MCP3008 SPI waveform

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** LogicPort D2-D5 on `ADC_CS_N`, `ADC_SCK`, `ADC_MOSI`, `ADC_MISO`. Trigger on the falling edge of `ADC_CS_N`. Sample at least 1 MHz.

**Steps:**
1. Capture 50 ms.
2. Zoom into one `ADC_CS_N` low pulse.
3. Measure the SCK period, the length of one `ADC_CS_N` low pulse, and the time between groups.

**Pass:**
- Every 10 ms (10.0-10.3 ms) there is a group of 4 `ADC_CS_N` low pulses.
- Each low pulse has exactly 16 `ADC_SCK` pulses; SCK idles low.
- `ADC_MOSI` on the first 5 rising edges reads 1, 1, 0, 0, 0 (start, single-ended, channel 0).
- `ADC_MISO` reads 0 after the falling edge of clock 6 (null bit), then 10 data bits.
- `ADC_CS_N` is high between conversions; `ADC_MISO` is high or floating while `ADC_CS_N` is high.
- Record the SCK frequency and the conversion time `(MEASURE)`; Hardware_Map 1.2 estimates about 0.2 ms per channel. `VERIFY:` the SCK frequency is above the MCP3008 datasheet's minimum clock rate.

**If it fails:** No activity on SCK: firmware not reaching `fader_task` (check D1). MISO stuck high or low: check `VREF_F`/power at U11 and the MISO wire. Wrong MOSI bits: check the D4 wiring order on the analyzer first.

### D6. ADC reading matches the voltage

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** DMM on DC volts across U11.1 (CH0) and U11.14 (GNDA). LogicPort as D5, with D0 also on.

**Steps:** For the knob at the bottom, middle and top:
1. Measure the voltage at U11.1 (`V1`) and at U11.15 (`VREF`).
2. Expected code = 1024 x `V1` / `VREF`, rounded down, capped at 1023.
3. Read the 10 data bits on MISO in one conversion, or move the fader slightly and use the `E0` message on D0 (14-bit value / 16).

**Pass:** The reading is within 4 counts of the expected code at all three positions.

**If it fails:** Off by a constant factor: `VREF` is not `VREF_F`. Off by a power of two: the firmware is reading one clock early or late (check the null bit in D5). Noisy by more than 10 counts: check the GNDA tie (NT1) and the 100 nF at CH0.

### D7. Fader messages on the UART

**Firmware:** Required: the MVP on U1 (flashed in C2). The KB2040 is not used.

**Setup:** LogicPort D0 on `MIDI_TX`, decode on, capture 20 s.

**Steps:**
1. Leave the fader still for 5 s.
2. Move the fader slowly from bottom to top over about 3 s, then stop.
3. Leave it still for 10 s.
4. Move it quickly from top to bottom, then stop.

**Pass:**
- While still: no bytes at all (after any earlier touch-off).
- On each move: first `90 68 7F`, then `E0 ll mm` messages no closer together than 10 ms, with values rising as the fader rises (or falling, if A6 found the ends reversed).
- About 250 ms after the fader stops: `90 68 00`.
- No message is cut short or interleaved with another.

**If it fails:** Messages while still: noise above the 4-count deadband; record the spread and go to G3. Values move the wrong way: expected if A6 found the top reads low; fixed in G2.

---

## Stage E: The KB2040 bridge on its own

Board power off for E1-E3. Disconnect the KB2040's D0 and D1 from A3 for E4 (or hold SW2 for the whole of E4, so the 8051 stays in reset and sends nothing).

### E1. Install CircuitPython

**Firmware:** Not needed on U1. This test installs CircuitPython on the KB2040.

**Steps:**
1. Hold the KB2040's BOOT button and plug its USB-C into the PC. A drive named `RPI-RP2` appears.
2. Copy the KB2040 CircuitPython `.uf2` onto it. The board restarts and a drive named `CIRCUITPY` appears.
3. Record the CircuitPython version (in `CIRCUITPY/boot_out.txt`).

**Pass:** `CIRCUITPY` appears.

**If it fails:** Try another cable (some are power-only) and USB port.

### E2. Load the bridge and check for errors

**Firmware:** Not needed on U1. This test loads the bridge (`code.py`) onto the KB2040.

**Steps:**
1. Copy [kb2040/code.py](kb2040/code.py) to `CIRCUITPY/code.py`.
2. Open the KB2040's USB serial port in a terminal (PuTTY, 115200 baud; the port appears in Device Manager under Ports).
3. Press Ctrl+C, then Ctrl+D to restart the program, and watch the output.

**Pass:** The program restarts with no traceback (no `Traceback` or `Error` lines).

**If it fails:** `AttributeError` on `board.TX`/`board.RX`: change them to `board.D0` and `board.D1`. `ImportError` on `usb_midi`: the CircuitPython build lacks it; use a current release.

### E3. USB-MIDI device appears

**Firmware:** Not needed on U1. Required: the bridge on the KB2040 (E2).

**Steps:**
1. Open Device Manager and look under "Sound, video and game controllers".
2. Open MIDI-OX, Options, MIDI Devices.

**Pass:** The KB2040 is listed as a MIDI device (record its exact name) in both MIDI-OX's input and output lists.

**If it fails:** Unplug and replug the USB. Check `boot.py` on `CIRCUITPY` does not disable `usb_midi`.

Only one Windows program can open a MIDI port at a time. Close Reaper whenever MIDI-OX is using the KB2040, and close MIDI-OX before stage H.

### E4. Loopback: USB to UART and back

**Firmware:** Not needed on U1: the 8051 is disconnected or held in reset. Required: the bridge on the KB2040 (E2).

**Setup:** KB2040 D0 and D1 disconnected from A3 (or the 8051 held in reset with SW2). A jumper wire from D0 to D1.

**Steps:**
1. In MIDI-OX, open the KB2040 as both input and output and open the input monitor.
2. Send Note On/Off messages from MIDI-OX's keyboard window, then move its pitch-bend control.
3. Remove the jumper wire and send again.
4. Reconnect D0 and D1 to A3, then repeat the A3 continuity checks for those two wires.

**Pass:** With the jumper, every message sent appears in the input monitor, unchanged, at once. Without it, nothing comes back.

**If it fails:** Nothing echoes: check the jumper is on D0-D1, and the program is running (E2). Echoes are corrupted: check the `BAUD` value in `code.py`.

---

## Stage F: 8051 through the KB2040 to the PC

### F1. Level shifter supply and idle levels

**Firmware:** Not needed on U1 (idle levels only). Required: the bridge on the KB2040 (E2), which also powers A3's LV side.

**Setup:** Plug the KB2040's USB in first (it supplies A3's LV reference), then turn SW1 on. `JP_RX` on 1-2.

**Steps and pass:**

| Point | Pass |
|---|---|
| A3 HV | 4.75-5.25 V |
| A3 LV | 3.2-3.4 V |
| A3 LV1 = KB2040 D1 (idle) | 3.2-3.4 V |
| A3 HV1 = U1.11 (idle) | Above 4.5 V |
| KB2040 D0 (idle) | 3.2-3.4 V |
| A3 HV2 = JP2 pin 1 (idle) | Above 4.5 V |
| U1.10 (P3.0, idle) | Above 4.5 V |

**If it fails:** LV at 0 V: the KB2040's 3V3 wire is missing. HV2 low: the KB2040's TX is not idling high (program not running) or LV2/HV2 are swapped.

### F2. Signal through the level shifter

**Firmware:** Required: the MVP on U1 (C2) and the bridge on the KB2040 (E2).

**Setup:** Scope (or LogicPort) on U1.11 and A3 LV1 at the same time. Trigger on U1.11 falling.

**Steps:** Press SW4.

**Pass:** LV1 shows the same bytes as U1.11, swinging 0 to about 3.3 V, with edges clean enough that every bit reaches its level well within a 32 us bit.

**If it fails:** Slow or rounded edges: check A3's pull-ups are present on both sides.

### F3. MIDI-OX sees the 8051's messages

**Firmware:** Required: the MVP on U1 (C2) and the bridge on the KB2040 (E2).

**Setup:** Reaper closed. MIDI-OX input monitor on the KB2040.

**Steps:**
1. Press SW2 (reset).
2. Press and release SW4 four times.
3. Move the fader slowly over its full travel, then stop.
4. Use the board for 5 minutes, mixing SW4 presses and fader moves.

**Pass:**
- After reset: Note On channel 1, note 0x68, velocity 127; a pitch bend on channel 1; about 250 ms later note 0x68 velocity 0.
- SW4: the Play/Stop pattern of D4, as Note On channel 1, notes 0x5E and 0x5D.
- Fader: touch on, pitch bends on channel 1 following the fader, touch off.
- Over 5 minutes: no message that was not caused by SW4 or the fader, and no corrupted or missing messages.

**If it fails:** Nothing arrives but D3 and E4 passed: check A3 channel 1 (U1.11 to HV1, LV1 to D1). Messages arrive corrupted: check the KB2040's ground to the board.

### F4. PC to 8051, and the 8051 survives heavy input

**Firmware:** Required: the MVP on U1 (C2) and the bridge on the KB2040 (E2).

**Setup:** LogicPort D1 on `MIDI_RX` (U1.10), decode on. MIDI-OX output open on the KB2040.

**Steps:**
1. Send a few notes from MIDI-OX's keyboard window.
2. Send a long SysEx file or a fast stream of messages for 30 s (MIDI-OX's SysEx window, or hold several keys and move the pitch-bend control continuously).
3. During step 2, press SW4 a few times and watch D8.

**Pass:**
- The LogicPort shows the sent bytes on U1.10 at 31,250 baud, idling high at 5 V.
- During the flood, D8 keeps blinking at the same rate and SW4 messages still reach MIDI-OX's input monitor.

**If it fails:** No bytes on U1.10: check `JP_RX` on 1-2 and A3 channel 2 (D0 to LV2, HV2 to JP2 pin 1). The LED stops during the flood: the receive interrupt or main loop is stuck; capture what was sent and report it.

---

## Stage G: Calibrate fader 1

### G1. Measure the ends

**Firmware:** Required: the MVP on U1 (C2) and the bridge on the KB2040 (E2).

**Setup:** As F3.

**Steps:**
1. Push the fader firmly to the bottom stop and wait for the touch-off note.
2. Move it up slightly and back down to the stop; repeat three times. Record the last pitch-bend value each time.
3. Do the same at the top stop.
4. Convert each 14-bit value to an ADC count: `adc = value x 1023 / 16383`, rounded.
5. Cross-check one reading at each stop with the DMM, as in D6: count = 1024 x (U11.1 voltage) / (U11.15 voltage). The deadband means the last message can be up to 3 counts from the true stop reading; the DMM is not limited that way.

**Pass:** The counts at each stop agree within 4, including the DMM value. If the bottom stop gives the high counts, the fader is reversed: replace every count with 1023 minus that count, and note it for G2. Then record:
- `ADC_BOTTOM` = the **highest** count seen at the bottom stop.
- `ADC_TOP` = the **lowest** count seen at the top stop.

**If it fails:** Counts spread by more than 4 at a stop: noisy wiper or ground; check NT1 and the RC at CH0 before calibrating.

### G2. Put the calibration into the firmware

**Firmware:** This test rebuilds the MVP with the calibration values and re-flashes U1 (C1, C2). Everything after it uses the calibrated build.

**Steps:**
1. In [src/main.c](src/main.c), set `FADER_ADC_MIN` to `ADC_BOTTOM + 2` and `FADER_ADC_MAX` to `ADC_TOP - 2`, so the stops always clamp to the ends. If G1 found the fader reversed, also set `FADER_INVERT` to 1 (the G1 values are already converted).
2. Rebuild (C1), reflash (C2), move `JP_RX` back to 1-2.
3. Record the values in the log and in Hardware_Map 3.5.

**Pass:** The build has no warnings.

### G3. Check the full range and the rest noise

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Setup:** As F3.

**Steps:**
1. Move the fader to the bottom stop, then the top stop.
2. Leave the fader still for 60 s.

**Pass:**
- At the bottom stop the last message is pitch bend 0 (`E0 00 00`); at the top stop it is 16383 (`E0 7F 7F`).
- Moving up always gives rising values.
- No messages during the 60 s rest.

**If it fails:** Messages at rest: raise `FADER_DEADBAND` to 6 or 8, or `FADER_SAMPLES` to 8, rebuild, and repeat; record what was needed. The ends do not reach 0/16383: widen the margins in G2 from 2 to 4.

---

## Stage H: Reaper

### H1. Set up the Mackie Control surface

**Firmware:** Not needed on U1: this only sets up Reaper. Required: the bridge on the KB2040 (E2).

**Setup:** MIDI-OX closed. Reaper open with a new project containing two tracks.

**Steps:**
1. Options, Preferences, Audio, MIDI Devices: check the KB2040 is listed under inputs and outputs.
2. Preferences, Control/OSC/Web, Add, Mackie Control Universal. Set MIDI input and MIDI output to the KB2040. Leave the surface offset at 0. OK.
3. Record the exact settings used.

**Pass:** The surface is added without an error message.

**If it fails:** The KB2040 is not offered: some setups need it enabled under MIDI Devices first (the README says to enable its input and output there). If enabling it there makes SW4 notes also reach armed tracks as MIDI input, disable it there again and check the surface still works. Record which setting works. `VERIFY:` that Reaper's MCU mode needs no SysEx handshake (Hardware_Map section 5).

### H2. SW4 controls the transport

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Steps:**
1. Press SW4.
2. Wait 5 s, press SW4 again.
3. Repeat twice.

**Pass:** The first press starts playback (the play cursor moves); the second stops it; the pattern repeats.

**If it fails:** No reaction but F3 passed: the surface is not listening to the KB2040 (H1). Reaper reacts to the release instead of the press: record it.

### H3. Fader 1 controls track 1's volume

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Steps:**
1. Move fader 1 slowly from bottom to top, watching track 1's volume fader in Reaper's mixer.
2. Move it to the middle and stop.
3. Check track 2's volume.

**Pass:**
- Track 1's volume follows the physical fader smoothly with no visible lag (under about 50 ms).
- Bottom = -inf dB. Top = Reaper's maximum for an MCU fader (record the dB value, `(MEASURE)`).
- Track 2 does not change.

**If it fails:** Track 1 does not move but F3 passed: check the surface offset is 0 and track 1 is in the first bank. Moves in steps: the deadband is too large (G3).

### H4. Reaper's feedback does not upset the 8051

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Setup:** LogicPort D1 on `MIDI_RX` (U1.10).

**Steps:**
1. Start playback with SW4. Drag track 1's volume with the mouse in Reaper.
2. Watch U1.10 on the LogicPort and D8 on the board.
3. Move the physical fader.

**Pass:**
- Reaper sends bytes to the board (`E0` messages when track 1's volume changes; other MCU traffic while playing), seen on U1.10.
- D8 keeps blinking at the same rate; SW4 still works.
- When the physical fader moves, track 1 jumps to the fader's position. That is expected: the fader has no motor in the MVP, so it does not follow Reaper.

**If it fails:** The 8051 stops responding during playback: capture U1.10 and report; the receive buffer or interrupt needs work.

### H5. Known MVP limitation: transport state can get out of step

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Steps:**
1. Start playback with SW4.
2. Stop playback with the spacebar in Reaper.
3. Press SW4 once, then again.

**Pass (expected behavior):** The first press sends Stop, so nothing happens; the second press starts playback. This is a known limit: the firmware remembers only what it last sent, and it will be fixed when the MIDI parser (M4) reads Reaper's transport LEDs.

### H6. Reconnection

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Steps:**
1. With Reaper open and the surface working, unplug the KB2040's USB for 5 s and plug it back in.
2. Try SW4 and the fader.
3. If they do not work, close and reopen the surface (Preferences, Control/OSC/Web, edit the surface, OK) or restart Reaper.

**Pass:** The 8051 keeps blinking throughout. Record what Reaper needed to work again.

---

## Stage I: Endurance and safety

### I1. 30-minute run

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Setup:** Reaper playing a project (loop a section). Board on the 9 V adapter.

**Steps:**
1. Every few minutes, move the fader and press SW4 twice.
2. At the end, touch the 7805 heat sink and the bridge diodes D1-D4.
3. Measure the board current at J6 (as B1) at the end.

**Pass:** D8 never stops blinking; every SW4 press and fader move takes effect; Reaper never shows a stuck state; the 7805 and diodes are warm at most. Record the current.

**If it fails:** Record the time and what stopped working, then capture U1.10 and U1.11 on the LogicPort when it happens again.

### I2. Power-cycle and reset

**Firmware:** Required: the calibrated MVP on U1 (G2) and the bridge on the KB2040 (E2).

**Steps:**
1. Turn SW1 off and on five times, 5 s apart.
2. With the board running, press SW2 five times, once during a fader move.

**Pass:** Each time, D8 resumes blinking within 1 s, the start-up burst of D3 is sent, and track 1 jumps to the fader position (expected). No other notes are sent.

### I3. Motor stays off with the motor supply connected

**Firmware:** Required: the MVP on U1. This test checks the MVP's motor-off setting; with any other program in U1 the faders could move, so do not run it without the MVP. The KB2040 is not needed.

Run this once, last, to confirm the firmware's motor-off setting with real motor power.

**Setup:** SW1 off. Install JP_VM. Have your hand on SW1.

**Steps:**
1. Turn SW1 on. Watch both faders.
2. Measure `VM` at A1, `MOT_STBY`, A1 `PWMA` and `PWMB`, and the voltage across each motor (A1 `AO1` to `AO2`, `BO1` to `BO2`).
3. Move both faders by hand.
4. Press SW2 ten times, watching the faders.
5. Turn SW1 off and remove JP_VM.

**Pass:**
- Neither fader moves on its own at power-up, during resets, or while running.
- `VM` is 7-10 V (record it; Hardware_Map 3.9 expects about 7.6 V from a 9 V adapter). `MOT_STBY`, `PWMA` and `PWMB` are under 0.4 V. Each motor's voltage is under 0.2 V.
- Both faders move freely by hand (no braking).

**If it fails:** A fader moves: turn SW1 off at once, remove JP_VM, and check D2 and B3 again. A fader resists hand movement: the driver is braking; check `MOT_STBY` and the '273 outputs (U14.2, U14.5, U14.6, U14.9).

---

## Results log

Fill in one row per test run. Keep failed runs; add a new row when you repeat a test.

| Test | Date | By | Result | Measured values | Notes |
|---|---|---|---|---|---|
| A1 | | | | U7 image: | |
| A2 | | | | | |
| A3 | | | | | |
| A4 | | | | | |
| A5 | | | | | |
| A6 | | | | Pin 1-3: kohm. Low end: top / bottom | |
| A7 | | | | | |
| B1 | | | | Current: mA | |
| B2 | | | | VRECT: V, +5 V: V, VREF_F: V | |
| B3 | | | | RST run/reset: V / V | |
| C1 | | | | ROM: bytes, XRAM: bytes | |
| C2 | | | | FLIP port and baud: | |
| D1 | | | | LED period: s | |
| D2 | | | | | |
| D3 | | | | Bit width: us | |
| D4 | | | | Press to message: ms | |
| D5 | | | | SCK: kHz, conversion: ms | |
| D6 | | | | Bottom/middle/top: expected vs read | |
| D7 | | | | | |
| E1 | | | | CircuitPython version: | |
| E2 | | | | | |
| E3 | | | | Device name: | |
| E4 | | | | | |
| F1 | | | | A3 LV: V | |
| F2 | | | | | |
| F3 | | | | | |
| F4 | | | | | |
| G1 | | | | ADC_BOTTOM: , ADC_TOP: , reversed: | |
| G2 | | | | FADER_ADC_MIN: , MAX: , INVERT: | |
| G3 | | | | Deadband/samples used: | |
| H1 | | | | Settings: | |
| H2 | | | | | |
| H3 | | | | Top of travel: dB | |
| H4 | | | | | |
| H5 | | | | | |
| H6 | | | | What Reaper needed: | |
| I1 | | | | Current at end: mA | |
| I2 | | | | | |
| I3 | | | | VM: V | |

## After the MVP

The next tests depend on U7 running `spld/final.pld` (not yet written). In order, from Hardware_Map section 7: bus decode on the logic analyzer (`LCD_E`, `BTN_OE_N`, `MOTDIR_CLK` and `VDP_WR_N` pulsing only for their addresses), button read at 0xF800, the LCD, the touch sensors, the motor open loop then closed loop, and MIDI received from Reaper (M4). Each gets its own section here when its firmware exists.
