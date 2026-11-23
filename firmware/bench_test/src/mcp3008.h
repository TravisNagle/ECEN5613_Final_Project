/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/19/26
 *  --------------------------------------------------------------------------------
 * mcp3008.h: MCP3008 8-channel 10-bit ADC, two ways (ADC option the course allows in
 * place of the DAC):
 *   Step 8: bit-banged SPI mode 0,0 on P1.2 /CS, P1.6 SCK, P1.7 MOSI, P3.3 MISO.
 *           same pins as the final project U11, so this one carries over.
 *   Step 6: the RC2's SPI controller, mode 1,1, MISO on P1.5 (needs a jumper from
 *           U11 DOUT to P1.5). SCK, MOSI and /CS are the same wires.
 * adc_set_mode() switches between them; adc_read() works the same in both.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: Microchip MCP3004/3008 datasheet;
 *   Atmel AT89C51RB2/RC2 datasheet doc4180 (Serial Port Interface).
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef MCP3008_H
#define MCP3008_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>

#define ADC_ERR_RANGE   0xFFFFU     // adc_read() with a channel > 7
#define ADC_ERR_SPI     0xFFFEU     // SPI controller never set SPIF (hardware mode)

#define ADC_MODE_BITBANG    0U      // Step 8
#define ADC_MODE_HWSPI      1U      // Step 6


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// SPI controller off, bit-banged mode, /CS high, SCK low, MOSI low, MISO latches 1
void     adc_init(void);

// ADC_MODE_BITBANG or ADC_MODE_HWSPI. anything else is ignored
void     adc_set_mode(uint8_t mode);
uint8_t  adc_get_mode(void);

// "bit-banged" / "SPI controller", for printf
__code const char *adc_mode_name(void);

// one single-ended conversion, 0-1023, ADC_ERR_RANGE or ADC_ERR_SPI. interrupts off
// for the frame: ~0.3 ms bit-banged, ~0.1 ms on the controller
uint16_t adc_read(uint8_t channel);

// code -> millivolts using ADC_VREF_MV
uint16_t adc_code_to_mv(uint16_t code);

#endif // #ifndef MCP3008_H
