/*
 * ====================================================================
 *  NAB - ENCODER ISOLATION TEST (ESP32, no motor drive)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  PURPOSE
 *    The bench calibration harness showed 0 raw counts on every motor,
 *    including the two encoders you actually wired (1 front GTK08,
 *    1 rear optical) - even though the wheels were physically spinning
 *    under PID/PWM. That rules out a code/decode problem (same PCNT
 *    logic ran the real robot for months) and points at the physical
 *    chain: encoder -> level shifter -> ESP32 pin.
 *
 *    This sketch NEVER touches the motor driver pins - PWM/DIR are left
 *    alone, so the motors stay off. Spin each wheel BY HAND and watch
 *    the numbers. This isolates the encoder+level-shifter+wiring chain
 *    from any PWM switching noise or PID interaction.
 *
 *  WHAT IT PRINTS  (every 250 ms)
 *    For each of the 4 encoder channels: the live raw digital level of
 *    A and B (so you can see the signal is reaching the pin at all,
 *    independent of PCNT), plus the PCNT hardware count (does not
 *    reset between prints, so you can watch it climb as you turn).
 *
 *  HOW TO USE
 *    1. Flash this. Motors will NOT move - that's correct.
 *    2. Open Serial Monitor at 115200.
 *    3. By hand, slowly rotate ONLY the wheel with the front (GTK08)
 *       encoder a few turns. Watch the FR (or wherever you wired it)
 *       row: A/B should visibly toggle 0/1, and cnt should change.
 *    4. Repeat for the rear (optical) encoder's wheel.
 *    5. Copy the whole log back.
 *
 *  READING THE RESULT
 *    - A and B never toggle (stuck at one level, e.g. always 1 or
 *      always 0) while you are physically turning that wheel:
 *      signal isn't reaching the ESP32 pin at all. Check level-shifter
 *      power (3.3V + 5V + common GND) and its OE pin (must be pulled
 *      HIGH on most TXS0108E breakouts, or outputs stay Hi-Z).
 *    - A/B toggle cleanly but cnt never changes: PCNT config problem
 *      or A/B wires swapped/crossed between channels - unlikely since
 *      this is the same decode as the working production robot, but
 *      possible if wiring landed on a different motor's pin pair.
 *    - A/B toggle AND cnt changes: that channel's hardware path is
 *      good. If Phase A of the bench harness still showed 0 for this
 *      motor, the fault is PWM-noise-related, not wiring/power.
 * ====================================================================
 */

#include "driver/pcnt.h"

#define FR 0
#define FL 1
#define RR 2
#define RL 3
#define NUM_MOTORS 4

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};

// Same pin map as production / the bench calibration harness.
const uint8_t ENC_A_PINS[NUM_MOTORS] = {36, 34, 32, 25};  // FR,FL,RR,RL - A
const uint8_t ENC_B_PINS[NUM_MOTORS] = {39, 35, 33, 26};  // FR,FL,RR,RL - B

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

void setupPCNT(int idx) {
    pcnt_unit_t unit = PCNT_UNITS[idx];
    uint8_t pinA = ENC_A_PINS[idx];
    uint8_t pinB = ENC_B_PINS[idx];

    pcnt_config_t c0 = {};
    c0.pulse_gpio_num = pinA; c0.ctrl_gpio_num = pinB;
    c0.channel = PCNT_CHANNEL_0; c0.unit = unit;
    c0.pos_mode = PCNT_COUNT_INC; c0.neg_mode = PCNT_COUNT_DEC;
    c0.lctrl_mode = PCNT_MODE_REVERSE; c0.hctrl_mode = PCNT_MODE_KEEP;
    c0.counter_h_lim = 32767; c0.counter_l_lim = -32768;
    pcnt_unit_config(&c0);

    pcnt_config_t c1 = {};
    c1.pulse_gpio_num = pinB; c1.ctrl_gpio_num = pinA;
    c1.channel = PCNT_CHANNEL_1; c1.unit = unit;
    c1.pos_mode = PCNT_COUNT_DEC; c1.neg_mode = PCNT_COUNT_INC;
    c1.lctrl_mode = PCNT_MODE_REVERSE; c1.hctrl_mode = PCNT_MODE_KEEP;
    c1.counter_h_lim = 32767; c1.counter_l_lim = -32768;
    pcnt_unit_config(&c1);

    pcnt_set_filter_value(unit, 100);
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);

    // Also readable as a plain GPIO input, independent of the PCNT
    // peripheral, so we can see the raw logic level even if PCNT
    // itself were misconfigured.
    pinMode(pinA, INPUT);
    pinMode(pinB, INPUT);
}

void setup() {
    Serial.begin(115200);
    delay(300);

    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);

    Serial.println();
    Serial.println("====================================================");
    Serial.println("  NAB ENCODER ISOLATION TEST - motors NOT driven");
    Serial.println("  Turn each wheel BY HAND and watch its row change.");
    Serial.println("====================================================");
    Serial.println("# Pin map:");
    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.printf("#   %s  A=GPIO%d  B=GPIO%d\n",
                      MOTOR_NAMES[i], ENC_A_PINS[i], ENC_B_PINS[i]);
    }
    Serial.println("# fmt: t_ms,FR_A,FR_B,FR_cnt,FL_A,FL_B,FL_cnt,RR_A,RR_B,RR_cnt,RL_A,RL_B,RL_cnt");
}

void loop() {
    static unsigned long last = 0;
    if (millis() - last < 250) return;
    last = millis();

    Serial.printf("%lu", millis());
    for (int i = 0; i < NUM_MOTORS; i++) {
        int a = digitalRead(ENC_A_PINS[i]);
        int b = digitalRead(ENC_B_PINS[i]);
        int16_t cnt = 0;
        pcnt_get_counter_value(PCNT_UNITS[i], &cnt);   // not cleared - watch it climb
        Serial.printf(",%d,%d,%d", a, b, cnt);
    }
    Serial.println();
}
