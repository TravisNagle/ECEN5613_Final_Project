/*
 * File        : adc.c
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : Bit-banged SPI (mode 0,0) read of the MCP3008. Pins are in
 *               board.h.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : read sequence from the MCP3008 datasheet (DS21295,
 *               section 6) and the PDR design doc (docs/MIDI-Controller.pdf, M3)
 */
#include "adc.h"

void adc_init(void)
{
    ADC_CS_N = 1;
    ADC_SCK = 0;
    ADC_MOSI = 0;
    ADC_MISO = 1;                       /* input: latch must be 1 */
}

uint16_t adc_read(uint8_t ch)
{
    /* locals in internal RAM: the large model would put them in XRAM, which is slower */
    __data uint8_t cmd = 0x18 | (ch & 0x07);    /* start bit, SGL = 1, D2-D0 */
    __data uint16_t result = 0;
    __data uint8_t i;

    ADC_CS_N = 0;

    /* clocks 1-5: the MCP3008 latches DIN on each rising edge */
    for (i = 0; i < 5; i++) {
        ADC_MOSI = (cmd & 0x10) ? 1 : 0;
        cmd <<= 1;
        ADC_SCK = 1;
        ADC_SCK = 0;
    }

    /*
     * Clock 6 ends the sample; DOUT then shows the null bit after its falling
     * edge, and B9..B0 after the falling edges of clocks 7-16. Read 11 bits
     * after each falling edge and keep the low 10.
     */
    for (i = 0; i < 11; i++) {
        ADC_SCK = 1;
        ADC_SCK = 0;
        result = (result << 1) | ADC_MISO;
    }

    ADC_CS_N = 1;
    return result & 0x03FF;
}
