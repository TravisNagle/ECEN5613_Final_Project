/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/19/26
 *  --------------------------------------------------------------------------------
 * mcp3008.c: MCP3008 ADC over SPI, bit-banged (Step 8) or on the RC2's SPI
 * controller (Step 6). Same chip, same /CS, SCK and MOSI wires, so the two can be
 * compared on the scope by switching modes.
 *
 * bit-banged, mode 0,0 (datasheet Figure 6-1), /CS low the whole time:
 *   clocks 1-5   master sends start (1), SGL/DIFF (1), D2, D1, D0 on MOSI. the ADC
 *                samples DIN on each rising edge, so MOSI is set while SCK is low
 *   clocks 5-6   ADC samples the input (sample-and-hold, ~1.5 clocks)
 *   clock 6      ADC drives a null bit (0) on DOUT after the falling edge
 *   clocks 7-16  ADC drives B9..B0, each changing after a falling edge
 * so after the command I give 11 more clocks and read MISO after each falling edge:
 * the first read is the null bit and the next 10 are the result. the null bit is 0,
 * so it falls off the top when I mask to 10 bits.
 *
 * SPI controller, mode 1,1 (datasheet Figure 6-2, 8-bit segments): the controller
 * only moves whole bytes, so the frame is padded to 24 clocks with leading zeros:
 *   out 0000 0001          start bit is the last bit of byte 1
 *   out S D2 D1 D0 xxxx    in  ???? ?0 B9 B8   (null bit, then the top 2 bits)
 *   out xxxx xxxx          in  B7 ... B0
 * mode 1,1 because /SS (P1.1) is the status LED and has to be ignored (SSDIS), and
 * the datasheet doesn't allow SSDIS with CPHA = 0. SCK idles high; the ADC still
 * samples on rising edges and shifts on falling edges, same as mode 0,0.
 *
 * timing: bit-banged SCK is set by loop speed, roughly 50-100 kHz (MEASURE). the
 * controller runs at F_OSC/32 = 345.6 kHz. the MCP3008 needs fCLK >= 10 kHz or the
 * sample cap droops (conversion must finish within ~1.2 ms). the clock ISR can take
 * over 1 ms when it waits on the LCD, which would stretch one clock (or the gap
 * between two controller bytes) past that, so the whole frame is __critical in both
 * modes (~0.3 ms / ~0.1 ms with interrupts off).
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: Microchip MCP3004/3008 datasheet DS21295.
 *   Atmel AT89C51RB2/RC2 datasheet doc4180 (Serial Port Interface: master mode,
 *   SPCON, clearing SPIF, Table 54 baud rates).
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/


/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "mcp3008.h"

#define CMD_MSB_MASK    (1U << (ADC_CMD_BITS - 1U))     // bit 4 of the 5-bit command
#define RESULT_MASK     0x03FFU
#define BYTE_BITS       8U


/* -------------------------------------------------- */
//          GLOBALS
/* -------------------------------------------------- */
static uint8_t s_mode;      // set in adc_init(), not by an initializer


/* -------------------------------------------------- */
//          HELPERS
/* -------------------------------------------------- */

// Step 8: one frame, all pins wiggled by hand. called with interrupts off
static uint16_t read_bitbang(uint8_t channel)
{
    uint8_t cmd = (uint8_t)(ADC_CMD_START_SGL | channel);   // 1 1 D2 D1 D0
    uint8_t i;
    uint16_t result = 0U;

    ADC_SCK = 0;
    ADC_CS_N = 0;                                       // start of frame
    for (i = 0U; i < ADC_CMD_BITS; i++) {
        ADC_MOSI = ((cmd & CMD_MSB_MASK) != 0U);        // set while SCK low
        cmd = (uint8_t)(cmd << 1);
        ADC_SCK = 1;                                    // ADC samples DIN here
        ADC_SCK = 0;
    }
    ADC_MOSI = 0;                                       // don't care from here
    for (i = 0U; i < ADC_READ_CLOCKS; i++) {
        ADC_SCK = 1;
        ADC_SCK = 0;                                    // ADC shifts DOUT here
        result = (uint16_t)((result << 1) | (ADC_MISO ? 1U : 0U));
    }
    ADC_CS_N = 1;                                       // end of frame, DOUT Hi-Z

    return (uint16_t)(result & RESULT_MASK);
}

// Step 6: one byte through the controller. writing SPDAT starts 8 clocks; SPIF
// sets when the byte is done and SPDAT then holds what came in on MISO. reading
// SPSTA (with SPIF set) and then SPDAT clears SPIF. *ok goes false on a timeout
static uint8_t spi_xfer(uint8_t out, bool *ok)
{
    uint8_t polls = 0U;

    SPDAT = out;
    while ((SPSTA & SPSTA_SPIF) == 0U) {
        polls++;
        if (polls >= ADC_SPI_WAIT_POLLS) {
            *ok = false;
            return 0U;
        }
    }
    return SPDAT;
}

// Step 6: one frame on the controller (3 bytes). called with interrupts off
static uint16_t read_hwspi(uint8_t channel)
{
    bool ok = true;
    uint8_t hi;
    uint8_t lo;

    ADC_CS_N = 0;                                       // start of frame
    (void)spi_xfer(ADC_HW_START_BYTE, &ok);
    hi = spi_xfer((uint8_t)(ADC_HW_SGL_BIT | (uint8_t)(channel << ADC_HW_CH_SHIFT)), &ok);
    lo = spi_xfer(0x00U, &ok);
    ADC_CS_N = 1;                                       // end of frame

    if (!ok) {
        return ADC_ERR_SPI;
    }
    return (uint16_t)(((uint16_t)(hi & ADC_HW_HIGH_MASK) << BYTE_BITS) | lo);
}


/* -------------------------------------------------- */
//          FUNCTION DEFINITIONS
/* -------------------------------------------------- */

void adc_init(void)
{
    SPCON = 0x00U;          // controller off -> P1.5-P1.7 are plain port pins
    s_mode = ADC_MODE_BITBANG;
    ADC_CS_N = 1;           // deselected, DOUT Hi-Z
    ADC_SCK = 0;            // mode 0: clock idles low
    ADC_MOSI = 0;
    ADC_MISO = 1;           // quasi-bidirectional: write 1 so the ADC can drive it
    ADC_HW_MISO = 1;        // same for the controller's MISO pin
}

void adc_set_mode(uint8_t mode)
{
    if (mode == ADC_MODE_HWSPI) {
        SPCON = 0x00U;              // CPOL/CPHA may only change with SPEN = 0
        ADC_CS_N = 1;
        // 8051 alternate-function outputs are ANDed with the port latch, so the
        // SCK and MOSI latches must be 1 or the controller can't drive them high
        ADC_SCK = 1;                // also the mode 1,1 idle level
        ADC_MOSI = 1;
        ADC_HW_MISO = 1;
        SPCON = SPCON_ADC_MASTER;   // master first, then enable (datasheet note 1)
        SPCON = (uint8_t)(SPCON_ADC_MASTER | SPCON_SPEN);
        (void)SPSTA;                // clear anything left over
        (void)SPDAT;
        s_mode = ADC_MODE_HWSPI;
    } else if (mode == ADC_MODE_BITBANG) {
        SPCON = 0x00U;              // frames are always finished, so just turn it off
        ADC_CS_N = 1;
        ADC_SCK = 0;                // mode 0 idle level
        ADC_MOSI = 0;
        s_mode = ADC_MODE_BITBANG;
    }
}

uint8_t adc_get_mode(void)
{
    return s_mode;
}

__code const char *adc_mode_name(void)
{
    return (s_mode == ADC_MODE_HWSPI) ? "SPI controller" : "bit-banged";
}

uint16_t adc_read(uint8_t channel) __critical
{
    if (channel > ADC_CHANNEL_MAX) {
        return ADC_ERR_RANGE;
    }
    if (s_mode == ADC_MODE_HWSPI) {
        return read_hwspi(channel);
    }
    return read_bitbang(channel);
}

// mV = code * VREF / 1024, done in 32 bits (1023 * 5000 overflows 16)
uint16_t adc_code_to_mv(uint16_t code)
{
    return (uint16_t)(((uint32_t)code * ADC_VREF_MV) / ADC_STEPS);
}
