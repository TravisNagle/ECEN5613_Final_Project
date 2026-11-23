/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/13/26
 *  --------------------------------------------------------------------------------
 * lcd.h: HD44780 LCD driver, memory mapped at 0xF400 (16x4 kit LCD). Part 2.
 * the required lab functions + one ISR-only write for the clock. anything that
 * touches an LCD register is __critical so the clock ISR can't land in the middle of
 * an access. lcdgotoxy/lcdputstr just chain those calls (lcd.c says why that's ok).
 *
 * Target: AT89C51RC2, 11.0592 MHz, X1 mode.  Toolchain: SDCC 4.6.0.
 * Part 3: lcd_read_ram() and lcdcreatechar().
 * Leveraged code: required function names and descriptions from the Lab 4 handout;
 *   instruction set and init sequence from the Hitachi HD44780U datasheet. 
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef LCD_H
#define LCD_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>
#include <stdbool.h>


/* -------------------------------------------------- */
//          FUNCTION DECLARATIONS
/* -------------------------------------------------- */
// Name: lcdinit()
// Description: Initializes the LCD (see Figure 25 on page 212
//  of the HD44780U data sheet).
// also checks the LCD actually answers -> lcd_is_ok(). ~60 ms
void lcdinit(void);

// Name: lcdbusywait()
// Description: Polls the LCD busy flag. Function does not return
//  until the LCD controller is ready to accept another command.
// (gives up after LCD_BUSY_TIMEOUT_POLLS and flags the LCD as dead so a missing
// LCD can't hang everything)
void lcdbusywait(void);

// Name: lcdgotoaddr()
// Description: Sets the cursor to the specified LCD DDRAM address.
//  Should call lcdbusywait().
void lcdgotoaddr(unsigned char addr);

// Name: lcdgotoxy()
// Description: Sets the cursor to the LCD DDRAM address corresponding
//  to the specified row and column. Location (0,0) is the top left
//  corner of the LCD screen. Must call lcdgotoaddr().
// bad row/col = ignored, cursor stays put
void lcdgotoxy(unsigned char row, unsigned char column);

// Name: lcdputch()
// Description: Writes the specified character to the current
//  LCD cursor position. Should call lcdbusywait().
void lcdputch(char cc);

// Name: lcdputstr()
// Description: Writes the specified null-terminated string to the LCD
//  starting at the current LCD cursor position. Automatically wraps
//  long strings to the next LCD line after the right edge of the
//  display screen has been reached. Must call lcdputch().
// '\n' jumps to the next line too. row 3 wraps back to row 0
void lcdputstr(char *ss);

// Name: lcdclear()
// Description: Clears the LCD using the HD44780 Clear display instruction.
void lcdclear(void);

// true if lcdinit found the LCD and no busy timeout since
bool lcd_is_ok(void);

// current DDRAM addr counter (0x00-0x7F)
uint8_t lcd_get_addr(void);

// how many busy polls the last wait took (to show clear >> one char)
uint16_t lcd_last_busy_polls(void);

// true if addr is real DDRAM (00-27, 40-67)
bool lcd_ddram_addr_valid(uint8_t addr);

// ISR ONLY (clock). save cursor, write len chars at addr, put cursor back so main
// never notices. does nothing before lcdinit is done or if the LCD is dead.
void lcd_isr_write_at(uint8_t addr, __xdata const char *text, uint8_t len);

// ---- Part 3 ----
// read len bytes of DDRAM (cgram=false, addr 00-7F) or CGRAM (cgram=true, addr
// 00-3F) into buf. cursor is put back afterwards. interrupts off while it runs.
void lcd_read_ram(bool cgram, uint8_t addr, __xdata uint8_t *buf, uint8_t len);

// Name: lcdcreatechar()
// Description: Function to create a 5x8 pixel custom character with
// character code ccode (0<=ccode<=7) using the row values given in
// the 8-byte array row_vals[].
void lcdcreatechar(unsigned char ccode, unsigned char row_vals[]);

// bring-up debug: no busy check, no dead-LCD check, exactly one MOVX each so I can
// see the raw bus when lcdinit fails. main only, interrupts OFF.
// raw byte at 0xF402 (busy + addr)
uint8_t lcd_diag_status_read(void);
// write cmd to 0xF400, no busy check
void lcd_diag_cmd_write(uint8_t cmd);

#endif // #ifndef LCD_H
