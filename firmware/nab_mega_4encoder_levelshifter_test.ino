/*
 * ====================================================================
 *  NAB - MEGA: ALL 4 ENCODERS THROUGH THE 8-CHANNEL LEVEL SHIFTER
 *
 *  Aritra Das (25D0074) - IIT Bombay - Prof. Ambarish Kunwar
 * ====================================================================
 *
 *  PURPOSE
 *    Independent confirmation that all four encoders and all eight
 *    level-shifter channels work, using the Mega instead of the ESP32.
 *    Hand-turn each wheel; nothing prints until something moves.
 *
 *  WIRING
 *    Level shifter LV+  -> Mega 3.3V        (LV must be the LOWER side)
 *    Level shifter LV-  -> Mega GND
 *    Level shifter HV+  -> 5V  (Mega 5V or buck)
 *    Level shifter HV-  -> same GND node
 *
 *    Encoder side (HV, 5 V)        Mega side (LV, 3.3 V)
 *      H0 = FR-A                     L0 -> D4
 *      H1 = FR-B                     L1 -> D5
 *      H2 = FL-A                     L2 -> D6
 *      H3 = FL-B                     L3 -> D7
 *      H4 = RR-A                     L4 -> D8
 *      H5 = RR-B                     L5 -> D9
 *      H6 = RL-A                     L6 -> D10
 *      H7 = RL-B                     L7 -> D11
 *
 *    All four encoders: Red -> 5V, Black -> the common GND node.
 *
 *    WIRE COLOURS DIFFER BY ENCODER TYPE - check the physical wire:
 *      GTK08     (FR, FL): Green = A, White = B, Yellow = Z (unused)
 *      RMCS-2086 (RR, RL): Yellow = A, Green = B
 *
 *  NOTE ON LOGIC LEVELS
 *    With LV+ = 3.3 V the shifter presents 3.3 V logic to the Mega.
 *    The ATmega2560 needs VIH >= 0.6 x 5 V = 3.0 V for a valid HIGH,
 *    so 3.3 V is above threshold but with only ~0.3 V of margin. That
 *    is in spec and works, but it is why the inputs below are plain
 *    INPUT and NOT INPUT_PULLUP: the Mega's internal pull-up goes to
 *    5 V and would fight the shifter's own 3.3 V pull-up, parking the
 *    line at an ambiguous voltage.
 *
 *  KEYS
 *    v   verdict table for all four channels
 *    z   zero all counters
 *    i   live pin levels
 *    h   help
 *
 *  BAUD 115200
 * ====================================================================
 */

#define NUM_MOTORS 4

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};
const char* ENC_TYPE[NUM_MOTORS]    = {"GTK08", "GTK08", "optical", "optical"};

// Counts per revolution at the wheel. Fronts carry GTK08 (1000 PPR x4
// x46.566); rears keep the RMCS-2086 optical (500 lines x4 x46.566).
const float ENCODER_CPR[NUM_MOTORS] = {186264.0f, 186264.0f, 93132.0f, 93132.0f};

// Pins, for the banner and pinMode only - sampling uses direct port reads.
const uint8_t ENC_A_PINS[NUM_MOTORS] = {4, 6,  8, 10};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {5, 7,  9, 11};

// ====================================================================
// FAST SAMPLING - direct port reads
//
//   Mega 2560 pin -> port/bit:
//     D4  = PG5     D5  = PE3
//     D6  = PH3     D7  = PH4
//     D8  = PH5     D9  = PH6
//     D10 = PB4     D11 = PB5
//
//   Four port reads replace eight digitalRead() calls (~5 us each on
//   AVR), which matters because the encoders sit BEFORE the 47:1
//   gearbox - even a slow hand-turn produces a fast pulse train.
// ====================================================================

static inline void readStates(uint8_t* st) {
    uint8_t g = PING, e = PINE, h = PINH, b = PINB;
    uint8_t a0 = (g >> 5) & 1, b0 = (e >> 3) & 1;   // D4 , D5
    uint8_t a1 = (h >> 3) & 1, b1 = (h >> 4) & 1;   // D6 , D7
    uint8_t a2 = (h >> 5) & 1, b2 = (h >> 6) & 1;   // D8 , D9
    uint8_t a3 = (b >> 4) & 1, b3 = (b >> 5) & 1;   // D10, D11
    st[0] = (a0 << 1) | b0;
    st[1] = (a1 << 1) | b1;
    st[2] = (a2 << 1) | b2;
    st[3] = (a3 << 1) | b3;
}

// x4 quadrature table, indexed by (prevState<<2)|currState, state=(A<<1)|B
const int8_t QDEC[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0
};

// ====================================================================
// STATE
// ====================================================================

struct Chan {
    uint8_t  prevState;
    long     pos;
    long     lastReportedPos;
    long     minPos, maxPos;
    unsigned long edgeA, edgeB;
    unsigned long skips;
    unsigned long lastReportMs;
};
Chan ch[NUM_MOTORS];

const unsigned long REPORT_INTERVAL_MS = 60;

// ====================================================================
// HELPERS
// ====================================================================

void zeroCounters() {
    uint8_t st[NUM_MOTORS];
    readStates(st);
    unsigned long now = millis();
    for (int i = 0; i < NUM_MOTORS; i++) {
        ch[i].prevState       = st[i];
        ch[i].pos             = 0;
        ch[i].lastReportedPos = 0;
        ch[i].minPos          = 0;
        ch[i].maxPos          = 0;
        ch[i].edgeA = ch[i].edgeB = ch[i].skips = 0;
        ch[i].lastReportMs    = now;
    }
}

const char* verdictFor(int i) {
    long range = ch[i].maxPos - ch[i].minPos;
    unsigned long eA = ch[i].edgeA, eB = ch[i].edgeB;
    if (eA == 0 && eB == 0) return "NO_SIGNAL";
    if (eA == 0)            return "CH_A_DEAD";
    if (eB == 0)            return "CH_B_DEAD";
    float r = (float)eA / (float)eB;
    if (r < 0.5f || r > 2.0f) return "CH_IMBALANCE";
    if (range < 200)          return "BARELY_MOVED (turn it more)";
    return "HEALTHY";
}

void printVerdict() {
    Serial.println();
    Serial.println(F("=============== CHANNEL VERDICT ==============="));
    Serial.println(F("motor  total     range     eA        eB        ratio  sk    verdict"));
    for (int i = 0; i < NUM_MOTORS; i++) {
        long range = ch[i].maxPos - ch[i].minPos;
        float r = ch[i].edgeB ? ((float)ch[i].edgeA / (float)ch[i].edgeB) : 0.0f;
        Serial.print(MOTOR_NAMES[i]);   Serial.print(F("     "));
        Serial.print(ch[i].pos);        Serial.print(F("\t"));
        Serial.print(range);            Serial.print(F("\t"));
        Serial.print(ch[i].edgeA);      Serial.print(F("\t"));
        Serial.print(ch[i].edgeB);      Serial.print(F("\t"));
        Serial.print(r, 3);             Serial.print(F("  "));
        Serial.print(ch[i].skips);      Serial.print(F("\t"));
        Serial.println(verdictFor(i));
    }
    Serial.println(F("==============================================="));
    Serial.println(F("# HEALTHY on all four = encoders AND all 8 shifter channels good."));
    Serial.println(F("# NO_SIGNAL    -> nothing reaching that pin pair."));
    Serial.println(F("# CH_A/B_DEAD  -> one line of the pair not getting through."));
    Serial.println(F("# Turn each wheel a few full turns before trusting a verdict."));
}

void printLevels() {
    uint8_t st[NUM_MOTORS];
    readStates(st);
    Serial.println();
    for (int i = 0; i < NUM_MOTORS; i++) {
        Serial.print(F("#  ")); Serial.print(MOTOR_NAMES[i]);
        Serial.print(F(" A=D")); Serial.print(ENC_A_PINS[i]);
        Serial.print(F(" B=D")); Serial.print(ENC_B_PINS[i]);
        Serial.print(F("   lvl A")); Serial.print((st[i] >> 1) & 1);
        Serial.print(F(" B"));       Serial.print(st[i] & 1);
        Serial.print(F("   pos "));  Serial.print(ch[i].pos);
        Serial.print(F("  eA "));    Serial.print(ch[i].edgeA);
        Serial.print(F("  eB "));    Serial.println(ch[i].edgeB);
    }
}

void printHelp() {
    Serial.println();
    Serial.println(F("=== KEYS ==="));
    Serial.println(F("  v  verdict table    z  zero counters"));
    Serial.println(F("  i  live pin levels   h  help"));
}

// ====================================================================
// SETUP / LOOP
// ====================================================================

void setup() {
    Serial.begin(115200);
    delay(300);

    // Plain INPUT - no pull-ups. See the note in the header: the Mega's
    // 5 V internal pull-up would fight the shifter's 3.3 V pull-up.
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(ENC_A_PINS[i], INPUT);
        pinMode(ENC_B_PINS[i], INPUT);
    }
    zeroCounters();

    Serial.println();
    Serial.println(F("=========================================================="));
    Serial.println(F("  MEGA - 4 ENCODERS VIA 8-CHANNEL LEVEL SHIFTER"));
    Serial.println(F("  Turn each wheel BY HAND. Silence = idle, not a hang."));
    Serial.println(F("=========================================================="));
    Serial.println(F("#  FR A=D4  B=D5   | FL A=D6  B=D7"));
    Serial.println(F("#  RR A=D8  B=D9   | RL A=D10 B=D11"));
    Serial.println(F("#  LV+=3.3V  LV-=GND  HV+=5V  HV-=GND (one common ground)"));
    Serial.println(F("#  Encoders sit BEFORE the 47:1 gearbox, so one wheel turn"));
    Serial.println(F("#  is ~47 encoder revolutions - counts pile up fast."));
    printHelp();
    Serial.println();
    Serial.println(F("# fmt: t_ms motor dir d_counts tot rad/s A B eA eB sk"));
}

void loop() {
    // ---- sample ----
    uint8_t st[NUM_MOTORS];
    readStates(st);
    for (int i = 0; i < NUM_MOTORS; i++) {
        uint8_t s = st[i], ps = ch[i].prevState;
        if (s != ps) {
            if (((s >> 1) & 1) != ((ps >> 1) & 1)) ch[i].edgeA++;
            if ((s & 1)        != (ps & 1))        ch[i].edgeB++;
            int8_t d = QDEC[(ps << 2) | s];
            if (d != 0) {
                ch[i].pos += d;
                if (ch[i].pos > ch[i].maxPos) ch[i].maxPos = ch[i].pos;
                if (ch[i].pos < ch[i].minPos) ch[i].minPos = ch[i].pos;
            } else {
                ch[i].skips++;   // both channels changed between samples
            }
            ch[i].prevState = s;
        }
    }

    // ---- event-gated reporting ----
    unsigned long now = millis();
    for (int i = 0; i < NUM_MOTORS; i++) {
        long delta = ch[i].pos - ch[i].lastReportedPos;
        if (delta == 0) continue;
        if (now - ch[i].lastReportMs < REPORT_INTERVAL_MS) continue;

        float secs = (now - ch[i].lastReportMs) / 1000.0f;
        if (secs <= 0) secs = 0.001f;
        float rads = ((float)delta / ENCODER_CPR[i]) * 6.2831853f / secs;

        Serial.print(now);                        Serial.print(' ');
        Serial.print(MOTOR_NAMES[i]);             Serial.print(' ');
        Serial.print(delta > 0 ? F("FWD") : F("REV")); Serial.print(F(" d"));
        Serial.print(delta);                      Serial.print(F(" tot"));
        Serial.print(ch[i].pos);                  Serial.print(' ');
        Serial.print(rads, 2);                    Serial.print(F("rad/s A"));
        Serial.print((st[i] >> 1) & 1);           Serial.print(F(" B"));
        Serial.print(st[i] & 1);                  Serial.print(F(" eA"));
        Serial.print(ch[i].edgeA);                Serial.print(F(" eB"));
        Serial.print(ch[i].edgeB);                Serial.print(F(" sk"));
        Serial.println(ch[i].skips);

        ch[i].lastReportedPos = ch[i].pos;
        ch[i].lastReportMs    = now;
    }

    // ---- keys ----
    if (Serial.available()) {
        char c = Serial.read();
        if      (c == 'v' || c == 'V') printVerdict();
        else if (c == 'z' || c == 'Z') { zeroCounters(); Serial.println(F("# counters zeroed")); }
        else if (c == 'i' || c == 'I') printLevels();
        else if (c == 'h' || c == 'H' || c == '?') printHelp();
    }
}
