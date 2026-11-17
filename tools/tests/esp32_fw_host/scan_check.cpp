// Compiles firmware/nab_imu_i2c_scan_esp32.ino against the host stand-ins and
// runs its loop() through every wiring fault it is supposed to recognise, with
// a fake bus that models which ESP32 pins have a pull-up and which pins the
// BNO055 is wired to. Run through tools/tests/esp32_firmware_hostcheck.py.
//
// The scanner is what someone reads when the hardware can't be opened, so a
// wrong verdict sends them after the wrong fault. Each scenario asserts the
// verdict text, not just that the sketch compiles.
#include "Arduino.h"
#include "Wire.h"

#include "../../../firmware/nab_imu_i2c_scan_esp32.ino"

static int g_fail = 0;
static void chk(bool cond, const char* label) {
    std::printf("  %s  %s\n", cond ? "PASS" : "FAIL", label);
    if (!cond) g_fail++;
}

static std::string verdict_of(const std::string& out) {
    size_t a = out.find("VERDICT: ");
    if (a == std::string::npos) return "";
    size_t b = out.find('\n', a);
    return out.substr(a, b == std::string::npos ? std::string::npos : b - a);
}

struct World {
    bool pull13 = false, pull14 = false, pull27 = false, pull12 = false;
    bool chip = true;
    int  sda = 14, scl = 13;
    bool addr29 = false;
};

static std::string run(const World& w) {
    for (auto& p : hostsim::pins) { p.mode = 0; p.level = HIGH; p.ext_pullup = false; }
    hostsim::pins[0].ext_pullup  = true;                 // BOOT button, always
    hostsim::pins[13].ext_pullup = w.pull13;
    hostsim::pins[14].ext_pullup = w.pull14;
    hostsim::pins[27].ext_pullup = w.pull27;
    hostsim::pins[12].ext_pullup = w.pull12;
    hostsim::bno.present  = w.chip;
    hostsim::bno.sda_pin  = w.sda;
    hostsim::bno.scl_pin  = w.scl;
    hostsim::bno.addr29   = w.addr29;
    hostsim::bno.fail_all = false;
    Serial.out.clear();
    loop();
    return Serial.out;
}

static bool has(const std::string& s, const char* needle) {
    return s.find(needle) != std::string::npos;
}

int main() {
    setup();
    chk(has(Serial.out, "NAB BNO055 I2C scan"), "banner printed");
    Serial.out.clear();

    std::printf("good wiring\n");
    {
        World w; w.pull13 = w.pull14 = true;
        std::string out = run(w), v = verdict_of(out);
        chk(has(v, "BNO055 found at 0x28 on the planned pins"), "verdict: found on the planned pins");
        chk(has(out, "planned SDA GPIO14: idles high, pulled up by the breakout"), "SDA line reported pulled up");
        chk(has(out, "answers at 0x28   CHIP_ID: repeated-start 0xA0, stop-start 0xA0   <- BNO055"),
            "chip ID read both ways");
    }

    std::printf("the failure on the robot: SDA reaches nothing, SCL is fine\n");
    {
        World w; w.pull13 = true; w.pull14 = false; w.chip = false;
        std::string out = run(w), v = verdict_of(out);
        chk(has(v, "SCL (GPIO13) reaches the breakout but SDA (GPIO14) does not"), "verdict names the open SDA wire");
        chk(has(v, "needs a hand on the wire"), "verdict says it needs hands on the hardware");
        chk(has(out, "13:YES") && has(out, "14:-"), "census shows 13 pulled up and 14 not");
    }

    std::printf("SCL open, SDA fine\n");
    {
        World w; w.pull13 = false; w.pull14 = true; w.chip = false;
        std::string v = verdict_of(run(w));
        chk(has(v, "SDA (GPIO14) reaches the breakout but SCL (GPIO13) does not"), "verdict names the open SCL wire");
    }

    std::printf("SDA wire landed on GPIO27, software can follow it\n");
    {
        World w; w.pull13 = true; w.pull27 = true; w.pull14 = false; w.sda = 27; w.scl = 13;
        std::string out = run(w), v = verdict_of(out);
        chk(has(v, "SDA=GPIO27, SCL=GPIO13, not the planned pins"), "verdict reports the pins it found the chip on");
        chk(!has(v, "boot-strapping"), "GPIO27 is not flagged as a strapping pin");
        chk(has(out, "27:YES"), "census found GPIO27");
    }

    std::printf("SDA wire on GPIO12 (a boot-strapping pin)\n");
    {
        World w; w.pull13 = true; w.pull12 = true; w.pull14 = false; w.sda = 12; w.scl = 13;
        std::string v = verdict_of(run(w));
        chk(has(v, "SDA=GPIO12, SCL=GPIO13"), "verdict reports GPIO12");
        chk(has(v, "boot-strapping pin"), "strapping-pin warning present");
    }

    std::printf("both wires fine but no chip answers (straps, or the wrong chip)\n");
    {
        World w; w.pull13 = w.pull14 = true; w.chip = false;
        std::string v = verdict_of(run(w));
        chk(has(v, "Both planned lines reach the breakout") && has(v, "PS0 and PS1"),
            "verdict points at the PS0/PS1 straps");
    }

    std::printf("SDA and SCL crossed\n");
    {
        World w; w.pull13 = w.pull14 = true; w.sda = 13; w.scl = 14;
        std::string v = verdict_of(run(w));
        chk(has(v, "SWAPPED"), "verdict says swapped");
    }

    std::printf("ADR high (chip at 0x29)\n");
    {
        World w; w.pull13 = w.pull14 = true; w.addr29 = true;
        std::string v = verdict_of(run(w));
        chk(has(v, "0x29") && has(v, "ADR pin is HIGH"), "verdict says ADR is high");
    }

    std::printf("nothing powered or connected\n");
    {
        World w; w.chip = false;
        std::string v = verdict_of(run(w));
        chk(has(v, "Nothing on any free pin is pulled up"), "verdict says unpowered or unconnected");
    }

    std::printf("the sketch never wiggles a motor or encoder pin\n");
    {
        World w; w.pull13 = w.pull14 = true;
        for (auto& p : hostsim::pins) p.mode = 0;
        run(w);
        bool touched = false;
        const int forbidden[] = {1, 3, 4, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 21, 22, 23,
                                 25, 26, 32, 33, 34, 35, 36, 39};
        for (int pin : forbidden) if (hostsim::pins[pin].mode != 0) touched = true;
        chk(!touched, "no motor, encoder, UART or flash pin was configured");
    }

    std::printf("\n%s\n", g_fail ? "SOME SCANNER CHECKS FAILED" : "all scanner checks passed");
    return g_fail ? 1 : 0;
}
