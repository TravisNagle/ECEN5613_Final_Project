/* ---------------------------------------------------------------------------------
 * File        : bench.h
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : Constants for the bench test: memory-mapped addresses, button
 *               bits, motor-latch bits and the tuning numbers for the fader
 *               moves. Pins and addresses are from Hardware_Map Rev 13.8
 *               (sections 3.2, 3.3, 3.5, 3.7 and Appendix A.4/A.5).
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
   ---------------------------------------------------------------------------------*/
#ifndef BENCH_H
#define BENCH_H

#include <stdint.h>

/* ---- Memory-mapped I/O (final.pld) ----------------------------------------- */
#define ADDR_MOTOR_LATCH    0xF000U     /* U14 '273, write only */
#define ADDR_BUTTONS        0xF800U     /* U16 '244, read only */

/* U16 bits (read at 0xF800). Buttons read 0 when pressed; TOUCH1 reads 1 when touched. */
#define BTN_CENTER          0x01U
#define BTN_UP              0x02U
#define BTN_DOWN            0x04U
#define BTN_LEFT            0x08U
#define BTN_RIGHT           0x10U
#define BTN_F1              0x20U
#define BTN_F2              0x40U
#define BTN_MASK            0x7FU
#define TOUCH1_BIT          0x80U

/* U14 bits (write at 0xF000). Q4, Q5 and Q7 are not connected. */
#define LATCH_AIN1          0x01U
#define LATCH_AIN2          0x02U
#define LATCH_BIN1          0x04U
#define LATCH_BIN2          0x08U
#define LATCH_STBY          0x40U

/* ---- Faders ------------------------------------------------------------------ */
#define FADER_COUNT         2U
#define FADER_ADC_CH0       0U          /* MCP3008 CH0 = fader 1 wiper */
#define FADER_ADC_CH1       1U          /* MCP3008 CH1 = fader 2 wiper */

/* Pot end readings, measured on page 2 (CAL) on 2026-11-22. Page 2 re-measures them and
   uses the new values until the next reset. */
#define FADER1_ADC_LO_DEFAULT   31U     /* 0x01F */
#define FADER1_ADC_HI_DEFAULT   999U    /* 0x3E7 */
#define FADER2_ADC_LO_DEFAULT   29U     /* 0x01D */
#define FADER2_ADC_HI_DEFAULT   994U    /* 0x3E2 */

/* ---- Timing ------------------------------------------------------------------ */
/* The main loop runs delay_ms(LOOP_DELAY_MS) plus the work, so one "tick" is about
   12-14 ms. Everything below is counted in ticks. */
#define LOOP_DELAY_MS       10U
#define BTN_DEBOUNCE_TICKS  2U          /* about 25 ms */
#define TOUCH_DEBOUNCE_TICKS 3U         /* AT42QT1010 HeartBeat pulse: need 3 matching reads */
#define PAGE_HOLD_TICKS     75U         /* hold CENTER about 1 s to change page */
#define HEARTBEAT_TICKS     40U         /* status LED toggle, about 0.5 s */

/* ---- Fader move tuning (all PWM values are 0-255) ---------------------------- */
#define MOVE_MIN_PWM        70U         /* base drive; a boost is added while the fader is not moving */
#define MOVE_MAX_PWM        170U        /* about 67 % before any boost */
#define MOVE_RAMP_COUNTS    250U        /* error (ADC counts) at which the drive reaches MAX */
#define MOVE_LOOKAHEAD_TICKS 3U         /* brake if the speed would cross the target in this many ticks */
#define MOVE_STILL_COUNTS   2U          /* counts per tick or less = "not moving" */
#define MOVE_BOOST_STEP     6U          /* PWM added per tick while stuck still */
#define MOVE_BOOST_MAX      80U
#define MOVE_NEAR_COUNTS    100U        /* inside this (about 10 % of travel) it positions by nudges */
#define MOVE_NUDGE_REST_TICKS 3U        /* braked ticks after each short nudge */
#define MOVE_NUDGE_START    140U        /* first nudge PWM; it adapts from here */
#define MOVE_NUDGE_FLOOR    50U
#define MOVE_NUDGE_MS       4U          /* nudge push length in ms (blocking); shorter = smaller steps */
#define MOVE_NUDGE_STEP     10U
#define MOVE_NUDGE_MIN_MOVE 3U        /* counts moved by a nudge: less than this raises the PWM */
#define MOVE_NUDGE_MAX_MOVE 14U        /* more than this lowers it (about 1.4 % of travel) */
#define MOVE_DEADBAND       15U        /* counts; the slide noise can be 14 counts p-p */
#define MOVE_SETTLE_TICKS   3U          /* ticks inside the deadband, nearly still, before the move is done */
#define MOVE_TIMEOUT_TICKS  250U        /* give up after about 3 s */

#define PROBE_START_PWM     90U         /* polarity probe: first push */
#define PROBE_MAX_PWM       230U        /* ... escalating to this if the fader does not move */
#define PROBE_STEP_PWM      20U
#define PROBE_POLL_MS       3U          /* check the pot this often during a push */
#define PROBE_POLLS         6U          /* about 18 ms per push before the next, stronger one */
#define PROBE_MIN_MOVE      6U          /* counts the pot must change to count as movement */

#define CAL_PWM             140U        /* end-to-end run for calibration */
#define CAL_RUN_TICKS       100U        /* about 1.2 s each way */

/* 1 = a fader touched by hand cancels an automatic move. Default 0 because motor PWM
   may couple into the touch sensor; with 0 the touch indicator is a pure test. */
#define ABORT_ON_TOUCH      0

#endif /* BENCH_H */
