/*
 * ====================================================================
 *  NarrowAisleBot (NAB) - AUTOMATIC BENCH CALIBRATION HARNESS
 *  ESP32 <-> USB Serial <-> PC (no WiFi, no Pi)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  PURPOSE
 *    Wheels IN THE AIR. ESP32 plugged into this PC over USB. Flash,
 *    open Serial Monitor at 115200, watch the countdown, let it run.
 *    It drives all four motors through a structured sequence and dumps
 *    every number needed to calibrate feedforward and PID. Select-all,
 *    copy, paste the whole log back to Claude for analysis.
 *
 *  WHAT'S DIFFERENT FROM THE PRODUCTION FIRMWARE
 *    - Front two motors (FR, FL) now use GTK08 1000-PPR encoders.
 *      Rear two (RR, RL) still the RMCS-2086 500-line optical.
 *      => ENCODER_CPR is now a PER-MOTOR array. Fronts are exactly 2x
 *         the rears in resolution. Get this wrong and front velocities
 *         read half-scale.
 *    - No WiFi / web page. Pure serial. Single-core state machine so
 *      the timing is dead simple to reason about.
 *    - Same pin map, same PCNT decode, same motor driver logic, same
 *      PID+FF math as production so the numbers transfer directly.
 *
 *  THE TEST SEQUENCE (all automatic)
 *    Phase A  Encoder & direction sanity   - are all 4 encoders alive,
 *                                            do signs match commands?
 *    Phase B  Feedforward characterization - PWM staircase both ways,
 *                                            steady-state velocity per
 *                                            step. Yields deadband, Kff
 *                                            slope, linearity, max speed,
 *                                            and a front/rear CPR cross-
 *                                            check (should be ~2.0).
 *    Phase C  Closed-loop step response    - velocity setpoint steps
 *                                            with the fitted Kff + PID.
 *                                            Yields rise/overshoot/
 *                                            settle/steady-state error.
 *    Phase D  Slow ramp 0->max->0          - low-speed stiction and
 *                                            tracking smoothness.
 *
 *  CONTROLS (send from Serial Monitor, no <> needed)
 *    S  - abort immediately, stop all motors
 *    A  - (when idle/done) run the full sequence again
 *    ?  - print config
 *
 *  BOARD: ESP32 Dev Module, 240 MHz. Arduino-ESP32 core 3.x.
 *  BAUD : 115200  (set the Serial Monitor to match)
 * ====================================================================
 */

#include "driver/pcnt.h"

// ====================================================================
// 1. PIN MAP  (identical to production aislebot_esp32.ino - do not change)
// ====================================================================

// Driver 1 - Front (FR = Ch1, FL = Ch2)
#define PWM1_PIN   4
#define DIR1_PIN  16
#define PWM2_PIN  17
#define DIR2_PIN  18
// Driver 2 - Rear (RR = Ch1, RL = Ch2)
#define PWM3_PIN  19
#define DIR3_PIN  21
#define PWM4_PIN  22
#define DIR4_PIN  23

// Encoders via TXS0108E level shifter (5V -> 3.3V)
#define ENC1_A_PIN  36   // FR-A  (GTK08)
#define ENC1_B_PIN  39   // FR-B  (GTK08)
#define ENC2_A_PIN  34   // FL-A  (GTK08)
#define ENC2_B_PIN  35   // FL-B  (GTK08)
#define ENC3_A_PIN  32   // RR-A  (RMCS optical)
#define ENC3_B_PIN  33   // RR-B  (RMCS optical)
#define ENC4_A_PIN  25   // RL-A  (RMCS optical)
#define ENC4_B_PIN  26   // RL-B  (RMCS optical)

// ====================================================================
// 2. MOTOR IDENTITY & CONSTANTS
// ====================================================================

#define FR 0
#define FL 1
#define RR 2
#define RL 3
#define NUM_MOTORS 4

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};

const uint8_t PWM_PINS[NUM_MOTORS]   = {PWM1_PIN, PWM2_PIN, PWM3_PIN, PWM4_PIN};
const uint8_t DIR_PINS[NUM_MOTORS]   = {DIR1_PIN, DIR2_PIN, DIR3_PIN, DIR4_PIN};
const uint8_t ENC_A_PINS[NUM_MOTORS] = {ENC1_A_PIN, ENC2_A_PIN, ENC3_A_PIN, ENC4_A_PIN};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {ENC1_B_PIN, ENC2_B_PIN, ENC3_B_PIN, ENC4_B_PIN};

// Right side faces opposite to left. Driver sign and encoder sign MUST
// match per motor or the closed loop sees positive feedback and runs away.
const int8_t MOTOR_DIR_SIGN[NUM_MOTORS] = {-1, +1, -1, +1};
const int8_t ENC_DIR_SIGN[NUM_MOTORS]   = {-1, +1, -1, +1};

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

// ---- PER-MOTOR ENCODER CPR (the important change) -------------------
// Front (GTK08):  1000 PPR x 4 (full quad) x 46.566 gear = 186,264
// Rear  (RMCS-2086 optical): 500 lines x 4 x 46.566      =  93,132
// The front value is a CALCULATED estimate. Phase B cross-checks it
// against the known-good rears: at matched PWM the front/rear raw-count
// ratio should come out ~2.00. If it does not, correct these numbers.
const float ENCODER_CPR[NUM_MOTORS] = {
    186264.0f,  // FR  GTK08
    186264.0f,  // FL  GTK08
     93132.0f,  // RR  optical
     93132.0f   // RL  optical
};

// ---- Wheel / geometry (unchanged from production) -------------------
const float WHEEL_RADIUS = 0.0762f;   // DekuPro 6-inch, 152.4 mm OD
const float MAX_WHEEL_SPEED = 6.28f;  // rad/s, ~60 RPM rated

// ---- PWM ------------------------------------------------------------
const int PWM_MAX           = 255;
const int MIN_PWM_THRESHOLD = 15;
const int PWM_FREQUENCY     = 5000;
const int PWM_RESOLUTION    = 8;

// ====================================================================
// 3. PID + FEEDFORWARD  (production baseline as starting point)
// ====================================================================

const float PID_LOOP_HZ = 50.0f;
const float PID_DT      = 1.0f / PID_LOOP_HZ;   // 0.02 s
const int   TICK_MS     = 20;                    // 50 Hz control tick

float Kp = 50.0f;
float Ki = 30.0f;
float Kd =  3.0f;

// PWM per (rad/s), per motor. Phase B refits these live before Phase C.
float Kff[NUM_MOTORS] = {42.1f, 40.2f, 43.7f, 47.9f};

const float INTEGRAL_MAX     = 200.0f;
const float D_FILTER_ALPHA   = 0.3f;
const float VEL_FILTER_ALPHA = 0.5f;

// ====================================================================
// 4. TEST SEQUENCE TUNABLES
// ====================================================================

const unsigned long SERIAL_BAUD = 115200;
const int  COUNTDOWN_SEC = 8;

// Phase B staircase (PWM magnitudes). Run forward then reverse.
const int  FF_STEPS[] = {20, 35, 50, 70, 95, 125, 160, 200, 230, 255};
const int  FF_NSTEPS  = sizeof(FF_STEPS) / sizeof(FF_STEPS[0]);
const int  FF_DWELL_MS  = 1500;   // total time at each PWM step
const int  FF_SETTLE_MS = 800;    // ignore this much at the start, then measure

// Phase C velocity setpoints (rad/s). 0 is inserted between each.
const float STEP_SETPTS[] = {1.5f, 3.0f, 4.5f, 6.0f};
const int   STEP_NSETPTS  = sizeof(STEP_SETPTS) / sizeof(STEP_SETPTS[0]);
const int   STEP_DWELL_MS = 1800;
const int   STEP_LOG_EVERY = 2;   // log every Nth tick (2 -> 25 Hz)

// Phase D ramp
const float RAMP_PEAK    = 6.0f;
const int   RAMP_UP_MS   = 5000;
const int   RAMP_DOWN_MS = 5000;
const int   RAMP_LOG_EVERY = 3;   // ~17 Hz

// ====================================================================
// 5. STATE
// ====================================================================

struct MotorState {
    float target_velocity;
    float actual_velocity;      // filtered (EMA)
    float raw_velocity;
    float error;
    float integral;
    float prev_error;
    float filtered_derivative;
    int   pwm_output;
    float ff_output;
    float pid_output;
};
MotorState motors[NUM_MOTORS];

int64_t accumCounts[NUM_MOTORS];   // running count total for open-loop windows

enum RunState { ST_COUNTDOWN, ST_RUNNING, ST_DONE };
RunState runState = ST_COUNTDOWN;

bool          aborted    = false;
unsigned long seqStartMs = 0;

// Least-squares accumulators for the forward FF sweep (vel vs pwm), per motor.
double fit_n[NUM_MOTORS], fit_Sx[NUM_MOTORS], fit_Sy[NUM_MOTORS],
       fit_Sxx[NUM_MOTORS], fit_Sxy[NUM_MOTORS];

// ====================================================================
// 6. PCNT ENCODER (identical decode to production)
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

    pcnt_set_filter_value(unit, 100);   // ~1.25 us glitch filter
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

int32_t readEncoderDelta(int idx) {
    int16_t count = 0;
    pcnt_get_counter_value(PCNT_UNITS[idx], &count);
    pcnt_counter_clear(PCNT_UNITS[idx]);
    return (int32_t)count * ENC_DIR_SIGN[idx];
}

// ====================================================================
// 7. MOTOR OUTPUT (identical to production)
// ====================================================================

void setupMotorPins() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(DIR_PINS[i], OUTPUT);
        digitalWrite(DIR_PINS[i], LOW);
        ledcAttach(PWM_PINS[i], PWM_FREQUENCY, PWM_RESOLUTION);
        ledcWrite(PWM_PINS[i], 0);
    }
}

void setMotorOutput(int idx, int pwm_value) {
    int  adjusted = pwm_value * MOTOR_DIR_SIGN[idx];
    bool reverse  = (adjusted < 0);
    int  abs_pwm  = abs(adjusted);
    if (abs_pwm < MIN_PWM_THRESHOLD) abs_pwm = 0;
    if (abs_pwm > PWM_MAX)           abs_pwm = PWM_MAX;
    digitalWrite(DIR_PINS[idx], reverse ? HIGH : LOW);
    ledcWrite(PWM_PINS[idx], abs_pwm);
}

void stopAllMotors() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].target_velocity = 0;
        motors[i].integral = 0;
        motors[i].prev_error = 0;
        motors[i].filtered_derivative = 0;
        motors[i].pwm_output = 0;
        setMotorOutput(i, 0);
    }
}

// ====================================================================
// 8. VELOCITY + PID (identical math to production)
// ====================================================================

// Read all encoders, update filtered velocity, accumulate raw counts.
void updateVelocity() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        int32_t delta = readEncoderDelta(i);
        accumCounts[i] += delta;
        float raw = ((float)delta / ENCODER_CPR[i]) * (2.0f * PI) / PID_DT;
        motors[i].raw_velocity = raw;
        motors[i].actual_velocity =
            VEL_FILTER_ALPHA * raw + (1.0f - VEL_FILTER_ALPHA) * motors[i].actual_velocity;
    }
}

void computePID(int idx) {
    MotorState& m = motors[idx];
    m.ff_output = Kff[idx] * m.target_velocity;

    m.error = m.target_velocity - m.actual_velocity;
    float p = Kp * m.error;

    m.integral += m.error * PID_DT;
    m.integral  = constrain(m.integral, -INTEGRAL_MAX, INTEGRAL_MAX);
    if (fabsf(m.target_velocity) < 0.01f && fabsf(m.actual_velocity) < 0.1f) m.integral = 0.0f;
    float it = Ki * m.integral;

    float raw_d = (m.error - m.prev_error) / PID_DT;
    m.filtered_derivative = D_FILTER_ALPHA * raw_d + (1.0f - D_FILTER_ALPHA) * m.filtered_derivative;
    float dt = Kd * m.filtered_derivative;
    m.prev_error = m.error;

    m.pid_output = p + it + dt;
    float total = m.ff_output + m.pid_output;
    if (fabsf(m.target_velocity) < 0.01f) total = 0.0f;
    m.pwm_output = (int)constrain(roundf(total), -PWM_MAX, PWM_MAX);
}

// ====================================================================
// 9. ABORT HANDLING
// ====================================================================

// Poll serial mid-test. 'S'/'s' aborts. Returns true if we should stop.
bool pollAbort() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == 'S' || c == 's') {
            aborted = true;
            stopAllMotors();
            Serial.println();
            Serial.println("!!! ABORTED BY USER - motors stopped !!!");
            return true;
        }
    }
    return aborted;
}

void flushEncoders() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        readEncoderDelta(i);              // discard stale
        accumCounts[i] = 0;
        motors[i].actual_velocity = 0;
        motors[i].raw_velocity = 0;
    }
}

// ====================================================================
// 10. LOW-LEVEL PHASE PRIMITIVES
// ====================================================================

// Open-loop: hold a fixed PWM on all motors for dwellMs, measure the
// steady-state velocity over the window after settleMs. Fills outVel and
// outCnt (full-dwell raw counts). Returns false if aborted.
bool driveOpenLoop(int pwm, int dwellMs, int settleMs,
                   float outVel[NUM_MOTORS], int64_t outCnt[NUM_MOTORS]) {
    for (int i = 0; i < NUM_MOTORS; i++) setMotorOutput(i, pwm);
    for (int i = 0; i < NUM_MOTORS; i++) accumCounts[i] = 0;

    int64_t settleCnt[NUM_MOTORS] = {0};
    bool settled = false;
    unsigned long t0 = millis();
    unsigned long nextTick = t0;

    while (millis() - t0 < (unsigned long)dwellMs) {
        if (millis() >= nextTick) {
            nextTick += TICK_MS;
            updateVelocity();
        }
        if (!settled && millis() - t0 >= (unsigned long)settleMs) {
            for (int i = 0; i < NUM_MOTORS; i++) settleCnt[i] = accumCounts[i];
            settled = true;
        }
        if (pollAbort()) return false;
        delay(1);   // yield to scheduler / feed idle-task watchdog
    }
    float measSec = (dwellMs - settleMs) / 1000.0f;
    for (int i = 0; i < NUM_MOTORS; i++) {
        outCnt[i] = accumCounts[i];
        float dcnt = (float)(accumCounts[i] - settleCnt[i]);
        outVel[i] = (dcnt / ENCODER_CPR[i]) * (2.0f * PI) / measSec;
    }
    return true;
}

// Closed-loop: hold a velocity setpoint on all motors, streaming CSV.
// Computes per-motor steady-state (last 500 ms) and peak for overshoot.
bool holdSetpoint(float setpt, int dwellMs, char tag) {
    // Only change the target - leave integral/derivative running, exactly
    // like a live <V> command on the robot. The 0-setpoint hold between
    // steps clears the integral naturally (zero-target clause in computePID),
    // so each rising step still starts from a clean, faithful state.
    for (int i = 0; i < NUM_MOTORS; i++) motors[i].target_velocity = setpt;

    float ssSum[NUM_MOTORS] = {0}; int ssN[NUM_MOTORS] = {0};
    float peak[NUM_MOTORS]  = {0};

    unsigned long t0 = millis(), nextTick = t0;
    int tickCount = 0;

    while (millis() - t0 < (unsigned long)dwellMs) {
        if (millis() >= nextTick) {
            nextTick += TICK_MS;
            updateVelocity();
            for (int i = 0; i < NUM_MOTORS; i++) { computePID(i); setMotorOutput(i, motors[i].pwm_output); }

            for (int i = 0; i < NUM_MOTORS; i++)
                if (fabsf(motors[i].actual_velocity) > peak[i]) peak[i] = fabsf(motors[i].actual_velocity);
            if (millis() - t0 >= (unsigned long)(dwellMs - 500)) {
                for (int i = 0; i < NUM_MOTORS; i++) { ssSum[i] += motors[i].actual_velocity; ssN[i]++; }
            }
            if ((tickCount % STEP_LOG_EVERY) == 0) {
                Serial.printf("%c,%lu,%.2f", tag, millis() - seqStartMs, setpt);
                for (int i = 0; i < NUM_MOTORS; i++)
                    Serial.printf(",%.3f,%d", motors[i].actual_velocity, motors[i].pwm_output);
                Serial.println();
            }
            tickCount++;
        }
        if (pollAbort()) return false;
        delay(1);   // yield to scheduler / feed idle-task watchdog
    }

    if (setpt > 0.05f) {   // summary only meaningful on a rising step
        Serial.printf("# SUMMARY setpt=%.2f |", setpt);
        for (int i = 0; i < NUM_MOTORS; i++) {
            float ss = ssN[i] ? ssSum[i] / ssN[i] : 0.0f;
            float ovr = peak[i] - setpt;
            Serial.printf(" %s ss=%.3f err=%+.3f ovr=%+.3f |",
                          MOTOR_NAMES[i], ss, ss - setpt, ovr);
        }
        Serial.println();
    }
    return true;
}

// Brief stop-and-settle between phases.
bool pausePhase(int ms) {
    stopAllMotors();
    unsigned long t0 = millis();
    while (millis() - t0 < (unsigned long)ms) { if (pollAbort()) return false; delay(5); }
    flushEncoders();
    return true;
}

// ====================================================================
// 11. THE PHASES
// ====================================================================

bool phaseA() {
    Serial.println();
    Serial.println("=== PHASE A: ENCODER & DIRECTION CHECK ===");
    Serial.println("# fmt: A,motor,pwm_cmd,raw_counts,vel_rads,result");
    if (!pausePhase(300)) return false;

    float vf[NUM_MOTORS]; int64_t cf[NUM_MOTORS];
    float vr[NUM_MOTORS]; int64_t cr[NUM_MOTORS];

    if (!driveOpenLoop(+90, 1200, 400, vf, cf)) return false;
    if (!pausePhase(400)) return false;
    if (!driveOpenLoop(-90, 1200, 400, vr, cr)) return false;
    if (!pausePhase(300)) return false;

    for (int i = 0; i < NUM_MOTORS; i++) {
        const char* res;
        if (fabsf(vf[i]) < 0.10f)      res = "DEAD_NO_COUNTS";
        else if (vf[i] < 0)            res = "SIGN_INVERTED";
        else                          res = "OK";
        Serial.printf("A,%s,+90,%ld,%.3f,%s\n", MOTOR_NAMES[i], (long)cf[i], vf[i], res);
    }
    for (int i = 0; i < NUM_MOTORS; i++) {
        const char* res;
        if (fabsf(vr[i]) < 0.10f)      res = "DEAD_NO_COUNTS";
        else if (vr[i] > 0)            res = "SIGN_INVERTED";
        else                          res = "OK";
        Serial.printf("A,%s,-90,%ld,%.3f,%s\n", MOTOR_NAMES[i], (long)cr[i], vr[i], res);
    }
    return true;
}

bool phaseB() {
    Serial.println();
    Serial.println("=== PHASE B: FEEDFORWARD CHARACTERIZATION ===");
    Serial.println("# fmt: B,dir,pwm,FR_vel,FL_vel,RR_vel,RL_vel,FR_cnt,FL_cnt,RR_cnt,RL_cnt");
    if (!pausePhase(300)) return false;

    for (int i = 0; i < NUM_MOTORS; i++) { fit_n[i]=fit_Sx[i]=fit_Sy[i]=fit_Sxx[i]=fit_Sxy[i]=0; }

    // mid-PWM raw counts captured for the CPR cross-check
    int64_t midCnt[NUM_MOTORS] = {0}; bool midCaptured = false;

    // ---- forward sweep (also feeds the least-squares fit) ----
    for (int s = 0; s < FF_NSTEPS; s++) {
        int pwm = FF_STEPS[s];
        float v[NUM_MOTORS]; int64_t c[NUM_MOTORS];
        if (!driveOpenLoop(pwm, FF_DWELL_MS, FF_SETTLE_MS, v, c)) return false;
        Serial.printf("B,+,%d,%.3f,%.3f,%.3f,%.3f,%ld,%ld,%ld,%ld\n",
            pwm, v[FR],v[FL],v[RR],v[RL],
            (long)c[FR],(long)c[FL],(long)c[RR],(long)c[RL]);
        for (int i = 0; i < NUM_MOTORS; i++) {
            if (v[i] > 0.15f) {   // only the moving region
                fit_n[i]+=1; fit_Sx[i]+=pwm; fit_Sy[i]+=v[i];
                fit_Sxx[i]+=(double)pwm*pwm; fit_Sxy[i]+=(double)pwm*v[i];
            }
        }
        if (!midCaptured && pwm >= 150) { for (int i=0;i<NUM_MOTORS;i++) midCnt[i]=c[i]; midCaptured=true; }
        if (pollAbort()) return false;
    }

    if (!pausePhase(400)) return false;

    // ---- reverse sweep (asymmetry check) ----
    for (int s = 0; s < FF_NSTEPS; s++) {
        int pwm = FF_STEPS[s];
        float v[NUM_MOTORS]; int64_t c[NUM_MOTORS];
        if (!driveOpenLoop(-pwm, FF_DWELL_MS, FF_SETTLE_MS, v, c)) return false;
        Serial.printf("B,-,%d,%.3f,%.3f,%.3f,%.3f,%ld,%ld,%ld,%ld\n",
            pwm, v[FR],v[FL],v[RR],v[RL],
            (long)c[FR],(long)c[FL],(long)c[RR],(long)c[RL]);
        if (pollAbort()) return false;
    }

    if (!pausePhase(300)) return false;

    // ---- CPR cross-check (front should be ~2.0x the rears) ----
    if (midCaptured) {
        double frontAvg = (fabs((double)midCnt[FR]) + fabs((double)midCnt[FL])) / 2.0;
        double rearAvg  = (fabs((double)midCnt[RR]) + fabs((double)midCnt[RL])) / 2.0;
        double ratio = rearAvg > 1 ? frontAvg / rearAvg : 0;
        Serial.printf("# CPR-CHECK: front/rear raw-count ratio @~150pwm = %.3f (expect ~2.00 for GTK08 vs optical)\n", ratio);
        Serial.println("#   if this is ~1.0, the fronts are NOT 2x res -> fix ENCODER_CPR[FR/FL].");
    }

    // ---- fit Kff + deadband per motor, then load Kff for Phase C ----
    Serial.println("# FF FIT (vel = m*pwm + c over moving points):");
    for (int i = 0; i < NUM_MOTORS; i++) {
        float suggKff = Kff[i], deadband = 0;
        if (fit_n[i] >= 3) {
            double n=fit_n[i], Sx=fit_Sx[i], Sy=fit_Sy[i], Sxx=fit_Sxx[i], Sxy=fit_Sxy[i];
            double denom = n*Sxx - Sx*Sx;
            if (fabs(denom) > 1e-6) {
                double m = (n*Sxy - Sx*Sy) / denom;
                double c = (Sy - m*Sx) / n;
                if (m > 1e-4) {
                    suggKff  = (float)(1.0 / m);      // PWM per rad/s
                    deadband = (float)(-c / m);        // PWM x-intercept
                }
            }
        }
        Serial.printf("#   %s  Kff=%.2f pwm/(rad/s)  deadband=%.1f pwm\n",
                      MOTOR_NAMES[i], suggKff, deadband);
        // apply if sane, else keep production default
        if (suggKff > 20.0f && suggKff < 120.0f) Kff[i] = suggKff;
    }
    Serial.printf("# Kff loaded for Phase C: FR=%.2f FL=%.2f RR=%.2f RL=%.2f\n",
                  Kff[FR],Kff[FL],Kff[RR],Kff[RL]);
    return true;
}

bool phaseC() {
    Serial.println();
    Serial.printf("=== PHASE C: CLOSED-LOOP STEP RESPONSE (Kp=%.0f Ki=%.0f Kd=%.1f) ===\n", Kp,Ki,Kd);
    Serial.println("# fmt: C,t_ms,setpt,FR_act,FR_pwm,FL_act,FL_pwm,RR_act,RR_pwm,RL_act,RL_pwm");
    if (!pausePhase(400)) return false;

    for (int s = 0; s < STEP_NSETPTS; s++) {
        if (!holdSetpoint(STEP_SETPTS[s], STEP_DWELL_MS, 'C')) return false;
        if (!holdSetpoint(0.0f, STEP_DWELL_MS, 'C')) return false;   // return to rest
    }
    return true;
}

bool phaseD() {
    Serial.println();
    Serial.println("=== PHASE D: SLOW RAMP (low-speed tracking / stiction) ===");
    Serial.println("# fmt: D,t_ms,setpt,FR_act,FR_pwm,FL_act,FL_pwm,RR_act,RR_pwm,RL_act,RL_pwm");
    if (!pausePhase(400)) return false;

    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].integral = 0; motors[i].prev_error = 0; motors[i].filtered_derivative = 0;
    }
    unsigned long t0 = millis(), nextTick = t0; int tickCount = 0;
    int total = RAMP_UP_MS + RAMP_DOWN_MS;
    while (millis() - t0 < (unsigned long)total) {
        if (millis() >= nextTick) {
            nextTick += TICK_MS;
            int el = millis() - t0;
            float setpt = (el < RAMP_UP_MS)
                          ? RAMP_PEAK * (el / (float)RAMP_UP_MS)
                          : RAMP_PEAK * (1.0f - (el - RAMP_UP_MS) / (float)RAMP_DOWN_MS);
            for (int i = 0; i < NUM_MOTORS; i++) motors[i].target_velocity = setpt;
            updateVelocity();
            for (int i = 0; i < NUM_MOTORS; i++) { computePID(i); setMotorOutput(i, motors[i].pwm_output); }
            if ((tickCount % RAMP_LOG_EVERY) == 0) {
                Serial.printf("D,%lu,%.3f", millis() - seqStartMs, setpt);
                for (int i = 0; i < NUM_MOTORS; i++)
                    Serial.printf(",%.3f,%d", motors[i].actual_velocity, motors[i].pwm_output);
                Serial.println();
            }
            tickCount++;
        }
        if (pollAbort()) return false;
        delay(1);   // yield to scheduler / feed idle-task watchdog
    }
    return true;
}

// ====================================================================
// 12. SEQUENCE DRIVER
// ====================================================================

void printConfig() {
    Serial.println("# ---- NAB BENCH CALIBRATION CONFIG ----");
    Serial.printf("# ENCODER_CPR: FR=%.0f FL=%.0f (GTK08) | RR=%.0f RL=%.0f (optical)\n",
                  ENCODER_CPR[FR],ENCODER_CPR[FL],ENCODER_CPR[RR],ENCODER_CPR[RL]);
    Serial.printf("# WHEEL_RADIUS=%.4f  MAX_WHEEL_SPEED=%.2f rad/s\n", WHEEL_RADIUS, MAX_WHEEL_SPEED);
    Serial.printf("# PID: Kp=%.1f Ki=%.1f Kd=%.1f  @ %.0f Hz\n", Kp,Ki,Kd,PID_LOOP_HZ);
    Serial.printf("# Kff start: FR=%.1f FL=%.1f RR=%.1f RL=%.1f\n", Kff[FR],Kff[FL],Kff[RR],Kff[RL]);
    Serial.printf("# MOTOR_DIR_SIGN: %d %d %d %d\n",
                  MOTOR_DIR_SIGN[0],MOTOR_DIR_SIGN[1],MOTOR_DIR_SIGN[2],MOTOR_DIR_SIGN[3]);
    Serial.println("# --------------------------------------");
}

void runSequence() {
    aborted = false;
    seqStartMs = millis();
    flushEncoders();

    Serial.println();
    Serial.println("########## BENCH CALIBRATION RUN START ##########");
    printConfig();

    if (phaseA() && phaseB() && phaseC() && phaseD()) {
        stopAllMotors();
        Serial.println();
        Serial.println("########## TEST COMPLETE ##########");
        Serial.println("# Select all, copy the whole log, paste it back for analysis.");
        Serial.println("# Send 'A' to run again.");
    } else {
        stopAllMotors();
        Serial.println();
        Serial.println("########## RUN ENDED EARLY (aborted) ##########");
        Serial.println("# Send 'A' to run again.");
    }
    runState = ST_DONE;
}

// ====================================================================
// 13. SETUP / LOOP
// ====================================================================

void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(300);
    memset(motors, 0, sizeof(motors));

    setupMotorPins();
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);
    stopAllMotors();
    flushEncoders();

    Serial.println();
    Serial.println("====================================================");
    Serial.println("  NAB BENCH CALIBRATION HARNESS");
    Serial.println("  >>> WHEELS MUST BE IN THE AIR <<<");
    Serial.println("====================================================");
    printConfig();
    Serial.println();
    Serial.println("  Controls:  S = abort/stop   A = run again   ? = config");
    Serial.printf ("  Auto-start in %d s. Send any character to abort start.\n", COUNTDOWN_SEC);
    Serial.println();
    runState = ST_COUNTDOWN;
}

void loop() {
    static int lastSec = -1;
    static unsigned long cdStart = 0;

    if (runState == ST_COUNTDOWN) {
        if (cdStart == 0) cdStart = millis();
        // abort countdown on any input
        if (Serial.available()) {
            while (Serial.available()) Serial.read();
            Serial.println("  Countdown aborted. Send 'A' to start the test.");
            runState = ST_DONE;
            cdStart = 0;
            return;
        }
        int remaining = COUNTDOWN_SEC - (millis() - cdStart) / 1000;
        if (remaining != lastSec) {
            lastSec = remaining;
            if (remaining >= 0) Serial.printf("  starting in %d ...\n", remaining);
        }
        if (millis() - cdStart >= (unsigned long)COUNTDOWN_SEC * 1000) {
            runState = ST_RUNNING;
        }
        return;
    }

    if (runState == ST_RUNNING) {
        runSequence();
        return;
    }

    // ST_DONE: idle, accept commands
    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'A' || c == 'a') { runState = ST_RUNNING; }
        else if (c == '?')        { printConfig(); }
        else if (c == 'S' || c == 's') { stopAllMotors(); Serial.println("# stopped."); }
    }
    delay(5);
}
