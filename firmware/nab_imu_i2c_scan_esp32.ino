/*
 * nab_imu_i2c_scan_esp32.ino — is the BNO055 on the bus, and where?
 *
 * Bench diagnostic. Independent of the drive firmware, so it can tell a
 * wiring, strap or address problem from a bug in aislebot_esp32.ino's IMU
 * driver. FLASHING THIS REPLACES THE DRIVE FIRMWARE: re-flash
 * aislebot_esp32.ino (v3.1) afterwards. Keep motor power off meanwhile; this
 * sketch never touches a motor pin.
 *
 * Every 3 s it prints, for the pins the integration plan uses
 * (SDA = GPIO14, SCL = GPIO13):
 *   1. the core and IDF versions (the BNO055 wants arduino-esp32 3.2+)
 *   2. whether each line idles high or is held low
 *   3. every I2C address that answers, 0x08-0x77, with the chip ID read
 *      two ways (repeated start, as the firmware does, and stop-then-start)
 *   4. the same scan with SDA and SCL swapped, in case two wires are crossed
 *   5. a verdict
 *
 * Serial Monitor: 921600 baud (same as the drive firmware).
 *
 * BOARD: ESP32 Dev Module, arduino-esp32 core 3.x. Library: none (Wire).
 */

#include <Wire.h>

const int      PIN_SDA = 14;      // BNO055 SDA, per the integration plan
const int      PIN_SCL = 13;      // BNO055 SCL
const uint32_t I2C_HZ  = 100000;

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

static ScanResult scanBus(int sda, int scl) {
    ScanResult r = {0, 0, -1, -1};
    Wire.begin(sda, scl, I2C_HZ);
    Wire.setTimeOut(20);
    for (uint8_t a = 0x08; a < 0x78; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() != 0) continue;
        r.found++;
        Serial.printf("    answers at 0x%02X", (unsigned)a);
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
    if (r.found == 0) Serial.println("    nothing answers");
    Wire.end();
    return r;
}

// A line that is high with the internal pull-up on is idle and free. One
// that reads LOW is held low: a short to ground, a wire on the wrong pin, or
// a chip stuck driving it. The pull-down read is only a hint: if it reads
// HIGH, something external (the breakout's own pull-ups) is pulling the
// line up, which means the breakout is powered and the wire reaches it.
static void lineCheck(int pin, const char* name) {
    pinMode(pin, INPUT_PULLUP);
    delay(5);
    int up = digitalRead(pin);
    pinMode(pin, INPUT_PULLDOWN);
    delay(5);
    int down = digitalRead(pin);
    pinMode(pin, INPUT);
    Serial.printf("  %s on GPIO%d: %s; %s\n", name, pin,
                  up ? "idles high" : "HELD LOW (short to ground, wrong pin, or a stuck chip)",
                  down ? "an external pull-up is present (board powered and connected)"
                       : "no external pull-up seen (board unpowered, wire not touching, or a board without pull-ups)");
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
    lineCheck(PIN_SDA, "SDA");
    lineCheck(PIN_SCL, "SCL");

    Serial.printf("SDA = GPIO%d, SCL = GPIO%d (as planned):\n", PIN_SDA, PIN_SCL);
    ScanResult a = scanBus(PIN_SDA, PIN_SCL);
    Serial.printf("SDA = GPIO%d, SCL = GPIO%d (swapped):\n", PIN_SCL, PIN_SDA);
    ScanResult b = scanBus(PIN_SCL, PIN_SDA);

    Serial.print("VERDICT: ");
    if (a.bno_addr == 0x28) {
        if (a.id_rs == 0xA0)
            Serial.println("BNO055 found at 0x28 on the planned pins. Wiring and straps are fine. "
                           "If aislebot_esp32.ino still says NOT_FOUND, the problem is the driver "
                           "or the core version above (needs 3.2+). Send this output.");
        else
            Serial.println("BNO055 found at 0x28, but it only reads with stop-then-start, not "
                           "repeated start. The driver uses repeated start. Send this output.");
    } else if (a.bno_addr == 0x29) {
        Serial.println("BNO055 found at 0x29: its ADR pin is HIGH. Tie ADR to GND for 0x28, or "
                       "tell Claude to switch the firmware to 0x29.");
    } else if (b.bno_addr != 0) {
        Serial.println("BNO055 found only with SDA and SCL SWAPPED. Swap the two wires.");
    } else if (a.found + b.found > 0) {
        Serial.println("Something answers, but it is not a BNO055 (no chip ID 0xA0 at 0x28 or "
                       "0x29). Check which board this really is.");
    } else {
        Serial.println("Nothing answers on either pin order. Check, in order: VIN to 3V3 and "
                       "GND to GND; the SDA/SCL wires actually touch the pins (and that SDA/SCL "
                       "are not on the board's UART pins); PS0 and PS1 strapped to GND on "
                       "clone boards; the breakout's power LED, if it has one.");
    }
    Serial.println();
    delay(3000);
}
