/*
 * File        : midi.h
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : MIDI message senders and the Mackie Control (MCU) note
 *               numbers Reaper uses (README "Mackie Control Messages Used",
 *               Hardware_Map section 5). Channels are 0-15 (0 = MIDI ch 1).
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#ifndef MIDI_H
#define MIDI_H

#include "board.h"

#define MIDI_NOTE_ON        0x90
#define MIDI_CC             0xB0
#define MIDI_PITCH_BEND     0xE0

#define MIDI_PB_MAX         16383u      /* 14-bit pitch bend */

/* MCU notes, all on channel 1 (index 0). Press = velocity 127, release = 0. */
#define MCU_PRESS           0x7F
#define MCU_RELEASE         0x00
#define MCU_REC(n)          (0x00 + (n))    /* strip n = 0-7 */
#define MCU_SOLO(n)         (0x08 + (n))
#define MCU_MUTE(n)         (0x10 + (n))
#define MCU_SELECT(n)       (0x18 + (n))
#define MCU_STOP            0x5D
#define MCU_PLAY            0x5E
#define MCU_RECORD          0x5F
#define MCU_FADER_TOUCH(n)  (0x68 + (n))

/* MCU fader n is pitch bend on channel n (E0 + n). */

void midi_note_on(uint8_t ch, uint8_t note, uint8_t velocity);
void midi_cc(uint8_t ch, uint8_t controller, uint8_t value);
void midi_pitch_bend(uint8_t ch, uint16_t value14);

#endif /* MIDI_H */
