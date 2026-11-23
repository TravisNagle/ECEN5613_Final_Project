/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/13/26
 *  --------------------------------------------------------------------------------
 * pcf8574.c: PCF8574 I2C I/O expander driver. Part 3 Step 7.
 *
 * chip basics (NXP datasheet):
 *  - no direction register. every pin is quasi-bidirectional like an 8051 port:
 *    write 0 = strong pull-down (output low), write 1 = weak ~100 uA pull-up, which
 *    is "high" for an output and "released" for an input. so an input pin must
 *    ALWAYS be written as 1 -> every write is (output shadow | input mask).
 *  - write = START, addr+W, one data byte, STOP. read = START, addr+R, one byte,
 *    master NACKs, STOP.
 *  - /INT (open drain) goes low when an input differs from the last read and goes
 *    back high when the port is read (or the input changes back).
 *
 * interrupt choice: /INT0 is EDGE triggered (IT0 = 1). /INT stays low until the
 * port is read over I2C, and that can't happen inside the ISR (main may be in the
 * middle of an EEPROM transaction, and the large-model I2C functions aren't
 * reentrant). with level triggering the ISR would fire again the moment it
 * returned and main would never run. so the ISR only sets a flag; pcf_service()
 * does the I2C read from main context. it also treats "/INT pin still low" as a
 * pending change, which covers a second change that arrives before the first read
 * (no new falling edge in that case).
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: NXP PCF8574 datasheet; uses my i2c.c bus routines from Part 1.
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/


/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "i2c.h"
#include "pcf8574.h"


/* -------------------------------------------------- */
//          GLOBALS
/* -------------------------------------------------- */
static uint8_t s_addr7 = PCF_NOT_FOUND;
static uint8_t s_input_mask = PCF_INPUT_MASK;   // 1 = input
static uint8_t s_out_shadow = PCF_OUTPUTS_OFF;  // what the output pins should be
static uint8_t s_last_inputs = PCF_INPUT_MASK;  // last read, input bits only

static volatile bool s_int_pending = false;     // set by the ISR
static volatile uint16_t s_int_count = 0U;      // ISR hits (edges seen)
static uint16_t s_service_count = 0U;           // reads done because of them


/* -------------------------------------------------- */
//          HELPERS
/* -------------------------------------------------- */

// one data byte to the chip, input pins forced to 1
static bool pcf_write_port(void)
{
    bool ok;

    if (s_addr7 == PCF_NOT_FOUND) {
        return false;
    }
    i2c_start();
    ok = i2c_write_byte((uint8_t)((s_addr7 << 1) | I2C_WRITE_BIT));
    if (ok) {
        ok = i2c_write_byte((uint8_t)(s_out_shadow | s_input_mask));
    }
    i2c_stop();
    return ok;
}


/* -------------------------------------------------- */
//          PUBLIC FUNCTIONS
/* -------------------------------------------------- */

bool pcf_init(void)
{
    uint8_t i;
    uint8_t pins;

    s_addr7 = PCF_NOT_FOUND;
    for (i = 0U; (i < PCF_ADDR_COUNT) && (s_addr7 == PCF_NOT_FOUND); i++) {
        if (i2c_probe((uint8_t)(PCF8574_ADDR_BASE + i))) {
            s_addr7 = (uint8_t)(PCF8574_ADDR_BASE + i);
        }
    }
    for (i = 0U; (i < PCF_ADDR_COUNT) && (s_addr7 == PCF_NOT_FOUND); i++) {
        if (i2c_probe((uint8_t)(PCF8574A_ADDR_BASE + i))) {
            s_addr7 = (uint8_t)(PCF8574A_ADDR_BASE + i);
        }
    }

    s_input_mask = PCF_INPUT_MASK;
    s_out_shadow = PCF_OUTPUTS_OFF;

    EX0 = 0;
    if (s_addr7 == PCF_NOT_FOUND) {
        return false;
    }
    (void)pcf_write_port();
    if (pcf_read(&pins)) {                      // clears /INT
        s_last_inputs = (uint8_t)(pins & s_input_mask);
    }
    s_int_pending = false;
    IT0 = 1;                                    // falling edge (see top of file)
    IE0 = 0;                                    // drop an edge from before now
    EX0 = 1;                                    // EA is set by elapsed_init()
    (void)pcf_service();                        // set the LEDs from the buttons now
    return true;
}

uint8_t pcf_address(void)
{
    return s_addr7;
}

bool pcf_set_direction(uint8_t input_mask)
{
    s_input_mask = input_mask;
    return pcf_write_port();
}

uint8_t pcf_get_direction(void)
{
    return s_input_mask;
}

// bit mask so only the selected output pins change
bool pcf_write_outputs(uint8_t value, uint8_t mask)
{
    s_out_shadow = (uint8_t)((s_out_shadow & (uint8_t)~mask) | (value & mask));
    return pcf_write_port();
}

uint8_t pcf_get_outputs(void)
{
    return (uint8_t)(s_out_shadow | s_input_mask);
}

bool pcf_read(uint8_t *pins)
{
    bool ok;

    if (s_addr7 == PCF_NOT_FOUND) {
        return false;
    }
    i2c_start();
    ok = i2c_write_byte((uint8_t)((s_addr7 << 1) | I2C_READ_BIT));
    if (ok) {
        *pins = i2c_read_byte(I2C_NACK);        // NACK = only one byte wanted
    }
    i2c_stop();
    return ok;
}

// demo: inputs P0-P3 -> (inverted) -> outputs P4-P7
bool pcf_service(void)
{
    uint8_t pins;
    uint8_t out;

    if (s_addr7 == PCF_NOT_FOUND) {
        return false;
    }
    if (!s_int_pending && (PCF_INT_PIN != 0)) {
        return false;                           // nothing changed
    }
    s_int_pending = false;                      // clear BEFORE the read, so an edge
                                                // during the read isn't lost
    if (!pcf_read(&pins)) {
        return false;
    }
    s_last_inputs = (uint8_t)(pins & s_input_mask);
    out = (uint8_t)(s_last_inputs << PCF_OUTPUT_SHIFT);
#if PCF_DEMO_INVERT
    out = (uint8_t)~out;
#endif
    (void)pcf_write_outputs(out, PCF_OUTPUT_MASK);
    s_service_count++;
    return true;
}

uint16_t pcf_int_count(void)
{
    uint16_t n;

    EX0 = 0;                                    // 16-bit read, keep the ISR out
    n = s_int_count;
    EX0 = (s_addr7 != PCF_NOT_FOUND);
    return n;
}

uint16_t pcf_service_count(void)
{
    return s_service_count;
}

uint8_t pcf_last_inputs(void)
{
    return s_last_inputs;
}

// /INT0 falling edge: just note it. IE0 is cleared by hardware on vector entry
// (edge mode). no function calls, so no reentrancy or register-bank worries.
void pcf_int0_isr(void) __interrupt(0)
{
    s_int_pending = true;
    s_int_count++;
}
