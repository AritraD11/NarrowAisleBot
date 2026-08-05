/*
 * ====================================================================
 *  NAB - MEGA FRONT ENCODER TEST, THROUGH THE LEVEL SHIFTER
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  PURPOSE
 *    The GTK08 encoders were already proven clean on the Mega WITHOUT
 *    a level shifter (21,033 edges, 0 invalid, both channels healthy).
 *    The ESP32 test through the level shifter came back noisy - sparse
 *    +/-1 blips with no real accumulation, not real hand-turning.
 *
 *    This test puts the level shifter's A-side (3.3V) output in front
 *    of the Mega instead, using the same interrupt-proven decode logic
 *    that already validated these encoders. If this comes back clean,
 *    the shifter chain is fine and the fault is ESP32-side. If this
 *    ALSO comes back noisy, the shifter/wiring chain itself is guilty,
 *    independent of which microcontroller is reading it.
 *
 *  WIRING  (only VCCA/OE move - everything else stays as-is)
 *    TXS0108E VCCA -> Mega 3.3V
 *    TXS0108E OE   -> Mega 3.3V   (tied to VCCA, same rule as before)
 *    TXS0108E VCCB -> your existing 5V buck output (unchanged)
 *    TXS0108E GND  -> common ground: Mega + buck + encoder (one node)
 *    A1 -> Mega D2   (FR-A)
 *    A2 -> Mega D3   (FR-B)
 *    A3 -> Mega D4   (FL-A)
 *    A4 -> Mega D5   (FL-B)
 *    B1-B4 -> unchanged, same encoder wires already landed there
 *
 *  BEHAVIOR
 *    Prints nothing while idle. A row appears only when a channel's
 *    position changes - i.e. only while you're turning that wheel.
 *    Turn ONE wheel at a time, by hand.
 *
 *  fmt: t_ms,motor,dir,d_counts,total_counts
 *  BAUD 115200
 * ====================================================================
 */

const uint8_t FR_A = 2, FR_B = 3;
const uint8_t FL_A = 4, FL_B = 5;

// x4 quadrature decode, indexed by (prevState<<2)|currState, state=(A<<1)|B
const int8_t QDEC[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0
};

struct Chan {
    uint8_t prevState;
    long    pos;
    long    lastPrintedPos;
    unsigned long lastPrintMs;
};
Chan fr, fl;

void initChan(Chan &c, uint8_t pinA, uint8_t pinB) {
    c.prevState = (digitalRead(pinA) << 1) | digitalRead(pinB);
    c.pos = 0;
    c.lastPrintedPos = 0;
    c.lastPrintMs = millis();
}

void poll(Chan &c, uint8_t pinA, uint8_t pinB, const char* name) {
    uint8_t a = digitalRead(pinA);
    uint8_t b = digitalRead(pinB);
    uint8_t s = (a << 1) | b;
    if (s != c.prevState) {
        int8_t d = QDEC[(c.prevState << 2) | s];
        c.pos += d;   // invalid (both-changed) transitions just don't move pos
        c.prevState = s;
    }

    long delta = c.pos - c.lastPrintedPos;
    unsigned long now = millis();
    if (delta != 0 && (now - c.lastPrintMs) >= 30) {   // small batching window
        Serial.print(now);   Serial.print(',');
        Serial.print(name);  Serial.print(',');
        Serial.print(delta > 0 ? "FWD" : "REV"); Serial.print(',');
        Serial.print(delta); Serial.print(',');
        Serial.println(c.pos);
        c.lastPrintedPos = c.pos;
        c.lastPrintMs = now;
    }
}

void setup() {
    Serial.begin(115200);
    delay(300);

    pinMode(FR_A, INPUT); pinMode(FR_B, INPUT);
    pinMode(FL_A, INPUT); pinMode(FL_B, INPUT);
    initChan(fr, FR_A, FR_B);
    initChan(fl, FL_A, FL_B);

    Serial.println();
    Serial.println(F("========================================================"));
    Serial.println(F("  MEGA FRONT ENCODER TEST - reading through level shifter"));
    Serial.println(F("  VCCA/OE = Mega 3.3V | VCCB = 5V buck | GND common"));
    Serial.println(F("  Nothing prints until you turn a wheel by hand."));
    Serial.println(F("========================================================"));
    Serial.println(F("#  FR  A=D2  B=D3"));
    Serial.println(F("#  FL  A=D4  B=D5"));
    Serial.println(F("# fmt: t_ms,motor,dir,d_counts,total_counts"));
}

void loop() {
    poll(fr, FR_A, FR_B, "FR");
    poll(fl, FL_A, FL_B, "FL");
}
