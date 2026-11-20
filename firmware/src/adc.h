/*
 * File        : adc.h
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : MCP3008 10-bit ADC (U11) on bit-banged SPI. Channels:
 *               CH0 fader 1, CH1 fader 2, CH3 pedal (Hardware_Map A.9).
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#ifndef ADC_H
#define ADC_H

#include "board.h"

#define ADC_CH_FADER1   0
#define ADC_CH_FADER2   1
#define ADC_CH_PEDAL    3

void adc_init(void);

/* Single-ended conversion of channel 0-7: 0-1023 (VREF_F = full scale). */
uint16_t adc_read(uint8_t ch);

#endif /* ADC_H */
