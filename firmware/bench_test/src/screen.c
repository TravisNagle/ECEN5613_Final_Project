/* ---------------------------------------------------------------------------------
 * File        : screen.c
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : See screen.h. The cursor is moved only when the next changed
 *               character is not the one after the last write, so a bar that grows
 *               by one cell costs one goto and one character.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : Lab 4 lcd.c driver (lcdgotoxy, lcdputch, lcdcreatechar); bar
 *               pixel maths from my Lab 4 adcbar.c
   ---------------------------------------------------------------------------------*/
#include <stdint.h>
#include "config.h"
#include "lcd.h"
#include "screen.h"

#define UNKNOWN_CHAR    ((char)0xFF)        /* never wanted, so a cell holding it is redrawn */

static char s_want[LCD_ROWS][LCD_COLS];
static char s_shown[LCD_ROWS][LCD_COLS];

void screen_load_bar_glyphs(void)
{
    uint8_t n;
    uint8_t r;
    uint8_t cols;
    uint8_t rows[LCD_CHAR_ROWS];

    for (n = 1U; n <= LCD_CHAR_WIDTH; n++) {
        cols = (uint8_t)((LCD_CHAR_ROW_MASK << (LCD_CHAR_WIDTH - n)) & LCD_CHAR_ROW_MASK);
        for (r = 0U; r < LCD_CHAR_ROWS; r++) {
            rows[r] = ((r >= 1U) && (r <= 6U)) ? cols : 0U;
        }
        lcdcreatechar(n, rows);
    }
}

void screen_clear(void)
{
    uint8_t r;
    uint8_t c;

    lcdclear();
    for (r = 0U; r < LCD_ROWS; r++) {
        for (c = 0U; c < LCD_COLS; c++) {
            s_want[r][c] = ' ';
            s_shown[r][c] = ' ';
        }
    }
}

void screen_putc(uint8_t row, uint8_t col, char ch)
{
    if ((row < LCD_ROWS) && (col < LCD_COLS)) {
        s_want[row][col] = ch;
    }
}

void screen_puts(uint8_t row, uint8_t col, const char *s)
{
    while ((*s != '\0') && (col < LCD_COLS)) {
        screen_putc(row, col, *s);
        s++;
        col++;
    }
}

static char hex_digit(uint8_t n)
{
    n &= 0x0FU;
    return (char)((n < 10U) ? ('0' + n) : ('A' + (n - 10U)));
}

void screen_put_hex3(uint8_t row, uint8_t col, uint16_t v)
{
    screen_putc(row, col, hex_digit((uint8_t)(v >> 8)));
    screen_putc(row, (uint8_t)(col + 1U), hex_digit((uint8_t)(v >> 4)));
    screen_putc(row, (uint8_t)(col + 2U), hex_digit((uint8_t)v));
}

void screen_put_hex2(uint8_t row, uint8_t col, uint8_t v)
{
    screen_putc(row, col, hex_digit((uint8_t)(v >> 4)));
    screen_putc(row, (uint8_t)(col + 1U), hex_digit(v));
}

/* lit pixel columns = code * 55 / 1024, rounded; cell i shows min(max(px - 5i, 0), 5) */
void screen_bar(uint8_t row, uint16_t code)
{
    uint32_t px32;
    uint8_t px;
    uint8_t cell;
    uint8_t start;
    uint8_t lit;

    if (code > ADC_CODE_MAX) {
        code = 0U;
    }
    px32 = (((uint32_t)code * BAR_PIXELS) + (ADC_STEPS / 2UL)) / ADC_STEPS;
    px = (px32 > BAR_PIXELS) ? (uint8_t)BAR_PIXELS : (uint8_t)px32;

    for (cell = 0U; cell < BAR_CELLS; cell++) {
        start = (uint8_t)(cell * LCD_CHAR_WIDTH);
        if (px <= start) {
            screen_putc(row, (uint8_t)(BAR_FIRST_COL + cell), ' ');
        } else {
            lit = (uint8_t)(px - start);
            if (lit > LCD_CHAR_WIDTH) {
                lit = LCD_CHAR_WIDTH;
            }
            screen_putc(row, (uint8_t)(BAR_FIRST_COL + cell), (char)lit);
        }
    }
}

void screen_flush(void)
{
    uint8_t r;
    uint8_t c;
    uint8_t next_r = 0xFFU;     /* where the cursor is after the last write */
    uint8_t next_c = 0xFFU;

    for (r = 0U; r < LCD_ROWS; r++) {
        for (c = 0U; c < LCD_COLS; c++) {
            if (s_want[r][c] == s_shown[r][c]) {
                continue;
            }
            if ((r != next_r) || (c != next_c)) {
                lcdgotoxy(r, c);
            }
            lcdputch(s_want[r][c]);
            s_shown[r][c] = s_want[r][c];
            next_r = r;
            next_c = (uint8_t)(c + 1U);     /* past the end of a row it will not match, so it re-gotos */
        }
    }
}

/* force a full redraw next flush (after the LCD was re-initialised) */
void screen_invalidate(void)
{
    uint8_t r;
    uint8_t c;

    for (r = 0U; r < LCD_ROWS; r++) {
        for (c = 0U; c < LCD_COLS; c++) {
            s_shown[r][c] = UNKNOWN_CHAR;
        }
    }
}
