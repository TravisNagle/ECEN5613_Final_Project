/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * delay.h: blocking ms delay on Timer 0 (polled). only for LCD power-up, before the
 * busy flag works. Part 2.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0.
 * Leveraged code: Timer 0 mode 1 from the AT89C51RB2/RC2 datasheet. 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef DELAY_H
#define DELAY_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// wait ms milliseconds (1.0004 ms each + a few us overhead). NOT from an ISR
void delay_ms(uint8_t ms);

#endif // #ifndef DELAY_H
