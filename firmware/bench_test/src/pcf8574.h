/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/13/26
 *  --------------------------------------------------------------------------------
 * pcf8574.h: PCF8574 I2C I/O expander driver + /INT0 change interrupt. Part 3 Step 7.
 * same chip and wiring as the final project button board (Hardware_Map 4.3).
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: NXP PCF8574 datasheet (quasi-bidirectional I/O, read/write frames,
 * /INT behaviour).
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef PCF8574_H
#define PCF8574_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>
#include <stdbool.h>

#define PCF_NOT_FOUND   0x00U   // pcf_address() before a chip answered


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// find the chip (0x20-0x27, then 0x38-0x3F), set P0-P3 as inputs and P4-P7 as
// outputs (LEDs off), read once to clear /INT, then enable /INT0 falling-edge.
// true if a chip answered
bool    pcf_init(void);

// 7-bit address in use, PCF_NOT_FOUND if none
uint8_t pcf_address(void);

// pins with a 1 in input_mask become inputs (written high = weak pull-up only),
// the rest are outputs driven from the output shadow. writes the chip.
bool    pcf_set_direction(uint8_t input_mask);
uint8_t pcf_get_direction(void);

// change only the output pins selected by mask: shadow = (shadow & ~mask) |
// (value & mask). input pins are always written as 1 regardless. writes the chip.
bool    pcf_write_outputs(uint8_t value, uint8_t mask);

// last value written to the output pins (input bits shown as 1)
uint8_t pcf_get_outputs(void);

// read all 8 pins (this also clears /INT). false = no ACK
bool    pcf_read(uint8_t *pins);

// call from the main loop / getchar wait. if /INT0 fired (or /INT is still low)
// it reads the inputs and writes the inverted value to the outputs. never call from
// an ISR: the I2C code is shared with the EEPROM and isn't reentrant.
// true if it serviced a change
bool    pcf_service(void);

// counters + last input read, for the status screen
uint16_t pcf_int_count(void);
uint16_t pcf_service_count(void);
uint8_t  pcf_last_inputs(void);

// /INT0 ISR, vector 0x03. prototype HAS to be visible in main.c or SDCC won't put
// it in the vector table
void    pcf_int0_isr(void) __interrupt(0);

#endif // #ifndef PCF8574_H
