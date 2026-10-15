/*
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║            NarrowAisleBot — ESP32 Motor Controller  v3.1          ║
 * ║                                                                  ║
 * ║  Pi-commanded  |  PID + 2-term Feedforward  |  Hardware PCNT     ║
 * ║  Per-motor CPR |  100 Hz control loop       |  Dual-core FreeRTOS║
 * ║  BNO055 IMU on its own core-0 task (IMUPLUS, 100 Hz)             ║
 * ║                                                                  ║
 * ║  Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar       ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * WHAT CHANGED FROM v3.0  (and why)
 *
 *   The PID, feedforward, filters, limits and trips are untouched. Every
 *   tuned number below is the v3.0 number.
 *
 *   1. BNO055 IMU added (§6b, §14b). It runs in its own task on core 0,
 *      so an I2C stall can never delay the PID task on core 1 or the
 *      serial parser. IMUPLUS mode only (accel + gyro, no magnetometer:
 *      a 30 A motor bus sits next to it). Reads one checked 32-byte burst
 *      every 10 ms, recovers a hung bus by itself (bus clear, then reset
 *      on GPIO27, then a full re-init), and streams
 *          [IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az,t_us
 *      only when asked with <N1[,hz]>. Status lines start [IMUS, and are
 *      kept to 8 comma fields or fewer, because esp32_bridge.py treats
 *      any 9-or-more-field line it doesn't recognise as wheel speeds.
 *      docs/BNO055_Integration_Research.md has the reasoning.
 *
 *   2. Only motion commands (<V> <B> <M> <T>) feed the command watchdog.
 *      In v3.0 any command did, including <?>, <P> and the bridge's
 *      periodic <L1>. A link that kept sending housekeeping commands but
 *      no motion would have held the last <V> past the 750 ms stop.
 *
 *   3. Every line now goes out in ONE Serial.write. The 13-column
 *      telemetry line was six separate writes (ten with <L2>), so a
 *      [TRIP] or [WARN] line printed from the PID task on core 1 could
 *      land in the middle of it. Byte format is unchanged.
 *
 *   4. A 1 KB serial TX buffer. v3.0 had none, so any print from the PID
 *      task could block the 100 Hz loop until the 128-byte UART FIFO
 *      drained. That matters more now that IMU lines share the link.
 *
 *   5. <R> is applied by the PID task. In v3.0 core 0 wrote position_rad
 *      while core 1 was doing += on it, so a reset could be lost.
 *
 *   6. The IK comment said vy is a right strafe. The math, and
 *      mecanum_teleop_asymmetric.py, use REP-103: vy is LEFT-positive.
 *      Comment only.
 *
 *   Known and left alone: readEncoderDelta() reads then clears the
 *   PCNT counter, so edges landing between the two calls are dropped.
 *   That window is about a microsecond, roughly 0.02 % of counts at top
 *   speed, and fixing it needs PCNT overflow handling.
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
 *   Upload Speed: 921600 | Arduino-ESP32 core 3.2 or newer
 *   (3.2 is the first core whose I2C driver waits long enough for the
 *   BNO055's clock stretching. Pin the exact version you flash with.)
 *
 * LIBRARIES: none beyond the ESP32 core. Wire is part of the core. The
 *            BNO055 is driven by direct register access, not a library.
 */

#include "driver/pcnt.h"
#include <Wire.h>

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

// BNO055 IMU — I2C on the pair reserved for it since Master_Reference v4.0.
// Never call Wire.begin() without pins: its defaults are 21/22, which are
// RR DIR and RL PWM on this robot.
#define IMU_SDA_PIN 14  // G14 → BNO055 SDA
#define IMU_SCL_PIN 13  // G13 → BNO055 SCL
#define IMU_RST_PIN 27  // G27 → BNO055 RST, open-drain. -1 if not wired.

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

// <R> only raises this flag. The PID task, which is the one doing
// position_rad += ..., does the zeroing, so the reset can't be lost to a
// read-modify-write racing on the other core.
volatile bool odom_reset_req = false;

// ═══════════════════════════════════════════════════════════════════
// 6b. BNO055 IMU — configuration, registers, shared state
//
//  Everything here is declared before the first function on purpose: the
//  Arduino builder generates prototypes above the first function, and a
//  prototype that names ImuSample before ImuSample exists won't compile.
//
//  Register map and scale factors are from Bosch's BNO055_driver
//  (bno055.h). The datasheet PDF itself couldn't be opened when this was
//  written; see docs/BNO055_Integration_Research.md for what is checked.
// ═══════════════════════════════════════════════════════════════════

#define IMU_ENABLED 1        // 0 compiles the IMU out entirely

const uint8_t       IMU_I2C_ADDR       = 0x28;     // ADR/COM3 low. 0x29 if high.
const uint32_t      IMU_I2C_HZ         = 100000;   // 100 kHz: the board's 10 k pull-ups
                                                   // are out of spec at 400 kHz
const uint16_t      IMU_I2C_TIMEOUT_MS = 10;       // one failed read costs one period
const unsigned long IMU_PERIOD_MS      = 10;       // 100 Hz, the chip's fusion rate
const uint8_t       IMU_FAILS_BEFORE_RECOVERY = 5; // consecutive bad reads → bus clear + re-init
const unsigned long IMU_RETRY_MS       = 5000;     // retry interval while not found
const uint16_t      IMU_HOUSEKEEP_EVERY = 100;     // status registers once a second

// Axis remap. 0x24 / 0x00 is the chip's default placement (P1). Mount the
// board flat, component side up, silkscreen X to the robot's right and Y
// to the nose, and the sensor frame equals base_link (+X right, +Y
// forward, +Z up) with no remap and rpy 0 0 0 on imu_joint. Prove it with
// the sign checks before trusting it: spin CCW seen from above → gz > 0.
const uint8_t IMU_AXIS_MAP_CONFIG = 0x24;
const uint8_t IMU_AXIS_MAP_SIGN   = 0x00;

// 1 only if the breakout has the 32.768 kHz crystal (Adafruit boards do,
// many clones don't). Gyro rates don't depend on it; the fused quaternion's
// timebase does.
#define IMU_USE_EXT_CRYSTAL 0

// Fusion mode. IMUPLUS (0x08): accel + gyro, heading relative to power-on.
// NDOF (0x0C) would add the magnetometer, which this chassis can't support.
const uint8_t IMU_OPR_MODE = 0x08;

// Page-0 registers (bno055.h)
const uint8_t BNO_CHIP_ID         = 0x00;   // reads 0xA0
const uint8_t BNO_SW_REV_LSB      = 0x04;
const uint8_t BNO_PAGE_ID         = 0x07;
const uint8_t BNO_ACC_DATA        = 0x08;   // start of the 32-byte burst
const uint8_t BNO_TEMP            = 0x34;   // start of the 7-byte housekeeping read
const uint8_t BNO_UNIT_SEL        = 0x3B;
const uint8_t BNO_OPR_MODE        = 0x3D;
const uint8_t BNO_PWR_MODE        = 0x3E;
const uint8_t BNO_SYS_TRIGGER     = 0x3F;
const uint8_t BNO_AXIS_MAP_CONFIG = 0x41;
const uint8_t BNO_AXIS_MAP_SIGN   = 0x42;

const uint8_t BNO_CHIP_ID_VALUE   = 0xA0;
const uint8_t BNO_MODE_CONFIG     = 0x00;
const uint8_t BNO_SYS_STATUS_ERROR = 0x01;

// UNIT_SEL = 0x06: accel m/s², gyro rad/s, Euler rad, temp °C. Written
// explicitly at init rather than trusting the power-on default.
const uint8_t BNO_UNIT_SEL_VALUE  = 0x06;

// Scale factors for those units (bno055.h)
const float IMU_ACC_LSB_PER_MS2   = 100.0f;
const float IMU_GYR_LSB_PER_RADS  = 900.0f;
const float IMU_QUA_LSB           = 16384.0f;   // 2^14

// One burst, 0x08..0x27: accel(6) mag(6, zero in IMUPLUS) gyro(6)
// Euler(6, unused) quaternion(8). One transaction gives one coherent
// sample, one clock-stretch window and one return code to check.
const uint8_t IMU_BURST_LEN       = 32;
const uint8_t IMU_OFF_ACC         = 0;
const uint8_t IMU_OFF_GYR         = 12;
const uint8_t IMU_OFF_QUA         = 24;

// A quaternion from a working fusion engine has |q|² = 1. Anything far off
// (including all zeros from a chip that isn't fusing) is never published.
const float IMU_QNORM2_MIN        = 0.81f;
const float IMU_QNORM2_MAX        = 1.21f;

enum ImuState : uint8_t { IMU_OFF = 0, IMU_INIT, IMU_RUN, IMU_DEAD };

struct ImuSample {
    uint32_t seq;        // bumps on every published sample; 0 = none yet
    uint32_t t_us;       // ESP32 micros() right after the burst
    float    q[4];       // w, x, y, z
    float    g[3];       // rad/s
    float    a[3];       // m/s², gravity included (what REP-145 expects)
};

// Written only by the IMU task, read by the comms task for printing. The
// fields are aligned 8/32-bit words, so reads are never torn. They aren't
// volatile because C++20 deprecates ++ on volatile and the core builds
// sketches as C++23; state is the only field another task polls in a loop.
struct ImuHealth {
    volatile ImuState state;
    uint8_t  calib;        // CALIB_STAT: sys 7-6, gyr 5-4, acc 3-2, mag 1-0
    uint8_t  sys_status;   // 5 = fusion running
    uint8_t  sys_err;
    int8_t   temp_c;
    uint8_t  sw_rev_msb;
    uint8_t  sw_rev_lsb;
    uint32_t samples;
    uint32_t i2c_errors;
    uint32_t bad_samples;  // failed the quaternion check
    uint32_t dup_samples;  // chip hadn't updated since the last read
    uint32_t reinits;
};

// Loop state of the IMU task, kept in a struct so one iteration can be
// called on its own (the host checks in tools/tests/ do exactly that).
struct ImuLoop {
    uint8_t    prev[IMU_BURST_LEN];
    bool       have_prev;
    uint8_t    fails;
    uint32_t   tick;
    bool       reported_dead;
    TickType_t last_wake;
};

ImuHealth    imu_health = {};
ImuSample    imu_latest = {};                    // guarded by imu_mux
portMUX_TYPE imu_mux    = portMUX_INITIALIZER_UNLOCKED;

volatile bool          imu_stream_on          = false;  // <N1> / <N0>
volatile unsigned long imu_stream_interval_ms = 20;     // 50 Hz unless <N1,hz> says otherwise
volatile bool          imu_reinit_req         = false;  // <NR>

// Defined in §14b, called from the parser in §13. Declared here so the
// file also builds outside the Arduino IDE's prototype generator.
void imuPrintStatus();

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
//     vx = forward (+)    vy = LEFT strafe (+)    wz = CCW (+)
//     (REP-103, the same convention and the same four equations as
//      mecanum_teleop_asymmetric.py. v3.0's comment said "right"; the
//      math never did.)
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
        // ── 0. <R> requested on core 0, applied here where += happens ──
        if (odom_reset_req) {
            for (int i = 0; i < NUM_MOTORS; i++) motors[i].position_rad = 0.0;
            odom_reset_req = false;
        }

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

// Only a well-formed motion command proves the link is alive for driving.
// Housekeeping (<?>, <P>, <L1>, <N1> ...) deliberately does not count, so
// the 750 ms stop still fires if the Pi keeps talking but stops steering.
static inline void feedWatchdog() {
    last_cmd_ms      = millis();
    watchdog_tripped = false;
}

void printHelp() {
    Serial.println("=== NarrowAisleBot ESP32 v3.1 — command set ===");
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
    Serial.println("IMU (BNO055)");
    Serial.println("  <N1[,hz]> <N0>    [IMU] stream on (default 50 Hz) / off");
    Serial.println("  <N?>              IMU status: state  calibration  errors");
    Serial.println("  <NR>              force an IMU reset and re-init");
    Serial.println("  Only <V> <B> <M> <T> feed the 750 ms command watchdog.");
}

void processSerialCommand(const char* cmd) {
    switch (cmd[0]) {

        case 'V': { // <V,fr,fl,rr,rl>  wheel velocities rad/s
            float v[4];
            if (sscanf(cmd, "V,%f,%f,%f,%f", &v[0],&v[1],&v[2],&v[3]) == 4) {
                feedWatchdog();
                setTargets(v);
            } else Serial.println("[ERR,BAD_V]");
            break;
        }

        case 'B': { // <B,vx,vy,wz>  body twist — ESP32 runs the IK
            float vx, vy, wz, ws[NUM_MOTORS];
            if (sscanf(cmd, "B,%f,%f,%f", &vx,&vy,&wz) == 3) {
                feedWatchdog();
                mecanumIK(vx, vy, wz, ws);
                setTargets(ws);
            } else Serial.println("[ERR,BAD_B]");
            break;
        }

        case 'M': { // <M,fr,fl,rr,rl>  direct PWM, open loop
            int p[4];
            if (sscanf(cmd, "M,%d,%d,%d,%d", &p[0],&p[1],&p[2],&p[3]) == 4) {
                feedWatchdog();
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
                feedWatchdog();
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

        case 'R': // <R>  zero accumulated angles (applied by the PID task)
            odom_reset_req = true;
            Serial.println("[OK,ODOM_ZEROED]");
            break;

        case 'N': // <N1[,hz]> / <N0> / <N?> / <NR>  IMU stream and status
#if IMU_ENABLED
            if (cmd[1] == '1') {
                float hz;
                if (sscanf(cmd + 1, "%*d,%f", &hz) == 1 && hz > 0.0f) {
                    unsigned long iv = (unsigned long)(1000.0f / hz + 0.5f);
                    if (iv < IMU_PERIOD_MS) iv = IMU_PERIOD_MS;   // no faster than the chip
                    if (iv > 1000)          iv = 1000;
                    imu_stream_interval_ms = iv;
                }
                imu_stream_on = true;
                Serial.printf("[OK,IMU_STREAM=1,HZ=%.1f]\n",
                              1000.0f / (float)imu_stream_interval_ms);
            } else if (cmd[1] == '0') {
                imu_stream_on = false;
                Serial.println("[OK,IMU_STREAM=0]");
            } else if (cmd[1] == '?') {
                imuPrintStatus();
            } else if (cmd[1] == 'R') {
                imu_reinit_req = true;
                Serial.println("[OK,IMU_REINIT]");
            } else {
                Serial.println("[ERR,BAD_N]");
            }
#else
            Serial.println("[ERR,IMU_DISABLED]");
#endif
            break;

        case 'P': // <P>  ping
            Serial.println("[PONG]");
            break;

        case 'I': // <I>  configuration dump
            Serial.println("[INFO,NarrowAisleBot_ESP32_v3.1]");
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
#if IMU_ENABLED
            Serial.printf("[IMUCFG,addr=0x%02X,mode=0x%02X,axis=0x%02X/0x%02X,xtal=%d,rst=%d]\n",
                          (unsigned)IMU_I2C_ADDR, (unsigned)IMU_OPR_MODE,
                          (unsigned)IMU_AXIS_MAP_CONFIG, (unsigned)IMU_AXIS_MAP_SIGN,
                          (int)IMU_USE_EXT_CRYSTAL, (int)IMU_RST_PIN);
#endif
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
#if IMU_ENABLED
            imuPrintStatus();
#endif
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

// Append to a line buffer without ever running past its end. Returns the
// new length; on overflow the line is left as it was, and the caller's
// length check drops it rather than sending a truncated line.
static size_t lineAppend(char* buf, size_t cap, size_t len, const char* fmt, ...) {
    if (len >= cap) return cap;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf + len, cap - len, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t)n >= cap - len) return cap;
    return len + (size_t)n;
}

// Same bytes as v3.0 (including the "\r\n" Serial.println used to add),
// but built in one buffer and sent with one write, so a [TRIP] or [WARN]
// printed from core 1 can no longer land in the middle of the line.
void outputSerialTelemetry() {
    if (telemetry_mode == 0) return;

    char   line[320];
    size_t n = lineAppend(line, sizeof(line), 0, "%lu", millis());
    for (int i = 0; i < NUM_MOTORS; i++) {
        n = lineAppend(line, sizeof(line), n, ",%.3f,%.3f,%d",
                       motors[i].slewed_target,
                       motors[i].actual_velocity,
                       motors[i].pwm_output);
    }
    if (telemetry_mode >= 2) {
        for (int i = 0; i < NUM_MOTORS; i++) {
            n = lineAppend(line, sizeof(line), n, ",%.3f,%.1f,%.1f,%.3f",
                           motors[i].error,
                           motors[i].ff_output,
                           Ki * motors[i].integral,
                           (float)motors[i].position_rad);
        }
    }
    n = lineAppend(line, sizeof(line), n, "\r\n");
    if (n < sizeof(line)) Serial.write((const uint8_t*)line, n);
}

// ═══════════════════════════════════════════════════════════════════
// 14b. BNO055 IMU — driver and task (core 0, priority 2, 100 Hz)
//
//  Direct register access, no library. The Adafruit library returns
//  silent zeros on a failed read and can loop forever in begin() if the
//  chip stops answering; neither is acceptable in the drive firmware.
//  Every transaction here has a bound and a checked return.
//
//  Recovery ladder, all on core 0 so the wheel loop never waits on it:
//    one bad read         → counted, skipped
//    5 in a row           → bus clear (9 clocks + STOP), reset, re-init
//    re-init fails        → [IMUS,NOT_FOUND], retry every 5 s
//    SYS_STATUS = error   → re-init
//  A re-init re-zeroes the IMUPLUS heading. The Pi fuses yaw RATE, which
//  rides through that without a step.
// ═══════════════════════════════════════════════════════════════════

#if IMU_ENABLED

static inline int16_t le16(const uint8_t* p) {
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

bool imuWriteReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(IMU_I2C_ADDR);
    Wire.write(reg);
    Wire.write(val);
    return Wire.endTransmission(true) == 0;
}

bool imuReadRegs(uint8_t reg, uint8_t* buf, uint8_t len) {
    Wire.beginTransmission(IMU_I2C_ADDR);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;      // repeated start
    if (Wire.requestFrom((int)IMU_I2C_ADDR, (int)len) != (int)len) {
        while (Wire.available()) Wire.read();
        return false;
    }
    for (uint8_t i = 0; i < len; i++) buf[i] = (uint8_t)Wire.read();
    return true;
}

// Write, read back, compare the bits that register actually implements.
// The chip silently ignores most writes outside CONFIG mode, so a write
// that "succeeded" on the bus proves nothing on its own.
bool imuWriteVerify(uint8_t reg, uint8_t val, uint8_t mask) {
    if (!imuWriteReg(reg, val)) return false;
    vTaskDelay(pdMS_TO_TICKS(2));
    uint8_t rb = 0;
    if (!imuReadRegs(reg, &rb, 1)) return false;
    return (rb & mask) == (val & mask);
}

bool imuWaitChipId(unsigned long timeout_ms) {
    unsigned long t0 = millis();
    while (millis() - t0 < timeout_ms) {
        uint8_t id = 0;
        if (imuReadRegs(BNO_CHIP_ID, &id, 1) && id == BNO_CHIP_ID_VALUE) return true;
        vTaskDelay(pdMS_TO_TICKS(20));
    }
    return false;
}

// A slave that lost sync mid-byte can hold SDA low forever. Clock it out
// (up to 9 pulses), then put a STOP on the bus, then hand the pins back.
void imuBusClear() {
    Wire.end();
    pinMode(IMU_SDA_PIN, INPUT_PULLUP);
    pinMode(IMU_SCL_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(IMU_SCL_PIN, HIGH);
    delayMicroseconds(10);
    for (int i = 0; i < 9 && digitalRead(IMU_SDA_PIN) == LOW; i++) {
        digitalWrite(IMU_SCL_PIN, LOW);  delayMicroseconds(10);
        digitalWrite(IMU_SCL_PIN, HIGH); delayMicroseconds(10);
    }
    pinMode(IMU_SDA_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(IMU_SDA_PIN, LOW);  delayMicroseconds(10);   // STOP:
    digitalWrite(IMU_SCL_PIN, HIGH); delayMicroseconds(10);   // SDA rises
    digitalWrite(IMU_SDA_PIN, HIGH); delayMicroseconds(10);   // while SCL high
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN, IMU_I2C_HZ);
    Wire.setTimeOut(IMU_I2C_TIMEOUT_MS);
}

// Bounded init, roughly 2 s end to end. Returns false rather than waiting
// forever if the chip doesn't answer.
bool imuInit() {
    // Hardware reset if RST is wired. Then a software reset as well, which
    // also covers a board whose RST isn't connected and an ESP32-only reset
    // (a brownout can reboot the ESP32 and leave the BNO055 running).
    if (IMU_RST_PIN >= 0) {
        digitalWrite(IMU_RST_PIN, LOW);
        vTaskDelay(pdMS_TO_TICKS(10));
        digitalWrite(IMU_RST_PIN, HIGH);                     // released
        vTaskDelay(pdMS_TO_TICKS(650));                      // POR to CONFIG
    }
    if (!imuWaitChipId(1000)) return false;

    imuWriteReg(BNO_OPR_MODE, BNO_MODE_CONFIG);
    vTaskDelay(pdMS_TO_TICKS(25));
    imuWriteReg(BNO_SYS_TRIGGER, 0x20);         // RST_SYS. The ACK may be lost
    vTaskDelay(pdMS_TO_TICKS(650));             // to the reset itself, so the
    if (!imuWaitChipId(1000)) return false;     // chip ID is the real check.
    vTaskDelay(pdMS_TO_TICKS(50));

    if (!imuWriteReg(BNO_PWR_MODE, 0x00)) return false;      // normal power
    vTaskDelay(pdMS_TO_TICKS(10));
    if (!imuWriteReg(BNO_PAGE_ID, 0x00)) return false;
    if (!imuWriteVerify(BNO_UNIT_SEL, BNO_UNIT_SEL_VALUE, 0x97)) return false;
    if (!imuWriteVerify(BNO_AXIS_MAP_CONFIG, IMU_AXIS_MAP_CONFIG, 0x3F)) return false;
    if (!imuWriteVerify(BNO_AXIS_MAP_SIGN, IMU_AXIS_MAP_SIGN, 0x07)) return false;
    imuWriteReg(BNO_SYS_TRIGGER, IMU_USE_EXT_CRYSTAL ? 0x80 : 0x00);
    vTaskDelay(pdMS_TO_TICKS(10));

    if (!imuWriteVerify(BNO_OPR_MODE, IMU_OPR_MODE, 0x0F)) return false;
    // Bosch's own driver waits 600 ms after entering a fusion mode; the
    // datasheet's 7 ms covers only the chip's MCU. Output inside this
    // window isn't trusted, so the task doesn't read it.
    vTaskDelay(pdMS_TO_TICKS(600));

    uint8_t rev[2] = {0, 0};
    if (imuReadRegs(BNO_SW_REV_LSB, rev, 2)) {
        imu_health.sw_rev_lsb = rev[0];
        imu_health.sw_rev_msb = rev[1];
    }
    uint8_t hk[7];
    if (imuReadRegs(BNO_TEMP, hk, 7)) {
        imu_health.temp_c     = (int8_t)hk[0];
        imu_health.calib      = hk[1];
        imu_health.sys_status = hk[5];
        imu_health.sys_err    = hk[6];
    }
    return true;
}

// Decode one 32-byte burst, reject it if the quaternion isn't a unit
// quaternion, otherwise publish it for the comms task. Returns true if
// the sample was published.
bool imuProcessBurst(const uint8_t* b, uint32_t t_us) {
    ImuSample s;
    for (int k = 0; k < 3; k++) {
        s.a[k] = (float)le16(b + IMU_OFF_ACC + 2 * k) / IMU_ACC_LSB_PER_MS2;
        s.g[k] = (float)le16(b + IMU_OFF_GYR + 2 * k) / IMU_GYR_LSB_PER_RADS;
    }
    for (int k = 0; k < 4; k++) {
        s.q[k] = (float)le16(b + IMU_OFF_QUA + 2 * k) / IMU_QUA_LSB;
    }
    float n2 = s.q[0]*s.q[0] + s.q[1]*s.q[1] + s.q[2]*s.q[2] + s.q[3]*s.q[3];
    if (n2 < IMU_QNORM2_MIN || n2 > IMU_QNORM2_MAX) {
        imu_health.bad_samples++;
        return false;
    }
    s.t_us = t_us;

    taskENTER_CRITICAL(&imu_mux);
    s.seq = imu_latest.seq + 1;
    if (s.seq == 0) s.seq = 1;                  // 0 means "no sample yet"
    imu_latest = s;
    taskEXIT_CRITICAL(&imu_mux);
    imu_health.samples++;
    return true;
}

// [IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az,t_us — rad/s and m/s². The bridge
// reads fields 0-9; t_us is there so the Pi can later stamp by device
// time. Returns the length, or 0 if it didn't fit.
int formatImuLine(char* out, size_t cap, const ImuSample& s) {
    int n = snprintf(out, cap,
                     "[IMU]%.5f,%.5f,%.5f,%.5f,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%lu\r\n",
                     s.q[0], s.q[1], s.q[2], s.q[3],
                     s.g[0], s.g[1], s.g[2],
                     s.a[0], s.a[1], s.a[2],
                     (unsigned long)s.t_us);
    if (n < 0 || (size_t)n >= cap) return 0;
    return n;
}

const char* imuStateName(ImuState st) {
    switch (st) {
        case IMU_INIT: return "INIT";
        case IMU_RUN:  return "RUN";
        case IMU_DEAD: return "DEAD";
        default:       return "OFF";
    }
}

// Two lines, eight comma fields or fewer each (see the bridge note in the
// header). Calibration reads s/g/a/m 0-3; in IMUPLUS the magnetometer is
// off, so m stays 0 and s isn't expected to reach 3.
void imuPrintStatus() {
    unsigned c = imu_health.calib;
    Serial.printf("[IMUS,%s,cal=s%ug%ua%um%u,sys=%u,err=%u,T=%dC,sw=0x%02X%02X]\n",
                  imuStateName(imu_health.state),
                  (c >> 6) & 3u, (c >> 4) & 3u, (c >> 2) & 3u, c & 3u,
                  (unsigned)imu_health.sys_status, (unsigned)imu_health.sys_err,
                  (int)imu_health.temp_c,
                  (unsigned)imu_health.sw_rev_msb, (unsigned)imu_health.sw_rev_lsb);
    Serial.printf("[IMUC,n=%lu,i2c=%lu,bad=%lu,dup=%lu,reinit=%lu]\n",
                  (unsigned long)imu_health.samples,
                  (unsigned long)imu_health.i2c_errors,
                  (unsigned long)imu_health.bad_samples,
                  (unsigned long)imu_health.dup_samples,
                  (unsigned long)imu_health.reinits);
}

// One iteration of the IMU task. Split out so it can be stepped on its own.
void imuServiceOnce(ImuLoop& L) {
    if (imu_reinit_req) {
        imu_reinit_req = false;
        imu_health.reinits++;
        imu_health.state = IMU_INIT;
    }

    if (imu_health.state != IMU_RUN) {
        imu_health.state = IMU_INIT;
        if (imuInit()) {
            imu_health.state = IMU_RUN;
            L.fails = 0;
            L.have_prev = false;
            L.reported_dead = false;
            Serial.printf("[IMUS,UP,chip=0x%02X,sw=0x%02X%02X,sys=%u]\n",
                          (unsigned)BNO_CHIP_ID_VALUE, (unsigned)imu_health.sw_rev_msb,
                          (unsigned)imu_health.sw_rev_lsb, (unsigned)imu_health.sys_status);
            L.last_wake = xTaskGetTickCount();
        } else {
            imu_health.state = IMU_DEAD;
            if (!L.reported_dead) {
                Serial.println("[IMUS,NOT_FOUND,retry_s=5]");
                L.reported_dead = true;
            }
            vTaskDelay(pdMS_TO_TICKS(IMU_RETRY_MS));
        }
        return;
    }

    uint8_t buf[IMU_BURST_LEN];
    if (imuReadRegs(BNO_ACC_DATA, buf, IMU_BURST_LEN)) {
        uint32_t t_us = (uint32_t)micros();
        L.fails = 0;
        // The chip fuses at 100 Hz on its own clock, so now and then a
        // read lands before it has updated. A repeat carries nothing new.
        if (L.have_prev && memcmp(buf, L.prev, IMU_BURST_LEN) == 0) {
            imu_health.dup_samples++;
        } else {
            imuProcessBurst(buf, t_us);
            memcpy(L.prev, buf, IMU_BURST_LEN);
            L.have_prev = true;
        }
    } else {
        imu_health.i2c_errors++;
        if (++L.fails >= IMU_FAILS_BEFORE_RECOVERY) {
            Serial.printf("[IMUS,DOWN,i2c_fails=%u]\n", (unsigned)L.fails);
            imuBusClear();
            imu_health.reinits++;
            imu_health.state = IMU_INIT;
            return;
        }
    }

    if (++L.tick % IMU_HOUSEKEEP_EVERY == 0) {
        uint8_t hk[7];   // TEMP, CALIB_STAT, ST_RESULT, INT_STA, SYS_CLK, SYS_STATUS, SYS_ERR
        if (imuReadRegs(BNO_TEMP, hk, 7)) {
            imu_health.temp_c     = (int8_t)hk[0];
            imu_health.calib      = hk[1];
            imu_health.sys_status = hk[5];
            imu_health.sys_err    = hk[6];
            if (hk[5] == BNO_SYS_STATUS_ERROR) {
                Serial.printf("[IMUS,DOWN,sys_err=%u]\n", (unsigned)hk[6]);
                imu_health.reinits++;
                imu_health.state = IMU_INIT;
                return;
            }
        }
    }

    vTaskDelayUntil(&L.last_wake, pdMS_TO_TICKS(IMU_PERIOD_MS));
}

// Pins and bus, once, from inside the IMU task. Called from the task rather
// than setup(): ESP-IDF allocates the I2C interrupt on the core that calls
// begin(), and this task is pinned to core 0.
void imuTaskBegin(ImuLoop& L) {
    if (IMU_RST_PIN >= 0) {
        pinMode(IMU_RST_PIN, OUTPUT_OPEN_DRAIN);
        digitalWrite(IMU_RST_PIN, HIGH);   // released: the board's pull-up holds nRESET high
    }
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN, IMU_I2C_HZ);
    Wire.setTimeOut(IMU_I2C_TIMEOUT_MS);
    L = ImuLoop{};
    L.last_wake = xTaskGetTickCount();
    imu_health.state = IMU_INIT;
}

void imuTask(void* /*param*/) {
    ImuLoop L;
    imuTaskBegin(L);
    while (true) imuServiceOnce(L);
}

// Called from the comms task. Sends the newest sample at most once, and
// no faster than <N1,hz> asked. A sample the IMU task never published
// (stale, failed, rejected) is simply never sent, so silence on the Pi
// means "no data", never "the same data again".
void outputImuStream() {
    static uint32_t      last_seq = 0;
    static unsigned long last_ms  = 0;
    if (!imu_stream_on || imu_health.state != IMU_RUN) return;
    unsigned long now = millis();
    if (now - last_ms < imu_stream_interval_ms) return;

    ImuSample s;
    taskENTER_CRITICAL(&imu_mux);
    s = imu_latest;
    taskEXIT_CRITICAL(&imu_mux);
    if (s.seq == 0 || s.seq == last_seq) return;

    char line[128];
    int  n = formatImuLine(line, sizeof(line), s);
    if (n > 0) Serial.write((const uint8_t*)line, (size_t)n);
    last_seq = s.seq;
    last_ms  = now;
}

#endif  // IMU_ENABLED

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
#if IMU_ENABLED
        outputImuStream();
#endif
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ═══════════════════════════════════════════════════════════════════
// 16. SETUP & MAIN LOOP
// ═══════════════════════════════════════════════════════════════════

void setup() {
    // Must come before begin(). Without a TX ring buffer every write blocks
    // until it fits in the 128-byte UART FIFO, which a print from the PID
    // task would do inside the 100 Hz loop.
    Serial.setTxBufferSize(1024);
    Serial.begin(SERIAL_BAUD);
    delay(300);

    Serial.println();
    Serial.println("╔════════════════════════════════════════════╗");
    Serial.println("║  NarrowAisleBot ESP32 v3.1  —  Starting... ║");
    Serial.println("╚════════════════════════════════════════════╝");

    memset(motors, 0, sizeof(motors));

    Serial.print("  Motor pins    ... ");
    setupMotorPins();
    Serial.println("OK");

    Serial.print("  PCNT encoders ... ");
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);
    Serial.println("OK  (front 186264 CPR, rear 93132 CPR)");

    Serial.print("  Core 0 task   ... ");
    // 6 KB rather than 4: the telemetry and IMU lines are now formatted
    // into stack buffers with float vsnprintf.
    xTaskCreatePinnedToCore(communicationTask, "Comms", 6144, NULL, 1, NULL, 0);
    Serial.println("OK  (serial + telemetry)");

#if IMU_ENABLED
    Serial.print("  IMU task      ... ");
    // Core 0, priority 2: above Comms so a read is never late, and the I2C
    // driver blocks on a semaphore during a transfer so Comms keeps running.
    xTaskCreatePinnedToCore(imuTask, "IMU", 4096, NULL, 2, NULL, 0);
    Serial.printf("OK  (BNO055 0x%02X on SDA %d / SCL %d / RST %d  IMUPLUS)\n",
                  (unsigned)IMU_I2C_ADDR, IMU_SDA_PIN, IMU_SCL_PIN, IMU_RST_PIN);
#endif

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
    Serial.println("  Command source : USB serial from the Pi. No WiFi since v3.0.");
    Serial.println("  E-STOP         : <S> latches. Clear with <E1>.");
    Serial.println("  Telemetry      : <L1> compat 13-col, <L2> extended.");
    Serial.println("  IMU            : <N1[,hz]> streams [IMU] lines  <N?> status.");
    Serial.println("  Calibration    : gains are AIR values — see docs/PID_Calibration.md");
    Serial.println();
    Serial.println("[READY]");
}

void loop() {
    // All work happens in the two pinned FreeRTOS tasks.
    vTaskDelay(pdMS_TO_TICKS(1000));
}
