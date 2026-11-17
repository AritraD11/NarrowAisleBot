/*
 * nab_imu_i2c_scan_esp32.ino — is the BNO055 on the bus, and where?
 *
 * Bench diagnostic for when the hardware can't be opened. Independent of the
 * drive firmware, so it separates a wiring, strap or address problem from a
 * bug in aislebot_esp32.ino's IMU driver. FLASHING THIS REPLACES THE DRIVE
 * FIRMWARE: re-flash aislebot_esp32.ino afterwards. It never touches a motor
 * or encoder pin, so it is safe with the motors unpowered or powered.
 *
 * Every 3 s it prints:
 *   1. the arduino-esp32 core and IDF versions (the BNO055 wants core 3.2+)
 *   2. for the planned SDA (GPIO14) and SCL (GPIO13): whether the line is
 *      held low, and whether the breakout is pulling it up
 *   3. a census of the free GPIOs (0 2 5 12 13 14 15 27): which ones have
 *      something pulling them up. The BNO055 breakout pulls both SDA and SCL
 *      up, so a wire that lands on the wrong ESP32 pin shows up here.
 *   4. a full 0x08-0x77 scan on the planned pins, the chip ID read both ways
 *      (repeated start, as the firmware does, and stop-then-start)
 *   5. a probe of 0x28 and 0x29 on every other ordered pair of the pins that
 *      have a pull-up, plus the swapped planned pair
 *   6. a verdict that says what to do next
 *
 * The pull-up test is a release test: drive the pin low, let go, look 50 us
 * later. A pull-up brings it back high in about a microsecond; a floating pin
 * stays low. That doesn't depend on the ESP32's internal pull strength.
 *
 * Serial Monitor: 921600 baud (same as the drive firmware).
 * BOARD: ESP32 Dev Module, arduino-esp32 core 3.x. Library: none (Wire).
 */

#include <Wire.h>

const int      PLAN_SDA = 14;     // BNO055 SDA, per the integration plan
const int      PLAN_SCL = 13;     // BNO055 SCL
const uint32_t I2C_HZ   = 100000;

// Pins this sketch is willing to wiggle. Deliberately none of the motor
// (4 16 17 18 19 21 22 23) or encoder (25 26 32 33 34 35 36 39) pins, and
// not the UART (1 3) or flash (6-11) pins.
const int CAND[] = {0, 2, 5, 12, 13, 14, 15, 27};
const int NCAND  = (int)(sizeof(CAND) / sizeof(CAND[0]));

struct ScanResult {
    int     found;      // devices that ACKed
    uint8_t bno_addr;   // 0x28 or 0x29 if a BNO055 answered there, else 0
    int     id_rs;      // CHIP_ID via repeated start, -1 if the read failed
    int     id_stop;    // CHIP_ID via stop then start, -1 if the read failed
};

static int readChipId(uint8_t addr, bool repeated_start) {
    Wire.beginTransmission(addr);
    Wire.write((uint8_t)0x00);                              // CHIP_ID
    if (Wire.endTransmission(!repeated_start) != 0) return -1;
    if (Wire.requestFrom((int)addr, 1) != 1) return -1;
    return Wire.read();
}

// full = every address 0x08-0x77. Otherwise only the two BNO055 addresses.
// Prints a line only when something answers.
static ScanResult scanBus(int sda, int scl, bool full) {
    ScanResult r = {0, 0, -1, -1};
    Wire.begin(sda, scl, I2C_HZ);
    Wire.setTimeOut(10);
    uint8_t lo = full ? 0x08 : 0x28;
    uint8_t hi = full ? 0x78 : 0x2A;
    for (uint8_t a = lo; a < hi; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() != 0) continue;
        r.found++;
        Serial.printf("    SDA=GPIO%d SCL=GPIO%d: answers at 0x%02X", sda, scl, (unsigned)a);
        if (a == 0x28 || a == 0x29) {
            int rs   = readChipId(a, true);
            int stop = readChipId(a, false);
            Serial.printf("   CHIP_ID: repeated-start %s0x%02X, stop-start %s0x%02X",
                          rs   < 0 ? "FAILED " : "", rs   < 0 ? 0u : (unsigned)rs,
                          stop < 0 ? "FAILED " : "", stop < 0 ? 0u : (unsigned)stop);
            if (rs == 0xA0 || stop == 0xA0) {
                r.bno_addr = a;
                r.id_rs    = rs;
                r.id_stop  = stop;
                Serial.print("   <- BNO055");
            }
        }
        Serial.println();
    }
    Wire.end();
    return r;
}

// True if something external pulls the pin up. Drive low, let go, look 50 us
// later: a pull-up (10 k against ~20 pF) is back high within a microsecond,
// a floating pin stays where it was left.
static bool pulledUp(int pin) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    delayMicroseconds(200);
    pinMode(pin, INPUT);
    delayMicroseconds(50);
    bool high = digitalRead(pin) == HIGH;
    pinMode(pin, INPUT);
    return high;
}

// With the internal pull-up on, an idle line reads high. LOW means it is
// held down: a short to ground, or a chip stuck driving it.
static bool heldLow(int pin) {
    pinMode(pin, INPUT_PULLUP);
    delay(2);
    bool low = digitalRead(pin) == LOW;
    pinMode(pin, INPUT);
    return low;
}

static bool inSet(const int* s, int n, int v) {
    for (int i = 0; i < n; i++) if (s[i] == v) return true;
    return false;
}

void setup() {
    Serial.begin(921600);
    delay(2000);   // the BNO055 needs ~650 ms after power-up, and the monitor needs to open
    Serial.println();
    Serial.println("=== NAB BNO055 I2C scan ===");
#ifdef ESP_ARDUINO_VERSION_MAJOR
    Serial.printf("arduino-esp32 core %d.%d.%d\n", ESP_ARDUINO_VERSION_MAJOR,
                  ESP_ARDUINO_VERSION_MINOR, ESP_ARDUINO_VERSION_PATCH);
#endif
#ifdef ARDUINO_ARCH_ESP32
    Serial.printf("ESP-IDF %s\n", ESP.getSdkVersion());
#endif
}

void loop() {
    Serial.println("--- scan ---");

    // 1. The planned pins.
    bool sda_pu = pulledUp(PLAN_SDA), scl_pu = pulledUp(PLAN_SCL);
    Serial.printf("  planned SDA GPIO%d: %s, %s\n", PLAN_SDA,
                  heldLow(PLAN_SDA) ? "HELD LOW" : "idles high",
                  sda_pu ? "pulled up by the breakout" : "NO pull-up");
    Serial.printf("  planned SCL GPIO%d: %s, %s\n", PLAN_SCL,
                  heldLow(PLAN_SCL) ? "HELD LOW" : "idles high",
                  scl_pu ? "pulled up by the breakout" : "NO pull-up");

    // 2. Census of the free pins. GPIO0 has the BOOT button's own pull-up and
    //    is shown but never used.
    int up[NCAND], nup = 0;
    Serial.print("  pins with a pull-up:");
    for (int i = 0; i < NCAND; i++) {
        bool pu = pulledUp(CAND[i]);
        Serial.printf(" %d:%s", CAND[i], pu ? "YES" : "-");
        if (pu && CAND[i] != 0) up[nup++] = CAND[i];
    }
    Serial.println("   (0 is the BOOT button, ignore it)");

    // 3. Full scan on the planned pins.
    ScanResult plan = scanBus(PLAN_SDA, PLAN_SCL, true);
    if (plan.found == 0) Serial.println("    nothing answers on the planned pins");

    // 4. Probe the BNO055 addresses on every other ordered pair of the pins
    //    that have a pull-up, plus the planned pins swapped.
    int cs[NCAND + 2], nc = 0;
    for (int i = 0; i < nup; i++) cs[nc++] = up[i];
    if (!inSet(cs, nc, PLAN_SDA)) cs[nc++] = PLAN_SDA;
    if (!inSet(cs, nc, PLAN_SCL)) cs[nc++] = PLAN_SCL;
    int bsda = -1, bscl = -1;
    uint8_t baddr = 0;
    int bid = -1;
    if (plan.bno_addr) { bsda = PLAN_SDA; bscl = PLAN_SCL; baddr = plan.bno_addr; bid = plan.id_rs; }
    for (int i = 0; i < nc && !baddr; i++) {
        for (int j = 0; j < nc && !baddr; j++) {
            if (i == j || (cs[i] == PLAN_SDA && cs[j] == PLAN_SCL)) continue;
            ScanResult r = scanBus(cs[i], cs[j], false);
            if (r.bno_addr) { bsda = cs[i]; bscl = cs[j]; baddr = r.bno_addr; bid = r.id_rs; }
        }
    }

    // 5. Verdict.
    Serial.print("VERDICT: ");
    if (baddr && bsda == PLAN_SDA && bscl == PLAN_SCL && baddr == 0x28) {
        if (bid == 0xA0)
            Serial.println("BNO055 found at 0x28 on the planned pins. Wiring and straps are fine. "
                           "If aislebot_esp32.ino still says NOT_FOUND, the problem is its driver or "
                           "the core version above (needs 3.2+). Send this output.");
        else
            Serial.println("BNO055 found at 0x28, but it only reads with stop-then-start, not "
                           "repeated start, which the driver uses. Send this output.");
    } else if (baddr && bsda == PLAN_SDA && bscl == PLAN_SCL) {
        Serial.println("BNO055 found at 0x29: its ADR pin is HIGH. Tell Claude to switch the "
                       "firmware to 0x29 (one constant), or tie ADR to GND.");
    } else if (baddr && bsda == PLAN_SCL && bscl == PLAN_SDA) {
        Serial.println("BNO055 found only with SDA and SCL SWAPPED. Tell Claude: swap IMU_SDA_PIN "
                       "and IMU_SCL_PIN (two constants), or swap the wires.");
    } else if (baddr) {
        bool strap = (bsda == 0 || bsda == 2 || bsda == 5 || bsda == 12 || bsda == 15 ||
                      bscl == 0 || bscl == 2 || bscl == 5 || bscl == 12 || bscl == 15);
        Serial.printf("BNO055 answers at 0x%02X with SDA=GPIO%d, SCL=GPIO%d, not the planned "
                      "pins. Tell Claude these two numbers and the firmware can use them. %s\n",
                      (unsigned)baddr, bsda, bscl,
                      strap ? "One of them is a boot-strapping pin (0 2 5 12 15): it works "
                                "after boot but can disturb boot, so Claude will need to check."
                            : "");
    } else if (sda_pu && scl_pu) {
        Serial.println("Both planned lines reach the breakout and are pulled up, but no BNO055 "
                       "answers. The wires are fine. Suspect the board's settings: PS0 and PS1 "
                       "not strapped to GND on a clone board (the chip may be in UART mode), "
                       "or not a Bosch BNO055. Send a photo or the silkscreen text of the "
                       "board's pins.");
    } else if (scl_pu && !sda_pu) {
        Serial.printf("SCL (GPIO%d) reaches the breakout but SDA (GPIO%d) does not, and no other "
                      "free pin picks it up. The SDA wire is open somewhere (a loose jumper or a "
                      "bad crimp), or it went to a pin this sketch can't test (a motor or "
                      "encoder pin). It needs a hand on the wire.\n", PLAN_SCL, PLAN_SDA);
    } else if (sda_pu && !scl_pu) {
        Serial.printf("SDA (GPIO%d) reaches the breakout but SCL (GPIO%d) does not, and no other "
                      "free pin picks it up. The SCL wire is open somewhere (a loose jumper or a "
                      "bad crimp), or it went to a pin this sketch can't test. It needs a hand "
                      "on the wire.\n", PLAN_SDA, PLAN_SCL);
    } else if (nup > 0) {
        Serial.printf("Neither planned pin is pulled up, but %d other free pin(s) are (the YES "
                      "entries above). The wires may be on the wrong ESP32 pins. Send this output.\n",
                      nup);
    } else {
        Serial.println("Nothing on any free pin is pulled up. The breakout is unpowered or "
                       "unconnected: check VIN to 3V3 and GND to GND, and that both signal "
                       "wires touch their pins.");
    }
    Serial.println();
    delay(3000);
}
