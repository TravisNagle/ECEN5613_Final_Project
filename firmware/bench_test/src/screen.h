/* ---------------------------------------------------------------------------------
 * File        : screen.h
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : A 16x4 text buffer on top of the Lab 4 LCD driver. Draw into the
 *               buffer as often as you like; screen_flush() writes only the
 *               characters that differ from what the LCD shows. Character codes
 *               1-5 are the bar-graph glyphs (screen_load_bar_glyphs()).
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : bar glyph shapes from my Lab 4 adcbar.c (CGRAM codes 1-5 =
 *               1-5 lit pixel columns, rows 1-6)
   ---------------------------------------------------------------------------------*/
#ifndef SCREEN_H
#define SCREEN_H

#include <stdint.h>

#define BAR_FIRST_COL   1U
#define BAR_CELLS       11U                 /* cols 1-11 */
#define BAR_PIXELS      55U                 /* 11 cells x 5 columns */

void screen_load_bar_glyphs(void);
void screen_clear(void);                    /* clears the LCD and the buffer */
void screen_putc(uint8_t row, uint8_t col, char c);
void screen_puts(uint8_t row, uint8_t col, const char *s);
void screen_put_hex3(uint8_t row, uint8_t col, uint16_t v);     /* "000"-"FFF" */
void screen_put_hex2(uint8_t row, uint8_t col, uint8_t v);      /* "00"-"FF" */
void screen_bar(uint8_t row, uint16_t code);                    /* 0-1023 -> bar in cols 1-11 */
void screen_flush(void);
void screen_invalidate(void);               /* redraw everything on the next flush */

#endif /* SCREEN_H */
