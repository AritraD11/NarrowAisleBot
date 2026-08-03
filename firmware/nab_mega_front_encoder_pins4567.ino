/*
 * ====================================================================
 *  NAB - MEGA FRONT ENCODER TEST, RELOCATED PINS (D4-D7)
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  WHY THIS VERSION
 *    The D2/D3 swap test showed the broken behavior stays with the
 *    D2/D3 wiring position, not with either encoder - whichever unit
 *    was plugged into D2/D3 came out broken, whichever was on D4/D5
 *    came out clean, in both directions of the swap. That points at a
 *    bad physical connection specific to D2/D3 (loose jumper, worn
 *    breadboard contact, or that Mega pin) - not the encoders.
 *
 *    This version retires D2/D3 entirely and puts both channels on
 *    fresh pins: FR on D4/D5, FL on D6/D7. Direct wiring, no level
 *    shifter, same as the last test.
 *
 *  WIRING
 *    FR-A -> Mega D4        FL-A -> Mega D6
 *    FR-B -> Mega D5        FL-B -> Mega D7
 *    Encoder 5V (both) -> Mega 5V or your existing buck - either is fine
 *    Encoder GND (both) -> Mega GND - must be common
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

const uint8_t FR_A = 4, FR_B = 5;
const uint8_t FL_A = 6, FL_B = 7;

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
    Serial.println(F("  MEGA FRONT ENCODER TEST - relocated off D2/D3"));
    Serial.println(F("  Direct wiring, no level shifter."));
    Serial.println(F("  Nothing prints until you turn a wheel by hand."));
    Serial.println(F("========================================================"));
    Serial.println(F("#  FR  A=D4  B=D5"));
    Serial.println(F("#  FL  A=D6  B=D7"));
    Serial.println(F("# fmt: t_ms,motor,dir,d_counts,total_counts"));
}

void loop() {
    poll(fr, FR_A, FR_B, "FR");
    poll(fl, FL_A, FL_B, "FL");
}
