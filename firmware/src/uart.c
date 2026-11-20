/*
 * File        : uart.c
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : UART mode 1 (8-N-1) clocked by Timer 2 as the baud
 *               generator. The ISR moves bytes between SBUF and two ring
 *               buffers; the main loop does all parsing.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : Timer 2 baud formula and reload 0xFFF5 from the PDR design
 *               doc (docs/MIDI-Controller.pdf, M1); TH2/TL2 preload from the
 *               AT89C51RB2/RC2 errata (doc4181, item 2)
 */
#include "uart.h"

/*
 * Timer 2 baud generator, X1 mode: baud = fosc / (32 * (65536 - RCAP2)).
 * 65536 - 11 gives 31,418 baud, +0.54 % from MIDI's 31,250 (MIDI allows about 1 %).
 * OPEN #4 (Hardware_Map section 9): 31,250-baud MIDI is the listed default;
 * 115,200-baud packets would use 65536 - 3 (0xFFFD) and a different bridge.
 */
#define UART_RELOAD (65536u - 11u)      /* 0xFFF5 */

#define TX_SIZE     64                  /* powers of two: the indexes wrap with a mask */
#define RX_SIZE     64
#define TX_MASK     (TX_SIZE - 1)
#define RX_MASK     (RX_SIZE - 1)

static __xdata uint8_t tx_buf[TX_SIZE];
static __xdata uint8_t rx_buf[RX_SIZE];

/* head is written by the producer, tail by the consumer; each is a single byte */
static volatile __data uint8_t tx_head, tx_tail;
static volatile __data uint8_t rx_head, rx_tail;
static volatile __data uint8_t tx_busy;     /* 1 while the ISR is draining tx_buf */

void uart_init(void)
{
    tx_head = tx_tail = 0;
    rx_head = rx_tail = 0;
    tx_busy = 0;

    SCON = 0x50;                        /* mode 1, REN = 1 */
    T2CON = 0x30;                       /* RCLK = TCLK = 1; EXEN2 = 0 (P1.1 stays the LED); TR2 = 0 */
    RCAP2H = UART_RELOAD >> 8;
    RCAP2L = UART_RELOAD & 0xFF;
    TH2 = UART_RELOAD >> 8;             /* errata item 2: without this preload the */
    TL2 = UART_RELOAD & 0xFF;           /* UART is dead for about 10,000 cycles */
    TR2 = 1;
    ES = 1;
}

void uart_putc(uint8_t c)
{
    uint8_t next = (tx_head + 1) & TX_MASK;

    while (next == tx_tail) {
        /* full: the ISR frees a slot every 320 us */
    }
    tx_buf[tx_head] = c;

    ES = 0;
    tx_head = next;
    if (!tx_busy) {
        tx_busy = 1;
        TI = 1;                         /* start the ISR's send chain */
    }
    ES = 1;
}

int16_t uart_getc(void)
{
    uint8_t c;

    if (rx_tail == rx_head) {
        return -1;
    }
    c = rx_buf[rx_tail];
    rx_tail = (rx_tail + 1) & RX_MASK;
    return c;
}

void uart_isr(void) __interrupt(SI0_VECTOR)
{
    uint8_t next;

    if (RI) {
        RI = 0;
        next = (rx_head + 1) & RX_MASK;
        if (next != rx_tail) {
            rx_buf[rx_head] = SBUF;
            rx_head = next;
        }
        /* else: buffer full, the byte is dropped */
    }
    if (TI) {
        TI = 0;
        if (tx_tail != tx_head) {
            SBUF = tx_buf[tx_tail];
            tx_tail = (tx_tail + 1) & TX_MASK;
        } else {
            tx_busy = 0;
        }
    }
}
