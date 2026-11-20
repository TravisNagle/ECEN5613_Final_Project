/*
 * File        : main.c
 * Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-02
 * Project     : ECEN 5613 final project, 8051 firmware (MVP)
 * Description : MVP: the 8051 controls Reaper over MIDI through the KB2040,
 *               in Mackie Control (MCU) mode.
 *                 - SW4 (class board, P3.2) alternates Play and Stop.
 *                 - Fader 1 (MCP3008 CH0) sets track 1's volume as MCU
 *                   fader 1 (pitch bend, channel 1), with a synthetic touch
 *                   note around each move.
 *                 - The status LED blinks at 1 Hz while the main loop runs.
 *                 - Both motor PWM pins are held low.
 *               Send-only: bytes from Reaper are read and dropped. Needs no
 *               SPLD: the UART and the MCP3008 are on port pins.
 *               Interrupts only count or move bytes; the work runs here.
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
 */
#include "board.h"
#include "tick.h"
#include "uart.h"
#include "midi.h"
#include "adc.h"

/* ---- Fader 1 (Hardware_Map 3.5) ------------------------------------------- */
#define FADER_STRIP         0       /* MCU strip 0 = track 1 of Reaper's current bank */
#define FADER_ADC_MIN       0       /* (MEASURE) reading with the knob at the bottom */
#define FADER_ADC_MAX       1023    /* (MEASURE) reading with the knob at the top */
#define FADER_INVERT        0       /* 1 if the top of the travel reads low */
#define FADER_DEADBAND      4       /* counts; the datasheet's slide noise is up to ~14 counts p-p */
#define FADER_PERIOD_MS     10      /* read and maybe send at 100 Hz */
#define FADER_SAMPLES       4       /* readings averaged per period */
#define TOUCH_RELEASE_MS    250     /* release the synthetic touch after this long without a move */

/* ---- SW4 and LED ------------------------------------------------------------ */
#define SW4_DEBOUNCE_MS     20
#define LED_HALF_PERIOD_MS  500

/* SW4 */
static uint8_t sw4_pressed;         /* debounced state, 1 = pressed */
static uint8_t sw4_count;           /* ms the raw level has disagreed with sw4_pressed */
static uint8_t sw4_note;            /* MCU note sent on the last press, released on let-go */
static uint8_t playing;             /* our guess at Reaper's transport state */

/* Fader */
static uint8_t fader_timer;
static uint16_t fader_sent = 0xFFFF;    /* last value sent; 0xFFFF forces a send at start-up */
static uint8_t touched;
static uint16_t touch_idle_ms;

static uint16_t led_timer;

unsigned char __sdcc_external_startup(void)
{
    AUXR = 0x0C;    /* XRS1:XRS0 = 11: 1 KB on-chip XRAM; EXTRAM = 0; AO = 0 keeps ALE on */
    return 0;       /* 0: let the C runtime initialise variables */
}

/* SW4 press alternates Play and Stop; the release sends the same note with velocity 0. */
static void sw4_task(void)
{
    uint8_t raw = SW4_N ? 0 : 1;

    if (raw == sw4_pressed) {
        sw4_count = 0;
        return;
    }
    if (++sw4_count < SW4_DEBOUNCE_MS) {
        return;
    }
    sw4_count = 0;
    sw4_pressed = raw;

    if (sw4_pressed) {
        playing = !playing;
        sw4_note = playing ? MCU_PLAY : MCU_STOP;
        midi_note_on(0, sw4_note, MCU_PRESS);
    } else {
        midi_note_on(0, sw4_note, MCU_RELEASE);
    }
}

/* Calibrated 10-bit reading -> 14-bit MCU fader value. */
static uint16_t fader_to_pitch_bend(uint16_t adc)
{
    return (uint16_t)(((uint32_t)(adc - FADER_ADC_MIN) * MIDI_PB_MAX)
                      / (FADER_ADC_MAX - FADER_ADC_MIN));
}

static void fader_task(void)
{
    uint16_t adc = 0;
    uint8_t i;
    uint8_t moved;

    for (i = 0; i < FADER_SAMPLES; i++) {
        adc += adc_read(ADC_CH_FADER1);
    }
    adc /= FADER_SAMPLES;
#if FADER_INVERT
    adc = 1023 - adc;
#endif
#if FADER_ADC_MIN > 0
    if (adc < FADER_ADC_MIN) {
        adc = FADER_ADC_MIN;
    }
#endif
#if FADER_ADC_MAX < 1023
    if (adc > FADER_ADC_MAX) {
        adc = FADER_ADC_MAX;
    }
#endif

    /* A move is a change of at least the deadband, or reaching an end the
       deadband would otherwise stop just short of. */
    moved = (adc >= fader_sent + FADER_DEADBAND)
         || (fader_sent >= adc + FADER_DEADBAND)
         || ((adc == FADER_ADC_MIN || adc == FADER_ADC_MAX) && adc != fader_sent);

    if (moved) {
        if (!touched) {
            /* Real MCU hardware sends touch before moving a fader. Until the
               AT42QT1010 output (0xF800 bit 7) is readable, fake it. */
            midi_note_on(0, MCU_FADER_TOUCH(FADER_STRIP), MCU_PRESS);
            touched = 1;
        }
        midi_pitch_bend(FADER_STRIP, fader_to_pitch_bend(adc));
        fader_sent = adc;
        touch_idle_ms = 0;
    } else if (touched) {
        touch_idle_ms += FADER_PERIOD_MS;
        if (touch_idle_ms >= TOUCH_RELEASE_MS) {
            midi_note_on(0, MCU_FADER_TOUCH(FADER_STRIP), MCU_RELEASE);
            touched = 0;
        }
    }
}

static void every_ms(void)
{
    sw4_task();

    if (++fader_timer >= FADER_PERIOD_MS) {
        fader_timer = 0;
        fader_task();
    }

    if (++led_timer >= LED_HALF_PERIOD_MS) {
        led_timer = 0;
        LED_N = !LED_N;
    }
}

void main(void)
{
    uint8_t ticks_done = 0;

    /* Motors stay off in the MVP. The port latches reset to 1, which would hold
       both TB6612 PWM inputs high; only the '273 (STBY = 0) would then keep the
       motors still, and its clock is undriven until U7 runs final.pld. PWM low
       means outputs off (IN = 00) or brake, never drive. */
    PWM0 = 0;
    PWM1 = 0;

    LED_N = 1;          /* off */
    SW4_N = 1;          /* input */
    adc_init();
    tick_init();
    uart_init();
    EA = 1;

    for (;;) {
        /* catch up one call per elapsed millisecond */
        while (ticks_done != tick_ms) {
            ticks_done++;
            every_ms();
        }

        /* Reaper's MCU feedback (fader positions, meters, LEDs) is dropped
           until the MIDI parser (M4) exists. */
        while (uart_getc() >= 0) {
        }
    }
}
