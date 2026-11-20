/*
 * File        : tick.c
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : Timer 1, mode 1, as the 1 ms system tick (README firmware
 *               architecture). Timer 0 is left free for the soft-UART debug
 *               port.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : reload value 0xFC66 from the PDR design doc
 *               (docs/MIDI-Controller.pdf, M2)
 */
#include "tick.h"

/*
 * Timer 1 counts at fosc / 12 = 921.6 kHz; 922 counts = 1.0004 ms. Reloading
 * in the ISR loses the few counts of interrupt latency, so the tick runs about
 * 1-2 % slow: fine for debounce and pacing, not for timekeeping.
 */
#define T1_RELOAD   (65536u - 922u)     /* 0xFC66 */

volatile __data uint8_t tick_ms;

void tick_init(void)
{
    TMOD = (TMOD & 0x0F) | 0x10;        /* Timer 1: mode 1 (16-bit), timer, no gate */
    TH1 = T1_RELOAD >> 8;
    TL1 = T1_RELOAD & 0xFF;
    ET1 = 1;
    TR1 = 1;
}

void tick_isr(void) __interrupt(TF1_VECTOR)
{
    TH1 = T1_RELOAD >> 8;
    TL1 = T1_RELOAD & 0xFF;
    tick_ms++;
}
