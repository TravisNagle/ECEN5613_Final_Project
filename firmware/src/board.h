/*
 * File        : board.h
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : Board definitions for the class dev board (AT89C51RC2,
 *               11.0592 MHz, X1 mode): the SFR header and the port-pin names
 *               from Hardware_Map Rev 13.5 section 3.2.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : SFR and bit names from SDCC's at89c51ed2.h (the RC2's
 *               registers are a subset of the ED2's)
 */
#ifndef BOARD_H
#define BOARD_H

#include <at89c51ed2.h>
#include <stdint.h>

#define FOSC_HZ     11059200UL

/*
 * Port pins used by the MVP (Hardware_Map 3.2). Ports are quasi-bidirectional:
 * a pin used as an input must have a 1 in its port latch.
 */
#define LED_N       P1_1    /* status LED (class board Q1/D8), lit when 0 */
#define ADC_CS_N    P1_2    /* MCP3008 /CS, U11.10 */
#define PWM0        P1_3    /* CEX0 -> U9 -> TB6612 PWMA (fader 1 motor) */
#define PWM1        P1_4    /* CEX1 -> U9 -> TB6612 PWMB (fader 2 motor) */
#define ADC_SCK     P1_6    /* MCP3008 CLK, U11.13 */
#define ADC_MOSI    P1_7    /* MCP3008 DIN, U11.11 */
#define ADC_MISO    P3_3    /* MCP3008 DOUT, U11.12 (input) */
#define SW4_N       P3_2    /* class board SW4 on /INT0 (net BUS_INT_N), 0 = pressed */

#endif /* BOARD_H */
