/* ---------------------------------------------------------------------------------
 * File        : midi_tx.c
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : See midi_tx.h. No interrupts: the main loop calls midi_get_byte() once
 *               per tick, and at 31,250 baud a byte takes 320 us, so the receiver
 *               (one-byte buffer) can overrun if more than one byte arrives in a tick.
 *               That is fine for a connectivity test: the count shows bytes seen, and
 *               a Mac sending three-byte messages one at a time gets through.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : uart.c from the MVP firmware (Timer 2 reload 0xFFF5 and preload)
   ---------------------------------------------------------------------------------*/
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "midi_tx.h"

#define UART_RELOAD     (65536u - 11u)      /* 11059200 / (32 * 11) = 31,418 baud */

static uint16_t s_tx_count;
static uint16_t s_rx_count;

void midi_init(void)
{
    s_tx_count = 0U;
    s_rx_count = 0U;
    SCON = 0x50;                    /* mode 1, receiver on */
    T2CON = 0x30;                   /* RCLK = TCLK = 1; EXEN2 = 0 so P1.1 stays the LED; TR2 = 0 */
    RCAP2H = (uint8_t)(UART_RELOAD >> 8);
    RCAP2L = (uint8_t)(UART_RELOAD & 0xFFU);
    TH2 = (uint8_t)(UART_RELOAD >> 8);      /* preload, or the UART is dead for about 10,000 cycles */
    TL2 = (uint8_t)(UART_RELOAD & 0xFFU);
    TR2 = 1;
    TI = 1;                         /* transmitter ready */
    RI = 0;
}

void midi_send_byte(uint8_t b)
{
    while (TI == 0) {
        /* wait for the previous byte */
    }
    TI = 0;
    SBUF = b;
    s_tx_count++;
}

void midi_send_note(bool on, uint8_t note, uint8_t velocity)
{
    midi_send_byte(on ? 0x90U : 0x80U);
    midi_send_byte(note & 0x7FU);
    midi_send_byte(velocity & 0x7FU);
}

void midi_send_pitch_bend(uint8_t channel, uint16_t value14)
{
    midi_send_byte((uint8_t)(0xE0U | (channel & 0x0FU)));
    midi_send_byte((uint8_t)(value14 & 0x7FU));
    midi_send_byte((uint8_t)((value14 >> 7) & 0x7FU));
}

bool midi_get_byte(uint8_t *b)
{
    if (RI == 0) {
        return false;
    }
    *b = SBUF;
    RI = 0;
    s_rx_count++;
    return true;
}

uint16_t midi_tx_count(void)
{
    return s_tx_count;
}

uint16_t midi_rx_count(void)
{
    return s_rx_count;
}
