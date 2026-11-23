/* ---------------------------------------------------------------------------------
 * Nathan Cohen
 * ECEN 5613 - Fall 2026 - Prof. McClure
 * University of Colorado Boulder
 * Revised 11/11/26
 *  --------------------------------------------------------------------------------
 * config.h: all the board constants for Lab 4 in one spot - clock, baud (Timer 2),
 * Timer 0 delay, I2C pins, EEPROM size, LCD addresses/commands, PCA clock tick.
 * Pins match the final project Hardware_Map Rev 13 (3.2-3.3) so I only wire this once.
 *
 * Target: AT89C51RC2, 11.0592 MHz crystal, X1 mode.  Toolchain: SDCC 4.6.0.
 * Leveraged code: register names from SDCC's at89c51ed2.h; Timer 2 baud formula from
 *   the AT89C51RB2/RC2 datasheet (Timer 2 baud rate generator); 24C16 geometry from
 *   the Microchip 24LC16B datasheet. Structure follows my Lab 3 Step 7 config.h.
 * Headers and comments formatted with AI assistance, all code is written by hand.
   ---------------------------------------------------------------------------------*/

// header guard
#ifndef CONFIG_H
#define CONFIG_H
/* -------------------------------------------------- */
//          INCLUDES & DEFINES
/* -------------------------------------------------- */
#include <stdint.h>

// ---- Oscillator ----
// stay in X1 - X2 makes the E pulse too short for the HD44780 (Hardware_Map 3.12)
#define F_OSC_HZ                11059200UL

// ---- Serial: UART mode 1, Timer 2 for baud ----
// Timer 2 not Timer 1: final project needs T2 for 31250 MIDI anyway, and this keeps
// Timer 0 free.
// baud = F_OSC / (32 * (65536 - RCAP2))  ->  11059200 / (32*9600) = 36 exactly
// so RCAP2 = 65536 - 36 = 0xFFDC
#define BAUD_RATE               9600UL
#define T2_BAUD_DIVIDE          32UL
#define T2_COUNTS_PER_BIT       (F_OSC_HZ / (T2_BAUD_DIVIDE * BAUD_RATE))
#define T2_RELOAD               ((uint16_t)(65536UL - T2_COUNTS_PER_BIT))
#define T2_RELOAD_HIGH          ((uint8_t)(T2_RELOAD >> 8))
#define T2_RELOAD_LOW           ((uint8_t)(T2_RELOAD & 0xFFU))

// catch it at compile time if I ever pick a baud that doesn't divide evenly
#if ((F_OSC_HZ % (T2_BAUD_DIVIDE * BAUD_RATE)) != 0)
#error "BAUD_RATE is not exactly reachable with Timer 2 at F_OSC_HZ - pick another"
#endif

#define SCON_MODE1_REN          0x50U   // 8-bit UART + receiver on
#define T2CON_BAUD_RX_TX        0x30U   // RCLK=TCLK=1, T2 does both directions
                                        // (TR2 gets set separately)

// ---- AUXR: turn on the full 1 KB internal XRAM (no external RAM anymore) ----
#define AUXR_XRS_1KB            0x0CU   // XRS=11, EXTRAM=0, AO=0 - leave ALE on, the
                                        // '373 needs it for LCD RS and R/W

// ---- I2C (bit-banged) ----
// SDA = P3.4 (pin 14), SCL = P3.5 (pin 15), 5.1k pull-ups to 5V.
// port pins are quasi-bidirectional: write 1 = just the weak pull-up = "released",
// so it acts open-drain and I can read the pin back.
#define I2C_SDA                 P3_4
#define I2C_SCL                 P3_5
#define I2C_RELEASED            1
#define I2C_DRIVEN_LOW          0

// how long to wait for SCL to come back high before calling it a bus fault.
// ~7.6 us per loop -> 200 loops ~ 1.5 ms. 24C16/PCF8574 never stretch, so if this
// trips it's a short or something stuck, not a slow slave.
#define I2C_SCL_STRETCH_LOOPS   200U

// R/W bit tacked onto the 7-bit address
#define I2C_WRITE_BIT           0x00U
#define I2C_READ_BIT            0x01U
#define I2C_ADDR_MIN            0x08U   // 00-07 and 78-7F are reserved, skip in scan
#define I2C_ADDR_MAX            0x77U

// ---- 24C16 EEPROM (U10) ----
// 2 KB = 8 blocks x 256. chip ignores A0-A2 pins - block # (addr bits 10:8) goes in
// the device address instead, so it shows up as 0x50-0x57 and word addr is 1 byte.
// control byte = 1010 B2 B1 B0 R/W
#define EE_SIZE_BYTES           2048U
#define EE_ADDR_MAX             (EE_SIZE_BYTES - 1U)      // 0x7FF
#define EE_DEVICE_ADDR7         0x50U                     // block 0
#define EE_BLOCK_SHIFT          8U                        // addr bits 10:8 = block
#define EE_BLOCK_MASK           0x07U
#define EE_WORD_MASK            0xFFU

// tWC = 5 ms max. chip NACKs its address until the write is done (ACK polling).
// one poll ~130 us, 200 polls ~26 ms = plenty of margin
#define EE_WRITE_POLL_MAX       200U

// AN709 reset = START, 9 clocks w/ SDA high, START, STOP
#define EE_RESET_CLOCKS         9U

// ---- Hex dump ----
#define DUMP_BYTES_PER_LINE     16U

// ---- Timer 0: polled ms delay, only used for LCD power-up ----
// T0 ticks at F_OSC/12 = 921600 Hz. 1 ms = 921.6 -> round to 922 (1.0004 ms).
// mode 1 16-bit, just poll TF0, no interrupt
#define T0_CLOCK_HZ             (F_OSC_HZ / 12UL)
#define T0_COUNTS_PER_MS        ((uint16_t)((T0_CLOCK_HZ + 500UL) / 1000UL))
#define T0_RELOAD_1MS           ((uint16_t)(65536UL - T0_COUNTS_PER_MS))
#define TMOD_T0_MASK            0x0FU
#define TMOD_T0_MODE1           0x01U   // GATE=0 C/T=0 mode 1

// ---- LCD (Part 2): HD44780, memory mapped through U7 (final.pld) ----
// 0xF400-0xF7FF drives E. RS = latched A0, R/W = latched A1 (from U3)
#define LCD_ADDR_CMD_WR         0xF400U // RS=0 RW=0  command write
#define LCD_ADDR_DATA_WR        0xF401U // RS=1 RW=0  data write
#define LCD_ADDR_STATUS_RD      0xF402U // RS=0 RW=1  busy flag (bit 7) + addr counter
#define LCD_ADDR_DATA_RD        0xF403U // RS=1 RW=1  data read

// kit LCD is a Samsung 16x4. if I swap to the Optrex 20x4, change LCD_COLS to 20
#define LCD_COLS                16U
#define LCD_ROWS                4U
#if (LCD_COLS == 16U)
#define LCD_ROW0_ADDR           0x00U
#define LCD_ROW1_ADDR           0x40U
#define LCD_ROW2_ADDR           0x10U
#define LCD_ROW3_ADDR           0x50U
#elif (LCD_COLS == 20U)
#define LCD_ROW0_ADDR           0x00U
#define LCD_ROW1_ADDR           0x40U
#define LCD_ROW2_ADDR           0x14U
#define LCD_ROW3_ADDR           0x54U
#else
#error "LCD_COLS must be 16 or 20"
#endif

// HD44780 commands (datasheet Table 6)
#define LCD_CMD_CLEAR           0x01U   // clear + home, slow (~1.6 ms)
#define LCD_CMD_ENTRY_INC       0x06U   // cursor moves right, no shift
#define LCD_CMD_DISPLAY_OFF     0x08U
#define LCD_CMD_DISPLAY_ON_CUR  0x0EU   // display on, underline cursor, no blink
#define LCD_CMD_FUNC_8BIT       0x30U   // 8-bit, used for the wake-up writes
#define LCD_CMD_FUNC_8BIT_2LINE 0x38U   // 8-bit, 2-line (= 4-line module), 5x8
#define LCD_CMD_SET_DDRAM       0x80U   // OR in the address
#define LCD_CMD_SET_CGRAM       0x40U   // OR in the CGRAM address (6 bits)
#define LCD_BUSY_FLAG           0x80U   // status bit 7
#define LCD_ADDR_MASK           0x7FU   // status bits 6:0 = addr counter

// ---- LCD RAM (Part 3) ----
// DDRAM in 2-line mode = 2 lines x 40 cells at 00-27 and 40-67
#define LCD_DDRAM_LINE_LEN      0x28U
// CGRAM = 8 characters x 8 rows (5x8 font), CGRAM addr = code*8 + row
#define LCD_CGRAM_CHARS         8U
#define LCD_CHAR_ROWS           8U
#define LCD_CGRAM_SIZE          (LCD_CGRAM_CHARS * LCD_CHAR_ROWS)   // 64
#define LCD_CGRAM_ADDR_MASK     0x3FU
#define LCD_CHAR_CODE_MAX       (LCD_CGRAM_CHARS - 1U)              // 7
#define LCD_CHAR_CODE_SHIFT     3U      // code -> CGRAM addr (x8)
#define LCD_CHAR_WIDTH          5U
#define LCD_CHAR_ROW_MASK       0x1FU   // only bits 4:0 are pixels (bit 4 = left)

// power-up timing (Figure 23), padded a bit
#define LCD_POWERUP_MS          50U     // needs >15 ms
#define LCD_WAKE1_MS            5U      // needs >4.1 ms
#define LCD_WAKE2_MS            1U      // needs >100 us
#define LCD_WAKE3_MS            1U      // not required, just extra margin

// give up on busy after this many polls. ~9 us each -> ~18 ms, 10x a clear.
// a missing LCD reads 0xFF = busy forever, so without this it'd hang
#define LCD_BUSY_TIMEOUT_POLLS  2000U

// addr counter updates tADD after busy clears (~5.6 us at 270 kHz, ~8 us on a slow
// KS0066). read it too soon and I get the OLD address. 8 loops x ~4.3 us ~ 35 us.
#define LCD_TADD_SETTLE_LOOPS   8U

// ---- Elapsed clock (Part 2): PCA module 2 as a software timer ----
// PCA clock = F_OSC/4 = 2764800 Hz (CPS=01). same as the final project PWM so they
// can share the PCA.
// 10 ms = 27648 counts exactly. ISR adds this to the compare value each match so
// it never drifts even if the ISR runs late.
// module 2 pin (P1.5) isn't driven in this mode, TOG=0
#define PCA_CLOCK_HZ            (F_OSC_HZ / 4UL)
#define CLOCK_TICK_MS           10U
#define CLOCK_TICK_COUNTS       ((uint16_t)((PCA_CLOCK_HZ * CLOCK_TICK_MS) / 1000UL))
#define CLOCK_TICKS_PER_TENTH   10U     // 10 x 10 ms = 0.1 s
#if (((PCA_CLOCK_HZ * CLOCK_TICK_MS) % 1000UL) != 0)
#error "PCA tick is not an exact number of counts"
#endif
#define CMOD_CPS_PERIPH_DIV2    0x02U   // CPS=01, everything else off
#define CCAPM_SW_TIMER          0x49U   // ECOM | MAT | ECCF (Table 25)

// clock goes in the bottom-right corner, "MM:SS.S" = 7 chars
#define CLOCK_TEXT_LEN          7U
#define CLOCK_LCD_ROW           (LCD_ROWS - 1U)
#define CLOCK_LCD_COL           (LCD_COLS - CLOCK_TEXT_LEN)

// toggles every second -> 0.5 Hz square wave, check period on the logic analyzer.
// P1.0 is free for now (DBG_TX later in the final project)
#define CLOCK_SCOPE_PIN         P1_0

// ---- PCF8574 I/O expander (Part 3) ----
// shares SDA/SCL with the 24C16. Hardware_Map 4.3 button board: P0-P3 = buttons to
// GND (10k pull-ups), P4-P7 = LEDs, active low (330R to +5V). /INT (pin 13) ->
// P3.2 /INT0 = BUS_INT_N, 10k pull-up (class SW4 also pulls it low, harmless).
// address = base + A2..A0. the plain PCF8574 is 0x20-0x27, the A version 0x38-0x3F,
// pcf_init() looks in both and takes the first one that ACKs.
#define PCF8574_ADDR_BASE       0x20U
#define PCF8574A_ADDR_BASE      0x38U
#define PCF_ADDR_COUNT          8U
#define PCF_INPUT_MASK          0x0FU   // P0-P3 inputs (1 = input)
#define PCF_OUTPUT_MASK         0xF0U   // P4-P7 outputs
#define PCF_OUTPUT_SHIFT        4U      // input P(n) drives output P(n+4)
#define PCF_OUTPUTS_OFF         0xF0U   // active-low LEDs -> 1 = off
// demo rule from the handout: read the input pins, invert, write to the outputs.
// buttons and LEDs are both active low, so with INVERT=1 an LED is lit while its
// button is released and goes dark while pressed. set to 0 for "lit while pressed".
#define PCF_DEMO_INVERT         1
#define PCF_INT_PIN             P3_2    // /INT0, low while the PCF8574 has a change

// ---- MCP3008 10-bit ADC, bit-banged SPI (Part 3 Step 8, ADC option) ----
// (Step 6 uses the same chip on the SPI controller, see below)
// same pins as the final project U11 (Hardware_Map 3.2, A.9), so this driver is
// the fader-read driver later. SPI mode 0,0: data changes while SCK is low, the
// ADC samples DIN on the rising edge and changes DOUT on the falling edge.
// J15 (/INT1 to GND) and J16 (P1.6 to P1.5) MUST be off: J15 shorts DOUT to GND,
// J16 ties SCK to P1.5.
#define ADC_CS_N                P1_2    // U11.10 /CS
#define ADC_SCK                 P1_6    // U11.13 CLK
#define ADC_MOSI                P1_7    // U11.11 DIN
#define ADC_MISO                P3_3    // U11.12 DOUT (latch kept at 1 = input)
#define ADC_CHANNELS            8U
#define ADC_CHANNEL_MAX         (ADC_CHANNELS - 1U)
#define ADC_CODE_MAX            1023U
#define ADC_STEPS               1024UL
// VREF = VREF_F = +5 V through 100 R + 10 uF (A.9). MEASURE it and put the real
// value here, the mV readout scales from it.
#define ADC_VREF_MV             5000UL
// command = start bit, SGL/DIFF = 1 (single ended), D2 D1 D0 = channel -> 5 bits
#define ADC_CMD_START_SGL       0x18U   // 1 1 000
#define ADC_CMD_BITS            5U
// after the command: 1 clock for the null bit + 10 data bits, each read after a
// falling edge
#define ADC_READ_CLOCKS         11U

// ---- Part 3 Step 6: the same MCP3008 on the RC2's SPI controller ----
// datasheet doc4180 section "Serial Port Interface": SCK = P1.6, MOSI = P1.7 (same
// wires as above), MISO = P1.5, /SS = P1.1. the final project has DOUT on P3.3,
// which the controller can't read, so for Step 6 DOUT also gets a jumper to P1.5
// (A5 / TOUCH2 isn't built, J16 must be off). P1.1 drives the status LED, so the
// /SS input is ignored (SSDIS = 1). SSDIS isn't allowed with CPHA = 0, so the
// controller runs SPI mode 1,1 (CPOL = 1, CPHA = 1), which the MCP3008 also
// supports (it samples DIN on rising edges and shifts DOUT on falling edges in both
// modes). /CS stays a plain port pin (P1.2).
#define ADC_HW_MISO             P1_5    // latch 1 = input for the controller
#define SPCON_SPR2              0x80U
#define SPCON_SPEN              0x40U
#define SPCON_SSDIS             0x20U
#define SPCON_MSTR              0x10U
#define SPCON_CPOL              0x08U
#define SPCON_CPHA              0x04U
#define SPCON_SPR1              0x02U
#define SPCON_SPR0              0x01U
#define SPSTA_SPIF              0x80U   // byte done; cleared by reading SPSTA then SPDAT
// F_CLK_PERIPH = F_OSC / 2 in X1 mode; SPR = 011 -> /16 -> 11.0592 MHz / 32 =
// 345.6 kHz. MCP3008 at 5 V allows 10 kHz to 3.6 MHz. the port pins only have a
// short strong pull-up on 0 -> 1, so start slow and look at the SCK edges (MEASURE)
#define SPCON_DIV16             (SPCON_SPR1 | SPCON_SPR0)
#define SPCON_ADC_MASTER        (SPCON_MSTR | SPCON_SSDIS | SPCON_CPOL | SPCON_CPHA | \
                                 SPCON_DIV16)    // 0x3F, SPEN set separately
#define ADC_SPI_HZ              ((F_OSC_HZ / 2UL) / 16UL)
#define ADC_SPI_WAIT_POLLS      200U    // SPIF timeout per byte (a byte is ~23 us)
// 3-byte frame (MCP3008 datasheet section 6.1, 8-bit segments):
//   send 0x01 (start bit last), send SGL D2 D1 D0 0000, send 0x00
//   2nd reply byte low 2 bits = B9 B8, 3rd reply byte = B7..B0
#define ADC_HW_START_BYTE       0x01U
#define ADC_HW_SGL_BIT          0x80U
#define ADC_HW_CH_SHIFT         4U
#define ADC_HW_HIGH_MASK        0x03U
#define ADC_BAR_CH0             0U      // V command: top bar
#define ADC_BAR_CH1             1U      // V command: second bar
#define ADC_BAR_UPDATE_MS       100U    // V refresh (only changed cells redrawn)

// ---- Misc ----
#define ASCII_CR                '\r'
#define ASCII_LF                '\n'
#define ASCII_BS                0x08
#define ASCII_DEL               0x7F
#define ASCII_ESC               0x1B
#define ASCII_BEL               0x07
#define ASCII_PRINTABLE_MIN     0x20
#define ASCII_PRINTABLE_MAX     0x7E
#define LINE_BUFFER_SIZE        16U     // hex entries are 3 digits max, extra for spaces
#define LCD_TEXT_BUFFER_SIZE    ((LCD_COLS * LCD_ROWS) + 1U) // full screen + NUL
#define HEX_BASE                16U

#endif // #ifndef CONFIG_H
