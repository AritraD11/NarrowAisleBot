/*
 * ====================================================================
 *  NAB - ENCODER HAND-TURN DIAGNOSTIC  (ESP32)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  WHY THIS EXISTS
 *    Bench calibration returned DEAD_NO_COUNTS on all four motors while
 *    the wheels spun. All supply voltages have since been verified good
 *    (buck 5V, VCCA 3.3V, VCCB 5V, OE 3.3V, common GND). The front-pair
 *    wiring diagram was checked pin-by-pin and is correct.
 *
 *    So the question is now narrow: is a signal actually ARRIVING at the
 *    ESP32 pins, and if it is, is PCNT counting it?
 *
 *  MOTORS ARE NEVER DRIVEN. PWM/DIR are explicitly forced LOW at boot so
 *  nothing moves. Turn the wheels BY HAND.
 *
 *  ----------------------------------------------------------------
 *  THE KEY TEST (Phase 1) - "is the level shifter driving the line?"
 *
 *    GPIO 32, 33, 25, 26 (the REAR pins) have internal pull-ups AND
 *    pull-downs. So we can interrogate them:
 *
 *      pull-up -> reads 1  AND  pull-down -> reads 0   => FLOATING
 *          Nothing is driving this pin. The level shifter output is
 *          dead, Hi-Z, or the wire is open. This is the smoking gun.
 *
 *      pull-up -> reads X  AND  pull-down -> reads X   => DRIVEN to X
 *          Something IS holding the line. The shifter is working on
 *          this channel; the problem is elsewhere.
 *
 *    GPIO 34, 35, 36, 39 (the FRONT pins) are input-only on the ESP32
 *    and have NO internal pull resistors, so this test cannot run on
 *    them. That is a silicon limitation, not a wiring fault. For those
 *    four we fall back on Phase 2/3 activity detection.
 *  ----------------------------------------------------------------
 *
 *  PHASES
 *    1  Float / drive test        (see above)
 *    2  Static level snapshot     - 2 s of sampling; stable or changing?
 *    3  LIVE hand-turn monitor    - runs forever. Turn each wheel and
 *                                   watch its row. Reports, per channel:
 *                                     A,B      live logic levels
 *                                     %hi      fraction of time HIGH
 *                                     edgeA/B  software-counted edges
 *                                     pos      software x4 quadrature
 *                                     inval    illegal state transitions
 *                                     pcnt     ESP32 PCNT hardware count
 *
 *  READING PHASE 3
 *    edgeA/edgeB climb + pos climbs + inval 0  -> channel fully healthy
 *    edgeA/edgeB climb + pcnt stays 0          -> signal present, PCNT
 *                                                 config/pin problem
 *    edgeA climbs, edgeB stuck at 0            -> one dead channel
 *                                                 (the RMCS failure mode)
 *    nothing moves at all                      -> no signal reaching the
 *                                                 pin; see Phase 1
 *
 *  CONTROLS   R = re-run phases 1-2    Z = zero all counters
 *  BAUD 115200
 * ====================================================================
 */

#include "driver/pcnt.h"

// ====================================================================
// PIN MAP - identical to production firmware. Do not change.
// ====================================================================

#define NUM_MOTORS 4
const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};

const uint8_t ENC_A_PINS[NUM_MOTORS] = {36, 34, 32, 25};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {39, 35, 33, 26};

// Which encoder each motor carries (for the log header only).
const char* ENC_TYPE[NUM_MOTORS] = {"GTK08", "GTK08", "optical", "optical"};

// GPIO 34/35/36/39 are input-only: no internal pull-up or pull-down.
static inline bool hasInternalPull(uint8_t pin) {
    return !(pin == 34 || pin == 35 || pin == 36 || pin == 39);
}

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

// Motor driver pins - forced LOW so nothing can move.
const uint8_t PWM_PINS[NUM_MOTORS] = {4, 17, 19, 22};
const uint8_t DIR_PINS[NUM_MOTORS] = {16, 18, 21, 23};

// ====================================================================
// FAST PIN SAMPLING - direct register reads
// ====================================================================

static inline uint32_t rd0() { return REG_READ(GPIO_IN_REG);  }  // GPIO 0-31
static inline uint32_t rd1() { return REG_READ(GPIO_IN1_REG); }  // GPIO 32-39

static inline uint8_t lvl(uint8_t pin, uint32_t in0, uint32_t in1) {
    return (pin < 32) ? ((in0 >> pin) & 1u) : ((in1 >> (pin - 32)) & 1u);
}

// ====================================================================
// COUNTERS
// ====================================================================

// x4 quadrature decode table, indexed by (prevState << 2) | currState
// where state = (A << 1) | B.  0 = no change, +/-1 = valid step.
const int8_t QDEC[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0
};

struct ChanStat {
    uint8_t  prevState;
    uint32_t edgeA, edgeB;
    int32_t  pos;
    uint32_t invalid;
    uint32_t hiA, hiB;      // samples where A / B were HIGH
    int64_t  pcntAccum;
};
ChanStat ch[NUM_MOTORS];

uint32_t sampleCount = 0;

void zeroCounters() {
    uint32_t in0 = rd0(), in1 = rd1();
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        ch[i].prevState = (a << 1) | b;
        ch[i].edgeA = ch[i].edgeB = 0;
        ch[i].pos = 0;
        ch[i].invalid = 0;
        ch[i].hiA = ch[i].hiB = 0;
        ch[i].pcntAccum = 0;
        pcnt_counter_clear(PCNT_UNITS[i]);
    }
    sampleCount = 0;
}

// ====================================================================
// SETUP HELPERS
// ====================================================================

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

    // 1.25 us glitch filter (100 APB cycles @ 80 MHz). Hand-turning is
    // far slower than this, so nothing real gets filtered out.
    pcnt_set_filter_value(unit, 100);
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

void motorsHardOff() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(PWM_PINS[i], OUTPUT); digitalWrite(PWM_PINS[i], LOW);
        pinMode(DIR_PINS[i], OUTPUT); digitalWrite(DIR_PINS[i], LOW);
    }
}

// ====================================================================
// PHASE 1 - FLOAT / DRIVE TEST
// ====================================================================

void phase1_floatTest() {
    Serial.println();
    Serial.println("=== PHASE 1: FLOAT / DRIVE TEST ===");
    Serial.println("# Is anything actually driving each ESP32 pin?");
    Serial.println("# fmt: 1,motor,chan,gpio,pullup_reads,pulldown_reads,VERDICT");

    for (int i = 0; i < NUM_MOTORS; i++) {
        for (int c = 0; c < 2; c++) {
            uint8_t pin = c ? ENC_B_PINS[i] : ENC_A_PINS[i];
            const char* cn = c ? "B" : "A";

            if (!hasInternalPull(pin)) {
                Serial.printf("1,%s,%s,%d,-,-,INPUT_ONLY_NO_PULL(cannot test)\n",
                              MOTOR_NAMES[i], cn, pin);
                continue;
            }

            pinMode(pin, INPUT_PULLUP);
            delay(6);
            int up = digitalRead(pin);

            pinMode(pin, INPUT_PULLDOWN);
            delay(6);
            int dn = digitalRead(pin);

            pinMode(pin, INPUT);   // restore

            const char* verdict;
            if (up == 1 && dn == 0)      verdict = "FLOATING <<< nothing driving it";
            else if (up == 1 && dn == 1) verdict = "DRIVEN_HIGH (ok, line is held)";
            else if (up == 0 && dn == 0) verdict = "DRIVEN_LOW (ok, line is held)";
            else                         verdict = "INCONSISTENT(noisy?)";

            Serial.printf("1,%s,%s,%d,%d,%d,%s\n",
                          MOTOR_NAMES[i], cn, pin, up, dn, verdict);
        }
    }
    Serial.println("# FLOATING on a rear pin => level shifter is not driving that");
    Serial.println("#   channel. Check the shifter itself, its OE, and the B-side wire.");
    Serial.println("# Front pins (34/35/36/39) are input-only, so they cannot be");
    Serial.println("#   probed this way - judge those from Phase 3 activity.");
}

// ====================================================================
// PHASE 2 - STATIC SNAPSHOT
// ====================================================================

void phase2_snapshot() {
    Serial.println();
    Serial.println("=== PHASE 2: STATIC SNAPSHOT (2 s, do not touch wheels) ===");
    Serial.println("# fmt: 2,motor,A_pct_high,B_pct_high,A_transitions,B_transitions,VERDICT");

    uint32_t hiA[NUM_MOTORS] = {0}, hiB[NUM_MOTORS] = {0};
    uint32_t trA[NUM_MOTORS] = {0}, trB[NUM_MOTORS] = {0};
    uint8_t  pA[NUM_MOTORS], pB[NUM_MOTORS];
    uint32_t n = 0;

    uint32_t in0 = rd0(), in1 = rd1();
    for (int i = 0; i < NUM_MOTORS; i++) {
        pA[i] = lvl(ENC_A_PINS[i], in0, in1);
        pB[i] = lvl(ENC_B_PINS[i], in0, in1);
    }

    unsigned long t0 = millis();
    while (millis() - t0 < 2000) {
        in0 = rd0(); in1 = rd1();
        for (int i = 0; i < NUM_MOTORS; i++) {
            uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
            uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
            if (a) hiA[i]++;
            if (b) hiB[i]++;
            if (a != pA[i]) { trA[i]++; pA[i] = a; }
            if (b != pB[i]) { trB[i]++; pB[i] = b; }
        }
        n++;
    }

    for (int i = 0; i < NUM_MOTORS; i++) {
        float pctA = n ? (100.0f * hiA[i] / n) : 0;
        float pctB = n ? (100.0f * hiB[i] / n) : 0;
        const char* verdict;
        if (trA[i] > 50 || trB[i] > 50)      verdict = "NOISY (transitions with wheels still)";
        else if (trA[i] == 0 && trB[i] == 0) verdict = "STABLE (expected at rest)";
        else                                 verdict = "SLIGHT_ACTIVITY";
        Serial.printf("2,%s,%.1f,%.1f,%lu,%lu,%s\n",
                      MOTOR_NAMES[i], pctA, pctB,
                      (unsigned long)trA[i], (unsigned long)trB[i], verdict);
    }
    Serial.printf("# %lu samples in 2000 ms (%.0f kHz sampling)\n",
                  (unsigned long)n, n / 2000.0f);
}

// ====================================================================
// PHASE 3 - LIVE HAND-TURN MONITOR
// ====================================================================

void printLiveHeader() {
    Serial.println();
    Serial.println("=== PHASE 3: LIVE HAND-TURN MONITOR ===");
    Serial.println("# Turn ONE wheel at a time, by hand, slowly, a few full turns.");
    Serial.println("# Watch that motor's row. Then move to the next wheel.");
    Serial.println("# Note: encoders sit on the motor shaft BEFORE the 47:1 gearbox,");
    Serial.println("#       so one wheel turn = ~47 encoder revolutions = a LOT of counts.");
    Serial.println("# Controls: R = re-run phases 1-2   Z = zero counters");
    Serial.println("# fmt: 3,t_ms,motor,A,B,A%hi,B%hi,edgeA,edgeB,pos,inval,pcnt");
}

void samplePins() {
    uint32_t in0 = rd0(), in1 = rd1();
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        if (a) ch[i].hiA++;
        if (b) ch[i].hiB++;

        uint8_t s  = (a << 1) | b;
        uint8_t ps = ch[i].prevState;
        if (s != ps) {
            if (((s >> 1) & 1) != ((ps >> 1) & 1)) ch[i].edgeA++;
            if ((s & 1)        != (ps & 1))        ch[i].edgeB++;
            int8_t d = QDEC[(ps << 2) | s];
            if (d != 0) ch[i].pos += d;
            else        ch[i].invalid++;   // both channels changed at once
            ch[i].prevState = s;
        }
    }
    sampleCount++;
}

void drainPCNT() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        int16_t c = 0;
        pcnt_get_counter_value(PCNT_UNITS[i], &c);
        if (c > 16000 || c < -16000) {      // drain before 16-bit wrap
            ch[i].pcntAccum += c;
            pcnt_counter_clear(PCNT_UNITS[i]);
        }
    }
}

int64_t pcntTotal(int i) {
    int16_t c = 0;
    pcnt_get_counter_value(PCNT_UNITS[i], &c);
    return ch[i].pcntAccum + c;
}

void printLiveRow() {
    unsigned long t = millis();
    uint32_t n = sampleCount ? sampleCount : 1;
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint32_t in0 = rd0(), in1 = rd1();
        Serial.printf("3,%lu,%s,%d,%d,%.0f,%.0f,%lu,%lu,%ld,%lu,%lld\n",
            t, MOTOR_NAMES[i],
            lvl(ENC_A_PINS[i], in0, in1),
            lvl(ENC_B_PINS[i], in0, in1),
            100.0f * ch[i].hiA / n,
            100.0f * ch[i].hiB / n,
            (unsigned long)ch[i].edgeA,
            (unsigned long)ch[i].edgeB,
            (long)ch[i].pos,
            (unsigned long)ch[i].invalid,
            (long long)pcntTotal(i));
    }
}

// ====================================================================
// SETUP / LOOP
// ====================================================================

void runPhases12() {
    phase1_floatTest();
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);   // restore after pull test
    phase2_snapshot();
    zeroCounters();
    printLiveHeader();
}

void setup() {
    Serial.begin(115200);
    delay(400);

    motorsHardOff();

    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(ENC_A_PINS[i], INPUT);
        pinMode(ENC_B_PINS[i], INPUT);
    }
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);

    Serial.println();
    Serial.println("========================================================");
    Serial.println("  NAB ENCODER HAND-TURN DIAGNOSTIC");
    Serial.println("  MOTORS ARE FORCED OFF - turn the wheels by hand.");
    Serial.println("========================================================");
    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.printf("#  %s (%-7s)  A=GPIO%-2d  B=GPIO%-2d  %s\n",
            MOTOR_NAMES[i], ENC_TYPE[i], ENC_A_PINS[i], ENC_B_PINS[i],
            hasInternalPull(ENC_A_PINS[i]) ? "(pull test available)"
                                           : "(input-only, no pull test)");
    }

    runPhases12();
}

void loop() {
    static unsigned long lastPrint = 0;
    static unsigned long lastDrain = 0;

    samplePins();

    if (millis() - lastDrain >= 20) { lastDrain = millis(); drainPCNT(); }

    if (millis() - lastPrint >= 500) {
        lastPrint = millis();
        printLiveRow();
    }

    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'R' || c == 'r') { runPhases12(); lastPrint = millis(); }
        else if (c == 'Z' || c == 'z') { zeroCounters(); Serial.println("# counters zeroed"); }
    }
}
