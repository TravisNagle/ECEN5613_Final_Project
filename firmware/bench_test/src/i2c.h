/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * i2c.h: bit-banged I2C master, SDA = P3.4, SCL = P3.5. just the bus-level stuff
 * (start, stop, byte in/out, raw clocks) - eeprom.c and later the PCF8574 sit on top.
 * Part 1.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0.
 * Leveraged code: protocol from the NXP I2C-bus specification UM10204 (section 3)
 *   and the ECEN 5613 EEPROM Guide. 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef I2C_H
#define I2C_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>
#include <stdbool.h>

#define I2C_ACK     true    // for i2c_read_byte: want more bytes
#define I2C_NACK    false   // for i2c_read_byte: last byte


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// let go of both lines (idle = both high)
void    i2c_init(void);

// START, or repeated START if already mid-transaction
void    i2c_start(void);

// STOP, leaves bus idle
void    i2c_stop(void);

// 8 bits out MSB first, then read the ACK. true = ACK, false = NACK or bus fault
bool    i2c_write_byte(uint8_t value);

// 8 bits in MSB first, then send ACK (I2C_ACK) or NACK (I2C_NACK)
uint8_t i2c_read_byte(bool ack);

// count SCL pulses with SDA released (for eereset / AN709)
void    i2c_clock_ones(uint8_t count);

// START + addr/write + STOP. true if something ACKed
bool    i2c_probe(uint8_t addr7);

// true if SCL got stuck low since last time I asked. clears the flag
bool    i2c_bus_fault(void);

#endif // #ifndef I2C_H
