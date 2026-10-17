/*
 * nab_imu_function_test_esp32.ino  (v2)
 *
 * Bench test for the BNO055: does each function of the sensor work?
 * Needs only an ESP32 and the sensor. Independent of the drive firmware, so
 * FLASHING THIS REPLACES THE DRIVE FIRMWARE: re-flash aislebot_esp32.ino
 * afterwards. It never touches a motor or encoder pin.
 *
 * Wiring (what the I2C scan sketch just proved works):
 *     BNO055 VIN -> 3V3     GND -> GND
 *     BNO055 SDA -> GPIO14  SCL -> GPIO13     (change below if yours differ)
 *
 * Serial Monitor: 921600 baud, same as the scan sketch. Type a letter, Enter.
 *
 *   a  auto checks, board FLAT, FACE UP and STILL for about 8 s. Runs once
 *      by itself after boot. Checks the four chip IDs, the built-in self
 *      test, system status, temperature, accelerometer (gravity), gyro
 *      (zero rate), quaternion length, fused gravity and linear
 *      acceleration, and in NDOF the magnetometer.
 *   s  live stream of every output, 5 lines a second. Any key stops it.
 *   r  rotation test. You turn the board by hand for 8 s. The sketch
 *      integrates the gyro and compares it with the sensor's own fused
 *      quaternion. If the two agree, the gyro scale, the quaternion scale
 *      and their handedness are all consistent.
 *   f  six-face gravity test. Point each axis up, then down. Shows the
 *      accelerometer sign, gain and offset per axis.
 *   n  noise floor and resolution. Board STILL on a table for 10 s. Gives
 *      the spread of every sensor, the size of one step in the output, and
 *      what that means: the smallest tilt and the smallest turn rate the
 *      sensor can show, and how much heading a gyro offset would add.
 *   p  peak hold. Move the board any way you like for 10 s (tilt, shake,
 *      spin). Reports how far each sensor swung, the peak acceleration and
 *      rotation rate, and the largest tilt. Flags a reading stuck near 4 g.
 *   m  switch mode: NDOF (bench, has the magnetometer) or IMUPLUS (accel +
 *      gyro only, what aislebot_esp32.ino runs on the robot).
 *   i  full re-init (soft reset).   h  help.
 *
 * Pass/fail limits below are this sketch's own, chosen loose enough that a
 * working board passes and a dead axis, a flipped sign or a wrong scale does
 * not. They are not Bosch figures. The register map and scale factors come
 * from the same second-hand source as the drive firmware (the datasheet could
 * not be opened); the rotation and six-face tests check those scales on the
 * real chip.
 *
 * BOARD: ESP32 Dev Module, arduino-esp32 core 3.x. Library: none (Wire).
 */

#include <Wire.h>

// ── Wiring and setup ───────────────────────────────────────────────
const int      IMU_SDA_PIN = 14;
const int      IMU_SCL_PIN = 13;
const uint8_t  IMU_ADDR    = 0x28;     // ADR low
const uint32_t I2C_HZ      = 100000;   // 100 kHz, as the drive firmware uses
const bool     USE_EXT_CRYSTAL = false;   // true only if the breakout has the 32 kHz crystal

const uint8_t MODE_CONFIG  = 0x00;
const uint8_t MODE_IMUPLUS = 0x08;     // accel + gyro, heading relative to power-on
const uint8_t MODE_NDOF    = 0x0C;     // accel + gyro + magnetometer
const uint8_t START_MODE   = MODE_NDOF;

// Registers (page 0)
const uint8_t R_CHIP_ID          = 0x00;   // ..0x06 are IDs and revisions
const uint8_t R_PAGE_ID          = 0x07;
const uint8_t R_BLOCK_A          = 0x08;   // accel, mag, gyro, euler, quaternion (32 bytes)
const uint8_t R_BLOCK_B          = 0x28;   // lin. accel, gravity, temp, calib, status (19 bytes)
const uint8_t R_ST_RESULT        = 0x36;
const uint8_t R_UNIT_SEL         = 0x3B;
const uint8_t R_OPR_MODE         = 0x3D;
const uint8_t R_PWR_MODE         = 0x3E;
const uint8_t R_SYS_TRIGGER      = 0x3F;
const uint8_t R_AXIS_MAP_CONFIG  = 0x41;
const uint8_t R_AXIS_MAP_SIGN    = 0x42;

// Same units and axis map as aislebot_esp32.ino: accel m/s2, gyro rad/s,
// Euler rad, temperature degC, identity axis map.
const uint8_t UNIT_SEL_VALUE     = 0x06;
const uint8_t AXIS_MAP_CONFIG    = 0x24;
const uint8_t AXIS_MAP_SIGN      = 0x00;

const float ACC_LSB = 100.0f;      // per m/s2 (also linear accel and gravity)
const float MAG_LSB = 16.0f;       // per uT
const float GYR_LSB = 900.0f;      // per rad/s
const float EUL_LSB = 900.0f;      // per rad
const float QUA_LSB = 16384.0f;
const float G0      = 9.80665f;
const float RAD2DEG = 57.2957795f;

// Block A offsets
const int A_ACC = 0, A_MAG = 6, A_GYR = 12, A_EUL = 18, A_QUA = 24;
// Block B offsets
const int B_LIA = 0, B_GRV = 6, B_TEMP = 12, B_CAL = 13, B_ST = 14, B_SYS = 17, B_ERR = 18;
const uint8_t BLOCK_A_LEN = 32;
const uint8_t BLOCK_B_LEN = 19;

// Limits
const float LIM_ACC_NORM_TOL   = 0.8f;     // |accel| must be 9.81 +- this, m/s2 (about 80 mg: a fresh, uncalibrated accel can be that far off)
const float LIM_GYR_MEAN       = 0.05f;    // static gyro mean per axis, rad/s (about 2.9 deg/s)
const float LIM_GYR_SD         = 0.02f;    // static gyro noise per axis, rad/s
const float LIM_QNORM_TOL      = 0.02f;    // |q| = 1 +- this
const float LIM_LIA            = 0.5f;     // static linear accel magnitude, m/s2
const float LIM_YAW_DRIFT_DEG  = 1.0f;     // fused yaw drift while still, over the window
const float LIM_ROT_MIN_DEG    = 30.0f;    // rotation test needs at least this much motion
const float LIM_FACE_MIN       = 9.3f;     // m/s2 on the axis pointing up or down
const float LIM_FACE_CROSS     = 1.5f;     // m/s2 allowed on the other two axes
const float LIM_GAIN_TOL       = 0.05f;    // accel gain 1 +- this
const float LIM_OFFSET         = 1.0f;     // accel offset, m/s2

// ── Types (all before the first function, so the IDE's generated
//    prototypes can see them) ─────────────────────────────────────────
enum Level : uint8_t { L_PASS = 0, L_WARN, L_FAIL, L_INFO };

struct Sample {
    float   acc[3];      // m/s2, gravity included
    float   mag[3];      // uT
    float   gyr[3];      // rad/s
    float   eul[3];      // rad: heading, roll, pitch
    float   q[4];        // w, x, y, z
    float   lia[3];      // m/s2
    float   grv[3];      // m/s2
    int8_t  temp;        // degC
    uint8_t calib;       // sys 7-6, gyr 5-4, acc 3-2, mag 1-0
    uint8_t st_result;   // bit0 acc, bit1 mag, bit2 gyr, bit3 mcu; 0x0F = all pass
    uint8_t sys_status;  // 5 = fusion running
    uint8_t sys_err;
};

struct Stat {
    double   sum  = 0;
    double   sum2 = 0;
    double   lo   = 1e30;
    double   hi   = -1e30;
    uint32_t n    = 0;
    void  add(float v) {
        sum += v; sum2 += (double)v * v; n++;
        if (v < lo) lo = v;
        if (v > hi) hi = v;
    }
    float mean() const { return n ? (float)(sum / n) : 0.0f; }
    float pp()   const { return n ? (float)(hi - lo) : 0.0f; }
    float lowest()  const { return n ? (float)lo : 0.0f; }
    float highest() const { return n ? (float)hi : 0.0f; }
    float sd() const {
        if (n < 2) return 0.0f;
        double m = sum / n, v = sum2 / n - m * m;
        return v > 0 ? (float)sqrt(v) : 0.0f;
    }
};

// ── State ──────────────────────────────────────────────────────────
uint8_t       g_mode        = START_MODE;
bool          g_up          = false;
const char*   g_step        = "";
bool          g_stream      = false;
unsigned long g_stream_last = 0;
uint8_t       g_stream_fail = 0;
int           g_count[4]    = {0, 0, 0, 0};

// ── I2C, the same calls the drive firmware uses ────────────────────
static int16_t le16(const uint8_t* p) {
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

bool writeReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(IMU_ADDR);
    Wire.write(reg);
    Wire.write(val);
    return Wire.endTransmission(true) == 0;
}

bool readRegs(uint8_t reg, uint8_t* buf, uint8_t len) {
    Wire.beginTransmission(IMU_ADDR);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;      // repeated start
    if (Wire.requestFrom((int)IMU_ADDR, (int)len) != (int)len) {
        while (Wire.available()) Wire.read();
        return false;
    }
    for (uint8_t i = 0; i < len; i++) buf[i] = (uint8_t)Wire.read();
    return true;
}

// Write, read back, compare only the bits that register implements. The chip
// silently ignores most writes outside CONFIG mode.
bool writeVerify(uint8_t reg, uint8_t val, uint8_t mask) {
    if (!writeReg(reg, val)) return false;
    delay(2);
    uint8_t rb = 0;
    if (!readRegs(reg, &rb, 1)) return false;
    return (rb & mask) == (val & mask);
}

bool waitChipId(unsigned long timeout_ms) {
    unsigned long t0 = millis();
    while (millis() - t0 < timeout_ms) {
        uint8_t id = 0;
        if (readRegs(R_CHIP_ID, &id, 1) && id == 0xA0) return true;
        delay(20);
    }
    return false;
}

// Reads block A (always) and block B (if full) and converts to SI units.
bool readSample(Sample& s, bool full) {
    uint8_t a[BLOCK_A_LEN];
    if (!readRegs(R_BLOCK_A, a, BLOCK_A_LEN)) return false;
    for (int k = 0; k < 3; k++) {
        s.acc[k] = (float)le16(a + A_ACC + 2 * k) / ACC_LSB;
        s.mag[k] = (float)le16(a + A_MAG + 2 * k) / MAG_LSB;
        s.gyr[k] = (float)le16(a + A_GYR + 2 * k) / GYR_LSB;
        s.eul[k] = (float)le16(a + A_EUL + 2 * k) / EUL_LSB;
    }
    for (int k = 0; k < 4; k++) s.q[k] = (float)le16(a + A_QUA + 2 * k) / QUA_LSB;
    if (full) {
        uint8_t b[BLOCK_B_LEN];
        if (!readRegs(R_BLOCK_B, b, BLOCK_B_LEN)) return false;
        for (int k = 0; k < 3; k++) {
            s.lia[k] = (float)le16(b + B_LIA + 2 * k) / ACC_LSB;
            s.grv[k] = (float)le16(b + B_GRV + 2 * k) / ACC_LSB;
        }
        s.temp       = (int8_t)b[B_TEMP];
        s.calib      = b[B_CAL];
        s.st_result  = b[B_ST];
        s.sys_status = b[B_SYS];
        s.sys_err    = b[B_ERR];
    }
    return true;
}

// ── Chip bring-up ──────────────────────────────────────────────────
// Same order as the drive firmware's init. g_step names the step that failed.
bool initChip(uint8_t mode) {
    g_step = "chip ID before reset";
    if (!waitChipId(1000)) return false;
    writeReg(R_OPR_MODE, MODE_CONFIG);
    delay(25);
    writeReg(R_SYS_TRIGGER, 0x20);                 // RST_SYS; its ACK may be lost
    delay(650);
    g_step = "chip ID after reset";
    if (!waitChipId(1000)) return false;
    delay(50);
    g_step = "power mode";
    if (!writeReg(R_PWR_MODE, 0x00)) return false;
    delay(10);
    if (!writeReg(R_PAGE_ID, 0x00)) return false;
    g_step = "unit and axis registers (read-back mismatch)";
    if (!writeVerify(R_UNIT_SEL, UNIT_SEL_VALUE, 0x97)) return false;
    if (!writeVerify(R_AXIS_MAP_CONFIG, AXIS_MAP_CONFIG, 0x3F)) return false;
    if (!writeVerify(R_AXIS_MAP_SIGN, AXIS_MAP_SIGN, 0x07)) return false;
    writeReg(R_SYS_TRIGGER, USE_EXT_CRYSTAL ? 0x80 : 0x00);
    delay(10);
    g_step = "entering the fusion mode";
    if (!writeVerify(R_OPR_MODE, mode, 0x0F)) return false;
    delay(600);                                    // output inside this window is not trusted
    g_mode = mode;
    g_step = "";
    return true;
}

bool setMode(uint8_t mode) {
    writeReg(R_OPR_MODE, MODE_CONFIG);
    delay(25);
    if (!writeVerify(R_OPR_MODE, mode, 0x0F)) return false;
    delay(600);
    g_mode = mode;
    return true;
}

// ── Small helpers ──────────────────────────────────────────────────
const char* modeName(uint8_t m) {
    if (m == MODE_NDOF)    return "NDOF";
    if (m == MODE_IMUPLUS) return "IMUPLUS";
    if (m == MODE_CONFIG)  return "CONFIG";
    return "other";
}

void check(Level lvl, const char* name, const char* fmt, ...) __attribute__((format(printf, 3, 4)));
void check(Level lvl, const char* name, const char* fmt, ...) {
    char msg[200];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof(msg), fmt, ap);
    va_end(ap);
    static const char* const tag[4] = {"PASS", "WARN", "FAIL", "info"};
    g_count[lvl]++;
    Serial.printf("  %-4s  %-24s %s\n", tag[lvl], name, msg);
}

void resetCounts() { for (int i = 0; i < 4; i++) g_count[i] = 0; }

void summary() {
    Serial.printf("RESULT: %d PASS, %d WARN, %d FAIL\n", g_count[L_PASS], g_count[L_WARN], g_count[L_FAIL]);
    if (g_count[L_FAIL] > 0)
        Serial.println("Read the FAIL lines above. Send this whole output if you want a second pair of eyes.");
    Serial.println();
}

// Waits `secs` seconds, printing the count.
void countdown(int secs) {
    for (int i = secs; i > 0; i--) {
        Serial.printf("  %d...", i);
        delay(1000);
    }
    Serial.println("  GO");
}

float vnorm3(const float* v) { return sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); }

// Quaternions are w, x, y, z (Hamilton product).
void qmul(const float* a, const float* b, float* o) {
    o[0] = a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3];
    o[1] = a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2];
    o[2] = a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1];
    o[3] = a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0];
}

void qconj(const float* a, float* o) { o[0] = a[0]; o[1] = -a[1]; o[2] = -a[2]; o[3] = -a[3]; }

void qnorm(float* q) {
    float n = sqrtf(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
    if (n < 1e-6f) { q[0] = 1; q[1] = q[2] = q[3] = 0; return; }
    for (int i = 0; i < 4; i++) q[i] /= n;
}

// Rotation vector (axis * angle) of a unit quaternion, in degrees.
void rotvecDeg(const float* q, float* rv) {
    float w = q[0], x = q[1], y = q[2], z = q[3];
    if (w < 0) { w = -w; x = -x; y = -y; z = -z; }       // shortest rotation
    float s = sqrtf(x * x + y * y + z * z);
    if (s < 1e-6f) { rv[0] = rv[1] = rv[2] = 0; return; }
    float ang = 2.0f * atan2f(s, w) * RAD2DEG;
    rv[0] = x / s * ang; rv[1] = y / s * ang; rv[2] = z / s * ang;
}

float yawDeg(const float* q) {
    return atan2f(2.0f * (q[0] * q[3] + q[1] * q[2]), 1.0f - 2.0f * (q[2] * q[2] + q[3] * q[3])) * RAD2DEG;
}

float wrap180(float d) {
    while (d > 180.0f) d -= 360.0f;
    while (d < -180.0f) d += 360.0f;
    return d;
}

char readKey() {
    while (Serial.available()) {
        int c = Serial.read();
        if (c > ' ') return (char)c;
    }
    return 0;
}

// ── a: auto checks ─────────────────────────────────────────────────
void autoChecks() {
    resetCounts();
    Serial.printf("--- auto checks, mode %s: board FLAT, FACE UP, STILL for about 8 s ---\n", modeName(g_mode));

    uint8_t id[7];
    if (!readRegs(R_CHIP_ID, id, 7)) {
        check(L_FAIL, "chip answers", "no reply at 0x%02X (check wiring, then run the scan sketch)", (unsigned)IMU_ADDR);
        summary();
        return;
    }
    check(id[0] == 0xA0 ? L_PASS : L_FAIL, "CHIP_ID", "0x%02X (expect 0xA0)", (unsigned)id[0]);
    check(id[1] == 0xFB ? L_PASS : L_FAIL, "ACC_ID (accelerometer)", "0x%02X (expect 0xFB)", (unsigned)id[1]);
    check(id[2] == 0x32 ? L_PASS : L_FAIL, "MAG_ID (magnetometer)", "0x%02X (expect 0x32)", (unsigned)id[2]);
    check(id[3] == 0x0F ? L_PASS : L_FAIL, "GYR_ID (gyroscope)", "0x%02X (expect 0x0F)", (unsigned)id[3]);
    check(L_INFO, "firmware revision", "SW 0x%04X, bootloader 0x%02X", (unsigned)(id[4] | (id[5] << 8)), (unsigned)id[6]);

    // Self test, triggered here so the result is fresh. Needs CONFIG mode.
    uint8_t mode_before = g_mode;
    writeReg(R_OPR_MODE, MODE_CONFIG);
    delay(25);
    writeReg(R_SYS_TRIGGER, (uint8_t)(0x01 | (USE_EXT_CRYSTAL ? 0x80 : 0x00)));
    delay(1000);
    uint8_t st = 0;
    bool st_ok = readRegs(R_ST_RESULT, &st, 1);
    if (!setMode(mode_before)) {
        check(L_FAIL, "mode restore", "could not re-enter %s after the self test", modeName(mode_before));
        summary();
        return;
    }
    if (!st_ok) {
        check(L_FAIL, "built-in self test", "could not read ST_RESULT");
    } else {
        check(st == 0x0F ? L_PASS : L_FAIL, "built-in self test",
              "ST_RESULT 0x%02X  accel %s  mag %s  gyro %s  mcu %s",
              (unsigned)st, (st & 1) ? "ok" : "BAD", (st & 2) ? "ok" : "BAD",
              (st & 4) ? "ok" : "BAD", (st & 8) ? "ok" : "BAD");
    }

    // Static window: 150 samples at about 50 Hz.
    Stat acc[3], gyr[3], mag[3], lia[3], grv[3];
    Stat accn, qn, grvn, lian, magn;
    Sample s = {};
    float q_first[4] = {1, 0, 0, 0};
    bool  have_first = false;
    int   n_fail = 0;
    const int N = 150;
    Serial.println("  measuring... do not touch it");
    for (int i = 0; i < N; i++) {
        if (!readSample(s, true)) { n_fail++; delay(20); continue; }
        for (int k = 0; k < 3; k++) {
            acc[k].add(s.acc[k]); gyr[k].add(s.gyr[k]); mag[k].add(s.mag[k]);
            lia[k].add(s.lia[k]); grv[k].add(s.grv[k]);
        }
        accn.add(vnorm3(s.acc));
        grvn.add(vnorm3(s.grv));
        lian.add(vnorm3(s.lia));
        magn.add(vnorm3(s.mag));
        qn.add(sqrtf(s.q[0] * s.q[0] + s.q[1] * s.q[1] + s.q[2] * s.q[2] + s.q[3] * s.q[3]));
        if (!have_first) { for (int k = 0; k < 4; k++) q_first[k] = s.q[k]; have_first = true; }
        delay(20);
    }
    if (!have_first) {
        check(L_FAIL, "I2C reads", "all %d sample reads failed", N);
        summary();
        return;
    }
    check(n_fail == 0 ? L_PASS : (n_fail < N / 10 ? L_WARN : L_FAIL), "I2C reads",
          "%d of %d failed", n_fail, N);

    check(s.sys_status == 5 ? L_PASS : L_FAIL, "system status",
          "%u (5 = fusion running; 1 = error, 6 = running without fusion)", (unsigned)s.sys_status);
    check(s.sys_err == 0 ? L_PASS : L_FAIL, "system error", "%u (0 = none)", (unsigned)s.sys_err);
    check((s.temp >= 5 && s.temp <= 70) ? L_PASS : L_FAIL, "temperature",
          "%d C (room temperature plus a few degrees is normal)", (int)s.temp);

    float an = accn.mean();
    check(fabsf(an - G0) <= LIM_ACC_NORM_TOL ? L_PASS : L_FAIL, "accelerometer",
          "x %+6.2f  y %+6.2f  z %+6.2f m/s2, |a| %.2f (expect 9.81 +-%.1f), noise %.3f",
          acc[0].mean(), acc[1].mean(), acc[2].mean(), an, LIM_ACC_NORM_TOL,
          fmaxf(acc[0].sd(), fmaxf(acc[1].sd(), acc[2].sd())));
    int up = 0;
    for (int k = 1; k < 3; k++) if (fabsf(acc[k].mean()) > fabsf(acc[up].mean())) up = k;
    check(L_INFO, "gravity axis", "%c%c carries gravity (flat and face up should give +Z)",
          acc[up].mean() >= 0 ? '+' : '-', "XYZ"[up]);

    bool gyr_ok = true, gyr_noisy = false;
    for (int k = 0; k < 3; k++) {
        if (fabsf(gyr[k].mean()) > LIM_GYR_MEAN) gyr_ok = false;
        if (gyr[k].sd() > LIM_GYR_SD) gyr_noisy = true;
    }
    check(gyr_ok ? (gyr_noisy ? L_WARN : L_PASS) : L_FAIL, "gyroscope at rest",
          "x %+6.2f  y %+6.2f  z %+6.2f deg/s (limit +-%.1f), noise %.3f rad/s",
          gyr[0].mean() * RAD2DEG, gyr[1].mean() * RAD2DEG, gyr[2].mean() * RAD2DEG,
          LIM_GYR_MEAN * RAD2DEG, fmaxf(gyr[0].sd(), fmaxf(gyr[1].sd(), gyr[2].sd())));

    float qm = qn.mean();
    check(fabsf(qm - 1.0f) <= LIM_QNORM_TOL ? L_PASS : L_FAIL, "fused quaternion",
          "|q| %.4f (expect 1.000), w %+.3f x %+.3f y %+.3f z %+.3f", qm, s.q[0], s.q[1], s.q[2], s.q[3]);
    float drift = wrap180(yawDeg(s.q) - yawDeg(q_first));
    check(fabsf(drift) <= LIM_YAW_DRIFT_DEG ? L_PASS : L_WARN, "yaw drift while still",
          "%+.2f deg over the window", drift);
    check(fabsf(grvn.mean() - G0) <= LIM_ACC_NORM_TOL ? L_PASS : L_FAIL, "fused gravity vector",
          "|g| %.2f (expect 9.81), x %+.2f y %+.2f z %+.2f", grvn.mean(), grv[0].mean(), grv[1].mean(), grv[2].mean());
    check(lian.mean() <= LIM_LIA ? L_PASS : L_WARN, "linear acceleration",
          "|lin| %.2f m/s2 at rest (expect near 0, limit %.1f; an uncalibrated accel can offset it)", lian.mean(), LIM_LIA);

    if (g_mode == MODE_NDOF) {
        float mn = magn.mean();
        check((mn >= 15.0f && mn <= 100.0f) ? L_PASS : L_WARN, "magnetometer",
              "x %+6.1f  y %+6.1f  z %+6.1f uT, |m| %.1f (Earth is 25-65; steel and magnets nearby shift it)",
              mag[0].mean(), mag[1].mean(), mag[2].mean(), mn);
    } else {
        check(L_INFO, "magnetometer", "off in %s (the robot runs this way on purpose)", modeName(g_mode));
    }
    check(L_INFO, "calibration", "system %u  gyro %u  accel %u  mag %u   (3 = fully calibrated)",
          (unsigned)((s.calib >> 6) & 3), (unsigned)((s.calib >> 4) & 3),
          (unsigned)((s.calib >> 2) & 3), (unsigned)(s.calib & 3));
    summary();
}

// ── s: live stream ─────────────────────────────────────────────────
void streamHeader() {
    Serial.printf("--- live stream, mode %s. Any key stops it. ---\n", modeName(g_mode));
    Serial.println("acc m/s2 (gravity in) | gyro deg/s | mag uT | Euler deg H/R/P | quaternion w x y z | |lin| | T | cal S/G/A/M");
}

bool streamLine() {
    Sample s;
    if (!readSample(s, true)) return false;
    Serial.printf("%+6.2f %+6.2f %+6.2f | %+7.1f %+7.1f %+7.1f | %+6.1f %+6.1f %+6.1f | %6.1f %+6.1f %+6.1f | %+.3f %+.3f %+.3f %+.3f | %.2f | %d | %u/%u/%u/%u\n",
                  s.acc[0], s.acc[1], s.acc[2],
                  s.gyr[0] * RAD2DEG, s.gyr[1] * RAD2DEG, s.gyr[2] * RAD2DEG,
                  s.mag[0], s.mag[1], s.mag[2],
                  s.eul[0] * RAD2DEG, s.eul[1] * RAD2DEG, s.eul[2] * RAD2DEG,
                  s.q[0], s.q[1], s.q[2], s.q[3], vnorm3(s.lia), (int)s.temp,
                  (unsigned)((s.calib >> 6) & 3), (unsigned)((s.calib >> 4) & 3),
                  (unsigned)((s.calib >> 2) & 3), (unsigned)(s.calib & 3));
    return true;
}

// ── r: rotation test ───────────────────────────────────────────────
void rotationTest() {
    resetCounts();
    Serial.printf("--- rotation test, mode %s ---\n", modeName(g_mode));
    Serial.println("Hold the board. After the count you have 8 s to turn it by hand, smoothly,");
    Serial.println("at least 45 degrees in total: one axis at a time is easiest (for example, flat on the");
    Serial.println("table, spin it about 90 degrees counter-clockwise seen from above, then stop).");
    countdown(3);

    Sample s = {};
    if (!readSample(s, false)) {
        check(L_FAIL, "I2C reads", "could not read the sensor");
        summary();
        return;
    }
    float q0[4], q1[4], qi[4] = {1, 0, 0, 0};
    for (int k = 0; k < 4; k++) q0[k] = q1[k] = s.q[k];
    qnorm(q0);
    float w_prev[3] = {s.gyr[0], s.gyr[1], s.gyr[2]};
    float peak[3]   = {0, 0, 0};
    unsigned long t_prev = micros();
    unsigned long t0 = millis();
    int reads = 0, fails = 0;
    while (millis() - t0 < 8000) {
        delay(8);
        if (!readSample(s, false)) { fails++; continue; }
        reads++;
        unsigned long t = micros();
        float dt = (float)(t - t_prev) * 1e-6f;
        t_prev = t;
        float w[3];
        for (int k = 0; k < 3; k++) {
            w[k] = 0.5f * (w_prev[k] + s.gyr[k]);
            w_prev[k] = s.gyr[k];
            if (fabsf(s.gyr[k]) > peak[k]) peak[k] = fabsf(s.gyr[k]);
        }
        float wm = vnorm3(w);
        if (wm > 1e-6f) {
            float ang = wm * dt, sc = sinf(0.5f * ang) / wm;
            float dq[4] = {cosf(0.5f * ang), w[0] * sc, w[1] * sc, w[2] * sc};
            float tmp[4];
            qmul(qi, dq, tmp);
            for (int k = 0; k < 4; k++) qi[k] = tmp[k];
            qnorm(qi);
        }
        for (int k = 0; k < 4; k++) q1[k] = s.q[k];
    }
    qnorm(q1);
    float c0[4], rel[4];
    qconj(q0, c0);
    qmul(c0, q1, rel);
    qnorm(rel);
    float rv_f[3], rv_g[3];
    rotvecDeg(rel, rv_f);
    rotvecDeg(qi, rv_g);
    float ci[4], qe[4];
    qconj(qi, ci);
    qmul(ci, rel, qe);
    float ew = fabsf(qe[0]) > 1.0f ? 1.0f : fabsf(qe[0]);
    float err = 2.0f * acosf(ew) * RAD2DEG;
    float total = vnorm3(rv_f);

    Serial.printf("  gyro, integrated   X %+7.1f  Y %+7.1f  Z %+7.1f deg\n", rv_g[0], rv_g[1], rv_g[2]);
    Serial.printf("  fused quaternion   X %+7.1f  Y %+7.1f  Z %+7.1f deg   (total %.0f deg)\n",
                  rv_f[0], rv_f[1], rv_f[2], total);
    Serial.printf("  peak rate          X %7.1f  Y %7.1f  Z %7.1f deg/s\n",
                  peak[0] * RAD2DEG, peak[1] * RAD2DEG, peak[2] * RAD2DEG);
    check(fails * 10 <= reads ? L_PASS : L_WARN, "I2C reads", "%d of %d failed", fails, reads + fails);
    if (total < LIM_ROT_MIN_DEG) {
        check(L_WARN, "gyro vs quaternion", "only %.0f deg of rotation seen, need %.0f or more. Run r again and turn it further.",
              total, LIM_ROT_MIN_DEG);
    } else {
        float tol = fmaxf(6.0f, 0.08f * total);
        check(err <= tol ? L_PASS : L_FAIL, "gyro vs quaternion",
              "disagree by %.1f deg (limit %.1f). A big gap means a wrong scale, a flipped axis or a dead gyro axis.",
              err, tol);
    }
    Serial.println("  Sign check by hand: the +Z arrow points out of the top of the board. Counter-clockwise");
    Serial.println("  seen from above, looking down that arrow, must show Z positive in BOTH rows.");
    summary();
}

// ── f: six-face gravity test ───────────────────────────────────────
void sixFaceTest() {
    resetCounts();
    struct Pose { const char* what; int axis; int sign; };
    static const Pose poses[6] = {
        {"+Z UP    (flat on the table, chip side up)",     2, +1},
        {"-Z UP    (flipped over, chip side down)",        2, -1},
        {"+X UP    (+X arrow pointing at the ceiling)",    0, +1},
        {"-X UP    (+X arrow pointing at the floor)",      0, -1},
        {"+Y UP    (+Y arrow pointing at the ceiling)",    1, +1},
        {"-Y UP    (+Y arrow pointing at the floor)",      1, -1},
    };
    float mean[6][3];
    Serial.printf("--- six-face gravity test, mode %s ---\n", modeName(g_mode));
    Serial.println("Six poses. For each, get the board into the pose and hold it STILL until the next prompt.");
    Serial.println("You get 6 s to settle, then it measures for 2 s.");
    unsigned long t_test = millis();
    bool read_ok = true;
    for (int p = 0; p < 6; p++) {
        Serial.printf("Pose %d of 6: %s\n", p + 1, poses[p].what);
        unsigned long t_pose = t_test + (unsigned long)p * 8000UL;
        int shown = 7;
        while (millis() - t_pose < 6000UL) {
            int left = 6 - (int)((millis() - t_pose) / 1000UL);
            if (left < shown) { shown = left; Serial.printf("  %d...", left); }
            delay(20);
        }
        Serial.println("  measuring");
        Stat st[3];
        while (millis() - t_pose < 8000UL) {
            Sample s;
            if (readSample(s, false)) { for (int k = 0; k < 3; k++) st[k].add(s.acc[k]); }
            delay(20);
        }
        if (st[0].n == 0) read_ok = false;
        for (int k = 0; k < 3; k++) mean[p][k] = st[k].mean();
        Serial.printf("  accel  x %+6.2f  y %+6.2f  z %+6.2f m/s2\n", mean[p][0], mean[p][1], mean[p][2]);
    }
    if (!read_ok) {
        check(L_FAIL, "I2C reads", "no samples in at least one pose");
        summary();
        return;
    }
    for (int ax = 0; ax < 3; ax++) {
        float plus = 0, minus = 0, cross = 0;
        for (int p = 0; p < 6; p++) {
            if (poses[p].axis != ax) continue;
            float v = mean[p][ax];
            if (poses[p].sign > 0) plus = v; else minus = v;
            for (int k = 0; k < 3; k++) if (k != ax && fabsf(mean[p][k]) > cross) cross = fabsf(mean[p][k]);
        }
        bool sign_ok = plus >= LIM_FACE_MIN && minus <= -LIM_FACE_MIN;
        float gain = (plus - minus) / (2.0f * G0);
        float offs = 0.5f * (plus + minus);
        Level lvl = !sign_ok ? L_FAIL
                  : (fabsf(gain - 1.0f) > LIM_GAIN_TOL || fabsf(offs) > LIM_OFFSET) ? L_FAIL
                  : (cross > LIM_FACE_CROSS ? L_WARN : L_PASS);
        char name[24];
        snprintf(name, sizeof(name), "accelerometer %c", "XYZ"[ax]);
        check(lvl, name, "up %+.2f, down %+.2f m/s2, gain %.3f, offset %+.2f m/s2 (%+.0f mg), other axes up to %.2f",
              plus, minus, gain, offs, offs / G0 * 1000.0f, cross);
    }
    Sample s;
    if (readSample(s, true))
        check(L_INFO, "calibration", "system %u  gyro %u  accel %u  mag %u   (3 = fully calibrated; the six poses help accel reach 3)",
              (unsigned)((s.calib >> 6) & 3), (unsigned)((s.calib >> 4) & 3),
              (unsigned)((s.calib >> 2) & 3), (unsigned)(s.calib & 3));
    summary();
}

// ── n: noise floor and resolution ──────────────────────────────────
// How small a change can the sensor show? Lie it still for 10 s; the spread
// of the readings is the noise, and a change has to beat about three times
// that to be believed.
void noiseFloor() {
    resetCounts();
    Serial.printf("--- noise floor and resolution, mode %s ---\n", modeName(g_mode));
    Serial.println("Lie the board on a table and leave it alone for 10 s. Do not touch the table or the cable.");
    countdown(3);
    Stat acc[3], gyr[3], mag[3];
    Sample s = {};
    int ok = 0, fails = 0;
    unsigned long t0 = millis();
    while (millis() - t0 < 10000) {
        if (readSample(s, false)) {
            ok++;
            for (int k = 0; k < 3; k++) { acc[k].add(s.acc[k]); gyr[k].add(s.gyr[k]); mag[k].add(s.mag[k]); }
        } else {
            fails++;
        }
        delay(8);
    }
    if (ok < 50) {
        check(L_FAIL, "I2C reads", "only %d good reads in 10 s", ok);
        summary();
        return;
    }
    float asd = fmaxf(acc[0].sd(), fmaxf(acc[1].sd(), acc[2].sd()));
    float gsd = fmaxf(gyr[0].sd(), fmaxf(gyr[1].sd(), gyr[2].sd()));
    check(L_INFO, "samples", "%d reads in 10 s (%d failed), about %d per second", ok, fails, ok / 10);
    check(L_INFO, "accelerometer at rest",
          "mean %+.3f %+.3f %+.3f | sd %.3f %.3f %.3f | p-p %.3f %.3f %.3f m/s2   (1 LSB = %.3f)",
          acc[0].mean(), acc[1].mean(), acc[2].mean(), acc[0].sd(), acc[1].sd(), acc[2].sd(),
          acc[0].pp(), acc[1].pp(), acc[2].pp(), 1.0f / ACC_LSB);
    check(L_INFO, "gyroscope at rest",
          "mean %+.3f %+.3f %+.3f | sd %.3f %.3f %.3f | p-p %.3f %.3f %.3f deg/s   (1 LSB = %.4f)",
          gyr[0].mean() * RAD2DEG, gyr[1].mean() * RAD2DEG, gyr[2].mean() * RAD2DEG,
          gyr[0].sd() * RAD2DEG, gyr[1].sd() * RAD2DEG, gyr[2].sd() * RAD2DEG,
          gyr[0].pp() * RAD2DEG, gyr[1].pp() * RAD2DEG, gyr[2].pp() * RAD2DEG, RAD2DEG / GYR_LSB);
    if (g_mode == MODE_NDOF)
        check(L_INFO, "magnetometer at rest", "sd %.3f %.3f %.3f | p-p %.3f %.3f %.3f uT   (1 LSB = %.4f)",
              mag[0].sd(), mag[1].sd(), mag[2].sd(), mag[0].pp(), mag[1].pp(), mag[2].pp(), 1.0f / MAG_LSB);
    float ratio = 3.0f * asd / G0;
    if (ratio > 1.0f) { ratio = 1.0f; }
    check(L_INFO, "smallest tilt seen", "%.2f deg   (3 x the worst accelerometer noise, as a tilt from level)",
          asinf(ratio) * RAD2DEG);
    check(L_INFO, "smallest turn rate seen", "%.2f deg/s   (3 x the worst gyro noise)", 3.0f * gsd * RAD2DEG);
    float off = 0;
    for (int k = 0; k < 3; k++) if (fabsf(gyr[k].mean()) > off) off = fabsf(gyr[k].mean());
    check(L_INFO, "gyro offset", "%.3f deg/s, which would add up to %.2f deg of heading per minute if nothing corrected it",
          off * RAD2DEG, off * RAD2DEG * 60.0f);
    check((asd <= 0.1f && gsd <= LIM_GYR_SD) ? L_PASS : L_WARN, "board was still",
          "accel noise %.3f m/s2, gyro noise %.3f rad/s. If WARN, it moved: put it on a table and run n again.", asd, gsd);
    summary();
}

// ── p: peak hold ───────────────────────────────────────────────────
// Move it any way you like for 10 s. Records how far each sensor swings.
void peakHold() {
    resetCounts();
    Serial.printf("--- peak hold, mode %s ---\n", modeName(g_mode));
    Serial.println("After the count you have 10 s to move the board any way you like: tilt it, shake it,");
    Serial.println("spin it. It records how far each sensor swings.");
    countdown(3);
    Stat acc[3], gyr[3], mag[3];
    float peak_a = 0, peak_w = 0, max_tilt = 0;
    Sample s = {};
    int ok = 0, fails = 0;
    unsigned long t0 = millis();
    while (millis() - t0 < 10000) {
        if (readSample(s, false)) {
            ok++;
            for (int k = 0; k < 3; k++) { acc[k].add(s.acc[k]); gyr[k].add(s.gyr[k]); mag[k].add(s.mag[k]); }
            float an = vnorm3(s.acc), wn = vnorm3(s.gyr);
            if (an > peak_a) { peak_a = an; }
            if (wn > peak_w) { peak_w = wn; }
            float zc = 1.0f - 2.0f * (s.q[1] * s.q[1] + s.q[2] * s.q[2]);   // world-up component of the body Z axis
            if (zc > 1.0f)  { zc = 1.0f; }
            if (zc < -1.0f) { zc = -1.0f; }
            float tilt = acosf(zc) * RAD2DEG;
            if (tilt > max_tilt) { max_tilt = tilt; }
        } else {
            fails++;
        }
        delay(8);
    }
    if (ok < 50) {
        check(L_FAIL, "I2C reads", "only %d good reads in 10 s", ok);
        summary();
        return;
    }
    check(L_INFO, "accelerometer swing", "x %+7.2f..%+7.2f  y %+7.2f..%+7.2f  z %+7.2f..%+7.2f m/s2",
          acc[0].lowest(), acc[0].highest(), acc[1].lowest(), acc[1].highest(), acc[2].lowest(), acc[2].highest());
    check(L_INFO, "peak acceleration", "%.1f m/s2 = %.2f g (gravity included)", peak_a, peak_a / G0);
    check(L_INFO, "gyroscope swing", "x %+8.1f..%+8.1f  y %+8.1f..%+8.1f  z %+8.1f..%+8.1f deg/s",
          gyr[0].lowest() * RAD2DEG, gyr[0].highest() * RAD2DEG, gyr[1].lowest() * RAD2DEG, gyr[1].highest() * RAD2DEG,
          gyr[2].lowest() * RAD2DEG, gyr[2].highest() * RAD2DEG);
    check(L_INFO, "peak rotation rate", "%.0f deg/s = %.1f rad/s", peak_w * RAD2DEG, peak_w);
    check(L_INFO, "max tilt of Z axis", "%.0f deg from vertical (fused quaternion)", max_tilt);
    if (g_mode == MODE_NDOF)
        check(L_INFO, "magnetometer swing", "x %+7.1f..%+7.1f  y %+7.1f..%+7.1f  z %+7.1f..%+7.1f uT",
              mag[0].lowest(), mag[0].highest(), mag[1].lowest(), mag[1].highest(), mag[2].lowest(), mag[2].highest());
    if (peak_a >= 38.0f)
        check(L_WARN, "accelerometer range", "peak %.1f m/s2 is close to 4 g (39.2). If it sits flat there, the sensor is clipping. (The 4 g figure is second-hand.)",
              peak_a);
    check(fails * 10 <= ok ? L_PASS : L_WARN, "I2C reads", "%d of %d failed", fails, ok + fails);
    summary();
}

// ── Menu ───────────────────────────────────────────────────────────
void printMenu() {
    Serial.println("Commands (a letter, then Enter):");
    Serial.println("  a  auto checks (flat, face up, still)     s  live stream, any key stops");
    Serial.println("  r  rotation test, turn it by hand         f  six-face gravity test");
    Serial.println("  n  noise floor and resolution (still)     p  peak hold, move it any way you like");
    Serial.println("  m  switch NDOF <-> IMUPLUS                i  full re-init     h  help");
    Serial.println();
}

void printInitFailure() {
    Serial.printf("IMU init FAILED at: %s\n", g_step);
    Serial.printf("Check VIN, GND, SDA=GPIO%d, SCL=GPIO%d, then run the I2C scan sketch. Retrying every 3 s.\n",
                  IMU_SDA_PIN, IMU_SCL_PIN);
}

void setup() {
    Serial.begin(921600);
    delay(2000);                       // the monitor needs to open; the BNO055 needs about 650 ms
    Serial.println();
    Serial.println("=== NAB BNO055 function test v2 ===");
#ifdef ESP_ARDUINO_VERSION_MAJOR
    Serial.printf("arduino-esp32 core %d.%d.%d\n", ESP_ARDUINO_VERSION_MAJOR,
                  ESP_ARDUINO_VERSION_MINOR, ESP_ARDUINO_VERSION_PATCH);
#endif
    Serial.printf("SDA GPIO%d, SCL GPIO%d, address 0x%02X, %lu Hz\n", IMU_SDA_PIN, IMU_SCL_PIN,
                  (unsigned)IMU_ADDR, (unsigned long)I2C_HZ);
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN, I2C_HZ);
    Wire.setTimeOut(50);
    g_up = initChip(START_MODE);
    if (!g_up) {
        printInitFailure();
        return;
    }
    Serial.printf("IMU is up in %s mode.\n\n", modeName(g_mode));
    printMenu();
    autoChecks();
}

void loop() {
    if (!g_up) {
        delay(3000);
        g_up = initChip(g_mode);
        if (!g_up) { printInitFailure(); return; }
        Serial.printf("IMU is up in %s mode.\n\n", modeName(g_mode));
        printMenu();
        autoChecks();
        return;
    }

    char c = readKey();
    if (g_stream) {
        if (c) {
            g_stream = false;
            Serial.println("--- stream stopped ---");
            c = 0;
        } else if (millis() - g_stream_last >= 200) {
            g_stream_last = millis();
            if (streamLine()) {
                g_stream_fail = 0;
            } else if (++g_stream_fail >= 20) {
                g_stream = false;
                g_up = false;
                Serial.println("20 failed reads in a row, stopping the stream and re-initialising.");
            }
        }
    }

    switch (c) {
        case 0: break;
        case 'a': case 'A': autoChecks(); break;
        case 's': case 'S': streamHeader(); g_stream = true; g_stream_fail = 0; g_stream_last = 0; break;
        case 'r': case 'R': rotationTest(); break;
        case 'f': case 'F': sixFaceTest(); break;
        case 'n': case 'N': noiseFloor(); break;
        case 'p': case 'P': peakHold(); break;
        case 'm': case 'M': {
            uint8_t next = (g_mode == MODE_NDOF) ? MODE_IMUPLUS : MODE_NDOF;
            if (setMode(next)) Serial.printf("Mode is now %s. Run a for the checks in this mode.\n\n", modeName(g_mode));
            else Serial.println("Mode switch failed. Try i.");
            break;
        }
        case 'i': case 'I':
            g_up = initChip(g_mode);
            if (g_up) Serial.printf("Re-initialised in %s mode.\n\n", modeName(g_mode));
            else printInitFailure();
            break;
        case 'h': case 'H': case '?': printMenu(); break;
        default: Serial.printf("Unknown command '%c'. h for help.\n", c); break;
    }
    delay(2);
}
