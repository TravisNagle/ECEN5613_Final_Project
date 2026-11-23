/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * delay.c: blocking ms delay, Timer 0 mode 1, poll TF0. Part 2.
 * using the timer instead of a counted loop so it doesn't depend on what SDCC does
 * with the loop. T0 = F_OSC/12 = 921600 Hz -> 922 counts/ms (reload 0xFC66).
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Leveraged code: Timer 0 mode 1 from the AT89C51RB2/RC2 datasheet. 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/


/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <at89c51ed2.h>
#include <stdint.h>
#include "config.h"
#include "delay.h"


/* -------------------------------------------------- */
//          FUNCTION DEFINITIONS
/* -------------------------------------------------- */

// each ms: load 65536-922, run, wait for overflow. only touch T0's half of TMOD
void delay_ms(uint8_t ms)
{
    TR0 = 0;
    TMOD = (TMOD & (uint8_t)~TMOD_T0_MASK) | TMOD_T0_MODE1;
    while (ms > 0U) {
        TH0 = (uint8_t)(T0_RELOAD_1MS >> 8);
        TL0 = (uint8_t)(T0_RELOAD_1MS & 0xFFU);
        TF0 = 0;
        TR0 = 1;
        while (TF0 == 0) {
            // wait for 1 ms
        }
        TR0 = 0;
        ms--;
    }
    TF0 = 0;
}
