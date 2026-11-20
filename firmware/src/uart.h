/*
 * File        : uart.h
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : Hardware UART on Timer 2: the MIDI link to the KB2040.
 *               Interrupt-driven, with a ring buffer each way.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#ifndef UART_H
#define UART_H

#include "board.h"

void uart_init(void);

/* Queue one byte. Waits while the TX buffer is full; never call with EA = 0. */
void uart_putc(uint8_t c);

/* Next received byte, or -1 when none is waiting. */
int16_t uart_getc(void);

/* The prototype must be visible in main.c so SDCC places the vector. */
void uart_isr(void) __interrupt(SI0_VECTOR);

#endif /* UART_H */
