/*
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║            NarrowAisleBot — ESP32 Motor Controller  v3.0          ║
 * ║                                                                  ║
 * ║  Pi-commanded  |  PID + 2-term Feedforward  |  Hardware PCNT     ║
 * ║  Per-motor CPR |  100 Hz control loop       |  Dual-core FreeRTOS║
 * ║                                                                  ║
 * ║  Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar       ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * WHAT CHANGED FROM v2.0  (and why)
 *
 *   1. WiFi / WebSocket / joystick web page REMOVED.
 *      The Raspberry Pi 5 is now the only command source. Removing the
 *      radio frees ~40 % of flash, removes WiFi's periodic CPU steal on
 *      Core 0, and deletes the whole WiFi-vs-Serial arbitration path —
 *      which was the only place two writers could fight over the
 *      setpoints. One source, one owner, no arbitration.
 *
 *   2. ENCODER_CPR is now PER MOTOR.
 *      The front motors carry GTK08 encoders (1000 PPR), the rears keep
 *      the RMCS-2086 optical (500 lines). The fronts are exactly 2x the
 *      resolution of the rears. v2.0's single 93132 constant made the
 *      fronts read DOUBLE their true speed — with FF+PID closing on that,
 *      the fronts would have run at half the commanded velocity.
 *      Confirmed on the bench 4 Aug 2026 (docs/Bench_Test_Map.md): the
 *      front/rear raw-count ratio at matched PWM lands at ~2.0x.
 *
 *   3. Feedforward is now a TWO-TERM model:  pwm = Kff*w + Kstat*sgn(w)
 *      A single slope cannot fit both ends of the range. Kstat covers
 *      breakaway/Coulomb friction, Kff covers the viscous slope. See
 *      docs/PID_Calibration.md for the fit and the source data.
 *
 *   4. Ki raised from 30 to 250.  This is the headline fix.
 *      At Ki=30 the integral moved ~3 PWM per second — far too slow to
 *      correct a feedforward error inside a manoeuvre, which is why the
 *      14 May air run settled in up to 3.79 s. Ki now follows from the
 *      measured plant gain, not from guesswork.
 *
 *   5. Derivative acts on MEASUREMENT, not error.  No derivative kick
 *      when the Pi sends a new setpoint (which it does, in steps, at
 *      20 Hz). Same damping, none of the spike.
 *
 *   6. Anti-windup is a DYNAMIC clamp against real PWM headroom.
 *      v2.0's fixed +/-200 clamp with Ki=30 allowed a 6000 PWM integral
 *      term — i.e. it never actually bound. The integral is now held to
 *      exactly the authority left over after FF + P + D.
 *
 *   7. Control loop 50 Hz -> 100 Hz.  Affordable because PCNT counts in
 *      silicon and the 186k-CPR fronts quantize at 0.0034 rad/s per count
 *      even at 100 Hz. Halves sampling delay, halves counts-per-tick.
 *
 *   8. Setpoint slew limiting, plus overspeed / runaway / stall trips.
 *      A MOTOR_DIR_SIGN / ENC_DIR_SIGN mismatch is positive feedback —
 *      the motor pins itself at redline the wrong way until something
 *      mechanical gives. The runaway trip catches that in 500 ms.
 *
 *   9. <M> direct-PWM actually works now.
 *      In v2.0 the PID task overwrote it on the next tick, so an <M>
 *      command drove the motors for under 20 ms and then stopped. It went
 *      unnoticed because nothing used <M> until open-loop calibration
 *      needed it. There is now an explicit open-loop mode, left again by
 *      the next <V>/<B>/<T>.
 *
 * WIRE PROTOCOL — unchanged where it matters.
 *   <V,...> and the 13-column telemetry line are byte-identical to v2.0,
 *   so esp32_bridge.py and aislebot_pid_analysis_v2.py both keep working
 *   with no edits. <L2> appends extra columns AFTER those 13, so the
 *   bridge's fixed-index parse is unaffected.
 *
 * BOARD SETTINGS:
 *   Board: ESP32 Dev Module | CPU: 240 MHz | Flash: 4 MB
 *   Partition: Default 4 MB with spiffs | PSRAM: Disabled
 *   Upload Speed: 921600 | Arduino-ESP32 core 3.x
 *
 * LIBRARIES: none beyond the ESP32 core. (ArduinoJson / WebSockets are
 *            no longer required — the web joystick is gone.)
 */

#include "driver/pcnt.h"

// ═══════════════════════════════════════════════════════════════════
// 1. PIN DEFINITIONS  — unchanged from v2.0, bench-confirmed 4 Aug 2026
//    Motor driver outputs: 3.3 V direct, no level shifting.
//    Encoder inputs: 5 V via the 8-channel BSS138 shifter (H0-H7/L0-L7).
// ═══════════════════════════════════════════════════════════════════

// Driver 1 — Front motors (FR = Ch1, FL = Ch2)
#define PWM1_PIN   4    // G4  → Driver 1 PWM1  (FR)
#define DIR1_PIN  16    // G16 → Driver 1 DIR1  (FR)
#define PWM2_PIN  17    // G17 → Driver 1 PWM2  (FL)
#define DIR2_PIN  18    // G18 → Driver 1 DIR2  (FL)

// Driver 2 — Rear motors (RR = Ch1, RL = Ch2)
#define PWM3_PIN  19    // G19 → Driver 2 PWM1  (RR)
#define DIR3_PIN  21    // G21 → Driver 2 DIR1  (RR)
#define PWM4_PIN  22    // G22 → Driver 2 PWM2  (RL)
#define DIR4_PIN  23    // G23 → Driver 2 DIR2  (RL)

// Encoders — shifter channel L0..L7 in this exact order
#define ENC1_A_PIN  36  // SP  → FR-A   (GTK08,   green)
#define ENC1_B_PIN  39  // SN  → FR-B   (GTK08,   white)
#define ENC2_A_PIN  34  // G34 → FL-A   (GTK08,   green)
#define ENC2_B_PIN  35  // G35 → FL-B   (GTK08,   white)
#define ENC3_A_PIN  32  // G32 → RR-A   (RMCS-2086, yellow)
#define ENC3_B_PIN  33  // G33 → RR-B   (RMCS-2086, green)
#define ENC4_A_PIN  25  // G25 → RL-A   (RMCS-2086, yellow)
#define ENC4_B_PIN  26  // G26 → RL-B   (RMCS-2086, green)

// ═══════════════════════════════════════════════════════════════════
// 2. MOTOR & ROBOT CONSTANTS
// ═══════════════════════════════════════════════════════════════════

#define FR  0
#define FL  1
#define RR  2
#define RL  3
#define NUM_MOTORS 4

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};

const uint8_t PWM_PINS[NUM_MOTORS]   = {PWM1_PIN, PWM2_PIN, PWM3_PIN, PWM4_PIN};
const uint8_t DIR_PINS[NUM_MOTORS]   = {DIR1_PIN, DIR2_PIN, DIR3_PIN, DIR4_PIN};
const uint8_t ENC_A_PINS[NUM_MOTORS] = {ENC1_A_PIN, ENC2_A_PIN, ENC3_A_PIN, ENC4_A_PIN};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {ENC1_B_PIN, ENC2_B_PIN, ENC3_B_PIN, ENC4_B_PIN};

// Right-side motors face opposite to left.
// MOTOR_DIR_SIGN and ENC_DIR_SIGN MUST be identical per motor. If they
// disagree the loop sees positive feedback and runs away — the runaway
// trip in §10 exists specifically to catch that.
const int8_t MOTOR_DIR_SIGN[NUM_MOTORS] = {-1, +1, -1, +1}; // FR,FL,RR,RL
const int8_t ENC_DIR_SIGN[NUM_MOTORS]   = {-1, +1, -1, +1}; // Must match above

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

// ── Encoders — PER MOTOR, the fronts are NOT the same as the rears ───
//   Front  GTK08      : 1000 PPR × 4 (full quad) × 46.566 = 186 264
//   Rear   RMCS-2086  :  500 lines × 4             × 46.566 =  93 132
// Verified on the bench: front/rear raw-count ratio at matched PWM and
// duration came out at 2.0-2.1x across hundreds of thousands of counts.
const float ENCODER_CPR[NUM_MOTORS] = {
    186264.0f,   // FR  GTK08
    186264.0f,   // FL  GTK08
     93132.0f,   // RR  RMCS-2086 optical
     93132.0f    // RL  RMCS-2086 optical
};

// ── Wheel ────────────────────────────────────────────────────────────
// DekuPro 6-inch SR Mecanum: OD = 152.4 mm → radius = 76.2 mm
const float WHEEL_RADIUS = 0.0762f;

// ── Asymmetric robot geometry (from SolidWorks) ──────────────────────
// l1 = 0.403 m outer pair (FR, RL) | l2 = 0.333 m inner pair (FL, RR)
// d  = 0.15769 m half-track width
const float ROBOT_L1 = 0.403f;
const float ROBOT_L2 = 0.333f;
const float ROBOT_D  = 0.15769f;
const float K_OUTER  = ROBOT_L1 + ROBOT_D;  // 0.56069 m  (FR, RL)
const float K_INNER  = ROBOT_L2 + ROBOT_D;  // 0.49069 m  (FL, RR)

// ── PWM ──────────────────────────────────────────────────────────────
const int PWM_MAX        = 255;
const int PWM_FREQUENCY  = 5000;   // 5 kHz — above audible
const int PWM_RESOLUTION = 8;      // 8-bit (0–255)

// Only kills true hum. v2.0 used 15 here, which punched a dead zone
// straight through the middle of the controller's fine-regulation range
// and produced a limit cycle at low speed. Breakaway friction is handled
// properly by Kstat below, so this can drop to the level where the
// motor genuinely makes no sound.
const int MIN_PWM_OUT = 5;

// ═══════════════════════════════════════════════════════════════════
// 3. CALIBRATED PLANT MODEL  —  see docs/PID_Calibration.md
//
//    Feedforward model, per motor:
//        pwm_ff = Kff[i] * w_target  +  Kstat[i] * sgn(w_target)
//
//    Fitted to three independent in-air campaigns:
//      · 4 Aug 2026 manual drive, steady state : PWM  80 → 1.83-1.94 rad/s
//      · 4 Aug 2026 AUTO TEST, 1.5 s windows   : PWM 110 → 2.59-2.67 rad/s
//      · 14 May 2026 closed-loop back-calc     : pwm/w ratio ~46.9 @ ~1.5 rad/s
//
//    The rising pwm/w ratio at low speed is exactly the signature of a
//    non-zero Kstat; a single-slope model cannot reproduce it. Fitting
//    both terms gives Kff ~ 38 and Kstat ~ 8, which reproduces every
//    measured point to within ~6 %.
//
//    NOTE ON THE OLD PER-MOTOR SPREAD: v2.0 shipped Kff 40.2 … 47.9, a
//    19 % spread between FL and RL. That spread came from the era of the
//    faulty encoder path (the FR/FL cross-connection found on 4 Aug).
//    Re-measured on the confirmed-good path, all four motors fall inside
//    a 3 % band. The near-identical values below are the real hardware.
// ═══════════════════════════════════════════════════════════════════

// PWM per (rad/s) — viscous slope. AIR-CALIBRATED.
float Kff[NUM_MOTORS] = {37.3f, 38.4f, 38.3f, 38.0f};  // FR, FL, RR, RL

// PWM offset to break stiction — Coulomb/breakaway term. AIR-CALIBRATED.
// Expect this to be the term that grows most on the ground; re-measure
// it first (PWM staircase from 5 upward, find start-of-motion per motor).
float Kstat[NUM_MOTORS] = {8.0f, 8.0f, 8.0f, 8.0f};

// Kstat is faded in over this velocity range instead of being applied as
// a hard step at any nonzero target — avoids a PWM discontinuity when
// the Pi commands a very small velocity.
const float KSTAT_FADE_LO = 0.05f;   // rad/s — below this, no static term
const float KSTAT_FADE_HI = 0.20f;   // rad/s — above this, full static term

// ═══════════════════════════════════════════════════════════════════
// 4. PID CONFIGURATION
//
//    Plant (from the FF fit):  K = 1/38 = 0.0263 rad/s per PWM.
//    Lambda (direct-synthesis) tuning for a first-order plant:
//        Ki = 1 / (K * lambda)        <- depends only on K, NOT on tau
//        Kp = tau * Ki
//    With lambda = 0.15 s (a deliberately conservative closed-loop time
//    constant, 15 control periods):  Ki = 1/(0.0263*0.15) = 253.
//
//    Kp still contains tau, the plant's mechanical time constant, which
//    has never been measured on this robot — the bench runs so far only
//    ever logged steady-state points, never a transient. Kp = 45 assumes
//    tau ~ 0.18 s, plausible for a 100 W motor behind a 47:1 planetary.
//    Kp is the one gain here that is an estimate rather than a fit.
//    tools/nab_pid_logger.py --test plant  measures it in about 40 s.
//
//    Kd is deliberately small. Against a first-order plant a matched PI
//    needs no derivative at all; this much only damps the unmodelled lag
//    (driver delay, gearbox compliance, the velocity filter itself).
// ═══════════════════════════════════════════════════════════════════

const float PID_LOOP_HZ          = 100.0f;
const float PID_LOOP_INTERVAL_MS = 1000.0f / PID_LOOP_HZ;  // 10 ms
const float PID_DT               = 1.0f    / PID_LOOP_HZ;  // 0.01 s

float Kp =  45.0f;   // PWM per (rad/s) of error
float Ki = 250.0f;   // PWM per (rad/s · s) of accumulated error
float Kd =   0.5f;   // PWM per (rad/s²) — acts on measurement, not error

// Absolute backstop on the integral. The real limit is the dynamic
// headroom clamp in computePID(); this only bounds the state itself.
const float INTEGRAL_ABS_MAX = 20.0f;

// Velocity measurement filter. One encoder count is 0.0034 rad/s (front)
// / 0.0067 rad/s (rear) at 100 Hz, so quantisation noise is negligible
// and this can stay light — 0.4 gives a ~15 ms time constant.
const float VEL_FILTER_ALPHA = 0.4f;

// Derivative filter — heavier, because differentiating always amplifies
// whatever noise survives the velocity filter.
const float D_FILTER_ALPHA = 0.25f;

// ═══════════════════════════════════════════════════════════════════
// 5. LIMITS, TIMING & SAFETY
// ═══════════════════════════════════════════════════════════════════

// Runtime-settable so the Pi can lower them after ground calibration
// without a reflash. See <X> and <A>.

// AIR value. At 5.20 rad/s the worst motor needs 38.4*5.2 + 8 = 208 PWM,
// leaving 47 PWM (18 %) of authority for the PID — a sane margin.
// ON THE GROUND: feedforward is expected to rise 10-30 %, which would
// eat that margin entirely. Re-measure Kff/Kstat loaded, then drop this
// to roughly 4.2 rad/s (or whatever keeps ~40 PWM of headroom).
float max_wheel_speed = 5.20f;   // rad/s

// Setpoint slew limit. Stops the Pi's step commands from demanding an
// acceleration the hardware cannot produce, which is what drives the
// integral into saturation. 0 disables the limiter.
float max_wheel_accel = 12.0f;   // rad/s²

const unsigned long WATCHDOG_TIMEOUT_MS = 750;  // no command → ramp to stop
const unsigned long SERIAL_BAUD         = 921600;

// Telemetry rate, settable with <L1,hz> / <L2,hz>. 20 Hz is plenty for
// watching a run; plant identification wants 50 Hz so a ~150 ms
// mechanical time constant is resolved by more than three samples.
volatile unsigned long telemetry_interval_ms = 50;   // 20 Hz
const unsigned long TELEMETRY_MIN_INTERVAL_MS = 10;  // 100 Hz ceiling

// Safety trips (toggle with <Y1>/<Y0>)
//
// OVERSPEED — measured speed well past what could have been commanded.
const float         OVERSPEED_FACTOR   = 1.30f;   // × max_wheel_speed
const unsigned long OVERSPEED_TRIP_MS  = 300;
//
// RUNAWAY — saturated PWM pushing one way, wheel turning the other, and
// not slowing down. A rated-60-RPM motor cannot overspeed its way past
// the OVERSPEED threshold, so a sign-inverted encoder would sit there
// pinned at redline forever without that check ever firing. This is the
// one that actually catches it.
const int           RUNAWAY_PWM_SAT    = 240;     // |pwm| counts as saturated
const float         RUNAWAY_MIN_SPEED  = 1.0f;    // rad/s — ignore creep
const float         RUNAWAY_DECEL_TOL  = 0.20f;   // rad/s over the window
const unsigned long RUNAWAY_WINDOW_MS  = 500;     // deceleration lookback
const unsigned long RUNAWAY_TRIP_MS    = 500;
//
// STALL — full PWM, wheel not turning. Jam, seized gearbox, or a driver
// output failed short. All three want the power off, not more of it.
const int           STALL_PWM_THRESHOLD   = 250;
const float         STALL_SPEED_THRESHOLD = 0.15f; // rad/s
const unsigned long STALL_TRIP_MS         = 2000;

// ═══════════════════════════════════════════════════════════════════
// 6. DATA STRUCTURES
// ═══════════════════════════════════════════════════════════════════

struct MotorState {
    float target_velocity;      // rad/s — commanded (pre-slew)
    float slewed_target;        // rad/s — what the PID actually chases
    float actual_velocity;      // rad/s — filtered
    float raw_velocity;         // rad/s — unfiltered, for diagnostics
    float prev_velocity;        // rad/s — for derivative-on-measurement
    float error;
    float integral;
    float filtered_derivative;
    float ff_output;
    float pid_output;
    int   pwm_output;           // -255 … +255
    double position_rad;        // accumulated wheel angle, for odometry
    unsigned long overspeed_since_ms;
    unsigned long runaway_since_ms;
    unsigned long stall_since_ms;
    float         vel_checkpoint;      // |velocity| one window ago
    unsigned long checkpoint_ms;
};

MotorState motors[NUM_MOTORS];

enum EstopReason { ES_NONE, ES_COMMAND, ES_RUNAWAY, ES_STALL };

volatile bool motors_enabled   = true;
volatile bool watchdog_enabled = true;
volatile bool trips_enabled    = true;
volatile bool estop_active     = false;
volatile EstopReason estop_reason = ES_NONE;

// Open-loop mode, entered by <M> and left by any velocity command.
// Without an explicit flag the PID task would overwrite a direct-PWM
// command on its very next tick — <M> would appear to do nothing for
// 10 ms and then stop. (v2.0 had exactly that bug; it went unnoticed
// because nothing used <M> until the calibration harness needed it.)
volatile bool manual_pwm_mode = false;

volatile uint8_t       telemetry_mode  = 0;   // 0 off, 1 compat 13-col, 2 extended
volatile unsigned long last_cmd_ms     = 0;
volatile bool          watchdog_tripped = false;

// Set by the serial parser (Core 0), consumed by the PID task (Core 1).
portMUX_TYPE cmd_mux = portMUX_INITIALIZER_UNLOCKED;

// ═══════════════════════════════════════════════════════════════════
// 7. PCNT ENCODER SETUP — full quadrature, both channels, all edges
//
//  Counts-per-tick sanity at 100 Hz: the fastest case is a front wheel
//  at max_wheel_speed. 5.2 rad/s = 0.83 rev/s × 186264 = 154k counts/s
//  = 1543 counts per 10 ms tick, against an int16 range of ±32767. Even
//  a 200 ms scheduling stall would not overflow the counter.
// ═══════════════════════════════════════════════════════════════════

void setupPCNT(int idx) {
    pcnt_unit_t unit = PCNT_UNITS[idx];
    uint8_t     pinA = ENC_A_PINS[idx];
    uint8_t     pinB = ENC_B_PINS[idx];

    // Channel 0: count A edges, direction from B
    pcnt_config_t cfg0 = {};
    cfg0.pulse_gpio_num = pinA;
    cfg0.ctrl_gpio_num  = pinB;
    cfg0.channel        = PCNT_CHANNEL_0;
    cfg0.unit           = unit;
    cfg0.pos_mode       = PCNT_COUNT_INC;
    cfg0.neg_mode       = PCNT_COUNT_DEC;
    cfg0.lctrl_mode     = PCNT_MODE_REVERSE;
    cfg0.hctrl_mode     = PCNT_MODE_KEEP;
    cfg0.counter_h_lim  =  32767;
    cfg0.counter_l_lim  = -32768;
    pcnt_unit_config(&cfg0);

    // Channel 1: count B edges, direction from A
    pcnt_config_t cfg1 = {};
    cfg1.pulse_gpio_num = pinB;
    cfg1.ctrl_gpio_num  = pinA;
    cfg1.channel        = PCNT_CHANNEL_1;
    cfg1.unit           = unit;
    cfg1.pos_mode       = PCNT_COUNT_DEC;
    cfg1.neg_mode       = PCNT_COUNT_INC;
    cfg1.lctrl_mode     = PCNT_MODE_REVERSE;
    cfg1.hctrl_mode     = PCNT_MODE_KEEP;
    cfg1.counter_h_lim  =  32767;
    cfg1.counter_l_lim  = -32768;
    pcnt_unit_config(&cfg1);

    // 100 APB cycles ≈ 1.25 µs glitch filter. The fastest real edge is a
    // 10.6 µs half-period (GTK08 at motor redline), so this rejects noise
    // with ~8x margin and cannot eat a genuine transition.
    pcnt_set_filter_value(unit, 100);
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

// Returns encoder delta since last call, sign-corrected for motor direction.
int32_t readEncoderDelta(int idx) {
    int16_t count = 0;
    pcnt_get_counter_value(PCNT_UNITS[idx], &count);
    pcnt_counter_clear(PCNT_UNITS[idx]);
    return (int32_t)count * ENC_DIR_SIGN[idx];
}

// ═══════════════════════════════════════════════════════════════════
// 8. MOTOR OUTPUT
// ═══════════════════════════════════════════════════════════════════

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

    if (abs_pwm < MIN_PWM_OUT) abs_pwm = 0;
    if (abs_pwm > PWM_MAX)     abs_pwm = PWM_MAX;

    digitalWrite(DIR_PINS[idx], reverse ? HIGH : LOW);
    ledcWrite(PWM_PINS[idx], abs_pwm);
}

// Full reset of every controller state. Used on E-STOP and disable.
void stopAllMotors() {
    manual_pwm_mode = false;
    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].target_velocity     = 0;
        motors[i].slewed_target       = 0;
        motors[i].integral            = 0;
        motors[i].filtered_derivative = 0;
        motors[i].pwm_output          = 0;
        motors[i].overspeed_since_ms  = 0;
        motors[i].runaway_since_ms    = 0;
        motors[i].stall_since_ms      = 0;
        setMotorOutput(i, 0);
    }
}

// ═══════════════════════════════════════════════════════════════════
// 9. PID + FEEDFORWARD
// ═══════════════════════════════════════════════════════════════════

// Two-term feedforward. The static term fades in across
// KSTAT_FADE_LO..HI so a tiny commanded velocity does not produce an
// instant 8-PWM step at the output.
static inline float feedforward(int idx, float w) {
    float aw = fabsf(w);
    float ff = Kff[idx] * w;

    if (aw > KSTAT_FADE_LO) {
        float fade = (aw - KSTAT_FADE_LO) / (KSTAT_FADE_HI - KSTAT_FADE_LO);
        if (fade > 1.0f) fade = 1.0f;
        ff += Kstat[idx] * fade * (w > 0 ? 1.0f : -1.0f);
    }
    return ff;
}

void computePID(int idx) {
    MotorState& m = motors[idx];

    // ── At rest: hold everything at zero. Coasting to a stop is both
    //    kinder to the drivers and safer than active braking; the slew
    //    limiter has already walked the setpoint down before we get here.
    if (fabsf(m.slewed_target) < 0.01f) {
        m.error               = 0.0f - m.actual_velocity;
        m.integral            = 0.0f;
        m.filtered_derivative = 0.0f;
        m.ff_output           = 0.0f;
        m.pid_output          = 0.0f;
        m.pwm_output          = 0;
        return;
    }

    // ── Feedforward — supplies the bulk of the PWM immediately ────────
    m.ff_output = feedforward(idx, m.slewed_target);

    // ── Proportional ──────────────────────────────────────────────────
    m.error      = m.slewed_target - m.actual_velocity;
    float p_term = Kp * m.error;

    // ── Derivative ON MEASUREMENT ─────────────────────────────────────
    //    d(error)/dt would spike every time the Pi steps the setpoint.
    //    -d(measurement)/dt gives identical damping with no kick.
    float raw_d = -(m.actual_velocity - m.prev_velocity) / PID_DT;
    m.filtered_derivative = D_FILTER_ALPHA * raw_d +
                            (1.0f - D_FILTER_ALPHA) * m.filtered_derivative;
    float d_term = Kd * m.filtered_derivative;

    // ── Integral, clamped to the authority actually left over ─────────
    //    This is the anti-windup. Everything except the I term is known
    //    at this point, so the exact PWM headroom is known too — and the
    //    integral is never allowed to accumulate past it. No windup is
    //    possible, and recovery from saturation is immediate rather than
    //    waiting for the accumulated error to bleed back off.
    float base = m.ff_output + p_term + d_term;
    float i_term = 0.0f;

    if (Ki > 1e-6f) {
        m.integral += m.error * PID_DT;

        float i_hi = ( (float)PWM_MAX - base) / Ki;
        float i_lo = (-(float)PWM_MAX - base) / Ki;
        if (i_lo > i_hi) { float t = i_lo; i_lo = i_hi; i_hi = t; }

        m.integral = constrain(m.integral, i_lo, i_hi);
        m.integral = constrain(m.integral, -INTEGRAL_ABS_MAX, INTEGRAL_ABS_MAX);
        i_term = Ki * m.integral;
    } else {
        m.integral = 0.0f;
    }

    m.pid_output = p_term + i_term + d_term;
    m.pwm_output = (int)constrain(roundf(base + i_term), -PWM_MAX, PWM_MAX);
}

// Walk slewed_target toward the commanded target at no more than
// max_wheel_accel. Called once per control tick, per motor. `target` is
// passed in rather than read from the struct so the whole four-wheel set
// can be snapshotted atomically against the serial parser on Core 0 —
// otherwise a <V> arriving mid-loop could be applied to two wheels this
// tick and two the next, which on a mecanum base is a momentary
// commanded twist that nobody asked for.
static inline void slewTarget(int idx, float target) {
    MotorState& m = motors[idx];

    if (max_wheel_accel <= 0.0f) {          // limiter disabled
        m.slewed_target = target;
        return;
    }
    float step = max_wheel_accel * PID_DT;
    float diff = target - m.slewed_target;

    if (diff >  step)      m.slewed_target += step;
    else if (diff < -step) m.slewed_target -= step;
    else                   m.slewed_target  = target;
}

// ═══════════════════════════════════════════════════════════════════
// 10. SAFETY TRIPS
//
//  The failure this exists for: a MOTOR_DIR_SIGN / ENC_DIR_SIGN mismatch
//  turns the loop into positive feedback. The motor spins the wrong way,
//  the controller reads that as a bigger error, pushes harder, and the
//  wheel ends up pinned at redline in the wrong direction until a
//  gearbox tooth or a driver FET gives out.
//
//  Detecting it needs care, because "PWM one way, wheel the other" is
//  also what a perfectly ordinary hard deceleration looks like. The
//  distinguishing feature is that under braking the wheel is SLOWING;
//  under runaway it is not. Hence the deceleration check — without it
//  this trips on every fast reversal.
// ═══════════════════════════════════════════════════════════════════

void latchEstop(EstopReason reason) {
    estop_active = true;
    estop_reason = reason;
    stopAllMotors();
}

void checkTrips() {
    if (!trips_enabled) return;
    unsigned long now = millis();
    float overspeed_limit = max_wheel_speed * OVERSPEED_FACTOR;

    for (int i = 0; i < NUM_MOTORS; i++) {
        MotorState& m = motors[i];
        float v  = m.actual_velocity;
        float av = fabsf(v);

        // Refresh the deceleration reference once per window.
        if (now - m.checkpoint_ms >= RUNAWAY_WINDOW_MS) {
            m.vel_checkpoint = av;
            m.checkpoint_ms  = now;
        }

        // ── Overspeed ─────────────────────────────────────────────────
        if (av > overspeed_limit) {
            if (m.overspeed_since_ms == 0) m.overspeed_since_ms = now;
            else if (now - m.overspeed_since_ms > OVERSPEED_TRIP_MS) {
                Serial.printf("[TRIP,OVERSPEED,%s,vel=%.2f,limit=%.2f]\n",
                              MOTOR_NAMES[i], v, overspeed_limit);
                latchEstop(ES_RUNAWAY);
                return;
            }
        } else {
            m.overspeed_since_ms = 0;
        }

        // ── Runaway: saturated, opposing, and not slowing down ────────
        bool saturated = abs(m.pwm_output) >= RUNAWAY_PWM_SAT;
        bool opposing  = (v * (float)m.pwm_output < 0.0f) && av > RUNAWAY_MIN_SPEED;
        bool not_decel = av >= m.vel_checkpoint - RUNAWAY_DECEL_TOL;

        if (saturated && opposing && not_decel) {
            if (m.runaway_since_ms == 0) m.runaway_since_ms = now;
            else if (now - m.runaway_since_ms > RUNAWAY_TRIP_MS) {
                Serial.printf("[TRIP,RUNAWAY,%s,pwm=%d,vel=%.2f]\n",
                              MOTOR_NAMES[i], m.pwm_output, v);
                Serial.println("[TRIP,CHECK MOTOR_DIR_SIGN vs ENC_DIR_SIGN — "
                               "they must match per motor]");
                latchEstop(ES_RUNAWAY);
                return;
            }
        } else {
            m.runaway_since_ms = 0;
        }

        // ── Stall ─────────────────────────────────────────────────────
        if (abs(m.pwm_output) >= STALL_PWM_THRESHOLD &&
            av < STALL_SPEED_THRESHOLD) {
            if (m.stall_since_ms == 0) m.stall_since_ms = now;
            else if (now - m.stall_since_ms > STALL_TRIP_MS) {
                Serial.printf("[TRIP,STALL,%s,pwm=%d,vel=%.3f]\n",
                              MOTOR_NAMES[i], m.pwm_output, v);
                latchEstop(ES_STALL);
                return;
            }
        } else {
            m.stall_since_ms = 0;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
// 11. ASYMMETRIC MECANUM INVERSE KINEMATICS
//
//     vx = forward (+)    vy = right strafe (+)    wz = CCW (+)
//
//     ωFR = (vx + vy + wz·K_OUTER) / R    outer pair: FR, RL
//     ωFL = (vx − vy − wz·K_INNER) / R    inner pair: FL, RR
//     ωRR = (vx − vy + wz·K_INNER) / R
//     ωRL = (vx + vy − wz·K_OUTER) / R
//
//  The Pi normally does its own IK and sends wheel velocities with <V>.
//  This is kept for <B>, so a twist can be sent straight through when
//  that is more convenient (e.g. a Nav2 cmd_vel passthrough).
// ═══════════════════════════════════════════════════════════════════

void mecanumIK(float vx, float vy, float wz, float* ws) {
    ws[FR] = ( vx + vy + wz * K_OUTER) / WHEEL_RADIUS;
    ws[FL] = ( vx - vy - wz * K_INNER) / WHEEL_RADIUS;
    ws[RR] = ( vx - vy + wz * K_INNER) / WHEEL_RADIUS;
    ws[RL] = ( vx + vy - wz * K_OUTER) / WHEEL_RADIUS;

    // Proportional scaling — preserves the commanded direction if any
    // one wheel would exceed the limit.
    float max_spd = 0.0f;
    for (int i = 0; i < NUM_MOTORS; i++) {
        if (fabsf(ws[i]) > max_spd) max_spd = fabsf(ws[i]);
    }
    if (max_spd > max_wheel_speed) {
        float scale = max_wheel_speed / max_spd;
        for (int i = 0; i < NUM_MOTORS; i++) ws[i] *= scale;
    }
}

// ═══════════════════════════════════════════════════════════════════
// 12. CORE 1 — PID TASK (100 Hz, hard real-time)
// ═══════════════════════════════════════════════════════════════════

void pidControlTask(void* /*param*/) {
    TickType_t       xLastWake = xTaskGetTickCount();
    const TickType_t xPeriod   = pdMS_TO_TICKS((int)PID_LOOP_INTERVAL_MS);

    while (true) {
        // ── 1. Read encoders, update velocity + accumulated position ──
        for (int i = 0; i < NUM_MOTORS; i++) {
            int32_t delta   = readEncoderDelta(i);
            float   rev     = (float)delta / ENCODER_CPR[i];
            float   raw_vel = rev * (2.0f * PI) / PID_DT;

            motors[i].prev_velocity = motors[i].actual_velocity;
            motors[i].raw_velocity  = raw_vel;
            motors[i].actual_velocity =
                VEL_FILTER_ALPHA * raw_vel +
                (1.0f - VEL_FILTER_ALPHA) * motors[i].actual_velocity;

            motors[i].position_rad += (double)rev * 2.0 * PI;
        }

        // ── 2. E-STOP / disabled guard ─────────────────────────────────
        if (estop_active || !motors_enabled) {
            for (int i = 0; i < NUM_MOTORS; i++) {
                motors[i].target_velocity = 0;
                motors[i].slewed_target   = 0;
                motors[i].integral        = 0;
                motors[i].pwm_output      = 0;
                setMotorOutput(i, 0);
            }
            vTaskDelayUntil(&xLastWake, xPeriod);
            continue;
        }

        // ── 3. Watchdog — a silent link means stop ─────────────────────
        bool wd_fired = watchdog_enabled &&
                        (millis() - last_cmd_ms > WATCHDOG_TIMEOUT_MS);
        if (wd_fired) {
            if (!watchdog_tripped) {
                watchdog_tripped = true;
                Serial.println("[WARN,WATCHDOG,no command — stopping]");
            }
            // Closed loop ramps down under the slew limiter; open loop has
            // no setpoint to ramp, so cut it.
            for (int i = 0; i < NUM_MOTORS; i++) motors[i].target_velocity = 0;
            if (manual_pwm_mode) {
                for (int i = 0; i < NUM_MOTORS; i++) motors[i].pwm_output = 0;
            }
        }

        // ── 4. Drive the outputs ───────────────────────────────────────
        if (manual_pwm_mode) {
            // Open loop: hold what <M> asked for. Encoders are still read
            // above, so telemetry and plant identification work normally.
            for (int i = 0; i < NUM_MOTORS; i++) {
                setMotorOutput(i, motors[i].pwm_output);
            }
        } else {
            // Snapshot the four targets together so a <V> landing mid-loop
            // cannot be applied to two wheels this tick and two the next —
            // on a mecanum base that split is a commanded twist nobody
            // asked for.
            float tgt[NUM_MOTORS];
            taskENTER_CRITICAL(&cmd_mux);
            for (int i = 0; i < NUM_MOTORS; i++) tgt[i] = motors[i].target_velocity;
            taskEXIT_CRITICAL(&cmd_mux);

            for (int i = 0; i < NUM_MOTORS; i++) {
                slewTarget(i, tgt[i]);
                computePID(i);
                setMotorOutput(i, motors[i].pwm_output);
            }
        }

        // ── 5. Safety trips ────────────────────────────────────────────
        checkTrips();

        vTaskDelayUntil(&xLastWake, xPeriod);
    }
}

// ═══════════════════════════════════════════════════════════════════
// 13. SERIAL COMMAND PARSER
//     All commands wrapped in < >   e.g.  <V,1.5,1.5,1.5,1.5>  or  <S>
// ═══════════════════════════════════════════════════════════════════

char serialBuffer[192];
int  serialBufIdx    = 0;
bool serialReceiving = false;

// Any velocity command leaves open-loop mode. The integral is dropped on
// the way back in — it was accumulated against a target of zero while
// <M> was driving, so it is meaningless now and would only kick.
void setTargets(const float* v) {
    taskENTER_CRITICAL(&cmd_mux);
    if (manual_pwm_mode) {
        manual_pwm_mode = false;
        for (int i = 0; i < NUM_MOTORS; i++) {
            motors[i].integral            = 0;
            motors[i].filtered_derivative = 0;
            motors[i].slewed_target       = 0;
        }
    }
    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].target_velocity = constrain(v[i], -max_wheel_speed, max_wheel_speed);
    }
    taskEXIT_CRITICAL(&cmd_mux);
}

void printHelp() {
    Serial.println("=== NarrowAisleBot ESP32 v3.0 — command set ===");
    Serial.println("MOTION");
    Serial.println("  <V,fr,fl,rr,rl>   wheel velocities rad/s (closed loop)  [primary]");
    Serial.println("  <B,vx,vy,wz>      body twist m/s,m/s,rad/s (ESP32 runs IK)");
    Serial.println("  <M,fr,fl,rr,rl>   direct PWM -255..255, open loop until the");
    Serial.println("                    next <V>/<B>/<T>. Send <W0> first for a");
    Serial.println("                    hold longer than the watchdog timeout.");
    Serial.println("  <T,idx,vel>       single motor velocity, idx 0=FR 1=FL 2=RR 3=RL");
    Serial.println("SAFETY");
    Serial.println("  <S>               E-STOP — LATCHES, clear with <E1>");
    Serial.println("  <E1> / <E0>       enable (+ clear E-STOP) / disable");
    Serial.println("  <W1> / <W0>       command watchdog on / off");
    Serial.println("  <Y1> / <Y0>       runaway + stall trips on / off");
    Serial.println("TUNING");
    Serial.println("  <G,kp,ki,kd>      PID gains");
    Serial.println("  <F,fr,fl,rr,rl>   Kff  — PWM per rad/s, per motor");
    Serial.println("  <K,fr,fl,rr,rl>   Kstat— static friction PWM, per motor");
    Serial.println("  <A,accel>         setpoint slew limit rad/s^2 (0 = off)");
    Serial.println("  <X,vmax>          max wheel speed rad/s");
    Serial.println("TELEMETRY");
    Serial.println("  <L0> <L1[,hz]> <L2[,hz]>  off / 13-col compat / extended");
    Serial.println("  <O>               accumulated wheel angle (rad), for odometry");
    Serial.println("  <R>               zero the accumulated wheel angles");
    Serial.println("  <P> <I> <?> <H>   ping / config / live state / this help");
}

void processSerialCommand(const char* cmd) {
    last_cmd_ms      = millis();
    watchdog_tripped = false;

    switch (cmd[0]) {

        case 'V': { // <V,fr,fl,rr,rl>  wheel velocities rad/s
            float v[4];
            if (sscanf(cmd, "V,%f,%f,%f,%f", &v[0],&v[1],&v[2],&v[3]) == 4) {
                setTargets(v);
            } else Serial.println("[ERR,BAD_V]");
            break;
        }

        case 'B': { // <B,vx,vy,wz>  body twist — ESP32 runs the IK
            float vx, vy, wz, ws[NUM_MOTORS];
            if (sscanf(cmd, "B,%f,%f,%f", &vx,&vy,&wz) == 3) {
                mecanumIK(vx, vy, wz, ws);
                setTargets(ws);
            } else Serial.println("[ERR,BAD_B]");
            break;
        }

        case 'M': { // <M,fr,fl,rr,rl>  direct PWM, open loop
            int p[4];
            if (sscanf(cmd, "M,%d,%d,%d,%d", &p[0],&p[1],&p[2],&p[3]) == 4) {
                taskENTER_CRITICAL(&cmd_mux);
                manual_pwm_mode = true;
                for (int i = 0; i < NUM_MOTORS; i++) {
                    motors[i].target_velocity = 0;
                    motors[i].slewed_target   = 0;
                    motors[i].integral        = 0;
                    motors[i].pwm_output      = constrain(p[i], -PWM_MAX, PWM_MAX);
                }
                taskEXIT_CRITICAL(&cmd_mux);
                Serial.printf("[OK,M,%d,%d,%d,%d]\n", p[0],p[1],p[2],p[3]);
            } else Serial.println("[ERR,BAD_M]");
            break;
        }

        case 'T': { // <T,idx,vel>  single motor, closed loop
            int idx; float vel;
            if (sscanf(cmd, "T,%d,%f", &idx, &vel) == 2 &&
                idx >= 0 && idx < NUM_MOTORS) {
                float v[NUM_MOTORS] = {0, 0, 0, 0};
                for (int i = 0; i < NUM_MOTORS; i++) v[i] = motors[i].target_velocity;
                v[idx] = vel;
                if (manual_pwm_mode) {
                    for (int i = 0; i < NUM_MOTORS; i++) if (i != idx) v[i] = 0;
                }
                setTargets(v);                     // also leaves open-loop mode
                Serial.printf("[OK,T,%d,%.2f]\n", idx, vel);
            } else Serial.println("[ERR,BAD_T]");
            break;
        }

        case 'S': // <S>  emergency stop — LATCHES, clear with <E1>
            latchEstop(ES_COMMAND);
            Serial.println("[OK,ESTOP_LATCHED]");
            break;

        case 'E': // <E1> enable + clear E-STOP / <E0> disable
            if (cmd[1] == '1') {
                motors_enabled = true;
                estop_active   = false;
                estop_reason   = ES_NONE;
                for (int i = 0; i < NUM_MOTORS; i++) {
                    motors[i].overspeed_since_ms = 0;
                    motors[i].runaway_since_ms   = 0;
                    motors[i].stall_since_ms     = 0;
                }
                Serial.println("[OK,ENABLED]");
            } else {
                motors_enabled = false;
                stopAllMotors();
                Serial.println("[OK,DISABLED]");
            }
            break;

        case 'W': // <W1>/<W0>  command watchdog
            watchdog_enabled = (cmd[1] == '1');
            Serial.printf("[OK,WDOG=%d]\n", watchdog_enabled);
            break;

        case 'Y': // <Y1>/<Y0>  runaway + stall trips
            trips_enabled = (cmd[1] == '1');
            Serial.printf("[OK,TRIPS=%d]\n", trips_enabled);
            break;

        case 'G': { // <G,Kp,Ki,Kd>
            float kp,ki,kd;
            if (sscanf(cmd, "G,%f,%f,%f", &kp,&ki,&kd) == 3) {
                Kp=kp; Ki=ki; Kd=kd;
                // Bumpless-ish: a stale integral scaled by a new Ki is
                // meaningless, so drop it rather than let it kick.
                for (int i = 0; i < NUM_MOTORS; i++) motors[i].integral = 0;
                Serial.printf("[OK,GAINS,%.2f,%.2f,%.2f]\n", Kp,Ki,Kd);
            } else Serial.println("[ERR,BAD_G]");
            break;
        }

        case 'F': { // <F,fr,fl,rr,rl>  feedforward slope
            float f[4];
            if (sscanf(cmd, "F,%f,%f,%f,%f", &f[0],&f[1],&f[2],&f[3]) == 4) {
                for (int i = 0; i < NUM_MOTORS; i++) Kff[i] = f[i];
                Serial.printf("[OK,FF,%.2f,%.2f,%.2f,%.2f]\n", f[0],f[1],f[2],f[3]);
            } else Serial.println("[ERR,BAD_F]");
            break;
        }

        case 'K': { // <K,fr,fl,rr,rl>  static friction feedforward
            float k[4];
            if (sscanf(cmd, "K,%f,%f,%f,%f", &k[0],&k[1],&k[2],&k[3]) == 4) {
                for (int i = 0; i < NUM_MOTORS; i++) Kstat[i] = k[i];
                Serial.printf("[OK,KSTAT,%.2f,%.2f,%.2f,%.2f]\n", k[0],k[1],k[2],k[3]);
            } else Serial.println("[ERR,BAD_K]");
            break;
        }

        case 'A': { // <A,accel>  setpoint slew limit, 0 = off
            float a;
            if (sscanf(cmd, "A,%f", &a) == 1 && a >= 0.0f) {
                max_wheel_accel = a;
                Serial.printf("[OK,ACCEL=%.2f]\n", max_wheel_accel);
            } else Serial.println("[ERR,BAD_A]");
            break;
        }

        case 'X': { // <X,vmax>  wheel speed clamp
            float v;
            if (sscanf(cmd, "X,%f", &v) == 1 && v > 0.0f && v <= 6.28f) {
                max_wheel_speed = v;
                Serial.printf("[OK,VMAX=%.2f]\n", max_wheel_speed);
            } else Serial.println("[ERR,BAD_X]");
            break;
        }

        case 'L': { // <L0> / <L1[,hz]> / <L2[,hz]>  telemetry mode + rate
            telemetry_mode = (cmd[1] >= '0' && cmd[1] <= '2') ? (cmd[1] - '0') : 0;
            float hz;
            if (sscanf(cmd + 1, "%*d,%f", &hz) == 1 && hz > 0.0f) {
                unsigned long iv = (unsigned long)(1000.0f / hz + 0.5f);
                if (iv < TELEMETRY_MIN_INTERVAL_MS) iv = TELEMETRY_MIN_INTERVAL_MS;
                telemetry_interval_ms = iv;
            }
            Serial.printf("[OK,LOG=%d,HZ=%.1f]\n",
                          telemetry_mode, 1000.0f / (float)telemetry_interval_ms);
            break;
        }

        case 'O': // <O>  accumulated wheel angle, rad
            Serial.printf("[ODOM,%.4f,%.4f,%.4f,%.4f]\n",
                          motors[FR].position_rad, motors[FL].position_rad,
                          motors[RR].position_rad, motors[RL].position_rad);
            break;

        case 'R': // <R>  zero accumulated angles
            for (int i = 0; i < NUM_MOTORS; i++) motors[i].position_rad = 0.0;
            Serial.println("[OK,ODOM_ZEROED]");
            break;

        case 'P': // <P>  ping
            Serial.println("[PONG]");
            break;

        case 'I': // <I>  configuration dump
            Serial.println("[INFO,NarrowAisleBot_ESP32_v3.0]");
            Serial.printf("[GAINS,Kp=%.2f,Ki=%.2f,Kd=%.2f,Hz=%.0f]\n",
                          Kp, Ki, Kd, PID_LOOP_HZ);
            Serial.printf("[FF,FR=%.2f,FL=%.2f,RR=%.2f,RL=%.2f]\n",
                          Kff[FR],Kff[FL],Kff[RR],Kff[RL]);
            Serial.printf("[KSTAT,FR=%.2f,FL=%.2f,RR=%.2f,RL=%.2f]\n",
                          Kstat[FR],Kstat[FL],Kstat[RR],Kstat[RL]);
            Serial.printf("[CPR,FR=%.0f,FL=%.0f,RR=%.0f,RL=%.0f]\n",
                          ENCODER_CPR[FR],ENCODER_CPR[FL],
                          ENCODER_CPR[RR],ENCODER_CPR[RL]);
            Serial.printf("[GEOM,R=%.4f,K_OUT=%.5f,K_INN=%.5f]\n",
                          WHEEL_RADIUS, K_OUTER, K_INNER);
            Serial.printf("[LIMITS,Vmax=%.2f,Accel=%.2f,Vlin=%.2f]\n",
                          max_wheel_speed, max_wheel_accel,
                          max_wheel_speed * WHEEL_RADIUS);
            break;

        case '?': { // <?>  live state
            const char* r = "NONE";
            if (estop_reason == ES_COMMAND) r = "COMMAND";
            else if (estop_reason == ES_RUNAWAY) r = "RUNAWAY";
            else if (estop_reason == ES_STALL)   r = "STALL";
            Serial.printf("[STATE,EN=%d,WD=%d,TRIPS=%d,ESTOP=%d,WHY=%s,MODE=%s]\n",
                          motors_enabled, watchdog_enabled,
                          trips_enabled, estop_active, r,
                          manual_pwm_mode ? "OPENLOOP" : "PID");
            for (int i = 0; i < NUM_MOTORS; i++) {
                Serial.printf("[%s,tgt=%.2f,slew=%.2f,act=%.2f,pwm=%d,err=%+.3f,i=%+.3f]\n",
                    MOTOR_NAMES[i],
                    motors[i].target_velocity, motors[i].slewed_target,
                    motors[i].actual_velocity, motors[i].pwm_output,
                    motors[i].error, motors[i].integral);
            }
            break;
        }

        case 'H': // <H>  help
            printHelp();
            break;

        default:
            Serial.printf("[ERR,UNKNOWN:%c]\n", cmd[0]);
            break;
    }
}

void handleSerialInput() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '<') {
            serialReceiving = true;
            serialBufIdx    = 0;
        } else if (c == '>' && serialReceiving) {
            serialReceiving            = false;
            serialBuffer[serialBufIdx] = '\0';
            processSerialCommand(serialBuffer);
        } else if (serialReceiving) {
            if (serialBufIdx < (int)sizeof(serialBuffer) - 1) {
                serialBuffer[serialBufIdx++] = c;
            } else {
                serialReceiving = false;   // overlong frame — drop it
                serialBufIdx    = 0;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
// 14. SERIAL TELEMETRY
//
//  <L1> — 13 columns, byte-identical to v2.0:
//     ms, FR_tgt,FR_act,FR_pwm, FL_…, RR_…, RL_…
//     Parsed by esp32_bridge.py (fixed indices 2/5/8/11) and by
//     aislebot_pid_analysis_v2.py.
//
//  <L2> — those same 13 columns, then 4 more per motor:
//     err, ff, i_term, position_rad
//     Anything indexing the first 13 keeps working untouched; the extra
//     columns are what actually let a log be tuned from rather than just
//     plotted. tools/nab_pid_logger.py writes them with a header.
// ═══════════════════════════════════════════════════════════════════

void outputSerialTelemetry() {
    if (telemetry_mode == 0) return;

    Serial.printf("%lu", millis());
    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.printf(",%.3f,%.3f,%d",
                      motors[i].slewed_target,
                      motors[i].actual_velocity,
                      motors[i].pwm_output);
    }
    if (telemetry_mode >= 2) {
        for (int i = 0; i < NUM_MOTORS; i++) {
            Serial.printf(",%.3f,%.1f,%.1f,%.3f",
                          motors[i].error,
                          motors[i].ff_output,
                          Ki * motors[i].integral,
                          (float)motors[i].position_rad);
        }
    }
    Serial.println();
}

// ═══════════════════════════════════════════════════════════════════
// 15. CORE 0 — COMMUNICATION TASK
// ═══════════════════════════════════════════════════════════════════

void communicationTask(void* /*param*/) {
    unsigned long lastTelMs = 0;
    while (true) {
        handleSerialInput();

        if (millis() - lastTelMs >= telemetry_interval_ms) {
            lastTelMs = millis();
            outputSerialTelemetry();
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ═══════════════════════════════════════════════════════════════════
// 16. SETUP & MAIN LOOP
// ═══════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(300);

    Serial.println();
    Serial.println("╔════════════════════════════════════════════╗");
    Serial.println("║  NarrowAisleBot ESP32 v3.0  —  Starting... ║");
    Serial.println("╚════════════════════════════════════════════╝");

    memset(motors, 0, sizeof(motors));

    Serial.print("  Motor pins    ... ");
    setupMotorPins();
    Serial.println("OK");

    Serial.print("  PCNT encoders ... ");
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);
    Serial.println("OK  (front 186264 CPR, rear 93132 CPR)");

    Serial.print("  Core 0 task   ... ");
    xTaskCreatePinnedToCore(communicationTask, "Comms", 4096, NULL, 1, NULL, 0);
    Serial.println("OK  (serial + telemetry)");

    Serial.print("  Core 1 task   ... ");
    xTaskCreatePinnedToCore(pidControlTask, "PID", 4096, NULL, 3, NULL, 1);
    Serial.printf("OK  (PID @ %.0f Hz)\n", PID_LOOP_HZ);

    last_cmd_ms = millis();   // don't trip the watchdog before the Pi speaks

    Serial.println();
    Serial.printf("  PID     : Kp=%.1f  Ki=%.1f  Kd=%.2f  @ %.0f Hz\n",
                  Kp, Ki, Kd, PID_LOOP_HZ);
    Serial.printf("  Kff     : FR=%.1f  FL=%.1f  RR=%.1f  RL=%.1f  PWM/(rad/s)\n",
                  Kff[FR], Kff[FL], Kff[RR], Kff[RL]);
    Serial.printf("  Kstat   : FR=%.1f  FL=%.1f  RR=%.1f  RL=%.1f  PWM\n",
                  Kstat[FR], Kstat[FL], Kstat[RR], Kstat[RL]);
    Serial.printf("  Limits  : v_wheel=%.2f rad/s  accel=%.1f rad/s^2  v_lin=%.2f m/s\n",
                  max_wheel_speed, max_wheel_accel,
                  max_wheel_speed * WHEEL_RADIUS);
    Serial.println();
    Serial.println("  Command source : USB serial from the Pi. No WiFi in v3.0.");
    Serial.println("  E-STOP         : <S> latches. Clear with <E1>.");
    Serial.println("  Telemetry      : <L1> compat 13-col, <L2> extended.");
    Serial.println("  Calibration    : gains are AIR values — see docs/PID_Calibration.md");
    Serial.println();
    Serial.println("[READY]");
}

void loop() {
    // All work happens in the two pinned FreeRTOS tasks.
    vTaskDelay(pdMS_TO_TICKS(1000));
}
