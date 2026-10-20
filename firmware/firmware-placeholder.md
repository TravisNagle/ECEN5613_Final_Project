# firmware

8051 C source for the AT89C51RC2, built with SDCC.

- `main.c`: init and the cooperative main loop
- Drivers: UART (Timer 2), soft UART (Timer 0), SPI/ADC, '165 scan, PWM, LCD, NVRAM
- Modules: MIDI parser, merge/filter, pedal, fader PD loop, MCU link, presets

Build output (`.ihx`, `.hex`, `.lst`, `.rel`) is not committed.