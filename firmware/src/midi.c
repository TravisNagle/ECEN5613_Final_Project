/*
 * File        : midi.c
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : Builds channel messages and queues them on the UART. Every
 *               message carries its status byte (no running status) until
 *               the KB2040 bridge is shown to pass running status through.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#include "midi.h"
#include "uart.h"

static void send3(uint8_t status, uint8_t data1, uint8_t data2)
{
    uart_putc(status);
    uart_putc(data1 & 0x7F);
    uart_putc(data2 & 0x7F);
}

void midi_note_on(uint8_t ch, uint8_t note, uint8_t velocity)
{
    send3(MIDI_NOTE_ON | (ch & 0x0F), note, velocity);
}

void midi_cc(uint8_t ch, uint8_t controller, uint8_t value)
{
    send3(MIDI_CC | (ch & 0x0F), controller, value);
}

void midi_pitch_bend(uint8_t ch, uint16_t value14)
{
    /* LSB first: E0 ll mm */
    send3(MIDI_PITCH_BEND | (ch & 0x0F), value14 & 0x7F, (value14 >> 7) & 0x7F);
}
