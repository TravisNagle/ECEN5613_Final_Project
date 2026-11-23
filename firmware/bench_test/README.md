# Panel bench test (8051)

| Field | Value |
|---|---|
| Revision | 2, 2026-11-22: mover brakes ahead of the target (rev 1 hunted end to end). 1: first draft |
| Status | **DRAFTED.** It builds with SDCC 4.6.0 (10.6 KB code, 387 bytes XRAM, no warnings). It has not been run on hardware |
| Hardware | [Hardware_Map.md](../../Hardware_Map.md) Rev 13.8 |
| AI use | Drafted with AI assistance (Anthropic Claude); reviewed by the student. The `lcd`, `i2c`, `eeprom`, `mcp3008`, `pcf8574`, `delay` and `config.h` files are copied unchanged from my Lab 4 code |

A stand-alone test of the panel, the button board and the motor drivers. There is no MIDI and no UART, and the motors stay off until you press F1 or F2.

## Build and flash

```bash
cd firmware/bench_test
make
```

This writes `build/bench_test.hex`. **FLIP has no macOS build**, and I found no verified macOS tool for the AT89C51RC2's bootloader. Copy the `.hex` to a Windows or Linux machine with FLIP, or run `make flash COM_PORT=COM4` there (it uses the same `batchisp` command as the Lab 4 Makefile). Put `JP_RX` in the PC position, hold SW3 (PSEN) through reset, and move `JP_RX` back to KB afterwards.

## Pages

Hold D-pad **CENTER** for about 1 s to go to the next page (MAIN, BUS, CAL, then MAIN again). A short press of CENTER only shows `C` on the main page.

### Page 0, MAIN

```
1 ▌▌▌▌▌       ^ 1A3     row 0: fader 1 bar (Lab 4 style), motion, 10-bit reading in hex
2 ▌▌▌         v 0F0     row 1: fader 2
T1:HELD T2:----         row 2: capacitive touch (A4, A5)
D:UDLRC F:12 S:4        row 3: D-pad, fader buttons, class board SW4 (letter = pressed)
```

- **F1 / F2** move that fader to 25 %, then 50 %, then 75 %, then back to 25 %, one step per press.
- Motion character: `^` moving up, `v` moving down, `!` timed out (about 2 s), `X` the motor does not move at all.
- The very first move of each fader runs a short probe (about 0.3 s) that finds which direction raises the pot reading, so it does not matter which way round the motor leads went. If the probe shows no movement in either direction, the status shows `X`: check the motor supply, `STBY` (U14 Q6), the `PWM` path and the motor wires.

### Page 1, BUS

- PCF8574 button board: its address, the four buttons (`BTN:1--4` style), and the four LEDs light while their buttons are held.
- 24C16 self-test: writes `A5` and `5A` to the last byte (0x7FF), reads each back, then restores the original value. F1 repeats it.
- An I2C scan (the 24C16 answers at all of 0x50-0x57, so only 0x50 is listed).

### Page 2, CAL

F1 or F2 runs that fader to both ends (about 1.2 s each way at 55 % PWM), records the pot readings at the ends and shows them as `L` and `H`, then parks the fader at 50 %. Those ends are used for the 25/50/75 % targets until reset. Write them into the `FADERn_ADC_LO_DEFAULT` and `FADERn_ADC_HI_DEFAULT` lines in [src/bench.h](src/bench.h) to keep them. The letter at the end of each row is the polarity found: `F` = driving FWD raises the reading, `R` = REV raises it, `X` = no movement, `?` = not tested yet.

The status LED on the class board (P1.1) blinks at about 1 Hz while the program runs. A fast blink means the LCD is not answering.

## Other things this test covers

| Test | How |
|---|---|
| Pot wiring and ADC | Slide each fader by hand and watch the bar and hex value on page 0 |
| Pot direction | Which end reads low (the bar and hex change together) |
| Touch sensors | `HELD` while you touch the fader knob. Run a move with the other sensor untouched to see if motor PWM makes it chatter |
| D-pad, F1, F2, SW4 | Each shows its letter while held |
| Button board and its LEDs | Page 1 |
| EEPROM | Page 1 |
| Motor wiring, `STBY`, U9 and U14 | Any F1 or F2 move; the polarity probe fails (`X`) if any of them is wrong |
| Fader end-to-end range and speed | Page 2 |
| Motor stall current (`MEASURE`) | Put the meter in series with the Vmotor `+` lead and run page 2; the end of each run is a stall for a fraction of a second |

## Bench results

Read from page 2 (CAL) on 2026-11-22 and typed in by hand; the readings are 10-bit MCP3008 codes with `VREF_F` about 5 V.

| Fader | Motor polarity | Low reading | High reading | Span |
|---|---|---|---|---|
| 1 | `F`: driving FWD (`AIN1` high) raises the reading | 0x01F (31) | 0x3E7 (999) | 968 counts |
| 2 | `F`: driving FWD (`BIN1` high) raises the reading | 0x01D (29) | 0x3E2 (994) | 965 counts |

Both motors turn the same way for the same latch code, so the wiring is consistent. Neither pot reaches 0 or 1023 (about 3 % at the low end, 2 to 3 % at the high end), which fits the datasheet's residual resistance. These ends are the defaults (`FADER1_ADC_LO_DEFAULT` and the three others in [src/bench.h](src/bench.h)), so the 25/50/75 % targets use them straight after reset. A calibration run on page 2 replaces them until the next reset.

## Tuning

All the numbers are in [src/bench.h](src/bench.h): PWM range (`MOVE_MIN_PWM`, `MOVE_MAX_PWM`), the deadband, the timeout and the calibration drive. The mover brakes when its speed would carry the fader across the target (`MOVE_LOOKAHEAD_TICKS`), and adds a boost while the fader is not moving. If a fader still overshoots, lower `MOVE_MAX_PWM` or raise `MOVE_LOOKAHEAD_TICKS`. If it stops short, raise `MOVE_MIN_PWM` or `MOVE_BOOST_MAX`. If it hunts at the target, raise `MOVE_DEADBAND`. Set `ABORT_ON_TOUCH` to 1 to make a touch cancel a move.

## Files

| File | What |
|---|---|
| `src/main.c` | Pages, inputs, fader moves, calibration |
| `src/motor.c` | U14 latch, PCA PWM (10.8 kHz), polarity probe |
| `src/screen.c` | 16x4 text buffer over the Lab 4 LCD driver, bar graph |
| `src/bench.h` | Addresses, bit masks, tuning |
| `src/config.h`, `lcd.*`, `i2c.*`, `eeprom.*`, `mcp3008.*`, `pcf8574.*`, `delay.*` | Lab 4 code, unchanged |
