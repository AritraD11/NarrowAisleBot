// Compiles firmware/nab_imu_function_test_esp32.ino against the host stand-ins
// and runs every command through a BNO055 register model whose data registers
// follow the fake clock. Run through tools/tests/esp32_firmware_hostcheck.py.
//
// The bench sketch is what someone reads to decide whether a sensor works, so
// the checks assert the PASS/FAIL it prints for a healthy board AND for each
// fault it exists to catch: wrong chip IDs, failed self test, a gyro offset, a
// wrong gyro scale, a flipped gyro sign, a dead or flipped accelerometer axis,
// and a chip that stops answering. The rotation test is also fed a tilted-axis
// motion, since a hand never turns a board about one clean axis.
#include "Arduino.h"
#include "Wire.h"

#include "../../../firmware/nab_imu_function_test_esp32.ino"

using hostsim::FakeBno;

static int g_fail = 0;
static void chk(bool cond, const char* label) {
    std::printf("  %s  %s\n", cond ? "PASS" : "FAIL", label);
    if (!cond) g_fail++;
}
static bool has(const std::string& s, const char* needle) { return s.find(needle) != std::string::npos; }

// The last line that contains `key`, or "".
static std::string line_with(const std::string& out, const char* key) {
    size_t at = out.rfind(key);
    if (at == std::string::npos) return "";
    size_t a = out.rfind('\n', at);
    a = (a == std::string::npos) ? 0 : a + 1;
    size_t b = out.find('\n', at);
    return out.substr(a, b == std::string::npos ? std::string::npos : b - a);
}

// ── What the fake chip reports ─────────────────────────────────────
struct Scn {
    float   acc[3] = {0.0f, 0.0f, 9.81f};
    float   mag[3] = {12.0f, -30.0f, 40.0f};
    float   gyr[3] = {0.0f, 0.0f, 0.0f};
    float   q[4]   = {1.0f, 0.0f, 0.0f, 0.0f};
    float   lia[3] = {0.02f, 0.0f, 0.0f};
    float   grv[3] = {0.0f, 0.0f, 9.81f};
    int     temp   = 27;
    uint8_t calib = 0xFF, sys = 5, err = 0;
    uint8_t acc_id = 0xFB, mag_id = 0x32, gyr_id = 0x0F;
};
static Scn      g_scn;
static uint64_t t_cmd = 0;               // fake time when the current command started

static void put16(FakeBno& b, int reg, float v, float lsb) {
    long i = lroundf(v * lsb);
    if (i > 32767)  { i = 32767; }
    if (i < -32768) { i = -32768; }
    b.regs[reg]     = (uint8_t)(i & 0xFF);
    b.regs[reg + 1] = (uint8_t)((i >> 8) & 0xFF);
}

static void fill(FakeBno& b, const Scn& s) {
    for (int k = 0; k < 3; k++) {
        put16(b, 0x08 + 2 * k, s.acc[k], 100.0f);
        put16(b, 0x0E + 2 * k, s.mag[k], 16.0f);
        put16(b, 0x14 + 2 * k, s.gyr[k], 900.0f);
        put16(b, 0x28 + 2 * k, s.lia[k], 100.0f);
        put16(b, 0x2E + 2 * k, s.grv[k], 100.0f);
    }
    for (int k = 0; k < 4; k++) put16(b, 0x20 + 2 * k, s.q[k], 16384.0f);
    b.regs[0x01] = s.acc_id;
    b.regs[0x02] = s.mag_id;
    b.regs[0x03] = s.gyr_id;
    b.regs[0x34] = (uint8_t)(int8_t)s.temp;
    b.regs[0x35] = s.calib;
    b.regs[0x39] = s.sys;
    b.regs[0x3A] = s.err;
}

static void hook_static(FakeBno& b) { fill(b, g_scn); }

// A rotation about a fixed body axis: still until t = 4 s after the command,
// turning at `rot_rate` for 4 s, still again. The gyro reads rate * scale; the
// quaternion is the true attitude.
static float rot_axis[3] = {0, 0, 1};
static float rot_rate    = 0.5f;
static float gyro_scale  = 1.0f;
static void hook_rotate(FakeBno& b) {
    Scn s = g_scn;
    double t  = (double)(hostsim::now_us - t_cmd) * 1e-6;
    double mv = t - 4.0;
    if (mv < 0.0) { mv = 0.0; }
    if (mv > 4.0) { mv = 4.0; }
    double th = (double)rot_rate * mv;
    s.q[0] = (float)cos(th / 2);
    for (int k = 0; k < 3; k++) {
        s.q[k + 1] = (float)(rot_axis[k] * sin(th / 2));
        s.gyr[k]   = (t >= 4.0 && t < 8.0) ? rot_axis[k] * rot_rate * gyro_scale : 0.0f;
    }
    fill(b, s);
}

// Six poses of 8 s each, in the sketch's order: +Z, -Z, +X, -X, +Y, -Y.
static float face_gain[3] = {1.01f, 0.99f, 1.0f};
static float face_off[3]  = {0.1f, -0.2f, 0.3f};
static bool  dead_y = false, flip_x = false;
static void hook_faces(FakeBno& b) {
    static const int axis_of[6] = {2, 2, 0, 0, 1, 1};
    int p = (int)((hostsim::now_us - t_cmd) / 8000000ULL);
    if (p < 0) { p = 0; }
    if (p > 5) { p = 5; }
    int ax = axis_of[p];
    float sign = (p % 2 == 0) ? 1.0f : -1.0f;
    Scn s = g_scn;
    for (int k = 0; k < 3; k++) s.acc[k] = 0.2f;                     // hand-held cross-axis leakage
    s.acc[ax] = sign * G0 * face_gain[ax] + face_off[ax];
    if (dead_y) { s.acc[1] = 0.0f; }
    if (flip_x) { s.acc[0] = -s.acc[0]; }
    fill(b, s);
}

// Types one command, runs the sketch's loop() once, returns what it printed.
static std::string cmd(char c, void (*hook)(FakeBno&)) {
    hostsim::bno.on_read = hook;
    Serial.in.clear();
    Serial.in += c;
    Serial.in += '\n';
    Serial.out.clear();
    t_cmd = hostsim::now_us;
    loop();
    return Serial.out;
}

// Noise: every read alternates -d / +d around a fixed mean, so the standard
// deviation over any whole number of reads is exactly d. Accel d = 0.01, 0.02,
// 0.03 m/s2 on x, y, z (1, 2, 3 LSB); gyro d = 2 LSB around a 2 LSB offset.
static float noise_gyro_lsb = 2.0f;
static void hook_noise(FakeBno& b) {
    static unsigned calls = 0;
    float sg = (calls++ % 2) ? 1.0f : -1.0f;
    Scn s = g_scn;
    s.acc[0] = 0.10f + sg * 0.01f;
    s.acc[1] = -0.20f + sg * 0.02f;
    s.acc[2] = 9.80f + sg * 0.03f;
    for (int k = 0; k < 3; k++) s.gyr[k] = (2.0f + sg * noise_gyro_lsb) / 900.0f;
    fill(b, s);
}

// Motion: a 2 s shake of amplitude shake_amp along x with a 6 rad/s wobble
// about z (both start 4 s after the command), then a 50 degree tilt about x
// from 8 s on.
static float shake_amp = 30.0f;
static void hook_motion(FakeBno& b) {
    Scn s = g_scn;
    double t = (double)(hostsim::now_us - t_cmd) * 1e-6;
    const double pi = 3.14159265358979;
    if (t >= 4.0 && t < 6.0) {
        double ph = 2.0 * pi * (t - 4.0);
        s.acc[0] = (float)(shake_amp * sin(ph));
        s.gyr[2] = (float)(6.0 * sin(ph));
    }
    if (t >= 8.0) {
        s.q[0] = (float)cos(25.0 * pi / 180.0);
        s.q[1] = (float)sin(25.0 * pi / 180.0);
    }
    fill(b, s);
}

static void reset_world() {
    hostsim::bno = FakeBno();
    g_scn = Scn();
    noise_gyro_lsb = 2.0f;
    shake_amp = 30.0f;
    rot_axis[0] = 0; rot_axis[1] = 0; rot_axis[2] = 1;
    rot_rate = 0.5f; gyro_scale = 1.0f;
    face_gain[0] = 1.01f; face_gain[1] = 0.99f; face_gain[2] = 1.0f;
    face_off[0] = 0.1f; face_off[1] = -0.2f; face_off[2] = 0.3f;
    dead_y = flip_x = false;
}

static bool parse3(const std::string& line, const char* fmt, float* v) {
    return std::sscanf(line.c_str(), fmt, &v[0], &v[1], &v[2]) == 3;
}

int main() {
    hostsim::bno.on_read = hook_static;
    setup();
    std::string boot = Serial.out;

    std::printf("boot: init, menu, then the auto checks by themselves\n");
    chk(has(boot, "IMU is up in NDOF mode."), "init succeeds and reports NDOF");
    chk(has(boot, "Commands (a letter, then Enter):"), "menu printed");
    chk(has(boot, "PASS  CHIP_ID") && has(boot, "PASS  ACC_ID") && has(boot, "PASS  MAG_ID") &&
        has(boot, "PASS  GYR_ID"), "all four chip IDs pass");
    chk(has(boot, "PASS  built-in self test"), "self test passes");
    chk(has(boot, "PASS  accelerometer") && has(boot, "PASS  gyroscope at rest"), "accel and gyro pass at rest");
    chk(has(boot, "PASS  fused quaternion") && has(boot, "PASS  fused gravity vector"), "quaternion and gravity pass");
    chk(has(boot, "PASS  magnetometer"), "magnetometer passes in NDOF");
    chk(has(boot, "+Z carries gravity"), "gravity axis reported as +Z");
    chk(has(boot, "RESULT: 16 PASS, 0 WARN, 0 FAIL"), "healthy board: 16 PASS, 0 WARN, 0 FAIL");
    chk((hostsim::bno.regs[0x3D] & 0x0F) == MODE_NDOF, "auto checks leave the chip in NDOF");
    chk(hostsim::bno.self_tests >= 1, "the self test was actually triggered");

    std::printf("a: each fault is caught\n");
    {
        reset_world(); g_scn.acc_id = 0x00;
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  ACC_ID") && has(o, "RESULT:") && !has(o, "0 FAIL"), "wrong ACC_ID fails");
    }
    {
        reset_world(); hostsim::bno.self_test_result = 0x0B;           // gyro self test bad
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  built-in self test") && has(o, "gyro BAD"), "failed self test fails and names the gyro");
    }
    {
        reset_world(); g_scn.gyr[2] = 0.10f;                           // 5.7 deg/s offset
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  gyroscope at rest"), "gyro offset fails");
    }
    {
        reset_world(); g_scn.acc[2] = 4.9f;                            // half the gravity: wrong scale
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  accelerometer"), "accelerometer scale error fails");
    }
    {
        reset_world(); g_scn.sys = 6;
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  system status"), "system status other than 5 fails");
    }
    {
        reset_world(); g_scn.q[0] = 0.5f;                              // |q| = 0.5
        std::string o = cmd('a', hook_static);
        chk(has(o, "FAIL  fused quaternion"), "non-unit quaternion fails");
    }
    {
        reset_world(); g_scn.mag[0] = g_scn.mag[1] = g_scn.mag[2] = 0.0f;
        std::string o = cmd('a', hook_static);
        chk(has(o, "WARN  magnetometer"), "a silent magnetometer is a WARN, not a FAIL");
    }
    {
        reset_world();
        std::string o = cmd('a', hook_static);
        hostsim::bno.present = false;
        o = cmd('a', hook_static);
        chk(has(o, "FAIL  chip answers") && has(o, "no reply at 0x28"), "a chip that stops answering is reported");
        hostsim::bno.present = true;
    }

    std::printf("m: mode switch\n");
    {
        reset_world();
        std::string o = cmd('m', hook_static);
        chk(has(o, "Mode is now IMUPLUS") && (hostsim::bno.regs[0x3D] & 0x0F) == MODE_IMUPLUS, "NDOF to IMUPLUS");
        o = cmd('a', hook_static);
        chk(has(o, "off in IMUPLUS") && !has(o, "magnetometer      x"), "IMUPLUS skips the magnetometer check");
        chk(has(o, "RESULT: 15 PASS, 0 WARN, 0 FAIL"), "healthy board in IMUPLUS: 15 PASS");
        o = cmd('m', hook_static);
        chk(has(o, "Mode is now NDOF") && (hostsim::bno.regs[0x3D] & 0x0F) == MODE_NDOF, "and back to NDOF");
    }

    std::printf("s: live stream\n");
    {
        reset_world();
        Serial.in = "s\n";
        Serial.out.clear();
        hostsim::bno.on_read = hook_static;
        loop();
        for (int i = 0; i < 400; i++) loop();
        std::string o = Serial.out;
        int lines = 0;
        for (size_t at = 0; (at = o.find(" | ", at)) != std::string::npos; at += 3) lines++;
        chk(has(o, "live stream, mode NDOF") && lines > 10, "stream prints lines");
        chk(has(o, "+0.00  +0.00  +9.81"), "stream shows the accelerometer in m/s2");
        Serial.in = "x\n";
        loop();
        chk(has(Serial.out, "--- stream stopped ---"), "any key stops the stream");
    }

    std::printf("r: rotation test, gyro against the fused quaternion\n");
    {
        reset_world(); rot_axis[0] = 0; rot_axis[1] = 0; rot_axis[2] = 1; rot_rate = 0.5f;
        std::string o = cmd('r', hook_rotate);
        float g[3], f[3];
        bool okg = parse3(line_with(o, "gyro, integrated"), "  gyro, integrated   X %f  Y %f  Z %f", g);
        bool okf = parse3(line_with(o, "fused quaternion   X"), "  fused quaternion   X %f  Y %f  Z %f", f);
        chk(okg && okf, "both rotation rows print");
        chk(okg && std::fabs(g[2] - 114.6f) < 1.5f && std::fabs(g[0]) < 1.0f && std::fabs(g[1]) < 1.0f,
            "gyro integral is +114.6 deg about Z (0.5 rad/s for 4 s)");
        chk(okf && std::fabs(f[2] - 114.6f) < 0.5f, "fused rotation is +114.6 deg about Z");
        chk(has(o, "PASS  gyro vs quaternion") && has(o, "0 FAIL"), "consistent gyro and quaternion pass");
        chk(has(o, "counter-clockwise"), "sign-check reminder printed");
    }
    {
        reset_world(); rot_axis[0] = 0.6f; rot_axis[1] = 0.0f; rot_axis[2] = 0.8f; rot_rate = 0.5f;
        std::string o = cmd('r', hook_rotate);
        float g[3];
        bool okg = parse3(line_with(o, "gyro, integrated"), "  gyro, integrated   X %f  Y %f  Z %f", g);
        chk(okg && std::fabs(g[0] - 0.6f * 114.6f) < 2.0f && std::fabs(g[2] - 0.8f * 114.6f) < 2.0f,
            "a tilted axis splits correctly between X and Z");
        chk(has(o, "PASS  gyro vs quaternion"), "tilted-axis rotation passes");
    }
    {
        reset_world(); gyro_scale = 0.5f;                              // gyro reads half: wrong scale
        std::string o = cmd('r', hook_rotate);
        chk(has(o, "FAIL  gyro vs quaternion"), "a gyro scale error is caught");
    }
    {
        reset_world(); gyro_scale = -1.0f;                             // gyro sign flipped
        std::string o = cmd('r', hook_rotate);
        chk(has(o, "FAIL  gyro vs quaternion"), "a flipped gyro sign is caught");
    }
    {
        reset_world(); rot_rate = 0.1f;                                // 23 deg: too little motion
        std::string o = cmd('r', hook_rotate);
        chk(has(o, "WARN  gyro vs quaternion") && has(o, "turn it further"), "too little motion is inconclusive, not a pass");
    }

    std::printf("f: six-face gravity test\n");
    {
        reset_world();
        std::string o = cmd('f', hook_faces);
        chk(has(o, "PASS  accelerometer X") && has(o, "PASS  accelerometer Y") && has(o, "PASS  accelerometer Z"),
            "healthy accelerometer passes on all three axes");
        std::string lx = line_with(o, "accelerometer X");
        chk(has(lx, "gain 1.010") && has(lx, "offset +0.10"), "gain and offset are recovered (1.01, +0.10)");
        chk(has(o, "Pose 6 of 6"), "all six poses were prompted");
    }
    {
        reset_world(); dead_y = true;
        std::string o = cmd('f', hook_faces);
        chk(has(o, "FAIL  accelerometer Y") && has(o, "PASS  accelerometer X"), "a dead Y axis fails only Y");
    }
    {
        reset_world(); flip_x = true;
        std::string o = cmd('f', hook_faces);
        chk(has(o, "FAIL  accelerometer X") && has(o, "PASS  accelerometer Z"), "a flipped X sign fails only X");
    }
    {
        reset_world(); face_gain[2] = 1.10f;
        std::string o = cmd('f', hook_faces);
        chk(has(o, "FAIL  accelerometer Z"), "a 10 percent gain error fails");
    }

    std::printf("n: noise floor and resolution\n");
    {
        reset_world();
        std::string o = cmd('n', hook_noise);
        float am[3], asd[3], app[3], gm[3], gsd[3], gpp[3];
        bool oka = std::sscanf(line_with(o, "accelerometer at rest").c_str(),
                               "  info  accelerometer at rest mean %f %f %f | sd %f %f %f | p-p %f %f %f",
                               &am[0], &am[1], &am[2], &asd[0], &asd[1], &asd[2], &app[0], &app[1], &app[2]) == 9;
        bool okg = std::sscanf(line_with(o, "gyroscope at rest").c_str(),
                               "  info  gyroscope at rest mean %f %f %f | sd %f %f %f | p-p %f %f %f",
                               &gm[0], &gm[1], &gm[2], &gsd[0], &gsd[1], &gsd[2], &gpp[0], &gpp[1], &gpp[2]) == 9;
        chk(oka && std::fabs(am[2] - 9.80f) < 0.002f && std::fabs(am[1] + 0.20f) < 0.002f, "accelerometer means recovered");
        chk(oka && std::fabs(asd[0] - 0.010f) < 0.001f && std::fabs(asd[1] - 0.020f) < 0.001f &&
            std::fabs(asd[2] - 0.030f) < 0.001f, "accelerometer sd is the injected 0.01, 0.02, 0.03 m/s2");
        chk(oka && std::fabs(app[2] - 0.060f) < 0.002f, "peak-to-peak is twice the sd for a two-level signal");
        const float d_dps = 2.0f / 900.0f * 57.2957795f;                 // 2 LSB in deg/s
        chk(okg && std::fabs(gsd[0] - d_dps) < 0.002f && std::fabs(gm[0] - d_dps) < 0.002f,
            "gyro sd and offset are the injected 2 LSB (0.127 deg/s)");
        float tilt = 0, rate = 0, off = 0, per_min = 0;
        bool okt = std::sscanf(line_with(o, "smallest tilt seen").c_str(), "  info  smallest tilt seen %f deg", &tilt) == 1;
        bool okr = std::sscanf(line_with(o, "smallest turn rate seen").c_str(), "  info  smallest turn rate seen %f deg/s", &rate) == 1;
        bool oko = std::sscanf(line_with(o, "gyro offset").c_str(),
                               "  info  gyro offset %f deg/s, which would add up to %f deg", &off, &per_min) == 2;
        chk(okt && std::fabs(tilt - 0.53f) < 0.011f, "smallest tilt = asin(3 x 0.03 / 9.81) = 0.53 deg");
        chk(okr && std::fabs(rate - 0.38f) < 0.011f, "smallest turn rate = 3 x 0.127 = 0.38 deg/s");
        chk(oko && std::fabs(off - d_dps) < 0.002f && std::fabs(per_min - 60.0f * d_dps) < 0.1f,
            "gyro offset and its heading drift per minute (0.127 deg/s -> 7.6 deg/min)");
        chk(has(o, "(1 LSB = 0.010)") && has(o, "(1 LSB = 0.0637)"), "one-step resolution printed (0.010 m/s2, 0.0637 deg/s)");
        chk(has(o, "magnetometer at rest"), "NDOF prints the magnetometer noise");
        chk(has(o, "PASS  board was still"), "a still board is reported as still");
    }
    {
        reset_world(); noise_gyro_lsb = 45.0f;                          // 0.05 rad/s of wobble: hand-held
        std::string o = cmd('n', hook_noise);
        chk(has(o, "WARN  board was still") && has(o, "put it on a table"), "a shaking board is a WARN with the fix named");
    }
    {
        reset_world();
        cmd('m', hook_static);
        std::string o = cmd('n', hook_noise);
        chk(!has(o, "magnetometer at rest"), "IMUPLUS has no magnetometer line");
        cmd('m', hook_static);                                          // back to NDOF for the tests below
        chk(g_mode == MODE_NDOF, "mode restored to NDOF");
    }

    std::printf("p: peak hold\n");
    {
        reset_world(); shake_amp = 30.0f;
        std::string o = cmd('p', hook_motion);
        float pa = 0, pg = 0, tl = 0, g_ = 0, lo = 0, hi = 0, d1 = 0, d2 = 0, d3 = 0, d4 = 0;
        bool oka = std::sscanf(line_with(o, "peak acceleration").c_str(), "  info  peak acceleration %f m/s2 = %f g", &pa, &g_) == 2;
        bool okg = std::sscanf(line_with(o, "peak rotation rate").c_str(), "  info  peak rotation rate %f deg/s", &pg) == 1;
        bool okt = std::sscanf(line_with(o, "max tilt of Z axis").c_str(), "  info  max tilt of Z axis %f deg", &tl) == 1;
        bool oks = std::sscanf(line_with(o, "accelerometer swing").c_str(),
                               "  info  accelerometer swing x %f..%f y %f..%f", &lo, &hi, &d1, &d2) == 4;
        (void)d3; (void)d4;
        chk(oka && std::fabs(pa - 31.56f) < 0.3f && std::fabs(g_ - 3.22f) < 0.05f, "peak acceleration 31.6 m/s2 = 3.2 g (30 shake plus gravity)");
        chk(okg && std::fabs(pg - 344.0f) < 2.0f, "peak rotation rate 344 deg/s (6 rad/s)");
        chk(okt && std::fabs(tl - 50.0f) < 1.0f, "max tilt 50 deg");
        chk(oks && std::fabs(lo + 30.0f) < 0.3f && std::fabs(hi - 30.0f) < 0.3f, "accelerometer x swing -30..+30");
        chk(!has(o, "WARN  accelerometer range"), "no clipping warning at 3.2 g");
        chk(has(o, "PASS  I2C reads"), "reads clean during the motion");
    }
    {
        reset_world(); shake_amp = 39.2f;                               // right at 4 g
        std::string o = cmd('p', hook_motion);
        chk(has(o, "WARN  accelerometer range") && has(o, "clipping"), "a peak near 4 g is flagged as probable clipping");
    }

    std::printf("failure and recovery of the chip\n");
    {
        reset_world();
        hostsim::bno.present = false;
        std::string o = cmd('i', hook_static);
        chk(has(o, "IMU init FAILED at: chip ID before reset"), "init names the step that failed");
        hostsim::bno.present = true;
        Serial.out.clear();
        loop();                                                         // g_up is false: retries
        chk(has(Serial.out, "IMU is up in NDOF mode.") && has(Serial.out, "RESULT:"), "loop retries and recovers");
    }

    std::printf("unknown key and pin safety\n");
    {
        reset_world();
        std::string o = cmd('z', hook_static);
        chk(has(o, "Unknown command 'z'"), "unknown command answered");
        bool touched = false;
        for (int p = 0; p < 64; p++) if (hostsim::pins[p].mode != 0) touched = true;
        chk(!touched, "no GPIO was configured (only the I2C pins, through Wire)");
        chk(hostsim::pins[0].mode == 0, "BOOT pin untouched");
    }

    std::printf("\n%s\n", g_fail ? "SOME FUNCTION-TEST CHECKS FAILED" : "all function-test checks passed");
    return g_fail ? 1 : 0;
}
