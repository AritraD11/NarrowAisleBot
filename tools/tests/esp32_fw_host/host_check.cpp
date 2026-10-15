// Compiles the REAL aislebot_esp32.ino against the host stand-ins in
// stubs/ and steps it. Run through tools/tests/esp32_firmware_hostcheck.py,
// which builds this, runs it, and feeds the [IMU] lines it captures into
// the shipped esp32_bridge parser.
//
// What this proves: the sketch compiles (as C++23, -Wall -Wextra), the
// IMU driver's init / decode / recovery logic does what it says against
// a register model, every line the firmware prints keeps the format the
// Pi depends on, and only motion commands feed the watchdog.
// What it can't prove: anything about the real arduino-esp32 core, the
// real chip, or timing. Flash it and read the boot banner for that.
#include "Arduino.h"
#include "Wire.h"

#include "../../../aislebot_esp32.ino"

#include <vector>

static int g_fail = 0;
static void chk(bool cond, const char* label) {
    std::printf("  %s  %s\n", cond ? "PASS" : "FAIL", label);
    if (!cond) g_fail++;
}

static std::vector<std::string> lines_of(const std::string& s) {
    std::vector<std::string> out;
    size_t a = 0;
    while (a < s.size()) {
        size_t b = s.find('\n', a);
        if (b == std::string::npos) b = s.size();
        std::string ln = s.substr(a, b - a);
        if (!ln.empty() && ln.back() == '\r') ln.pop_back();
        if (!ln.empty()) out.push_back(ln);
        a = b + 1;
    }
    return out;
}

static size_t fields(const std::string& ln) {
    size_t n = 1;
    for (char c : ln) if (c == ',') n++;
    return n;
}

static void put16(uint8_t reg, int16_t v) {
    hostsim::bno.regs[reg]     = (uint8_t)(v & 0xFF);
    hostsim::bno.regs[reg + 1] = (uint8_t)((uint16_t)v >> 8);
}

static void set_sample(int16_t qw, int16_t qx, int16_t qy, int16_t qz,
                       int16_t gx, int16_t gy, int16_t gz,
                       int16_t ax, int16_t ay, int16_t az) {
    put16(0x08, ax); put16(0x0A, ay); put16(0x0C, az);
    put16(0x14, gx); put16(0x16, gy); put16(0x18, gz);
    put16(0x20, qw); put16(0x22, qx); put16(0x24, qy); put16(0x26, qz);
}

static std::string take_output() {
    std::string s = Serial.out;
    Serial.out.clear();
    return s;
}

int main() {
    std::string all_output;

    std::printf("boot\n");
    setup();
    all_output += take_output();
    chk(Serial.tx_set_before_begin && Serial.tx_buffer == 1024,
        "TX buffer set to 1024 before Serial.begin()");
    chk(all_output.find("v3.1") != std::string::npos, "banner says v3.1");

    std::printf("command watchdog: only motion feeds it\n");
    const char* housekeeping[] = {"P", "?", "L1", "N1", "N0", "N?", "I", "W1", "Y1", "V,1"};
    for (const char* c : housekeeping) {
        last_cmd_ms = 0;
        processSerialCommand(c);
        char label[80];
        std::snprintf(label, sizeof(label), "<%s> leaves the watchdog alone", c);
        chk(last_cmd_ms == 0, label);
    }
    const char* motion[] = {"V,0.1,0.1,0.1,0.1", "B,0.0,0.0,0.0", "T,0,0.1", "M,0,0,0,0"};
    for (const char* c : motion) {
        last_cmd_ms = 0;
        processSerialCommand(c);
        char label[80];
        std::snprintf(label, sizeof(label), "<%s> feeds the watchdog", c);
        chk(last_cmd_ms == millis(), label);
    }
    processSerialCommand("V,0,0,0,0");
    all_output += take_output();

    std::printf("telemetry line: v3.0 bytes, one write\n");
    float tgt[4] = {0.5f, -1.25f, 2.0f, 0.0f}, act[4] = {0.48f, -1.2f, 1.99f, 0.0f};
    int pwm[4] = {25, -49, 84, 0};
    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].slewed_target = tgt[i];
        motors[i].actual_velocity = act[i];
        motors[i].pwm_output = pwm[i];
        motors[i].error = 0.02f * (float)i;
        motors[i].ff_output = 18.5f;
        motors[i].integral = 0.004f;
        motors[i].position_rad = -12.3456 * (i + 1);
    }
    for (int mode = 1; mode <= 2; mode++) {
        char cmd[8];
        std::snprintf(cmd, sizeof(cmd), "L%d", mode);
        processSerialCommand(cmd);
        take_output();
        Serial.writes = 0;
        outputSerialTelemetry();
        std::string got = take_output();
        // The v3.0 sequence of printf calls, reproduced verbatim.
        char exp[400];
        int n = std::snprintf(exp, sizeof(exp), "%lu", millis());
        for (int i = 0; i < NUM_MOTORS; i++)
            n += std::snprintf(exp + n, sizeof(exp) - n, ",%.3f,%.3f,%d",
                               motors[i].slewed_target, motors[i].actual_velocity,
                               motors[i].pwm_output);
        if (mode >= 2)
            for (int i = 0; i < NUM_MOTORS; i++)
                n += std::snprintf(exp + n, sizeof(exp) - n, ",%.3f,%.1f,%.1f,%.3f",
                                   motors[i].error, motors[i].ff_output,
                                   Ki * motors[i].integral, (float)motors[i].position_rad);
        std::snprintf(exp + n, sizeof(exp) - n, "\r\n");
        char label[80];
        std::snprintf(label, sizeof(label), "<L%d> line byte-identical to v3.0", mode);
        chk(got == exp, label);
        std::snprintf(label, sizeof(label), "<L%d> line sent in exactly one write", mode);
        chk(Serial.writes == 1, label);
        std::snprintf(label, sizeof(label), "<L%d> line has %d fields", mode, mode == 1 ? 13 : 29);
        chk(fields(lines_of(got).empty() ? "" : lines_of(got)[0]) == (mode == 1 ? 13u : 29u), label);
    }
    processSerialCommand("L0");
    all_output += take_output();

    std::printf("<R> is deferred to the PID task\n");
    processSerialCommand("R");
    chk(odom_reset_req, "<R> raises odom_reset_req");
    chk(motors[0].position_rad != 0.0, "<R> doesn't write position_rad from core 0");
    odom_reset_req = false;
    all_output += take_output();

    std::printf("IMU init against the register model\n");
    ImuLoop L;
    imuTaskBegin(L);                        // exactly what imuTask() does first
    chk(Wire.running && Wire.sda == 14 && Wire.scl == 13 && Wire.freq == 100000,
        "I2C started on SDA 14 / SCL 13 at 100 kHz");
    chk(Wire.timeout_ms == 10, "I2C timeout 10 ms");
    chk(hostsim::pins[27].mode == OUTPUT_OPEN_DRAIN && hostsim::pins[27].level == HIGH,
        "RST on GPIO27 open-drain and released");
    uint64_t t0 = hostsim::now_us;
    imuServiceOnce(L);
    std::string out = take_output();
    all_output += out;
    chk(imu_health.state == IMU_RUN, "state RUN after init");
    chk(hostsim::bno.regs[0x3D] == 0x08, "OPR_MODE = IMUPLUS (0x08)");
    chk(hostsim::bno.regs[0x3B] == 0x06, "UNIT_SEL = 0x06 (m/s^2, rad/s)");
    chk(hostsim::bno.regs[0x41] == 0x24 && hostsim::bno.regs[0x42] == 0x00,
        "axis map 0x24 / 0x00 written");
    chk(hostsim::bno.soft_resets == 1, "one software reset during init");
    chk(out.find("[IMUS,UP,chip=0xA0,sw=0x0311,sys=5]") != std::string::npos,
        "prints [IMUS,UP,chip=0xA0,sw=0x0311,sys=5]");
    double init_s = (double)(hostsim::now_us - t0) / 1e6;
    std::printf("    init took %.2f s of simulated time\n", init_s);
    chk(init_s < 3.0, "init bounded under 3 s");

    std::printf("IMU sample decode and the [IMU] line\n");
    // q = (1,0,0,0), gz = 0.2 rad/s (180 LSB), az = 9.81 m/s^2 (981 LSB)
    set_sample(16384, 0, 0, 0, 0, 0, 180, 0, 0, 981);
    imuServiceOnce(L);
    chk(imu_health.samples == 1, "one sample published");
    processSerialCommand("N1,100");
    take_output();
    hostsim::now_us += 20000;
    outputImuStream();
    out = take_output();
    char exp1[128];
    std::snprintf(exp1, sizeof(exp1),
                  "[IMU]1.00000,0.00000,0.00000,0.00000,0.0000,0.0000,0.2000,0.00,0.00,9.81,%lu\r\n",
                  (unsigned long)imu_latest.t_us);
    chk(out == exp1, "[IMU] line exactly as expected for q=(1,0,0,0) gz=0.2 az=9.81");
    std::printf("IMU_LINE:%s", out.c_str());
    outputImuStream();
    chk(take_output().empty(), "same sample is never sent twice");

    // A 90 degree yaw quaternion and mixed rates, for the bridge round-trip
    set_sample(11585, 0, 0, 11585, -90, 45, -270, 12, -5, 979);
    imuServiceOnce(L);
    hostsim::now_us += 20000;
    outputImuStream();
    out = take_output();
    chk(out.rfind("[IMU]", 0) == 0, "second sample streamed");
    std::printf("IMU_LINE:%s", out.c_str());
    chk(lines_of(out).size() == 1 && fields(lines_of(out)[0]) == 11, "[IMU] line has 11 fields");

    std::printf("IMU duplicate, bad quaternion, stream off\n");
    uint32_t seq = imu_latest.seq;
    imuServiceOnce(L);
    chk(imu_health.dup_samples == 1 && imu_latest.seq == seq, "unchanged registers counted as a duplicate");
    set_sample(0, 0, 0, 0, 1, 2, 3, 4, 5, 981);
    imuServiceOnce(L);
    chk(imu_health.bad_samples == 1 && imu_latest.seq == seq, "zero quaternion rejected, not published");
    set_sample(16384, 0, 0, 0, 0, 0, 9, 0, 0, 980);
    imuServiceOnce(L);
    processSerialCommand("N0");
    take_output();
    hostsim::now_us += 20000;
    outputImuStream();
    chk(take_output().empty(), "<N0> stops the stream");

    std::printf("IMU recovery ladder\n");
    hostsim::bno.fail_all = true;
    uint32_t reinits0 = imu_health.reinits;
    for (int i = 0; i < 5; i++) imuServiceOnce(L);
    out = take_output();
    all_output += out;
    chk(imu_health.state == IMU_INIT, "5 failed reads move the IMU to INIT");
    chk(out.find("[IMUS,DOWN,i2c_fails=5]") != std::string::npos, "prints [IMUS,DOWN,i2c_fails=5]");
    chk(imu_health.reinits == reinits0 + 1, "reinit counted");
    imuServiceOnce(L);
    imuServiceOnce(L);
    out = take_output();
    all_output += out;
    chk(imu_health.state == IMU_DEAD, "IMU DEAD while the bus stays wedged");
    size_t nf = 0;
    for (const auto& ln : lines_of(out)) if (ln.rfind("[IMUS,NOT_FOUND", 0) == 0) nf++;
    chk(nf == 1, "NOT_FOUND printed once, not on every retry");
    hostsim::bno.fail_all = false;
    imuServiceOnce(L);
    out = take_output();
    all_output += out;
    chk(imu_health.state == IMU_RUN && out.find("[IMUS,UP") != std::string::npos,
        "comes back UP once the bus recovers");

    std::printf("IMU SYS_STATUS error triggers a re-init\n");
    hostsim::bno.regs[0x39] = 1;
    hostsim::bno.regs[0x3A] = 7;
    bool went_down = false;
    for (int i = 0; i < 120 && !went_down; i++) {
        set_sample(16384, 0, 0, 0, 0, 0, (int16_t)i, 0, 0, 981);
        hostsim::bno.regs[0x39] = 1;
        imuServiceOnce(L);
        went_down = imu_health.state == IMU_INIT;
    }
    out = take_output();
    all_output += out;
    chk(went_down && out.find("[IMUS,DOWN,sys_err=7]") != std::string::npos,
        "SYS_STATUS=1 seen at housekeeping and re-init requested");
    imuServiceOnce(L);
    chk(imu_health.state == IMU_RUN, "re-init succeeds");
    all_output += take_output();

    std::printf("<NR> forces a re-init\n");
    uint32_t r0 = imu_health.reinits;
    processSerialCommand("NR");
    imuServiceOnce(L);
    chk(imu_health.reinits == r0 + 1 && imu_health.state == IMU_RUN, "<NR> re-inits and returns to RUN");
    all_output += take_output();

    std::printf("every non-data line stays under the bridge's 9-field fallback\n");
    processSerialCommand("H");
    processSerialCommand("I");
    processSerialCommand("?");
    processSerialCommand("N?");
    processSerialCommand("Z");
    all_output += take_output();
    size_t checked = 0, too_wide = 0;
    for (const auto& ln : lines_of(all_output)) {
        bool data = (ln[0] >= '0' && ln[0] <= '9') || ln.rfind("[IMU]", 0) == 0;
        if (data) continue;
        checked++;
        if (fields(ln) >= 9) {
            too_wide++;
            std::printf("    too wide (%zu fields): %s\n", fields(ln), ln.c_str());
        }
    }
    std::printf("    %zu status/help lines checked\n", checked);
    chk(checked > 40 && too_wide == 0, "no status line has 9 or more comma fields");

    std::printf("\n%s\n", g_fail ? "SOME CHECKS FAILED" : "all firmware checks passed");
    return g_fail ? 1 : 0;
}
