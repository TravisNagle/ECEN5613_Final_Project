/* ---------------------------------------------------------------------------------
 * File        : main.c
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : Bench test for the panel and the motor drivers. No MIDI, no UART.
 *               Hold D-pad CENTER for about 1 s to switch page.
 *
 *               Page 0 (MAIN)
 *                 row 0, 1  fader 1 and 2: label, bar graph (as Lab 4), a motion
 *                           character (^ moving up, v moving down, ! timed out,
 *                           X motor does not move) and the 10-bit reading in hex
 *                 row 2     capacitive touch: T1:HELD / T1:---- and T2
 *                 row 3     D-pad U D L R C, fader buttons F1 F2, class board SW4
 *                 F1 / F2   each press moves that fader to the next of 25 %, 50 %,
 *                           75 % (then 25 % again)
 *               Page 1 (BUS)
 *                 PCF8574 button board: address, the four buttons (the four LEDs
 *                 follow them), 24C16 write/read/restore self-test (F1 repeats it),
 *                 and an I2C bus scan
 *               Page 2 (CAL)
 *                 F1 / F2 drive that fader to both ends, record the pot readings
 *                 at the ends and use them for the 25/50/75 % targets until reset
 *
 *               Always: status LED (P1.1) blinks about 1 Hz; fast blink = LCD
 *               not answering.
 *
 *               Motors: the first move of each fader runs a short probe to learn
 *               which latch direction raises the pot reading, so the wiring order of
 *               the motor leads does not matter. The motors are off at start and
 *               only run after F1 or F2 is pressed.
 * Target      : AT89C51RC2, 11.0592 MHz, X1, SDCC 4.6.0 --model-large (see Makefile)
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : my Lab 4 drivers (lcd, i2c, eeprom, mcp3008, pcf8574, delay, config.h),
 *               and the __sdcc_external_startup XRAM-copy workaround from my Lab 4
 *               main.c
   ---------------------------------------------------------------------------------*/
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "delay.h"
#include "lcd.h"
#include "i2c.h"
#include "eeprom.h"
#include "mcp3008.h"
#include "pcf8574.h"        /* its /INT0 ISR prototype must be visible here for the vector table */
#include "bench.h"
#include "motor.h"
#include "screen.h"

#define LED_N           P1_1        /* class board status LED, lit when 0 */
#define SW4_N           P3_2        /* class board SW4, 0 = pressed */
#define TOUCH2_PIN      P1_5        /* AT42QT1010 A5 OUT, 1 = touched */

#define PAGE_MAIN       0U
#define PAGE_BUS        1U
#define PAGE_CAL        2U
#define PAGE_COUNT      3U

#define EE_TEST_ADDR    0x07FFU     /* last EEPROM byte; saved and restored by the test */
#define EE_MISMATCH     (-100)

#define STEP_COUNT      3U

#define STATUS_IDLE     ' '
#define STATUS_UP       '^'
#define STATUS_DOWN     'v'
#define STATUS_TIMEOUT  '!'
#define STATUS_STUCK    'X'

static volatile __xdata __at(ADDR_BUTTONS) uint8_t s_btn_port;

static __code const uint8_t s_pct[STEP_COUNT] = { 25U, 50U, 75U };

/* ---- state (set in main(), not by initializers) ------------------------------ */
static uint8_t  s_page;
static uint8_t  s_hold_ticks;
static uint8_t  s_hold_done;

static uint8_t  s_btn_cand;
static uint8_t  s_btn_cnt;
static uint8_t  s_btn;              /* debounced pressed bits (BTN_*) */
static uint8_t  s_btn_prev;
static uint8_t  s_touch[FADER_COUNT];
static uint8_t  s_touch_cnt[FADER_COUNT];

static uint16_t s_pos[FADER_COUNT];
static uint16_t s_lo[FADER_COUNT];
static uint16_t s_hi[FADER_COUNT];

static uint16_t s_target[FADER_COUNT];
static uint8_t  s_active[FADER_COUNT];
static uint8_t  s_ticks[FADER_COUNT];
static uint8_t  s_settle[FADER_COUNT];
static uint16_t s_last[FADER_COUNT];     /* position on the previous tick */
static uint8_t  s_pulse[FADER_COUNT];    /* learned nudge PWM, kept between moves */
static uint8_t  s_nudge_dir[FADER_COUNT]; /* direction of the last nudge: 0 none, 1 up, 2 down */
static uint8_t  s_nudge[FADER_COUNT];    /* 0 = ready to nudge, else ticks into the rest after a nudge */
static uint16_t s_nudge_pos[FADER_COUNT];
static uint8_t  s_boost[FADER_COUNT];    /* extra PWM added while the fader is not moving */
static char     s_status[FADER_COUNT];
static uint8_t  s_step[FADER_COUNT];

static uint8_t  s_pcf_btn;          /* button board buttons, 1 = pressed */
static uint8_t  s_pcf_led_last;
static int      s_ee_result;
static uint8_t  s_scan_found[4];
static uint8_t  s_scan_count;
static char     s_cal_msg[17];

static uint8_t  s_heartbeat;

/* ---- startup ---------------------------------------------------------------- */

/* Copied from my Lab 4 main.c. The RC2's internal XRAM ignores the P2 page byte that
   SDCC's own XINIT copy uses, so the initialised xdata is copied here with MOVX @DPTR. */
unsigned char __sdcc_external_startup(void)
{
    AUXR = AUXR_XRS_1KB;
    __asm
        .globl  s_XINIT
        .globl  l_XINIT
        .globl  s_XISEG
        mov     r1,#l_XINIT
        mov     a,r1
        orl     a,#(l_XINIT >> 8)
        jz      00003$
        mov     r2,#((l_XINIT + 255) >> 8)
        mov     r4,#s_XINIT
        mov     r5,#(s_XINIT >> 8)
        mov     r6,#s_XISEG
        mov     r7,#(s_XISEG >> 8)
00001$:
        mov     dpl,r4
        mov     dph,r5
        clr     a
        movc    a,@a+dptr
        inc     dptr
        mov     r4,dpl
        mov     r5,dph
        mov     dpl,r6
        mov     dph,r7
        movx    @dptr,a
        inc     dptr
        mov     r6,dpl
        mov     r7,dph
        djnz    r1,00001$
        djnz    r2,00001$
00003$:
    __endasm;
    return 0U;
}

/* ---- inputs ----------------------------------------------------------------- */

static uint16_t read_pos(uint8_t m)
{
    uint8_t ch = (m == 0U) ? FADER_ADC_CH0 : FADER_ADC_CH1;
    uint16_t a = adc_read(ch);
    uint16_t b = adc_read(ch);

    if (a > ADC_CODE_MAX) { a = 0U; }
    if (b > ADC_CODE_MAX) { b = 0U; }
    return (uint16_t)((a + b) / 2U);
}

static void touch_debounce(uint8_t m, uint8_t raw)
{
    if (raw == s_touch[m]) {
        s_touch_cnt[m] = 0U;
    } else if (++s_touch_cnt[m] >= TOUCH_DEBOUNCE_TICKS) {
        s_touch[m] = raw;
        s_touch_cnt[m] = 0U;
    }
}

static void inputs_poll(void)
{
    uint8_t b = s_btn_port;
    uint8_t raw = (uint8_t)(~b) & BTN_MASK;

    s_btn_prev = s_btn;
    if (raw == s_btn_cand) {
        if (s_btn_cnt < BTN_DEBOUNCE_TICKS) {
            s_btn_cnt++;
        }
        if (s_btn_cnt >= BTN_DEBOUNCE_TICKS) {
            s_btn = raw;
        }
    } else {
        s_btn_cand = raw;
        s_btn_cnt = 0U;
    }

    touch_debounce(0U, (b & TOUCH1_BIT) ? 1U : 0U);
    touch_debounce(1U, TOUCH2_PIN ? 1U : 0U);

    s_pos[0] = read_pos(0U);
    s_pos[1] = read_pos(1U);
}

static bool pressed_edge(uint8_t mask)
{
    return ((s_btn & mask) != 0U) && ((s_btn_prev & mask) == 0U);
}

/* button board: LED n lights while button n is pressed (active-low LEDs) */
static void pcf_poll(void)
{
    uint8_t pins;
    uint8_t led;

    if (pcf_address() == PCF_NOT_FOUND) {
        s_pcf_btn = 0U;
        return;
    }
    if (!pcf_read(&pins)) {
        return;
    }
    s_pcf_btn = (uint8_t)(~pins) & PCF_INPUT_MASK;
    led = (uint8_t)(~(uint8_t)(s_pcf_btn << PCF_OUTPUT_SHIFT)) & PCF_OUTPUT_MASK;
    if (led != s_pcf_led_last) {
        (void)pcf_write_outputs(led, PCF_OUTPUT_MASK);
        s_pcf_led_last = led;
    }
}

/* ---- fader moves ------------------------------------------------------------ */

static uint16_t pct_to_counts(uint8_t m, uint8_t pct)
{
    return (uint16_t)(s_lo[m] + (((uint32_t)(s_hi[m] - s_lo[m]) * pct) / 100UL));
}

static void move_start(uint8_t m, uint16_t target)
{
    if (motor_polarity(m) == POL_STUCK) {
        s_status[m] = STATUS_STUCK;
        s_active[m] = 0U;
        return;
    }
    s_target[m] = target;
    s_ticks[m] = 0U;
    s_settle[m] = 0U;
    s_last[m] = s_pos[m];
    s_boost[m] = 0U;
    s_nudge[m] = 0U;
    s_nudge_dir[m] = 0U;
    s_status[m] = STATUS_IDLE;
    s_active[m] = 1U;
}

static void move_stop(uint8_t m, char status)
{
    motor_drive(m, MOTOR_COAST, 0U);
    s_active[m] = 0U;
    s_status[m] = status;
}

/*
 * One control step per tick. The first version drove the motor in proportion to the
 * error only; with a fast fader and a 12 ms tick that overshoots the target by more
 * than the error it started with, so it hunts from end to end. This version looks
 * ahead: if the speed (counts per tick) would carry the fader across the target within
 * MOVE_LOOKAHEAD_TICKS, it brakes instead of driving. Drive strength is the smaller of
 * the real and the predicted error, and a boost builds up while the fader is not
 * moving, so it finds the breakaway PWM by itself.
 */
static void move_service(uint8_t m)
{
    int16_t err;
    int16_t vel;
    int16_t perr;
    uint16_t aerr;
    uint16_t avel;
    uint16_t mag;
    uint16_t duty;
    bool up;

    if (s_active[m] == 0U) {
        return;
    }
#if ABORT_ON_TOUCH
    if (s_touch[m] != 0U) {
        move_stop(m, STATUS_IDLE);
        return;
    }
#endif
    if (++s_ticks[m] > MOVE_TIMEOUT_TICKS) {
        move_stop(m, STATUS_TIMEOUT);
        return;
    }

    vel = (int16_t)s_pos[m] - (int16_t)s_last[m];
    s_last[m] = s_pos[m];
    err = (int16_t)s_target[m] - (int16_t)s_pos[m];
    perr = err - (int16_t)(vel * (int16_t)MOVE_LOOKAHEAD_TICKS);
    up = (err > 0);
    aerr = (uint16_t)((err < 0) ? -err : err);
    avel = (uint16_t)((vel < 0) ? -vel : vel);

    if (aerr <= MOVE_DEADBAND) {
        motor_drive(m, MOTOR_BRAKE, 0U);
        s_boost[m] = 0U;
        if (avel <= MOVE_STILL_COUNTS) {
            if (++s_settle[m] >= MOVE_SETTLE_TICKS) {
                move_stop(m, STATUS_IDLE);
            }
        } else {
            s_settle[m] = 0U;
        }
        return;
    }
    s_settle[m] = 0U;

    if (aerr < MOVE_NEAR_COUNTS) {
        /* Fine positioning by nudges: one drive tick, then MOVE_NUDGE_REST_TICKS braked
           ticks, then look at how far it went. Too little movement raises the nudge PWM,
           too much lowers it, so it learns the breakaway drive and does not stick-slip. */
        if (s_nudge[m] != 0U) {
            motor_drive(m, MOTOR_BRAKE, 0U);
            if (++s_nudge[m] > MOVE_NUDGE_REST_TICKS) {
                uint16_t moved = (s_pos[m] > s_nudge_pos[m])
                               ? (uint16_t)(s_pos[m] - s_nudge_pos[m])
                               : (uint16_t)(s_nudge_pos[m] - s_pos[m]);
                s_nudge[m] = 0U;
                if ((moved < MOVE_NUDGE_MIN_MOVE) && (s_pulse[m] <= (uint8_t)(255U - MOVE_NUDGE_STEP))) {
                    s_pulse[m] += MOVE_NUDGE_STEP;
                } else if ((moved > MOVE_NUDGE_MAX_MOVE) && (s_pulse[m] >= (uint8_t)(MOVE_NUDGE_FLOOR + MOVE_NUDGE_STEP))) {
                    s_pulse[m] -= MOVE_NUDGE_STEP;
                }
            }
            return;
        }
        if (avel > (uint16_t)(MOVE_STILL_COUNTS + 2U)) {
            motor_drive(m, MOTOR_BRAKE, 0U);        /* still coasting in from the far zone */
            return;
        }
        /* a nudge in the opposite direction to the last one means it overshot: soften */
        if ((s_nudge_dir[m] != 0U) && (s_nudge_dir[m] != (uint8_t)(up ? 1U : 2U))
            && (s_pulse[m] >= (uint8_t)(MOVE_NUDGE_FLOOR + MOVE_NUDGE_STEP))) {
            s_pulse[m] -= MOVE_NUDGE_STEP;
        }
        s_nudge_dir[m] = up ? 1U : 2U;
        s_nudge_pos[m] = s_pos[m];
        s_nudge[m] = 1U;
        motor_drive(m, motor_dir_for(m, up), s_pulse[m]);
        delay_ms(MOVE_NUDGE_MS);                    /* a short push, shorter than one tick */
        motor_drive(m, MOTOR_BRAKE, 0U);
        s_status[m] = up ? STATUS_UP : STATUS_DOWN;
        return;
    }
    s_nudge[m] = 0U;

    if ((err > 0) != (perr > 0)) {
        /* at this speed it would cross the target: let it slow down */
        motor_drive(m, MOTOR_BRAKE, 0U);
        s_boost[m] = 0U;
        return;
    }

    mag = (uint16_t)((perr < 0) ? -perr : perr);
    if (mag > aerr) {
        mag = aerr;
    }
    if (avel <= MOVE_STILL_COUNTS) {
        if (s_boost[m] < MOVE_BOOST_MAX) {
            s_boost[m] += MOVE_BOOST_STEP;
        }
    } else if (s_boost[m] > 2U) {
        s_boost[m] -= 2U;
    } else {
        s_boost[m] = 0U;
    }
    duty = MOVE_MIN_PWM
         + (uint16_t)(((uint32_t)mag * (MOVE_MAX_PWM - MOVE_MIN_PWM)) / MOVE_RAMP_COUNTS)
         + s_boost[m];
    if (duty > 255U) {
        duty = 255U;
    }
    motor_drive(m, motor_dir_for(m, up), (uint8_t)duty);
    s_status[m] = up ? STATUS_UP : STATUS_DOWN;
}

/* F1 / F2 on the main page: next of 25 %, 50 %, 75 % */
static void fader_step(uint8_t m)
{
    s_step[m] = (uint8_t)((s_step[m] + 1U) % STEP_COUNT);
    move_start(m, pct_to_counts(m, s_pct[s_step[m]]));
}

/* ---- page 2: calibration ---------------------------------------------------- */

static void cal_message(const char *text)
{
    uint8_t i = 0U;

    while ((text[i] != '\0') && (i < LCD_COLS)) {
        s_cal_msg[i] = text[i];
        i++;
    }
    s_cal_msg[i] = '\0';
}

static void cal_draw(void);

static void cal_run(uint8_t m, bool up)
{
    uint8_t t;

    motor_drive(m, motor_dir_for(m, up), CAL_PWM);
    for (t = 0U; t < CAL_RUN_TICKS; t++) {
        delay_ms(LOOP_DELAY_MS);
    }
    motor_drive(m, MOTOR_COAST, 0U);
    delay_ms(150U);
}

static void calibrate(uint8_t m)
{
    uint16_t lo;
    uint16_t hi;

    cal_message(m == 0U ? "CAL 1: RUNNING" : "CAL 2: RUNNING");
    cal_draw();
    screen_flush();

    if (motor_polarity(m) == POL_STUCK) {
        cal_message(m == 0U ? "CAL 1: NO MOVE" : "CAL 2: NO MOVE");
        return;
    }
    cal_run(m, false);
    lo = read_pos(m);
    cal_run(m, true);
    hi = read_pos(m);

    if (hi < (uint16_t)(lo + 300U)) {
        cal_message(m == 0U ? "CAL 1: SHORT" : "CAL 2: SHORT");
        return;
    }
    s_lo[m] = lo;
    s_hi[m] = hi;
    cal_message(m == 0U ? "CAL 1: DONE" : "CAL 2: DONE");
    move_start(m, pct_to_counts(m, 50U));       /* park at 50 % */
}

static char pol_char(uint8_t m)
{
    switch (motor_polarity_known(m)) {
    case POL_FWD_RAISES: return 'F';
    case POL_REV_RAISES: return 'R';
    case POL_STUCK:      return 'X';
    default:             return '?';
    }
}

static void cal_draw(void)
{
    uint8_t m;
    uint8_t row;

    screen_puts(0U, 0U, "CAL  F1/F2=run");
    for (m = 0U; m < FADER_COUNT; m++) {
        row = (uint8_t)(1U + m);
        screen_putc(row, 0U, (char)('1' + m));
        screen_puts(row, 2U, "L");
        screen_put_hex3(row, 3U, s_lo[m]);
        screen_puts(row, 7U, "H");
        screen_put_hex3(row, 8U, s_hi[m]);
        screen_putc(row, 12U, pol_char(m));
        screen_putc(row, 13U, s_status[m]);
    }
    screen_puts(3U, 0U, "                ");
    screen_puts(3U, 0U, s_cal_msg);
}

/* ---- page 1: I2C bus -------------------------------------------------------- */

static int ee_selftest(void)
{
    int orig;
    int r;

    orig = eebyter(EE_TEST_ADDR);
    if (orig < 0) {
        return orig;
    }
    r = eebytew(EE_TEST_ADDR, 0xA5U);
    if (r != EE_OK) { return r; }
    r = eebyter(EE_TEST_ADDR);
    if (r < 0) { return r; }
    if (r != 0xA5) { return EE_MISMATCH; }

    r = eebytew(EE_TEST_ADDR, 0x5AU);
    if (r != EE_OK) { return r; }
    r = eebyter(EE_TEST_ADDR);
    if (r < 0) { return r; }
    if (r != 0x5A) { return EE_MISMATCH; }

    r = eebytew(EE_TEST_ADDR, (uint8_t)orig);   /* put back what was there */
    if (r != EE_OK) { return r; }
    r = eebyter(EE_TEST_ADDR);
    if (r < 0) { return r; }
    return (r == orig) ? EE_OK : EE_MISMATCH;
}

/* list the first few distinct devices; the 24C16 answers at all of 0x50-0x57, so only
   0x50 is listed */
static void bus_scan(void)
{
    uint8_t a;

    s_scan_count = 0U;
    for (a = I2C_ADDR_MIN; a <= I2C_ADDR_MAX; a++) {
        if ((a > 0x50U) && (a <= 0x57U)) {
            continue;
        }
        if (i2c_probe(a) && (s_scan_count < sizeof(s_scan_found))) {
            s_scan_found[s_scan_count++] = a;
        }
    }
}

static void bus_run_tests(void)
{
    s_ee_result = ee_selftest();
    bus_scan();
}

static void bus_draw(void)
{
    uint8_t a = pcf_address();
    uint8_t i;
    uint8_t col;

    if (a == PCF_NOT_FOUND) {
        screen_puts(0U, 0U, "PCF8574: none   ");
    } else {
        screen_puts(0U, 0U, (a >= PCF8574A_ADDR_BASE) ? "PCF8574A @" : "PCF8574  @");
        screen_put_hex2(0U, 10U, a);
    }

    screen_puts(1U, 0U, "BTN:");
    for (i = 0U; i < 4U; i++) {
        screen_putc(1U, (uint8_t)(4U + i), (s_pcf_btn & (1U << i)) ? (char)('1' + i) : '-');
    }
    screen_puts(1U, 8U, "LED follow");

    if (s_ee_result == EE_OK) {
        screen_puts(2U, 0U, "EE:PASS F1=again");
    } else if (s_ee_result == EE_MISMATCH) {
        screen_puts(2U, 0U, "EE:MISMATCH     ");
    } else {
        screen_puts(2U, 0U, "EE:                ");
        screen_puts(2U, 3U, ee_status_text(s_ee_result));
    }

    screen_puts(3U, 0U, "I2C:            ");
    col = 4U;
    for (i = 0U; i < s_scan_count; i++) {
        screen_put_hex2(3U, col, s_scan_found[i]);
        col = (uint8_t)(col + 3U);
    }
}

/* ---- page 0: main ----------------------------------------------------------- */

static void main_draw(void)
{
    uint8_t m;
    uint8_t row;
    uint8_t b = s_btn;

    for (m = 0U; m < FADER_COUNT; m++) {
        row = m;
        screen_putc(row, 0U, (char)('1' + m));
        screen_bar(row, s_pos[m]);
        screen_putc(row, 12U, s_status[m]);
        screen_put_hex3(row, 13U, s_pos[m]);
    }

    screen_puts(2U, 0U, s_touch[0] ? "T1:HELD" : "T1:----");
    screen_puts(2U, 8U, s_touch[1] ? "T2:HELD" : "T2:----");

    screen_puts(3U, 0U, "D:");
    screen_putc(3U, 2U, (b & BTN_UP)     ? 'U' : '-');
    screen_putc(3U, 3U, (b & BTN_DOWN)   ? 'D' : '-');
    screen_putc(3U, 4U, (b & BTN_LEFT)   ? 'L' : '-');
    screen_putc(3U, 5U, (b & BTN_RIGHT)  ? 'R' : '-');
    screen_putc(3U, 6U, (b & BTN_CENTER) ? 'C' : '-');
    screen_puts(3U, 8U, "F:");
    screen_putc(3U, 10U, (b & BTN_F1) ? '1' : '-');
    screen_putc(3U, 11U, (b & BTN_F2) ? '2' : '-');
    screen_puts(3U, 13U, "S:");
    screen_putc(3U, 15U, SW4_N ? '-' : '4');
}

/* ---- pages ------------------------------------------------------------------ */

static void page_enter(uint8_t page)
{
    s_page = page;
    screen_clear();
    if (page == PAGE_BUS) {
        bus_run_tests();
    }
}

static void page_poll_buttons(void)
{
    switch (s_page) {
    case PAGE_MAIN:
        if (pressed_edge(BTN_F1)) { fader_step(0U); }
        if (pressed_edge(BTN_F2)) { fader_step(1U); }
        break;
    case PAGE_BUS:
        if (pressed_edge(BTN_F1)) { bus_run_tests(); }
        break;
    default:    /* PAGE_CAL */
        if (pressed_edge(BTN_F1)) { calibrate(0U); }
        if (pressed_edge(BTN_F2)) { calibrate(1U); }
        break;
    }
}

/* hold CENTER about 1 s: next page. Must release before it can switch again. */
static void page_poll_hold(void)
{
    if ((s_btn & BTN_CENTER) == 0U) {
        s_hold_ticks = 0U;
        s_hold_done = 0U;
        return;
    }
    if (s_hold_done != 0U) {
        return;
    }
    if (++s_hold_ticks >= PAGE_HOLD_TICKS) {
        s_hold_done = 1U;
        page_enter((uint8_t)((s_page + 1U) % PAGE_COUNT));
    }
}

static void heartbeat(void)
{
    uint8_t period = lcd_is_ok() ? HEARTBEAT_TICKS : 5U;

    if (++s_heartbeat >= period) {
        s_heartbeat = 0U;
        LED_N = !LED_N;
    }
}

void main(void)
{
    uint8_t m;

    /* motors first: everything off, STBY low */
    motor_init();

    LED_N = 1;                  /* off */
    SW4_N = 1;                  /* inputs: latch high */
    TOUCH2_PIN = 1;

    for (m = 0U; m < FADER_COUNT; m++) {
        s_lo[m] = (m == 0U) ? FADER1_ADC_LO_DEFAULT : FADER2_ADC_LO_DEFAULT;
        s_hi[m] = (m == 0U) ? FADER1_ADC_HI_DEFAULT : FADER2_ADC_HI_DEFAULT;
        s_status[m] = STATUS_IDLE;
        s_pulse[m] = MOVE_NUDGE_START;
        s_step[m] = STEP_COUNT - 1U;        /* the first press goes to 25 % */
    }
    s_pcf_led_last = 0xFFU;
    s_cal_msg[0] = '\0';
    cal_message("READY");

    i2c_init();
    adc_init();
    eereset();
    lcdinit();
    (void)pcf_init();

    screen_load_bar_glyphs();
    page_enter(PAGE_MAIN);

    for (;;) {
        delay_ms(LOOP_DELAY_MS);

        inputs_poll();
        pcf_poll();
        page_poll_hold();
        page_poll_buttons();
        for (m = 0U; m < FADER_COUNT; m++) {
            move_service(m);
        }

        switch (s_page) {
        case PAGE_MAIN: main_draw(); break;
        case PAGE_BUS:  bus_draw();  break;
        default:        cal_draw();  break;
        }
        screen_flush();
        heartbeat();
    }
}
