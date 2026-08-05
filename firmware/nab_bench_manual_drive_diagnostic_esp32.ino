/*
 * ====================================================================
 *  NAB - BENCH MANUAL DRIVE + FULL ENCODER DIAGNOSTIC  (ESP32)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  >>> WHEELS MUST BE IN THE AIR. THIS SKETCH DRIVES THE MOTORS. <<<
 *  >>> PRESS  x  OR  SPACE  AT ANY TIME FOR IMMEDIATE STOP.      <<<
 *
 *  WHAT THIS IS FOR
 *    All 4 encoders are now wired through the 8-channel BSS138 level
 *    shifter. This sketch lets you drive each wheel from the keyboard
 *    and reports, per channel, everything needed to decide whether the
 *    feedback path is healthy - and if not, exactly which part is bad.
 *
 *  QUIET BY DEFAULT
 *    Nothing prints unless something happens. Encoder rows appear only
 *    while counts are actually changing. Silence = idle, not a hang.
 *
 *  ----------------------------------------------------------------
 *  TWO COUNTERS RUN IN PARALLEL, ON PURPOSE
 *
 *    PCNT (hardware)  - the ESP32's pulse counter. Runs in silicon, so
 *                       it NEVER misses an edge no matter what the CPU
 *                       is doing. This is the AUTHORITATIVE count and
 *                       all positions / speeds / directions come from it.
 *
 *    Software decode  - a direct GPIO-register poll in the main loop.
 *                       It CAN miss edges while the CPU is busy sending
 *                       serial data, so it is NOT used for position.
 *                       Its job is per-channel health: it is the only
 *                       way to see A and B separately and catch a single
 *                       dead channel, which PCNT cannot show you.
 *
 *    So: trust PCNT for "how far / how fast / which way".
 *        Trust the software edge counts for "is each channel alive".
 *        A gap between them at speed is EXPECTED, not a fault.
 *
 *    Likewise "skip" counts (both channels appearing to change between
 *    two samples) are a sampling artifact at motor speed and only mean
 *    something during slow hand-turning.
 *  ----------------------------------------------------------------
 *
 *  KEYS
 *    1 2 3 4   select FR / FL / RR / RL          0   select ALL
 *    w         drive selected FORWARD            s   drive selected REVERSE
 *    x SPACE   STOP ALL (immediate)
 *    p         pulse selected FORWARD 1.5 s then auto-stop
 *    o         pulse selected REVERSE 1.5 s then auto-stop
 *    + -       PWM step up / down by 10
 *    [ ] \     PWM = 60 / 150 / 255
 *    t         AUTO TEST - pulses every motor both ways, full verdict table
 *    f         re-run the float / drive pin test
 *    z         zero all counters
 *    i         status         h or ?   help
 *
 *  BAUD 115200
 * ====================================================================
 */

#include "driver/pcnt.h"

// ====================================================================
// 1. PIN MAP  (identical to production aislebot_esp32.ino)
// ====================================================================

#define NUM_MOTORS 4
#define FR 0
#define FL 1
#define RR 2
#define RL 3

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};
const char* ENC_TYPE[NUM_MOTORS]    = {"GTK08", "GTK08", "optical", "optical"};

const uint8_t ENC_A_PINS[NUM_MOTORS] = {36, 34, 32, 25};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {39, 35, 33, 26};

const uint8_t PWM_PINS[NUM_MOTORS]   = {4, 17, 19, 22};
const uint8_t DIR_PINS[NUM_MOTORS]   = {16, 18, 21, 23};

// Driver sign and encoder sign MUST agree per motor, or the closed loop
// sees positive feedback and runs away. Verifying this is one of the
// main jobs of this sketch - see the cmd/enc direction match column.
const int8_t MOTOR_DIR_SIGN[NUM_MOTORS] = {-1, +1, -1, +1};
const int8_t ENC_DIR_SIGN[NUM_MOTORS]   = {-1, +1, -1, +1};

// Per-motor CPR: fronts carry GTK08 (1000 PPR x4 x46.566), rears keep
// the RMCS-2086 optical (500 lines x4 x46.566) - exactly 2x apart.
const float ENCODER_CPR[NUM_MOTORS] = {186264.0f, 186264.0f, 93132.0f, 93132.0f};

// GPIO 34/35/36/39 are input-only: no internal pull-up or pull-down.
static inline bool hasInternalPull(uint8_t pin) {
    return !(pin == 34 || pin == 35 || pin == 36 || pin == 39);
}

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

// ====================================================================
// 2. TUNABLES
// ====================================================================

const unsigned long SERIAL_BAUD = 115200;

const int PWM_MAX        = 255;
const int PWM_FREQUENCY  = 5000;
const int PWM_RESOLUTION = 8;

int  drivePWM = 80;            // current manual PWM magnitude

const unsigned long REPORT_INTERVAL_MS = 120;   // min gap between rows per motor
const unsigned long MAX_RUN_MS         = 8000;  // safety auto-stop
const unsigned long PULSE_MS           = 1500;  // p / o pulse length
const int           AUTO_TEST_PWM      = 110;
const unsigned long AUTO_TEST_RUN_MS   = 1500;
const unsigned long AUTO_TEST_SETTLE_MS= 600;

// ====================================================================
// 3. FAST GPIO SAMPLING
// ====================================================================

static inline uint32_t rd0() { return REG_READ(GPIO_IN_REG);  }  // GPIO 0-31
static inline uint32_t rd1() { return REG_READ(GPIO_IN1_REG); }  // GPIO 32-39

static inline uint8_t lvl(uint8_t pin, uint32_t in0, uint32_t in1) {
    return (pin < 32) ? ((in0 >> pin) & 1u) : ((in1 >> (pin - 32)) & 1u);
}

// x4 quadrature table, indexed by (prevState<<2)|currState, state=(A<<1)|B
const int8_t QDEC[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0
};

// ====================================================================
// 4. PER-MOTOR STATE
// ====================================================================

struct Chan {
    // --- software decode (health only, may undercount at speed) ---
    uint8_t  prevState;
    int32_t  swPos;
    uint32_t edgeA, edgeB;
    uint32_t skips;            // both channels changed between samples

    // --- PCNT hardware (authoritative) ---
    int32_t  pcntAccum;
    int32_t  lastReportedPcnt;

    // --- drive state ---
    int      pwm;              // signed commanded PWM, 0 = stopped
    unsigned long driveStartMs;
    unsigned long pulseEndMs;  // 0 = not a pulse

    // --- burst accounting ---
    bool     inBurst;
    int32_t  burstStartPcnt;
    uint32_t burstStartEdgeA, burstStartEdgeB, burstStartSkips;
    unsigned long burstStartMs;
    int      burstPWM;

    unsigned long lastReportMs;
};
Chan ch[NUM_MOTORS];

int  selected     = -1;        // -1 = ALL
bool anyDriving   = false;

// Auto-test results
struct TestResult {
    int32_t fwdCounts, revCounts;
    uint32_t eA, eB;
    bool ran;
};
TestResult tr[NUM_MOTORS];

// ====================================================================
// 5. PCNT
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

    pcnt_set_filter_value(unit, 100);   // 1.25 us glitch filter
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

// PCNT is 16-bit. At full speed it would wrap in well under a second,
// so drain it into a wide accumulator constantly.
void drainPCNT() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        int16_t c = 0;
        pcnt_get_counter_value(PCNT_UNITS[i], &c);
        if (c > 8000 || c < -8000) {
            ch[i].pcntAccum += (int32_t)c;
            pcnt_counter_clear(PCNT_UNITS[i]);
        }
    }
}

int32_t pcntTotal(int i) {
    int16_t c = 0;
    pcnt_get_counter_value(PCNT_UNITS[i], &c);
    return (ch[i].pcntAccum + (int32_t)c) * ENC_DIR_SIGN[i];
}

// ====================================================================
// 6. SAMPLING
// ====================================================================

void samplePins() {
    uint32_t in0 = rd0(), in1 = rd1();
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        uint8_t s  = (a << 1) | b;
        uint8_t ps = ch[i].prevState;
        if (s != ps) {
            if (((s >> 1) & 1) != ((ps >> 1) & 1)) ch[i].edgeA++;
            if ((s & 1)        != (ps & 1))        ch[i].edgeB++;
            int8_t d = QDEC[(ps << 2) | s];
            if (d != 0) ch[i].swPos += d;
            else        ch[i].skips++;
            ch[i].prevState = s;
        }
    }
}

void zeroCounters() {
    uint32_t in0 = rd0(), in1 = rd1();
    unsigned long now = millis();
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint8_t a = lvl(ENC_A_PINS[i], in0, in1);
        uint8_t b = lvl(ENC_B_PINS[i], in0, in1);
        ch[i].prevState = (a << 1) | b;
        ch[i].swPos = 0;
        ch[i].edgeA = ch[i].edgeB = ch[i].skips = 0;
        ch[i].pcntAccum = 0;
        ch[i].lastReportedPcnt = 0;
        ch[i].lastReportMs = now;
        pcnt_counter_clear(PCNT_UNITS[i]);
    }
}

// ====================================================================
// 7. MOTOR OUTPUT
// ====================================================================

void setupMotorPins() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(DIR_PINS[i], OUTPUT);
        digitalWrite(DIR_PINS[i], LOW);
        ledcAttach(PWM_PINS[i], PWM_FREQUENCY, PWM_RESOLUTION);
        ledcWrite(PWM_PINS[i], 0);
    }
}

void applyMotor(int idx, int pwm_value) {
    int  adjusted = pwm_value * MOTOR_DIR_SIGN[idx];
    bool reverse  = (adjusted < 0);
    int  a        = adjusted < 0 ? -adjusted : adjusted;
    if (a > PWM_MAX) a = PWM_MAX;
    digitalWrite(DIR_PINS[idx], reverse ? HIGH : LOW);
    ledcWrite(PWM_PINS[idx], a);
}

void beginBurst(int i, int pwm) {
    ch[i].inBurst         = true;
    ch[i].burstStartPcnt  = pcntTotal(i);
    ch[i].burstStartEdgeA = ch[i].edgeA;
    ch[i].burstStartEdgeB = ch[i].edgeB;
    ch[i].burstStartSkips = ch[i].skips;
    ch[i].burstStartMs    = millis();
    ch[i].burstPWM        = pwm;
}

void reportBurst(int i);   // fwd decl

void driveMotor(int i, int pwm, unsigned long pulseMs) {
    // If the command changes mid-burst (e.g. 'w' then 's' without stopping),
    // close the old burst first so its summary reflects what was actually
    // commanded for that stretch, not the newest value.
    if (ch[i].inBurst && pwm != ch[i].burstPWM) {
        reportBurst(i);
        ch[i].inBurst = false;
    }
    if (pwm != 0 && !ch[i].inBurst) beginBurst(i, pwm);
    ch[i].pwm          = pwm;
    ch[i].driveStartMs = millis();
    ch[i].pulseEndMs   = pulseMs ? millis() + pulseMs : 0;
    applyMotor(i, pwm);
    anyDriving = true;
}

void stopMotor(int i, bool summarize) {
    bool was = (ch[i].pwm != 0);
    ch[i].pwm        = 0;
    ch[i].pulseEndMs = 0;
    applyMotor(i, 0);
    if (was && summarize && ch[i].inBurst) reportBurst(i);
    ch[i].inBurst = false;
}

void stopAll(bool summarize) {
    for (int i = 0; i < NUM_MOTORS; i++) stopMotor(i, summarize);
    anyDriving = false;
}

// ====================================================================
// 8. HEALTH ANALYSIS
// ====================================================================

// Classify a burst. Returns a short verdict string.
const char* verdictFor(int32_t counts, uint32_t eA, uint32_t eB,
                       int pwm, bool* dirOK) {
    *dirOK = true;

    if (eA == 0 && eB == 0 && counts == 0) return "NO_SIGNAL";
    if (eA == 0)                            return "CH_A_DEAD";
    if (eB == 0)                            return "CH_B_DEAD";

    // Channel balance - healthy quadrature has ~equal edges on A and B.
    float ratio = (float)eA / (float)(eB ? eB : 1);
    if (ratio < 0.5f || ratio > 2.0f)       return "CH_IMBALANCE";

    if (counts == 0)                        return "EDGES_BUT_NO_NET";

    // Direction: a positive commanded PWM should give positive counts
    // once ENC_DIR_SIGN is applied. If not, the driver sign and encoder
    // sign disagree -> the PID loop would run away.
    bool expectFwd = (pwm > 0);
    bool gotFwd    = (counts > 0);
    if (expectFwd != gotFwd) { *dirOK = false; return "DIR_MISMATCH"; }

    return "HEALTHY";
}

void reportBurst(int i) {
    unsigned long dur = millis() - ch[i].burstStartMs;
    if (dur == 0) dur = 1;
    int32_t  counts = pcntTotal(i) - ch[i].burstStartPcnt;
    uint32_t eA     = ch[i].edgeA - ch[i].burstStartEdgeA;
    uint32_t eB     = ch[i].edgeB - ch[i].burstStartEdgeB;
    uint32_t sk     = ch[i].skips - ch[i].burstStartSkips;

    float secs  = dur / 1000.0f;
    float rads  = ((float)counts / ENCODER_CPR[i]) * 2.0f * PI / secs;
    float rpm   = rads * 9.5493f;
    float ratio = eB ? ((float)eA / (float)eB) : 0.0f;

    bool dirOK;
    const char* v = verdictFor(counts, eA, eB, ch[i].burstPWM, &dirOK);

    Serial.println();
    Serial.printf("--- BURST %s (%s) ---\n", MOTOR_NAMES[i], ENC_TYPE[i]);
    Serial.printf("  pwm cmd     : %+d   (%s)\n", ch[i].burstPWM,
                  ch[i].burstPWM > 0 ? "FORWARD" : "REVERSE");
    Serial.printf("  duration    : %.2f s\n", secs);
    Serial.printf("  counts      : %+ld  (PCNT, authoritative)\n", (long)counts);
    Serial.printf("  speed       : %.2f rad/s   %.1f RPM\n", rads, rpm);
    Serial.printf("  edges A / B : %lu / %lu   ratio %.2f\n",
                  (unsigned long)eA, (unsigned long)eB, ratio);
    Serial.printf("  skips       : %lu  %s\n", (unsigned long)sk,
                  ch[i].burstPWM ? "(expected at motor speed - sampling limit)"
                                 : "(meaningful only at hand-turn speed)");
    Serial.printf("  direction   : cmd %s / enc %s  -> %s\n",
                  ch[i].burstPWM > 0 ? "FWD" : "REV",
                  counts > 0 ? "FWD" : (counts < 0 ? "REV" : "--"),
                  dirOK ? "MATCH" : "*** MISMATCH ***");
    Serial.printf("  VERDICT     : %s\n", v);
    if (!dirOK) {
        Serial.printf("  >>> MOTOR_DIR_SIGN[%s] and ENC_DIR_SIGN[%s] disagree.\n",
                      MOTOR_NAMES[i], MOTOR_NAMES[i]);
        Serial.println("  >>> Closed loop would RUN AWAY. Flip one sign in firmware.");
    }
}

// ====================================================================
// 9. EVENT-GATED LIVE REPORTING
// ====================================================================

void maybeReport(int i) {
    unsigned long now = millis();
    int32_t p  = pcntTotal(i);
    int32_t dp = p - ch[i].lastReportedPcnt;
    if (dp == 0) return;                                  // nothing happened
    if (now - ch[i].lastReportMs < REPORT_INTERVAL_MS) return;

    float secs = (now - ch[i].lastReportMs) / 1000.0f;
    if (secs <= 0) secs = 0.001f;
    float rads = ((float)dp / ENCODER_CPR[i]) * 2.0f * PI / secs;

    uint32_t in0 = rd0(), in1 = rd1();
    Serial.printf("%lu %s pwm%+d d%+ld tot%+ld %.2frad/s A%d B%d eA%lu eB%lu sk%lu sw%+ld\n",
        now, MOTOR_NAMES[i], ch[i].pwm,
        (long)dp, (long)p, rads,
        lvl(ENC_A_PINS[i], in0, in1),
        lvl(ENC_B_PINS[i], in0, in1),
        (unsigned long)ch[i].edgeA, (unsigned long)ch[i].edgeB,
        (unsigned long)ch[i].skips, (long)ch[i].swPos);

    ch[i].lastReportedPcnt = p;
    ch[i].lastReportMs     = now;
}

// ====================================================================
// 10. FLOAT / DRIVE PIN TEST
// ====================================================================

void floatTest() {
    Serial.println();
    Serial.println("=== FLOAT / DRIVE PIN TEST ===");
    Serial.println("# With the BSS138 shifter connected every channel has a built-in");
    Serial.println("# pull-up, so a healthy idle line reads DRIVEN_HIGH. A FLOATING");
    Serial.println("# result means the shifter is not connected to that pin at all.");
    Serial.println("# fmt: motor,chan,gpio,pullup,pulldown,VERDICT");

    for (int i = 0; i < NUM_MOTORS; i++) {
        for (int c = 0; c < 2; c++) {
            uint8_t pin = c ? ENC_B_PINS[i] : ENC_A_PINS[i];
            const char* cn = c ? "B" : "A";
            if (!hasInternalPull(pin)) {
                Serial.printf("  %s,%s,%d,-,-,INPUT_ONLY (no internal pull - cannot test)\n",
                              MOTOR_NAMES[i], cn, pin);
                continue;
            }
            pinMode(pin, INPUT_PULLUP);   delay(6); int up = digitalRead(pin);
            pinMode(pin, INPUT_PULLDOWN); delay(6); int dn = digitalRead(pin);
            pinMode(pin, INPUT);

            const char* v;
            if      (up == 1 && dn == 0) v = "FLOATING  <<< shifter not reaching this pin";
            else if (up == 1 && dn == 1) v = "DRIVEN_HIGH (normal idle)";
            else if (up == 0 && dn == 0) v = "DRIVEN_LOW";
            else                         v = "INCONSISTENT (noisy)";
            Serial.printf("  %s,%s,%d,%d,%d,%s\n", MOTOR_NAMES[i], cn, pin, up, dn, v);
        }
    }
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);   // restore after pin mode changes
    zeroCounters();
}

// ====================================================================
// 11. AUTO TEST - one key, tests everything, prints a verdict table
// ====================================================================

// Sample continuously for ms, honouring an abort key.
bool sampleFor(unsigned long ms) {
    unsigned long t0 = millis();
    while (millis() - t0 < ms) {
        samplePins();
        drainPCNT();
        if (Serial.available()) {
            char c = Serial.peek();
            if (c == 'x' || c == 'X' || c == ' ') {
                Serial.read();
                stopAll(false);
                Serial.println("!!! AUTO TEST ABORTED !!!");
                return false;
            }
        }
    }
    return true;
}

void autoTest() {
    Serial.println();
    Serial.println("################ AUTO TEST ################");
    Serial.printf("# Each motor: %d PWM forward %.1fs, then reverse %.1fs.\n",
                  AUTO_TEST_PWM, AUTO_TEST_RUN_MS / 1000.0f, AUTO_TEST_RUN_MS / 1000.0f);
    Serial.println("# Press x to abort at any time.");

    for (int i = 0; i < NUM_MOTORS; i++) tr[i].ran = false;

    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.printf("\n>>> %s forward...\n", MOTOR_NAMES[i]);
        zeroCounters();
        if (!sampleFor(200)) return;

        uint32_t eA0 = ch[i].edgeA, eB0 = ch[i].edgeB;
        int32_t  p0  = pcntTotal(i);
        applyMotor(i, +AUTO_TEST_PWM);
        if (!sampleFor(AUTO_TEST_RUN_MS)) return;
        applyMotor(i, 0);
        int32_t fwd = pcntTotal(i) - p0;
        uint32_t eAf = ch[i].edgeA - eA0, eBf = ch[i].edgeB - eB0;
        if (!sampleFor(AUTO_TEST_SETTLE_MS)) return;

        Serial.printf(">>> %s reverse...\n", MOTOR_NAMES[i]);
        int32_t p1 = pcntTotal(i);
        applyMotor(i, -AUTO_TEST_PWM);
        if (!sampleFor(AUTO_TEST_RUN_MS)) return;
        applyMotor(i, 0);
        int32_t rev = pcntTotal(i) - p1;
        if (!sampleFor(AUTO_TEST_SETTLE_MS)) return;

        tr[i].fwdCounts = fwd;
        tr[i].revCounts = rev;
        tr[i].eA = eAf; tr[i].eB = eBf;
        tr[i].ran = true;

        Serial.printf("    fwd %+ld   rev %+ld   edgesA %lu   edgesB %lu\n",
                      (long)fwd, (long)rev,
                      (unsigned long)eAf, (unsigned long)eBf);
    }

    // ---- verdict table ----
    Serial.println();
    Serial.println("=================== AUTO TEST SUMMARY ===================");
    Serial.println("motor  fwd_counts  rev_counts  dir  chA   chB   verdict");
    for (int i = 0; i < NUM_MOTORS; i++) {
        if (!tr[i].ran) { Serial.printf("%-6s (not run)\n", MOTOR_NAMES[i]); continue; }
        bool dirOK;
        const char* v = verdictFor(tr[i].fwdCounts, tr[i].eA, tr[i].eB,
                                   +AUTO_TEST_PWM, &dirOK);
        bool reversed = (tr[i].fwdCounts > 0) != (tr[i].revCounts > 0);
        Serial.printf("%-6s %+11ld %+11ld  %-4s %-5s %-5s %s%s\n",
            MOTOR_NAMES[i],
            (long)tr[i].fwdCounts, (long)tr[i].revCounts,
            dirOK ? "OK" : "BAD",
            tr[i].eA ? "OK" : "DEAD",
            tr[i].eB ? "OK" : "DEAD",
            v,
            reversed ? "" : "  (!! fwd/rev same sign)");
    }
    Serial.println("=========================================================");
    Serial.println("# HEALTHY on all four = feedback path is good, wire it up.");
    Serial.println("# NO_SIGNAL      -> that channel pair never moved. Shifter or wiring.");
    Serial.println("# CH_A/B_DEAD    -> one line of the pair is not getting through.");
    Serial.println("# DIR_MISMATCH   -> flip that motor's sign in firmware before closing the loop.");
    zeroCounters();
}

// ====================================================================
// 12. UI
// ====================================================================

void printHelp() {
    Serial.println();
    Serial.println("=== KEYS ===");
    Serial.println("  1 2 3 4  select FR/FL/RR/RL      0  select ALL");
    Serial.println("  w        drive selected FORWARD  s  drive selected REVERSE");
    Serial.println("  x SPACE  STOP ALL");
    Serial.println("  p        pulse FWD 1.5s          o  pulse REV 1.5s");
    Serial.println("  + -      PWM +/- 10              [ ] \\   PWM 60 / 150 / 255");
    Serial.println("  t        AUTO TEST (all motors, full verdict table)");
    Serial.println("  f        float/drive pin test    z  zero counters");
    Serial.println("  i        status                  h  this help");
}

void printStatus() {
    Serial.println();
    Serial.printf("# selected: %s   PWM: %d\n",
                  selected < 0 ? "ALL" : MOTOR_NAMES[selected], drivePWM);
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint32_t in0 = rd0(), in1 = rd1();
        Serial.printf("#  %-2s %-7s A=G%-2d B=G%-2d  lvl A%d B%d  pos%+ld  eA%lu eB%lu sk%lu  pwm%+d\n",
            MOTOR_NAMES[i], ENC_TYPE[i], ENC_A_PINS[i], ENC_B_PINS[i],
            lvl(ENC_A_PINS[i], in0, in1), lvl(ENC_B_PINS[i], in0, in1),
            (long)pcntTotal(i),
            (unsigned long)ch[i].edgeA, (unsigned long)ch[i].edgeB,
            (unsigned long)ch[i].skips, ch[i].pwm);
    }
}

void doDrive(int sign, unsigned long pulseMs) {
    int pwm = sign * drivePWM;
    if (selected < 0) {
        for (int i = 0; i < NUM_MOTORS; i++) driveMotor(i, pwm, pulseMs);
        Serial.printf("# ALL -> pwm %+d%s\n", pwm, pulseMs ? " (pulse)" : "");
    } else {
        driveMotor(selected, pwm, pulseMs);
        Serial.printf("# %s -> pwm %+d%s\n", MOTOR_NAMES[selected], pwm,
                      pulseMs ? " (pulse)" : "");
    }
}

void handleKey(char c) {
    switch (c) {
        case '1': case '2': case '3': case '4':
            selected = c - '1';
            Serial.printf("# selected %s\n", MOTOR_NAMES[selected]);
            break;
        case '0':
            selected = -1;
            Serial.println("# selected ALL");
            break;

        case 'w': case 'W': doDrive(+1, 0); break;
        case 's': case 'S': doDrive(-1, 0); break;
        case 'p': case 'P': doDrive(+1, PULSE_MS); break;
        case 'o': case 'O': doDrive(-1, PULSE_MS); break;

        case 'x': case 'X': case ' ':
            stopAll(true);
            Serial.println("# STOPPED");
            break;

        case '+': case '=':
            drivePWM += 10; if (drivePWM > PWM_MAX) drivePWM = PWM_MAX;
            Serial.printf("# PWM %d\n", drivePWM);
            break;
        case '-': case '_':
            drivePWM -= 10; if (drivePWM < 0) drivePWM = 0;
            Serial.printf("# PWM %d\n", drivePWM);
            break;
        case '[': drivePWM = 60;  Serial.printf("# PWM %d\n", drivePWM); break;
        case ']': drivePWM = 150; Serial.printf("# PWM %d\n", drivePWM); break;
        case '\\': drivePWM = 255; Serial.printf("# PWM %d\n", drivePWM); break;

        case 't': case 'T': stopAll(false); autoTest(); break;
        case 'f': case 'F': stopAll(false); floatTest(); break;
        case 'z': case 'Z': zeroCounters(); Serial.println("# counters zeroed"); break;
        case 'i': case 'I': printStatus(); break;
        case 'h': case 'H': case '?': printHelp(); break;

        default: break;   // ignore newlines and stray characters
    }
}

// ====================================================================
// 13. SETUP / LOOP
// ====================================================================

void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(400);

    memset(ch, 0, sizeof(ch));
    memset(tr, 0, sizeof(tr));

    setupMotorPins();
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(ENC_A_PINS[i], INPUT);
        pinMode(ENC_B_PINS[i], INPUT);
    }
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);
    zeroCounters();

    Serial.println();
    Serial.println("============================================================");
    Serial.println("  NAB BENCH - MANUAL DRIVE + ENCODER DIAGNOSTIC");
    Serial.println("  *** WHEELS IN THE AIR. x or SPACE = STOP. ***");
    Serial.println("============================================================");
    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.printf("#  %-2s %-7s  encA=GPIO%-2d encB=GPIO%-2d  pwm=GPIO%-2d dir=GPIO%-2d  CPR=%.0f\n",
            MOTOR_NAMES[i], ENC_TYPE[i], ENC_A_PINS[i], ENC_B_PINS[i],
            PWM_PINS[i], DIR_PINS[i], ENCODER_CPR[i]);
    }
    Serial.println("# PCNT = authoritative count. Software edges = channel health only.");
    printHelp();
    Serial.println();
    Serial.println("# Ready. Nothing prints until something moves.");
}

void loop() {
    samplePins();
    drainPCNT();

    // ---- serial input ----
    while (Serial.available()) handleKey((char)Serial.read());

    unsigned long now = millis();

    // ---- pulse expiry + safety auto-stop ----
    bool stillDriving = false;
    for (int i = 0; i < NUM_MOTORS; i++) {
        if (ch[i].pwm == 0) continue;
        if (ch[i].pulseEndMs && now >= ch[i].pulseEndMs) {
            stopMotor(i, true);
            Serial.printf("# %s pulse done\n", MOTOR_NAMES[i]);
            continue;
        }
        if (now - ch[i].driveStartMs > MAX_RUN_MS) {
            stopMotor(i, true);
            Serial.printf("# %s auto-stopped after %lu ms (safety)\n",
                          MOTOR_NAMES[i], MAX_RUN_MS);
            continue;
        }
        stillDriving = true;
    }
    anyDriving = stillDriving;

    // ---- event-gated reporting ----
    for (int i = 0; i < NUM_MOTORS; i++) maybeReport(i);
}
