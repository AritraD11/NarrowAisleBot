/*
 * ====================================================================
 *  NAB - FRONT ENCODER SPEED + DIRECTION (hand-turn, event-gated)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  WHY THIS VERSION
 *    The previous diagnostic printed a row every 500 ms regardless of
 *    activity, which floods the monitor with zeros while the wheel is
 *    sitting still. This one prints NOTHING while idle. A row appears
 *    only when a channel's position actually changed since the last
 *    print - i.e. only when you are physically turning that wheel.
 *
 *  SCOPE
 *    Front motors only (FR, FL) - the GTK08 encoders. Same exact pins
 *    as production: FR A=36 B=39, FL A=34 B=35. Motors are forced off
 *    at boot (PWM/DIR held LOW on all four channels) so nothing can
 *    move on its own - turn the wheels BY HAND.
 *
 *  EACH PRINTED ROW SHOWS
 *    dir          FWD or REV - relative to the firmware's positive
 *                 convention (ENC_DIR_SIGN already applied), i.e. the
 *                 same sign a positive commanded velocity would produce
 *    rad_s        speed at the motor shaft, wheel-equivalent (counts
 *                 converted through the full 186,264 CPR - includes
 *                 the 47:1 gearbox multiplication already baked into
 *                 that CPR figure, since the encoder sits pre-gearbox)
 *    d_counts     raw encoder counts since the last printed row
 *    total_counts running absolute position (software quadrature decode,
 *                 independent of the PCNT hardware - this is a direct
 *                 GPIO-register decode, so it works even if PCNT itself
 *                 turns out to be misconfigured)
 *    pcnt         the ESP32 PCNT hardware count over the same window,
 *                 printed alongside for a direct cross-check: if
 *                 d_counts is nonzero but pcnt stays 0, the signal is
 *                 arriving fine and PCNT is the actual problem
 *
 *  CONTROLS   Z = zero all counters
 *  BAUD 115200
 * ====================================================================
 */

#include "driver/pcnt.h"

// ── Pins - identical to production, front pair only ──────────────────
const uint8_t FR_A = 36, FR_B = 39;   // FR: PCNT_UNIT_0
const uint8_t FL_A = 34, FL_B = 35;   // FL: PCNT_UNIT_1

const uint8_t ENC_A_PINS[2] = {FR_A, FL_A};
const uint8_t ENC_B_PINS[2] = {FR_B, FL_B};
const char*   MOTOR_NAMES[2] = {"FR", "FL"};
const int8_t  ENC_DIR_SIGN[2] = {-1, +1};   // must match production firmware
const pcnt_unit_t PCNT_UNITS[2] = {PCNT_UNIT_0, PCNT_UNIT_1};

const float ENCODER_CPR = 186264.0f;   // GTK08: 1000 PPR x4 x 46.566 gear

// Motor driver pins - forced LOW so nothing can move on its own.
const uint8_t PWM_PINS[4] = {4, 17, 19, 22};
const uint8_t DIR_PINS[4] = {16, 18, 21, 23};

// ── Fast direct GPIO read ─────────────────────────────────────────────
static inline uint32_t rd0() { return REG_READ(GPIO_IN_REG);  }  // GPIO 0-31
static inline uint32_t rd1() { return REG_READ(GPIO_IN1_REG); }  // GPIO 32-39
static inline uint8_t lvl(uint8_t pin, uint32_t in0, uint32_t in1) {
    return (pin < 32) ? ((in0 >> pin) & 1u) : ((in1 >> (pin - 32)) & 1u);
}

// x4 quadrature decode, indexed by (prevState<<2)|currState, state=(A<<1)|B
const int8_t QDEC[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0
};

struct Chan {
    uint8_t  prevState;
    int32_t  pos;             // software-decoded absolute position
    int32_t  lastPrintedPos;
    unsigned long lastPrintMs;
    int64_t  pcntAccum;
};
Chan ch[2];

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

    pcnt_set_filter_value(unit, 100);   // 1.25 us glitch filter
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

void motorsHardOff() {
    for (int i = 0; i < 4; i++) {
        pinMode(PWM_PINS[i], OUTPUT); digitalWrite(PWM_PINS[i], LOW);
        pinMode(DIR_PINS[i], OUTPUT); digitalWrite(DIR_PINS[i], LOW);
    }
}

void zeroCounters() {
    uint32_t in0 = rd0(), in1 = rd1();
    unsigned long now = millis();
    for (int i = 0; i < 2; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        ch[i].prevState = (a << 1) | b;
        ch[i].pos = 0;
        ch[i].lastPrintedPos = 0;
        ch[i].lastPrintMs = now;
        ch[i].pcntAccum = 0;
        pcnt_counter_clear(PCNT_UNITS[i]);
    }
}

int64_t pcntTotal(int i) {
    int16_t c = 0;
    pcnt_get_counter_value(PCNT_UNITS[i], &c);
    return ch[i].pcntAccum + c;
}

void drainPCNT() {
    for (int i = 0; i < 2; i++) {
        int16_t c = 0;
        pcnt_get_counter_value(PCNT_UNITS[i], &c);
        if (c > 16000 || c < -16000) {      // drain before 16-bit wrap
            ch[i].pcntAccum += c;
            pcnt_counter_clear(PCNT_UNITS[i]);
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(400);

    motorsHardOff();
    pinMode(FR_A, INPUT); pinMode(FR_B, INPUT);
    pinMode(FL_A, INPUT); pinMode(FL_B, INPUT);
    setupPCNT(0);
    setupPCNT(1);
    zeroCounters();

    Serial.println();
    Serial.println("========================================================");
    Serial.println("  NAB FRONT ENCODER SPEED/DIRECTION - hand-turn, front only");
    Serial.println("  Motors are forced OFF. Nothing prints until you turn a");
    Serial.println("  wheel by hand. Silence = idle, not a hang.");
    Serial.println("========================================================");
    Serial.printf("#  FR  A=GPIO%d  B=GPIO%d\n", FR_A, FR_B);
    Serial.printf("#  FL  A=GPIO%d  B=GPIO%d\n", FL_A, FL_B);
    Serial.println("#  Note: encoder is on the motor shaft BEFORE the 47:1");
    Serial.println("#  gearbox, so ~186,264 counts = one full WHEEL turn.");
    Serial.println("#  Controls: Z = zero counters");
    Serial.println("# fmt: t_ms,motor,dir,rad_s,d_counts,total_counts,pcnt");
}

void loop() {
    // Sample continuously, decode in software (works even if PCNT is broken).
    uint32_t in0 = rd0(), in1 = rd1();
    for (int i = 0; i < 2; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        uint8_t s = (a << 1) | b;
        if (s != ch[i].prevState) {
            int8_t d = QDEC[(ch[i].prevState << 2) | s];
            ch[i].pos += d;   // invalid (both-changed) transitions just don't move pos
            ch[i].prevState = s;
        }
    }

    drainPCNT();

    // Print only channels that actually moved since their last print.
    unsigned long now = millis();
    for (int i = 0; i < 2; i++) {
        int32_t delta = ch[i].pos - ch[i].lastPrintedPos;
        if (delta == 0) continue;                      // no activity - print nothing

        unsigned long dtMs = now - ch[i].lastPrintMs;
        if (dtMs < 30) continue;                        // small batching window

        int32_t corrected = delta * ENC_DIR_SIGN[i];    // matches firmware sign convention
        float dtSec = dtMs / 1000.0f;
        float rad_s = ((float)corrected / ENCODER_CPR) * (2.0f * PI) / dtSec;

        Serial.printf("%lu,%s,%s,%.3f,%ld,%ld,%lld\n",
            now, MOTOR_NAMES[i],
            (corrected >= 0) ? "FWD" : "REV",
            fabsf(rad_s),
            (long)delta,
            (long)ch[i].pos,
            (long long)pcntTotal(i));

        ch[i].lastPrintedPos = ch[i].pos;
        ch[i].lastPrintMs = now;
    }

    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'Z' || c == 'z') { zeroCounters(); Serial.println("# counters zeroed"); }
    }
}
