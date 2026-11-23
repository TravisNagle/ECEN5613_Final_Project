/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * eeprom.h: 24C16 (2 KB) I2C EEPROM driver, U10. byte write w/ ACK polling, random
 * read, AN709 reset. Part 1.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0.
 * Leveraged code: command sequences from the Microchip 24LC16B datasheet and AN709.
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef EEPROM_H
#define EEPROM_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>

// status codes. eebyter returns the data (0-255) when it works, so errors are negative
#define EE_OK               0
#define EE_ERR_RANGE        (-1)    // addr > 7FF
#define EE_ERR_NACK_DEVICE  (-2)    // no ACK on control byte (missing or busy)
#define EE_ERR_NACK_WORD    (-3)    // no ACK on word addr
#define EE_ERR_NACK_DATA    (-4)    // no ACK on data
#define EE_ERR_WRITE_TIMEOUT (-5)   // ACK polling never saw the write finish
#define EE_ERR_BUS          (-6)    // SCL stuck low


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// write databyte at addr (000-7FF), waits for the write cycle. EE_OK or EE_ERR_*
int  eebytew(uint16_t addr, uint8_t databyte);

// read addr. byte (0-255) or EE_ERR_*
int  eebyter(uint16_t addr);

// Name: eereset()
// Description: Performs a software reset of the I2C EEPROM using an
// algorithm that conforms to Microchip application note AN709.
void eereset(void);

// short message for a status code
const char *ee_status_text(int status);

#endif // #ifndef EEPROM_H
