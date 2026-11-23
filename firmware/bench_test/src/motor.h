/* ---------------------------------------------------------------------------------
 * File        : motor.h
 * Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
 * Revision    : 1, 2026-11-22
 * Project     : ECEN 5613 final project, panel bench-test firmware
 * Description : Two TB6612 channels: direction latch U14 (0xF000), PWM from PCA
 *               modules 0 and 1 (P1.3 and P1.4) through U9. Everything is off
 *               after motor_init().
 * Status      : DRAFTED, not yet run on hardware
 * Leveraged   : none
   ---------------------------------------------------------------------------------*/
#ifndef MOTOR_H
#define MOTOR_H

#include <stdint.h>
#include <stdbool.h>

#define MOTOR_COAST     0U      /* IN1 = IN2 = 0: outputs off */
#define MOTOR_FWD       1U      /* IN1 = 1, IN2 = 0 */
#define MOTOR_REV       2U      /* IN1 = 0, IN2 = 1 */
#define MOTOR_BRAKE     3U      /* IN1 = IN2 = 1 */

#define POL_UNKNOWN     0U
#define POL_FWD_RAISES  1U      /* driving FWD makes the ADC reading go up */
#define POL_REV_RAISES  2U
#define POL_STUCK       3U      /* neither direction moved the pot */

/* Everything off: PWM low, latch 0 (STBY low). Call first thing in main(). */
void motor_init(void);

/* Set one motor: direction (MOTOR_*) and PWM duty 0-255. duty 0 = no PWM (pin low).
   STBY is raised while any motor is not COAST. */
void motor_drive(uint8_t m, uint8_t dir, uint8_t duty);

/* Coast both motors and drop STBY. */
void motor_all_off(void);

/* Which way the pot moves for FWD, found by a short probe (blocking, about 0.3 s).
   Returns POL_*. Remembered per motor, so the probe runs once. */
uint8_t motor_polarity(uint8_t m);
uint8_t motor_polarity_known(uint8_t m);

/* The MOTOR_* direction that raises (up = true) or lowers the ADC reading. */
uint8_t motor_dir_for(uint8_t m, bool up);

#endif /* MOTOR_H */
