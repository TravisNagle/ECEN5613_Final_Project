/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * eeprom.c: 24C16 driver on the bit-banged I2C. Part 1.
 *
 * 11-bit addr = 3-bit block (bits 10:8, goes in the control byte) + 8-bit word addr
 *     control = 1010 B2 B1 B0 R/W   (0x50 + block)
 * byte write (Fig 6-1):
 *     S | ctrl+W | A | word | A | data | A | P, then ACK poll till done
 * random read (Fig 8-2):
 *     S | ctrl+W | A | word | A | Sr | ctrl+R | A | data | NACK | P
 * checking every ACK - if one's missing, STOP and return an error.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: sequences from the Microchip 24LC16B datasheet (DS21703) and
 *   application note AN709 (software reset). 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/


/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "i2c.h"
#include "eeprom.h"


/* -------------------------------------------------- */
//          FUNCTION DEFINITIONS
/* -------------------------------------------------- */

// 7-bit device addr for whatever block addr is in
static uint8_t ee_device_addr7(uint16_t addr)
{
    return (uint8_t)(EE_DEVICE_ADDR7 | ((addr >> EE_BLOCK_SHIFT) & EE_BLOCK_MASK));
}

// START + control byte (write) + word addr. on error it already sent STOP
static int ee_select(uint16_t addr)
{
    i2c_start();
    if (!i2c_write_byte((uint8_t)(ee_device_addr7(addr) << 1) | I2C_WRITE_BIT)) {
        i2c_stop();
        return i2c_bus_fault() ? EE_ERR_BUS : EE_ERR_NACK_DEVICE;
    }
    if (!i2c_write_byte((uint8_t)(addr & EE_WORD_MASK))) {
        i2c_stop();
        return i2c_bus_fault() ? EE_ERR_BUS : EE_ERR_NACK_WORD;
    }
    return EE_OK;
}

// ACK polling - chip NACKs its addr while it's still writing
static int ee_wait_write_done(uint16_t addr)
{
    uint8_t attempt;

    for (attempt = 0U; attempt < EE_WRITE_POLL_MAX; attempt++) {
        if (i2c_probe(ee_device_addr7(addr))) {
            return EE_OK;
        }
    }
    return EE_ERR_WRITE_TIMEOUT;
}

// write byte, then wait out tWC so the next call can go right away
int eebytew(uint16_t addr, uint8_t databyte)
{
    int status;

    if (addr > EE_ADDR_MAX) {
        return EE_ERR_RANGE;
    }
    status = ee_select(addr);
    if (status != EE_OK) {
        return status;
    }
    if (!i2c_write_byte(databyte)) {
        i2c_stop();
        return i2c_bus_fault() ? EE_ERR_BUS : EE_ERR_NACK_DATA;
    }
    i2c_stop();                     // the STOP is what kicks off the write
    return ee_wait_write_done(addr);
}

// random read: dummy write to set addr, repeated START, read 1, NACK, STOP
int eebyter(uint16_t addr)
{
    int status;
    uint8_t value;

    if (addr > EE_ADDR_MAX) {
        return EE_ERR_RANGE;
    }
    status = ee_select(addr);
    if (status != EE_OK) {
        return status;
    }
    i2c_start();                    // repeated START
    if (!i2c_write_byte((uint8_t)(ee_device_addr7(addr) << 1) | I2C_READ_BIT)) {
        i2c_stop();
        return i2c_bus_fault() ? EE_ERR_BUS : EE_ERR_NACK_DEVICE;
    }
    value = i2c_read_byte(I2C_NACK); // only want one, NACK tells it to stop
    i2c_stop();
    return (int)value;
}

// Name: eereset()
// Description: Performs a software reset of the I2C EEPROM using an
// algorithm that conforms to Microchip application note AN709.
// START, 9 clocks w/ SDA high, START, STOP.
//  - if the chip was mid-byte (e.g. I hit reset during a read) it might be holding
//    SDA low. 9 clocks lets it finish, 9th looks like a NACK so it lets go.
//  - 2nd START puts its logic back to "waiting for control byte", STOP = idle.
// first START doesn't hurt if it was idle. memory isn't touched and a write already
// in progress still finishes.
void eereset(void)
{
    i2c_start();
    i2c_clock_ones(EE_RESET_CLOCKS);
    i2c_start();
    i2c_stop();
}

const char *ee_status_text(int status)
{
    switch (status) {
    case EE_OK:                 return "OK";
    case EE_ERR_RANGE:          return "address out of range (000-7FF)";
    case EE_ERR_NACK_DEVICE:    return "no ACK from EEPROM (check wiring/pull-ups)";
    case EE_ERR_NACK_WORD:      return "no ACK to word address";
    case EE_ERR_NACK_DATA:      return "no ACK to data byte (WP high?)";
    case EE_ERR_WRITE_TIMEOUT:  return "write cycle never finished";
    case EE_ERR_BUS:            return "SCL stuck low (bus fault)";
    default:                    return "unknown error";
    }
}
