/* ---------------------------------------------------------------------------------
 * File        : midi_tx.h
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : Polled (no interrupt) MIDI byte output and input on the 8051 UART at
 *               about 31,250 baud (Timer 2 baud generator, 31,418 baud, +0.54 %).
 *               TXD (P3.1) goes to the level shifter A3 and the KB2040; RXD (P3.0)
 *               comes back through JP_RX. Used by page 3 (MIDI) of the bench test.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : Timer 2 baud setup and the TH2/TL2 preload from the MVP firmware's
 *               uart.c (firmware/src/uart.c), which cites the AT89C51RB2/RC2
 *               datasheet errata
   ---------------------------------------------------------------------------------*/
#ifndef MIDI_TX_H
#define MIDI_TX_H

#include <stdint.h>
#include <stdbool.h>

void midi_init(void);

/* blocks until the byte has left the shift register's holding slot (about 320 us a byte) */
void midi_send_byte(uint8_t b);
void midi_send_note(bool on, uint8_t note, uint8_t velocity);       /* channel 1 */
void midi_send_pitch_bend(uint8_t channel, uint16_t value14);       /* channel 0-15, 0-16383 */

/* returns true and one received byte if one is waiting */
bool midi_get_byte(uint8_t *b);

uint16_t midi_tx_count(void);       /* bytes sent since reset (wraps at 65536) */
uint16_t midi_rx_count(void);       /* bytes received since reset */

#endif /* MIDI_TX_H */
