/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/13/26
 *  --------------------------------------------------------------------------------
 * lcd.c: HD44780 LCD driver, memory mapped. Part 2.
 *
 * hardware (final.pld, Hardware_Map 3.3/3.6): MOVX to 0xF400-0xF7FF raises E for as
 * long as /RD or /WR is low (~442 ns in X1). RS = latched A0, R/W = latched A1 from
 * the '373, so the 4 registers are just 4 addresses:
 *     F400 cmd write    F401 data write
 *     F402 status read  F403 data read
 * data lines = AD0-AD7. using __at xdata vars so each access is one MOVX.
 *
 * ISR stuff: the clock ISR writes through the static raw helpers. every public
 * function that touches the LCD is __critical (ints off for one command/char, worst
 * case ~1.7 ms waiting out a clear), so:
 *  - the ISR can't split an access (like between busy check and write)
 *  - the ISR can't re-enter a raw helper main is already in. this matters because
 *    --model-large functions aren't reentrant (params/locals at fixed xdata), so a
 *    nested call would stomp main's data.
 * lcdgotoxy/lcdputstr aren't critical themselves (SDCC won't let a critical function
 * call another critical one). fine though - the ISR puts the cursor back exactly,
 * so it's invisible between calls.
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0 (--model-large).
 * Part 3: lcd_read_ram() and lcdcreatechar() added.
 * Leveraged code: HD44780U datasheet (Table 6 instructions, Figure 23 8-bit init,
 *   Figure 4 DDRAM addressing); required function descriptions from the Lab 4 handout;
 *   ECEN 5613 LCD Guide. 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/


/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "delay.h"
#include "lcd.h"

#define LCD_NO_WRAP         0xFFU   // lcd_wrap_target(): no wrap
#define LCD_INIT_TEST_ADDR  0x45U   // lcdinit writes this and reads it back


/* -------------------------------------------------- */
//          GLOBALS
/* -------------------------------------------------- */
// LCD registers, one MOVX each
static volatile __xdata __at(LCD_ADDR_CMD_WR)    uint8_t s_lcd_cmd_wr;
static volatile __xdata __at(LCD_ADDR_DATA_WR)   uint8_t s_lcd_data_wr;
static volatile __xdata __at(LCD_ADDR_STATUS_RD) uint8_t s_lcd_status_rd;
static volatile __xdata __at(LCD_ADDR_DATA_RD)   uint8_t s_lcd_data_rd;   // Part 3

// DDRAM addr of col 0 for each row
static __code const uint8_t s_row_start[LCD_ROWS] = {
    LCD_ROW0_ADDR, LCD_ROW1_ADDR, LCD_ROW2_ADDR, LCD_ROW3_ADDR
};

static volatile bool s_lcd_ok = false;      // goes false on a busy timeout
static volatile bool s_lcd_ready = false;   // true once lcdinit is done
static volatile uint16_t s_last_polls = 0U; // busy reads in the last wait


/* -------------------------------------------------- */
//          RAW HELPERS (not critical - ISR or inside a critical function only)
/* -------------------------------------------------- */

// poll busy until clear. timeout -> mark LCD dead, then every raw call just returns
// until lcdinit works again
static void lcd_wait_ready(void)
{
    uint16_t polls = 0U;

    if (!s_lcd_ok) {
        return;
    }
    while ((s_lcd_status_rd & LCD_BUSY_FLAG) != 0U) {
        polls++;
        if (polls >= LCD_BUSY_TIMEOUT_POLLS) {
            s_lcd_ok = false;
            break;
        }
    }
    s_last_polls = polls;
}

// wait, then send a command
static void lcd_cmd_raw(uint8_t cmd)
{
    lcd_wait_ready();
    if (s_lcd_ok) {
        s_lcd_cmd_wr = cmd;
    }
}

// wait, then write a char at the cursor (cursor moves +1)
static void lcd_data_raw(uint8_t value)
{
    lcd_wait_ready();
    if (s_lcd_ok) {
        s_lcd_data_wr = value;
    }
}

// burn tADD so the addr counter is actually updated before I read it
// (see LCD_TADD_SETTLE_LOOPS)
static void lcd_tadd_settle(void)
{
    uint8_t i;

    for (i = 0U; i < LCD_TADD_SETTLE_LOOPS; i++) {
        __asm
            nop
        __endasm;
    }
}

// wait for busy + tADD, then read addr counter (bits 6:0)
static uint8_t lcd_addr_raw(void)
{
    lcd_wait_ready();
    lcd_tadd_settle();
    return (uint8_t)(s_lcd_status_rd & LCD_ADDR_MASK);
}

// call right after writing a char. if the cursor just went past the right edge
// (addr = row start + LCD_COLS) return the next row's start, else LCD_NO_WRAP.
// checking AFTER the write gets around the 16x4 weirdness where row 0 ends at 0F
// and 10 is the start of row 2.
static uint8_t lcd_wrap_target(uint8_t addr)
{
    uint8_t row;

    for (row = 0U; row < LCD_ROWS; row++) {
        if (addr == (uint8_t)(s_row_start[row] + LCD_COLS)) {
            return s_row_start[(uint8_t)((row + 1U) % LCD_ROWS)];
        }
    }
    return LCD_NO_WRAP;
}

// start of the row after the one addr is in (row 0 if addr isn't on screen). for '\n'
static uint8_t lcd_next_row_start(uint8_t addr)
{
    uint8_t row;

    for (row = 0U; row < LCD_ROWS; row++) {
        if ((addr >= s_row_start[row]) && (addr < (uint8_t)(s_row_start[row] + LCD_COLS))) {
            return s_row_start[(uint8_t)((row + 1U) % LCD_ROWS)];
        }
    }
    return s_row_start[0];
}


/* -------------------------------------------------- */
//          PUBLIC FUNCTIONS
/* -------------------------------------------------- */

// Figure 23, 8-bit. can't read busy until after the 3rd function set, so the first
// part is just timed delays. not critical (takes ~60 ms) - ISR stays away because
// s_lcd_ready is false until the end.
void lcdinit(void)
{
    s_lcd_ready = false;
    s_lcd_ok = true;

    delay_ms(LCD_POWERUP_MS);               // let VCC settle / internal reset
    s_lcd_cmd_wr = LCD_CMD_FUNC_8BIT;       // wake 1 (no busy check allowed yet)
    delay_ms(LCD_WAKE1_MS);
    s_lcd_cmd_wr = LCD_CMD_FUNC_8BIT;       // wake 2
    delay_ms(LCD_WAKE2_MS);
    s_lcd_cmd_wr = LCD_CMD_FUNC_8BIT;       // wake 3
    delay_ms(LCD_WAKE3_MS);

    lcd_cmd_raw(LCD_CMD_FUNC_8BIT_2LINE);   // 8-bit, 2-line, 5x8
    lcd_cmd_raw(LCD_CMD_DISPLAY_OFF);
    lcd_cmd_raw(LCD_CMD_CLEAR);
    lcd_cmd_raw(LCD_CMD_ENTRY_INC);         // cursor goes right, no shift
    lcd_cmd_raw(LCD_CMD_DISPLAY_ON_CUR);    // on, underline cursor

    // is it actually there? addr counter should read back what I wrote. no LCD =
    // P0 pulled up = 0xFF, so this fails or busy times out
    lcd_cmd_raw(LCD_CMD_SET_DDRAM | LCD_INIT_TEST_ADDR);
    if (lcd_addr_raw() != LCD_INIT_TEST_ADDR) {
        s_lcd_ok = false;
    }
    lcd_cmd_raw(LCD_CMD_SET_DDRAM | LCD_ROW0_ADDR);

    s_lcd_ready = s_lcd_ok;
}

void lcdbusywait(void) __critical
{
    lcd_wait_ready();
}

// set DDRAM addr (0x80 | addr). busy wait happens inside lcd_cmd_raw
void lcdgotoaddr(unsigned char addr) __critical
{
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | (addr & LCD_ADDR_MASK)));
}

// row/col -> addr from the table, then lcdgotoaddr
void lcdgotoxy(unsigned char row, unsigned char column)
{
    if ((row < LCD_ROWS) && (column < LCD_COLS)) {
        lcdgotoaddr((unsigned char)(s_row_start[row] + column));
    }
}

// write char at cursor, LCD bumps the cursor itself
void lcdputch(char cc) __critical
{
    lcd_data_raw((uint8_t)cc);
}

// lcdputch each char, read the addr after each one, jump rows at the right edge
// (0-1-2-3-0). ISR can sneak in between steps but it restores the cursor, so the
// wrap check still sees the right addr.
void lcdputstr(char *ss)
{
    uint8_t next;

    while (*ss != '\0') {
        if (*ss == '\n') {
            lcdgotoaddr(lcd_next_row_start(lcd_get_addr()));
        } else {
            lcdputch(*ss);
            next = lcd_wrap_target(lcd_get_addr());
            if (next != LCD_NO_WRAP) {
                lcdgotoaddr(next);
            }
        }
        ss++;
    }
}

// clear = all spaces, cursor to 00. LCD is busy ~1.6 ms after, next call's busy
// wait handles it
void lcdclear(void) __critical
{
    lcd_cmd_raw(LCD_CMD_CLEAR);
}

bool lcd_is_ok(void)
{
    return s_lcd_ok && s_lcd_ready;
}

uint8_t lcd_get_addr(void) __critical
{
    return lcd_addr_raw();
}

// read this inside a critical block right after the wait I care about, otherwise
// the ISR's waits overwrite it
uint16_t lcd_last_busy_polls(void)
{
    return s_last_polls;
}

// 2 DDRAM lines x 40 cells in 2-line mode
bool lcd_ddram_addr_valid(uint8_t addr)
{
    return (addr < LCD_DDRAM_LINE_LEN) ||
           ((addr >= LCD_ROW1_ADDR) && (addr < (uint8_t)(LCD_ROW1_ADDR + LCD_DDRAM_LINE_LEN)));
}

// ISR ONLY. save cursor -> write -> restore cursor (handout: cursor must be saved
// before and restored after any ISR).
// Part 3: the CGRAM/RAM-read functions below are __critical end to end and finish
// with a set DDRAM addr, so the ISR never sees the addr counter pointing into CGRAM.
void lcd_isr_write_at(uint8_t addr, __xdata const char *text, uint8_t len)
{
    uint8_t saved;

    if (!s_lcd_ready || !s_lcd_ok) {
        return;
    }
    saved = lcd_addr_raw();
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | addr));
    while (len > 0U) {
        lcd_data_raw((uint8_t)*text);
        text++;
        len--;
    }
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | saved));
}


/* -------------------------------------------------- */
//          PART 3: RAM READS + CUSTOM CHARACTERS
/* -------------------------------------------------- */

// read len bytes of DDRAM (cgram = false) or CGRAM (cgram = true) starting at addr
// into buf, then put the cursor back where it was.
// HD44780 rule (datasheet "Reading data from CG or DD RAM"): set the address first,
// then each data read returns one byte and bumps the addr counter. I still wait on
// busy + tADD before every read so the counter has moved before the next one.
// the whole thing is __critical: if the clock ISR ran halfway through it would
// restore the cursor as a DDRAM address and the rest of the read would come from the
// wrong RAM. worst case 64 reads x ~45 us ~ 3 ms with interrupts off; the PCA tick
// is drift-free so the clock just updates a little late, it doesn't lose time.
void lcd_read_ram(bool cgram, uint8_t addr, __xdata uint8_t *buf, uint8_t len) __critical
{
    uint8_t saved;

    if (!s_lcd_ready || !s_lcd_ok) {
        return;
    }
    saved = lcd_addr_raw();
    if (cgram) {
        lcd_cmd_raw((uint8_t)(LCD_CMD_SET_CGRAM | (addr & LCD_CGRAM_ADDR_MASK)));
    } else {
        lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | (addr & LCD_ADDR_MASK)));
    }
    while ((len > 0U) && s_lcd_ok) {
        lcd_wait_ready();
        lcd_tadd_settle();
        *buf = s_lcd_data_rd;
        buf++;
        len--;
    }
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | saved));
}

// Name: lcdcreatechar()
// Description: Function to create a 5x8 pixel custom character with
// character code ccode (0<=ccode<=7) using the row values given in
// the 8-byte array row_vals[].
// row_vals[0] = top row, bit 4 = leftmost pixel. bad ccode = ignored. ends with a
// set DDRAM addr back to the saved cursor so later lcdputch() goes to the screen,
// not into CGRAM. __critical for the same reason as lcd_read_ram().
void lcdcreatechar(unsigned char ccode, unsigned char row_vals[]) __critical
{
    uint8_t saved;
    uint8_t row;

    if (!s_lcd_ready || !s_lcd_ok || (ccode > LCD_CHAR_CODE_MAX)) {
        return;
    }
    saved = lcd_addr_raw();
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_CGRAM | (uint8_t)(ccode << LCD_CHAR_CODE_SHIFT)));
    for (row = 0U; row < LCD_CHAR_ROWS; row++) {
        lcd_data_raw((uint8_t)(row_vals[row] & LCD_CHAR_ROW_MASK));
    }
    lcd_cmd_raw((uint8_t)(LCD_CMD_SET_DDRAM | saved));
}


/* -------------------------------------------------- */
//          DIAGNOSTIC ACCESS (bring-up only)
/* -------------------------------------------------- */

uint8_t lcd_diag_status_read(void)
{
    return s_lcd_status_rd;
}

void lcd_diag_cmd_write(uint8_t cmd)
{
    s_lcd_cmd_wr = cmd;
}
