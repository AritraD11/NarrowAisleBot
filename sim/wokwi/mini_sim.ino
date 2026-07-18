/*
 * MiniAisleBot — Wokwi kinematics simulation
 * ==========================================
 * Runs the SAME asymmetric mecanum inverse kinematics as the real firmware,
 * in a simulator you can open at wokwi.com (no hardware needed).
 *
 *   3 slide pots  = vx (forward), vy (right strafe), wz (CCW yaw)
 *   4 LEDs        = FR, FL, RR, RL  — brightness ∝ |wheel speed| (PWM)
 *   Serial (115200) prints the 4 signed wheel speeds, each wheel's
 *   direction, and a forward-kinematics round-trip so you can confirm
 *   the IK ↔ FK pair is consistent.
 *
 * Paste mini_sim.ino + diagram.json into a new Wokwi ESP32 project.
 * Move the pots and watch the LEDs + serial monitor. Centre = zero.
 *
 * See docs/Mini_Prototype_Architecture.md §4 for the equations.
 */

// ── Prototype geometry (matches firmware ROBOT_PROFILE = MINI) ──
const float R        = 0.040f;   // wheel radius
const float L1       = 0.150f;   // outer longitudinal (FR, RL)
const float L2       = 0.120f;   // inner longitudinal (FL, RR)
const float D        = 0.075f;   // half-track
const float K_OUTER  = L1 + D;   // 0.225
const float K_INNER  = L2 + D;   // 0.195

const float MAX_LIN   = 0.45f;   // m/s at full stick
const float MAX_ANG   = 2.0f;    // rad/s at full stick
const float MAX_WHEEL = 22.0f;   // rad/s clamp → LED full brightness

// ── Pins ──
const int PIN_VX = 34;   // ADC — vx pot
const int PIN_VY = 35;   // ADC — vy pot
const int PIN_WZ = 32;   // ADC — wz pot
const int LED_FR = 25;
const int LED_FL = 26;
const int LED_RR = 27;
const int LED_RL = 14;
const int LED_PINS[4] = {LED_FR, LED_FL, LED_RR, LED_RL};
const char* NAME[4]   = {"FR", "FL", "RR", "RL"};

// Map a 12-bit ADC reading (0..4095, centre 2048) to [-range, +range]
float potToRange(int pin, float range) {
    int raw = analogRead(pin);
    float n = (raw - 2048.0f) / 2048.0f;      // -1 .. +1
    if (n > 1) n = 1; if (n < -1) n = -1;
    if (fabs(n) < 0.05f) n = 0;               // deadzone
    return n * range;
}

void ikAsymmetric(float vx, float vy, float wz, float* w) {
    w[0] = (vx + vy + wz * K_OUTER) / R;   // FR outer
    w[1] = (vx - vy - wz * K_INNER) / R;   // FL inner
    w[2] = (vx - vy + wz * K_INNER) / R;   // RR inner
    w[3] = (vx + vy - wz * K_OUTER) / R;   // RL outer

    float mx = 0;
    for (int i = 0; i < 4; i++) if (fabs(w[i]) > mx) mx = fabs(w[i]);
    if (mx > MAX_WHEEL) for (int i = 0; i < 4; i++) w[i] *= MAX_WHEEL / mx;
}

// Forward kinematics — should reconstruct (vx,vy,wz) from the wheel speeds
void fkAsymmetric(float* w, float& vx, float& vy, float& wz) {
    vx = (R / 4.0f) * ( w[0] + w[1] + w[2] + w[3]);
    vy = (R / 4.0f) * ( w[0] - w[1] - w[2] + w[3]);
    wz = (R / (2.0f * (L1 + L2 + 2.0f * D))) * ( w[0] - w[1] + w[2] - w[3]);
}

void setup() {
    Serial.begin(115200);
    for (int i = 0; i < 4; i++) ledcAttach(LED_PINS[i], 5000, 8);
    Serial.println("MiniAisleBot IK sim — move the pots (centre = 0)");
}

void loop() {
    float vx = potToRange(PIN_VX, MAX_LIN);
    float vy = potToRange(PIN_VY, MAX_LIN);
    float wz = potToRange(PIN_WZ, MAX_ANG);

    float w[4];
    ikAsymmetric(vx, vy, wz, w);

    for (int i = 0; i < 4; i++) {
        int duty = (int)(fabs(w[i]) / MAX_WHEEL * 255.0f);
        if (duty > 255) duty = 255;
        ledcWrite(LED_PINS[i], duty);
    }

    static unsigned long last = 0;
    if (millis() - last > 250) {
        last = millis();
        float fvx, fvy, fwz;
        fkAsymmetric(w, fvx, fvy, fwz);
        Serial.printf("cmd  vx=%+.2f vy=%+.2f wz=%+.2f  |  ",
                      vx, vy, wz);
        for (int i = 0; i < 4; i++)
            Serial.printf("%s=%+6.2f(%s) ", NAME[i], w[i],
                          w[i] > 0.1 ? "fwd" : w[i] < -0.1 ? "rev" : "---");
        Serial.printf(" |  FK vx=%+.2f vy=%+.2f wz=%+.2f\n", fvx, fvy, fwz);
    }
    delay(20);
}
