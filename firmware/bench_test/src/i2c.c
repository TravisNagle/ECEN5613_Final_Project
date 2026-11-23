/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * i2c.c: bit-banged I2C master on P3.4 (SDA) / P3.5 (SCL). Part 1.
 *
 * open drain trick: writing 1 to a port pin leaves just the weak pull-up, so with
 * the 5.1k pull-ups "write 1" = release, "write 0" = pull low. have to write 1
 * before reading a pin (SDA before ACK + every read bit, SCL when checking stretch).
 *
 * timing (X1, machine cycle = 1.085 us):
 *   i2c_half_bit_delay = LCALL(2) + NOP(1) + RET(2) = 5 cycles = 5.43 us
 *   each SCL low/high = one delay + a few cycles of bit stuff
 *   -> tLOW ~7-9 us, tHIGH ~6-7 us, SCL ~60-75 kHz (MEASURE on scope)
 *   standard mode mins (UM10204 Table 10, 24LC16B is fine at 100k):
 *     tLOW 4.7, tHIGH 4.0, tSU;STA 4.7, tHD;STA 4.0, tSU;STO 4.0, tBUF 4.7 us,
 *     tSU;DAT 250 ns, tHD;DAT 0
 *   rise time <= 1000 ns: ~0.85*R*C, 5.1k * ~50 pF ~ 220 ns. MEASURE
 *   fall time <= 300 ns: 8051 strong pull-down. MEASURE
 * an interrupt mid-byte just stretches a phase - no max in standard mode, so the
 * clock ISR can't break a transfer.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: protocol and timing limits from NXP UM10204 (I2C-bus specification)
 *   and the Microchip 24LC16B datasheet; open-drain technique from the ECEN 5613
 *   EEPROM Guide. 
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

#define BITS_PER_BYTE   8U
#define MSB_MASK        0x80U


/* -------------------------------------------------- */
//          GLOBALS
/* -------------------------------------------------- */
// set if SCL stays low too long, i2c_bus_fault() reads + clears it
static bool s_bus_fault = false;


/* -------------------------------------------------- */
//          FUNCTION DEFINITIONS
/* -------------------------------------------------- */

// ~5.4 us. keep this a real function - the LCALL/RET is most of the delay
static void i2c_half_bit_delay(void)
{
    __asm__("nop");
}

// release SCL and wait for it to really go high (slave could be stretching).
// false = timed out
static bool scl_release(void)
{
    uint8_t loops = 0U;

    I2C_SCL = I2C_RELEASED;
    while ((I2C_SCL == I2C_DRIVEN_LOW) && (loops < I2C_SCL_STRETCH_LOOPS)) {
        loops++;
    }
    if (I2C_SCL == I2C_DRIVEN_LOW) {
        s_bus_fault = true;
        return false;
    }
    return true;
}

void i2c_init(void)
{
    I2C_SDA = I2C_RELEASED;
    I2C_SCL = I2C_RELEASED;
    s_bus_fault = false;
}

// SDA falls while SCL high. release SDA first while SCL is still low so a repeated
// START doesn't accidentally make a STOP
void i2c_start(void)
{
    I2C_SDA = I2C_RELEASED;
    i2c_half_bit_delay();
    (void)scl_release();
    i2c_half_bit_delay();           // tSU;STA
    I2C_SDA = I2C_DRIVEN_LOW;       // START
    i2c_half_bit_delay();           // tHD;STA
    I2C_SCL = I2C_DRIVEN_LOW;
}

// SDA rises while SCL high, both left released
void i2c_stop(void)
{
    I2C_SDA = I2C_DRIVEN_LOW;
    i2c_half_bit_delay();
    (void)scl_release();
    i2c_half_bit_delay();           // tSU;STO
    I2C_SDA = I2C_RELEASED;         // STOP
    i2c_half_bit_delay();           // tBUF before next START
}

// shift out MSB first (only change SDA while SCL low), then let go of SDA and check
// ACK at the end of the 9th clock high
bool i2c_write_byte(uint8_t value)
{
    uint8_t bit_index;
    bool acked;

    for (bit_index = 0U; bit_index < BITS_PER_BYTE; bit_index++) {
        I2C_SDA = ((value & MSB_MASK) != 0U);
        value = (uint8_t)(value << 1);
        i2c_half_bit_delay();       // tLOW (covers tSU;DAT)
        (void)scl_release();
        i2c_half_bit_delay();       // tHIGH
        I2C_SCL = I2C_DRIVEN_LOW;
    }

    // 9th clock - slave's turn
    I2C_SDA = I2C_RELEASED;
    i2c_half_bit_delay();
    acked = scl_release();
    i2c_half_bit_delay();
    if (I2C_SDA != I2C_DRIVEN_LOW) {
        acked = false;              // nobody pulled it low = NACK
    }
    I2C_SCL = I2C_DRIVEN_LOW;
    return acked;
}

// release SDA, sample at the end of each SCL high, MSB first. then 9th bit:
// low = ACK (keep going), released = NACK (done)
uint8_t i2c_read_byte(bool ack)
{
    uint8_t bit_index;
    uint8_t value = 0U;

    I2C_SDA = I2C_RELEASED;         // slave drives SDA now
    for (bit_index = 0U; bit_index < BITS_PER_BYTE; bit_index++) {
        i2c_half_bit_delay();
        (void)scl_release();
        i2c_half_bit_delay();
        value = (uint8_t)(value << 1);
        if (I2C_SDA != I2C_DRIVEN_LOW) {
            value |= 1U;
        }
        I2C_SCL = I2C_DRIVEN_LOW;
    }

    I2C_SDA = ack ? I2C_DRIVEN_LOW : I2C_RELEASED;
    i2c_half_bit_delay();
    (void)scl_release();
    i2c_half_bit_delay();
    I2C_SCL = I2C_DRIVEN_LOW;
    I2C_SDA = I2C_RELEASED;
    return value;
}

// clock with SDA released. a slave stuck mid-read finishes shifting its byte out,
// sees NACK on the 9th clock, and lets go of SDA (AN709)
void i2c_clock_ones(uint8_t count)
{
    uint8_t pulse;

    I2C_SDA = I2C_RELEASED;
    for (pulse = 0U; pulse < count; pulse++) {
        i2c_half_bit_delay();
        (void)scl_release();
        i2c_half_bit_delay();
        I2C_SCL = I2C_DRIVEN_LOW;
    }
}

// address for write, then stop right away. safe on the 24C16 - no word addr means
// nothing gets written
bool i2c_probe(uint8_t addr7)
{
    bool acked;

    i2c_start();
    acked = i2c_write_byte((uint8_t)((addr7 << 1) | I2C_WRITE_BIT));
    i2c_stop();
    return acked;
}

bool i2c_bus_fault(void)
{
    bool fault = s_bus_fault;

    s_bus_fault = false;
    return fault;
}
