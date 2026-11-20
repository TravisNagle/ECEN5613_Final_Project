/*
 * File        : tick.h
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : 1 ms system tick on Timer 1. The ISR only counts; the main
 *               loop runs the per-millisecond work.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#ifndef TICK_H
#define TICK_H

#include "board.h"

/* Free-running millisecond count. 8 bits so the main loop reads it in one instruction. */
extern volatile __data uint8_t tick_ms;

void tick_init(void);

/* The prototype must be visible in main.c so SDCC places the vector. */
void tick_isr(void) __interrupt(TF1_VECTOR);

#endif /* TICK_H */
