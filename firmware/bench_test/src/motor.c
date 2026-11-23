/* ---------------------------------------------------------------------------------
 * File        : motor.c
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : TB6612 motor channels. U14 is write-only, so the byte last written
 *               is kept in s_latch and rebuilt from the two motors' states on every
 *               change. PWM comes from PCA modules 0 and 1 in 8-bit PWM mode, clock
 *               fosc/4 = 2.7648 MHz, so the PWM frequency is 10.8 kHz.
 *               PCA 8-bit PWM: CCAPnL is reloaded from CCAPnH at each counter
 *               overflow and the pin is high while CL >= CCAPnL, so the high time is
 *               (256 - CCAPnH) / 256. CCAPnH = 0 is 100 % (always high). 0 % is done
 *               by turning the module off and driving the port latch low.
 *               Safe state: PWM pins low and U14 = 0, which also holds STBY low.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : PCA registers and PWM mode from the AT89C51RB2/RC2 datasheet
 *               (doc4180, PCA section); pin map from Hardware_Map 3.2 and A.4.
   ---------------------------------------------------------------------------------*/
#include <at89c51ed2.h>
#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "delay.h"
#include "mcp3008.h"
#include "bench.h"
#include "motor.h"

#define CMOD_FOSC_DIV4      0x02U   /* CPS1:CPS0 = 01, no interrupt */
#define CCAPM_PWM8          0x42U   /* ECOM | PWM */
#define CCAPM_OFF           0x00U

static volatile __xdata __at(ADDR_MOTOR_LATCH) uint8_t s_latch_port;

static uint8_t s_dir[FADER_COUNT];
static uint8_t s_pol[FADER_COUNT];

/* ---- latch -------------------------------------------------------------------- */

static void latch_write(void)
{
    uint8_t v = 0U;

    /* motor 0 = AIN1/AIN2, motor 1 = BIN1/BIN2 */
    if (s_dir[0] & 1U) { v |= LATCH_AIN1; }     /* FWD or BRAKE */
    if (s_dir[0] & 2U) { v |= LATCH_AIN2; }     /* REV or BRAKE */
    if (s_dir[1] & 1U) { v |= LATCH_BIN1; }
    if (s_dir[1] & 2U) { v |= LATCH_BIN2; }
    if ((s_dir[0] != MOTOR_COAST) || (s_dir[1] != MOTOR_COAST)) {
        v |= LATCH_STBY;
    }
    s_latch_port = v;
}

/* ---- PWM ---------------------------------------------------------------------- */

static void pwm_set(uint8_t m, uint8_t duty)
{
    uint8_t hi = (uint8_t)(0U - duty);          /* 256 - duty, as a byte (0 for 100 %) */

    if (duty == 0U) {
        if (m == 0U) { CCAPM0 = CCAPM_OFF; P1_3 = 0; }
        else         { CCAPM1 = CCAPM_OFF; P1_4 = 0; }
        return;
    }
    if (m == 0U) {
        CCAP0H = hi;
        CCAP0L = hi;
        P1_3 = 1;                               /* latch high so the PCA output can drive the pin */
        CCAPM0 = CCAPM_PWM8;
    } else {
        CCAP1H = hi;
        CCAP1L = hi;
        P1_4 = 1;
        CCAPM1 = CCAPM_PWM8;
    }
}

/* ---- public ------------------------------------------------------------------- */

void motor_init(void)
{
    CCAPM0 = CCAPM_OFF;
    CCAPM1 = CCAPM_OFF;
    P1_3 = 0;
    P1_4 = 0;
    s_dir[0] = MOTOR_COAST;
    s_dir[1] = MOTOR_COAST;
    s_pol[0] = POL_UNKNOWN;
    s_pol[1] = POL_UNKNOWN;
    latch_write();
    CMOD = CMOD_FOSC_DIV4;
    CR = 1;                                     /* PCA counter runs; the pins stay low until enabled */
}

void motor_drive(uint8_t m, uint8_t dir, uint8_t duty)
{
    if (m >= FADER_COUNT) {
        return;
    }
    if (dir == MOTOR_COAST) {
        duty = 0U;
    }
    /* order matters: stop the PWM before a direction change, set the direction before
       the PWM starts */
    pwm_set(m, 0U);
    s_dir[m] = dir;
    latch_write();
    pwm_set(m, duty);
}

void motor_all_off(void)
{
    pwm_set(0U, 0U);
    pwm_set(1U, 0U);
    s_dir[0] = MOTOR_COAST;
    s_dir[1] = MOTOR_COAST;
    latch_write();
}

/* average of two readings, 0-1023; error codes read as 0 */
static uint16_t pos_read(uint8_t m)
{
    uint16_t a = adc_read(m == 0U ? FADER_ADC_CH0 : FADER_ADC_CH1);
    uint16_t b = adc_read(m == 0U ? FADER_ADC_CH0 : FADER_ADC_CH1);

    if (a > ADC_CODE_MAX) { a = 0U; }
    if (b > ADC_CODE_MAX) { b = 0U; }
    return (uint16_t)((a + b) / 2U);
}

/*
 * One probe in one direction. Escalating short pushes (PROBE_START_PWM up to
 * PROBE_MAX_PWM), each watched every PROBE_POLL_MS; it brakes the moment the pot has
 * moved PROBE_MIN_MOVE counts, so the fader travels a few millimetres at most. The first
 * version pushed 80 ms at one fixed PWM, which was enough to run a fader to its end.
 * Returns the signed change in counts (0 if nothing moved even at the top PWM).
 */
static int16_t probe(uint8_t m, uint8_t dir)
{
    int16_t p0 = (int16_t)pos_read(m);
    int16_t d;
    uint16_t duty;
    uint8_t i;

    for (duty = PROBE_START_PWM; duty <= PROBE_MAX_PWM; duty += PROBE_STEP_PWM) {
        motor_drive(m, dir, (uint8_t)duty);
        for (i = 0U; i < PROBE_POLLS; i++) {
            delay_ms(PROBE_POLL_MS);
            d = (int16_t)pos_read(m) - p0;
            if ((d >= (int16_t)PROBE_MIN_MOVE) || (d <= -(int16_t)PROBE_MIN_MOVE)) {
                motor_drive(m, MOTOR_BRAKE, 0U);
                delay_ms(40U);                  /* let it stop, then take the final reading */
                motor_drive(m, MOTOR_COAST, 0U);
                return (int16_t)((int16_t)pos_read(m) - p0);
            }
        }
        motor_drive(m, MOTOR_BRAKE, 0U);
        delay_ms(10U);
    }
    motor_drive(m, MOTOR_COAST, 0U);
    return 0;
}

uint8_t motor_polarity(uint8_t m)
{
    int16_t d;

    if (m >= FADER_COUNT) {
        return POL_STUCK;
    }
    if (s_pol[m] != POL_UNKNOWN) {
        return s_pol[m];
    }
    d = probe(m, MOTOR_FWD);
    if (d >= (int16_t)PROBE_MIN_MOVE) {
        s_pol[m] = POL_FWD_RAISES;
    } else if (d <= -(int16_t)PROBE_MIN_MOVE) {
        s_pol[m] = POL_REV_RAISES;
    } else {
        /* no movement: the fader may be against that end stop; try the other way */
        d = probe(m, MOTOR_REV);
        if (d >= (int16_t)PROBE_MIN_MOVE) {
            s_pol[m] = POL_REV_RAISES;
        } else if (d <= -(int16_t)PROBE_MIN_MOVE) {
            s_pol[m] = POL_FWD_RAISES;
        } else {
            s_pol[m] = POL_STUCK;
        }
    }
    return s_pol[m];
}

uint8_t motor_polarity_known(uint8_t m)
{
    return (m < FADER_COUNT) ? s_pol[m] : POL_STUCK;
}

uint8_t motor_dir_for(uint8_t m, bool up)
{
    bool fwd_raises = (s_pol[m] != POL_REV_RAISES);     /* unknown: assume FWD raises */

    return (up == fwd_raises) ? MOTOR_FWD : MOTOR_REV;
}
