/*
 * robot_mcu.ino - wheel velocity controller for the robot kit
 * ===========================================================
 *
 * The Raspberry Pi sends wheel velocity targets over USB serial. This sketch
 * closes a PID + feedforward loop per wheel on encoder feedback, enforces
 * the safety trips, and streams telemetry back. It is NarrowAisleBot's ESP32
 * v3.0 firmware generalised:
 *
 *   - any number of motors from 1 to 6           (NUM_MOTORS)
 *   - three motor driver styles                  (DRIVER_TYPE)
 *   - ESP32 hardware counters or interrupts      (ENCODER_BACKEND)
 *   - ESP32, AVR (Uno/Mega/Nano), RP2040, Teensy and other Arduino cores
 *
 * Every robot-specific number lives in robot_config.h, which generate.py
 * writes from robot_config.yaml. Do not put constants in this file.
 *
 * Board notes
 *   ESP32 (classic WROOM/WROVER): best choice. Arduino-ESP32 core 2.x or 3.x.
 *     The control loop runs in its own FreeRTOS task on core 1, serial on
 *     core 0, so a long telemetry line can never delay a control tick.
 *     PCNT counts encoder edges in silicon, no interrupt load at all.
 *   ESP32-C3: has no PCNT. Use encoder_backend: isr.
 *   AVR: everything runs from loop(). Use 115200 baud and control_hz 50.
 *     Every encoder pin that needs an interrupt must be an external-interrupt
 *     pin (Uno: 2, 3. Mega: 2, 3, 18, 19, 20, 21). The sketch checks this
 *     at boot and prints [ERR,ENC_PIN,...] if one is not.
 *
 * Wire protocol: see robot_base/protocol.py, or send <H>.
 */

#include <Arduino.h>
#include "robot_config.h"

#if defined(ARDUINO_ARCH_ESP32)
  #define KIT_ESP32 1
  #if defined(__has_include)
    #if __has_include("esp_arduino_version.h")
      #include "esp_arduino_version.h"
    #endif
  #endif
#endif

#if ENCODER_BACKEND == ENC_PCNT
  #ifndef KIT_ESP32
    #error "encoder_backend pcnt needs an ESP32. Set mcu.encoder_backend: isr and regenerate."
  #endif
  #include "driver/pcnt.h"
#endif

#if defined(__AVR__) && PWM_BITS != 8
  #error "AVR analogWrite is 8-bit. Set mcu.pwm_bits: 8."
#endif

#if NUM_MOTORS < 1 || NUM_MOTORS > 6
  #error "NUM_MOTORS must be 1 to 6"
#endif

#define FIRMWARE_VERSION "robot_kit_mcu 1.0"

// ═════════════════════════════════════════════════════════════════════
//  1. Tunables that are not robot-specific
// ═════════════════════════════════════════════════════════════════════

static const float CTRL_DT = 1.0f / (float)CONTROL_HZ;
static const float VEL_FILTER_ALPHA = 0.4f;   // EMA on measured velocity
static const float D_FILTER_ALPHA = 0.25f;    // heavier, derivative amplifies noise
static const float KSTAT_FADE_LO = 0.05f;     // rad/s: no static term below this
static const float KSTAT_FADE_HI = 0.20f;     // rad/s: full static term above this

// Safety trips. All latch the E-STOP and print [TRIP,...].
static const float OVERSPEED_FACTOR = 1.30f;              // x max_wheel_speed
static const unsigned long OVERSPEED_TRIP_MS = 300;
static const int RUNAWAY_PWM_SAT = (PWM_MAX * 94) / 100;  // counts as saturated
static const float RUNAWAY_DECEL_TOL = 0.20f;             // rad/s over the window
static const unsigned long RUNAWAY_WINDOW_MS = 500;
static const unsigned long RUNAWAY_TRIP_MS = 500;
static const int STALL_PWM = (PWM_MAX * 98) / 100;
static const float STALL_SPEED = 0.15f;                   // rad/s
static const unsigned long STALL_TRIP_MS = 2000;

static const int LINE_MAX = 40 + NUM_MOTORS * 72;
#if defined(__AVR__)
static const int TX_RING = (LINE_MAX * 2 < 384) ? 384 : LINE_MAX * 2;
#else
static const int TX_RING = 2048;
#endif
static const int RX_MAX = 160;

// AVR's libm has no guaranteed fabsf/lroundf, so the sketch carries its own.
static inline float absf(float x) { return x < 0 ? -x : x; }
static inline long roundToLong(float x) { return (long)(x >= 0 ? x + 0.5f : x - 0.5f); }

// ═════════════════════════════════════════════════════════════════════
//  2. State
// ═════════════════════════════════════════════════════════════════════

struct Motor {
  float target;          // rad/s, commanded
  float slewed;          // rad/s, what the PID chases
  float actual;          // rad/s, filtered
  float prev_actual;
  float error;
  float integral;
  float dfilt;
  float ff;
  int pwm;               // -PWM_MAX .. +PWM_MAX
  int64_t total_counts;  // since boot or <R>, for odometry
  int32_t win[VEL_WINDOW];
  uint8_t win_idx;
  int32_t win_sum;
  unsigned long overspeed_since, runaway_since, stall_since, checkpoint_ms;
  float vel_checkpoint;
};

static Motor motors[NUM_MOTORS];
static float Kp = KP_INIT, Ki = KI_INIT, Kd = KD_INIT;
static float Kff[NUM_MOTORS], Kstat[NUM_MOTORS];
static float max_wheel_speed = MAX_WHEEL_SPEED;
static float max_wheel_accel = MAX_WHEEL_ACCEL;

enum EstopWhy { ES_NONE, ES_COMMAND, ES_OVERSPEED, ES_RUNAWAY, ES_STALL };
static volatile bool enabled = true;
static volatile bool estop = false;
static volatile uint8_t estop_why = ES_NONE;
static volatile bool watchdog_on = true;
static volatile bool trips_on = true;
static volatile bool open_loop = false;
static volatile unsigned long last_cmd_ms = 0;
static volatile bool watchdog_fired = false;
static volatile bool watchdog_report = false;
static volatile uint8_t telemetry_mode = 0;
static volatile unsigned long telemetry_interval_ms = (unsigned long)(1000.0f / TELEMETRY_HZ_DEFAULT);

// A trip is detected in the control step and printed by the serial side,
// so the two never write to Serial at the same time.
struct TripReport { volatile bool pending; uint8_t why; uint8_t motor; float v1, v2; };
static TripReport trip_report = {false, 0, 0, 0, 0};

#ifdef KIT_ESP32
static portMUX_TYPE cmd_mux = portMUX_INITIALIZER_UNLOCKED;
#define CMD_LOCK()   portENTER_CRITICAL(&cmd_mux)
#define CMD_UNLOCK() portEXIT_CRITICAL(&cmd_mux)
#else
#define CMD_LOCK()
#define CMD_UNLOCK()
#endif

// ═════════════════════════════════════════════════════════════════════
//  3. PWM output, portable
// ═════════════════════════════════════════════════════════════════════

#if defined(KIT_ESP32) && !(defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3)
// Arduino-ESP32 2.x: channels must be assigned by hand.
static int pwm_pin_of_ch[16];
static int pwm_channels = 0;
static int esp32ChannelFor(int pin) {
  for (int c = 0; c < pwm_channels; c++) if (pwm_pin_of_ch[c] == pin) return c;
  return -1;
}
#endif

static void pwmInit(int pin) {
  if (pin < 0) return;
#if defined(KIT_ESP32)
  #if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(pin, PWM_FREQ_HZ, PWM_BITS);
  ledcWrite(pin, 0);
  #else
  int ch = pwm_channels++;
  pwm_pin_of_ch[ch] = pin;
  ledcSetup(ch, PWM_FREQ_HZ, PWM_BITS);
  ledcAttachPin(pin, ch);
  ledcWrite(ch, 0);
  #endif
#elif defined(ARDUINO_ARCH_RP2040)
  pinMode(pin, OUTPUT);
  analogWriteFreq(PWM_FREQ_HZ);
  analogWriteRange(PWM_MAX);
  analogWrite(pin, 0);
#elif defined(TEENSYDUINO)
  pinMode(pin, OUTPUT);
  analogWriteResolution(PWM_BITS);
  analogWriteFrequency(pin, PWM_FREQ_HZ);
  analogWrite(pin, 0);
#else
  pinMode(pin, OUTPUT);   // AVR and the rest: 8-bit, frequency fixed by the core
  analogWrite(pin, 0);
#endif
}

static void pwmWrite(int pin, int duty) {
  if (pin < 0) return;
#if defined(KIT_ESP32)
  #if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pin, duty);
  #else
  ledcWrite(esp32ChannelFor(pin), duty);
  #endif
#else
  analogWrite(pin, duty);
#endif
}

static void setupMotorPins() {
  for (int i = 0; i < NUM_MOTORS; i++) {
#if DRIVER_TYPE == DRIVER_PWM_DIR
    pwmInit(PIN_A[i]);
    pinMode(PIN_B[i], OUTPUT); digitalWrite(PIN_B[i], LOW);
#elif DRIVER_TYPE == DRIVER_PWM_IN1_IN2
    pwmInit(PIN_A[i]);
    pinMode(PIN_B[i], OUTPUT); digitalWrite(PIN_B[i], LOW);
    pinMode(PIN_C[i], OUTPUT); digitalWrite(PIN_C[i], LOW);
#elif DRIVER_TYPE == DRIVER_DUAL_PWM
    pwmInit(PIN_A[i]);
    pwmInit(PIN_B[i]);
#else
  #error "unknown DRIVER_TYPE"
#endif
  }
}

// pwm is in the WHEEL's sense: positive = this wheel rolls the robot forward.
static void setMotorOutput(int i, int pwm) {
  int v = pwm * MOTOR_DIR[i];
  bool rev = v < 0;
  int a = v < 0 ? -v : v;
  if (a < MIN_PWM_OUT) a = 0;
  if (a > PWM_MAX) a = PWM_MAX;
#if DRIVER_TYPE == DRIVER_PWM_DIR
  digitalWrite(PIN_B[i], rev ? HIGH : LOW);
  pwmWrite(PIN_A[i], a);
#elif DRIVER_TYPE == DRIVER_PWM_IN1_IN2
  if (a == 0) {                       // both low = coast
    digitalWrite(PIN_B[i], LOW);
    digitalWrite(PIN_C[i], LOW);
  } else {
    digitalWrite(PIN_B[i], rev ? LOW : HIGH);
    digitalWrite(PIN_C[i], rev ? HIGH : LOW);
  }
  pwmWrite(PIN_A[i], a);
#elif DRIVER_TYPE == DRIVER_DUAL_PWM
  if (rev) { pwmWrite(PIN_A[i], 0); pwmWrite(PIN_B[i], a); }
  else     { pwmWrite(PIN_B[i], 0); pwmWrite(PIN_A[i], a); }
#endif
}

// ═════════════════════════════════════════════════════════════════════
//  4. Encoders
// ═════════════════════════════════════════════════════════════════════

#if ENCODER_BACKEND == ENC_PCNT

static void setupEncoders() {
  for (int i = 0; i < NUM_MOTORS; i++) {
    pcnt_unit_t unit = (pcnt_unit_t)i;
    // Channel 0: count A edges, direction from B.
    pcnt_config_t c0 = {};
    c0.pulse_gpio_num = ENC_A[i];
    c0.ctrl_gpio_num = ENC_B[i];
    c0.channel = PCNT_CHANNEL_0;
    c0.unit = unit;
    c0.pos_mode = PCNT_COUNT_INC;
    c0.neg_mode = PCNT_COUNT_DEC;
    c0.lctrl_mode = PCNT_MODE_REVERSE;
    c0.hctrl_mode = PCNT_MODE_KEEP;
    c0.counter_h_lim = 32767;
    c0.counter_l_lim = -32768;
    pcnt_unit_config(&c0);
  #if ENCODER_DECODING == 4
    // Channel 1: count B edges, direction from A. Together: x4.
    pcnt_config_t c1 = c0;
    c1.pulse_gpio_num = ENC_B[i];
    c1.ctrl_gpio_num = ENC_A[i];
    c1.channel = PCNT_CHANNEL_1;
    c1.pos_mode = PCNT_COUNT_DEC;
    c1.neg_mode = PCNT_COUNT_INC;
    pcnt_unit_config(&c1);
  #endif
    // ~1.25 us glitch filter (100 APB cycles). Raise it only if you see noise.
    pcnt_set_filter_value(unit, 100);
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
  }
}

// Counts since the last call, in the wheel's forward sense. The int16
// hardware counter is read and cleared every tick; at 100 Hz it would take
// 3.2 million counts per second to overflow it.
static int32_t readEncoderDelta(int i) {
  int16_t c = 0;
  pcnt_get_counter_value((pcnt_unit_t)i, &c);
  pcnt_counter_clear((pcnt_unit_t)i);
  return (int32_t)c * ENC_DIR[i];
}

#else  // ENC_ISR

static volatile int32_t enc_count[NUM_MOTORS];
static volatile uint8_t enc_state[NUM_MOTORS];
// Quadrature state table: index = (old AB << 2) | new AB. A leading B = +1.
static const int8_t QEM[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};

#ifdef KIT_ESP32
static portMUX_TYPE enc_mux = portMUX_INITIALIZER_UNLOCKED;
  #define ENC_LOCK()       portENTER_CRITICAL(&enc_mux)
  #define ENC_UNLOCK()     portEXIT_CRITICAL(&enc_mux)
  #define ENC_LOCK_ISR()   portENTER_CRITICAL_ISR(&enc_mux)
  #define ENC_UNLOCK_ISR() portEXIT_CRITICAL_ISR(&enc_mux)
  #define ISR_ATTR IRAM_ATTR
#else
  #define ENC_LOCK()       noInterrupts()
  #define ENC_UNLOCK()     interrupts()
  #define ENC_LOCK_ISR()
  #define ENC_UNLOCK_ISR()
  #define ISR_ATTR
#endif

static inline void encStep(int i) {
  uint8_t a = digitalRead(ENC_A[i]) ? 1 : 0;
  uint8_t b = digitalRead(ENC_B[i]) ? 1 : 0;
  ENC_LOCK_ISR();
#if ENCODER_DECODING == 4
  uint8_t s = (uint8_t)((a << 1) | b);
  enc_count[i] += QEM[(enc_state[i] << 2) | s];
  enc_state[i] = s;
#else
  enc_count[i] += (a != b) ? 1 : -1;      // x2: only A interrupts
#endif
  ENC_UNLOCK_ISR();
}

#define ENC_ISR_DEF(I) static void ISR_ATTR encIsr##I() { encStep(I); }
ENC_ISR_DEF(0)
#if NUM_MOTORS > 1
ENC_ISR_DEF(1)
#endif
#if NUM_MOTORS > 2
ENC_ISR_DEF(2)
#endif
#if NUM_MOTORS > 3
ENC_ISR_DEF(3)
#endif
#if NUM_MOTORS > 4
ENC_ISR_DEF(4)
#endif
#if NUM_MOTORS > 5
ENC_ISR_DEF(5)
#endif

typedef void (*IsrFn)();
static const IsrFn ENC_ISRS[NUM_MOTORS] = {
  encIsr0,
#if NUM_MOTORS > 1
  encIsr1,
#endif
#if NUM_MOTORS > 2
  encIsr2,
#endif
#if NUM_MOTORS > 3
  encIsr3,
#endif
#if NUM_MOTORS > 4
  encIsr4,
#endif
#if NUM_MOTORS > 5
  encIsr5,
#endif
};

static bool enc_pin_error = false;
static int enc_bad_pin = -1;

static void attachEnc(int pin, IsrFn fn) {
  int irq = digitalPinToInterrupt(pin);
  if (irq < 0) { enc_pin_error = true; enc_bad_pin = pin; return; }
  attachInterrupt(irq, fn, CHANGE);
}

static void setupEncoders() {
  for (int i = 0; i < NUM_MOTORS; i++) {
    pinMode(ENC_A[i], INPUT_PULLUP);
    pinMode(ENC_B[i], INPUT_PULLUP);
    enc_state[i] = (uint8_t)(((digitalRead(ENC_A[i]) ? 1 : 0) << 1) | (digitalRead(ENC_B[i]) ? 1 : 0));
    enc_count[i] = 0;
    attachEnc(ENC_A[i], ENC_ISRS[i]);
  #if ENCODER_DECODING == 4
    attachEnc(ENC_B[i], ENC_ISRS[i]);
  #endif
  }
}

static int32_t readEncoderDelta(int i) {
  ENC_LOCK();
  int32_t c = enc_count[i];
  enc_count[i] = 0;
  ENC_UNLOCK();
  return c * ENC_DIR[i];
}

#endif

// ═════════════════════════════════════════════════════════════════════
//  5. Controller: two-term feedforward + PID with headroom anti-windup
// ═════════════════════════════════════════════════════════════════════

static void resetMotorState(int i) {
  Motor& m = motors[i];
  m.target = m.slewed = 0;
  m.error = 0;
  m.integral = m.dfilt = 0;
  m.ff = 0;
  m.pwm = 0;
  m.overspeed_since = m.runaway_since = m.stall_since = 0;
}

static void stopAll() {
  open_loop = false;
  for (int i = 0; i < NUM_MOTORS; i++) {
    resetMotorState(i);
    setMotorOutput(i, 0);
  }
}

// pwm_ff = Kff * w + Kstat * sgn(w), with Kstat faded in at low speed so a
// tiny command does not produce a step in PWM.
static float feedforward(int i, float w) {
  float aw = absf(w);
  float ff = Kff[i] * w;
  if (aw > KSTAT_FADE_LO) {
    float fade = (aw - KSTAT_FADE_LO) / (KSTAT_FADE_HI - KSTAT_FADE_LO);
    if (fade > 1.0f) fade = 1.0f;
    ff += Kstat[i] * fade * (w > 0 ? 1.0f : -1.0f);
  }
  return ff;
}

static void computePID(int i, float dt) {
  Motor& m = motors[i];
  if (absf(m.slewed) < 0.01f) {        // at rest: coast, hold nothing
    m.error = -m.actual;
    m.integral = 0;
    m.dfilt = 0;
    m.ff = 0;
    m.pwm = 0;
    return;
  }
  m.ff = feedforward(i, m.slewed);
  m.error = m.slewed - m.actual;
  float p = Kp * m.error;
  // Derivative on measurement, not error: no kick when the Pi steps the target.
  float raw_d = -(m.actual - m.prev_actual) / dt;
  m.dfilt = D_FILTER_ALPHA * raw_d + (1.0f - D_FILTER_ALPHA) * m.dfilt;
  float d = Kd * m.dfilt;

  // Integral, clamped to the PWM headroom actually left after FF + P + D.
  // Windup is impossible and recovery from saturation is immediate.
  float base = m.ff + p + d;
  float iterm = 0;
  if (Ki > 1e-6f) {
    m.integral += m.error * dt;
    float hi = ((float)PWM_MAX - base) / Ki;
    float lo = (-(float)PWM_MAX - base) / Ki;
    if (lo > hi) { float t = lo; lo = hi; hi = t; }
    if (m.integral > hi) m.integral = hi;
    if (m.integral < lo) m.integral = lo;
    iterm = Ki * m.integral;
  } else {
    m.integral = 0;
  }
  float out = base + iterm;
  if (out > PWM_MAX) out = PWM_MAX;
  if (out < -PWM_MAX) out = -PWM_MAX;
  m.pwm = (int)roundToLong(out);
}

static void slewTarget(int i, float target, float dt) {
  Motor& m = motors[i];
  if (max_wheel_accel <= 0) { m.slewed = target; return; }
  float step = max_wheel_accel * dt;
  float diff = target - m.slewed;
  if (diff > step) m.slewed += step;
  else if (diff < -step) m.slewed -= step;
  else m.slewed = target;
}

static void latchTrip(uint8_t why, int i, float v1, float v2) {
  estop = true;
  estop_why = why;
  stopAll();
  trip_report.why = why;
  trip_report.motor = (uint8_t)i;
  trip_report.v1 = v1;
  trip_report.v2 = v2;
  trip_report.pending = true;
}

// The failure the runaway trip exists for: MOTOR_DIR and ENC_DIR disagree,
// the loop becomes positive feedback, and the wheel pins itself at full
// PWM the wrong way. "PWM one way, wheel the other" is also what a hard
// deceleration looks like, so it only trips if the wheel is NOT slowing.
static void checkTrips() {
  if (!trips_on) return;
  unsigned long now = millis();
  float over = max_wheel_speed * OVERSPEED_FACTOR;
  float runaway_min = max_wheel_speed * 0.2f < 1.0f ? max_wheel_speed * 0.2f : 1.0f;
  for (int i = 0; i < NUM_MOTORS; i++) {
    Motor& m = motors[i];
    float v = m.actual, av = absf(v);
    if (now - m.checkpoint_ms >= RUNAWAY_WINDOW_MS) { m.vel_checkpoint = av; m.checkpoint_ms = now; }

    if (av > over) {
      if (!m.overspeed_since) m.overspeed_since = now;
      else if (now - m.overspeed_since > OVERSPEED_TRIP_MS) { latchTrip(ES_OVERSPEED, i, v, over); return; }
    } else m.overspeed_since = 0;

    bool sat = abs(m.pwm) >= RUNAWAY_PWM_SAT;
    bool opposing = (v * (float)m.pwm < 0) && av > runaway_min;
    bool not_slowing = av >= m.vel_checkpoint - RUNAWAY_DECEL_TOL;
    if (sat && opposing && not_slowing) {
      if (!m.runaway_since) m.runaway_since = now;
      else if (now - m.runaway_since > RUNAWAY_TRIP_MS) { latchTrip(ES_RUNAWAY, i, (float)m.pwm, v); return; }
    } else m.runaway_since = 0;

    if (abs(m.pwm) >= STALL_PWM && av < STALL_SPEED) {
      if (!m.stall_since) m.stall_since = now;
      else if (now - m.stall_since > STALL_TRIP_MS) { latchTrip(ES_STALL, i, (float)m.pwm, v); return; }
    } else m.stall_since = 0;
  }
}

// One control tick. dt is the measured interval, so loop jitter on boards
// without an RTOS does not turn into a velocity error.
static void controlStep(float dt) {
  for (int i = 0; i < NUM_MOTORS; i++) {
    Motor& m = motors[i];
    int32_t d = readEncoderDelta(i);
    m.total_counts += d;
    m.win_sum += d - m.win[m.win_idx];
    m.win[m.win_idx] = d;
    m.win_idx = (uint8_t)((m.win_idx + 1) % VEL_WINDOW);
    float raw = ((float)m.win_sum / ENCODER_CPR[i]) * (2.0f * PI) / (dt * VEL_WINDOW);
    m.prev_actual = m.actual;
    m.actual = VEL_FILTER_ALPHA * raw + (1.0f - VEL_FILTER_ALPHA) * m.actual;
  }

  if (estop || !enabled) {
    for (int i = 0; i < NUM_MOTORS; i++) { resetMotorState(i); setMotorOutput(i, 0); }
    return;
  }

  if (watchdog_on && (millis() - last_cmd_ms > WATCHDOG_MS)) {
    if (!watchdog_fired) { watchdog_fired = true; watchdog_report = true; }
    for (int i = 0; i < NUM_MOTORS; i++) motors[i].target = 0;   // closed loop ramps down
    if (open_loop) for (int i = 0; i < NUM_MOTORS; i++) motors[i].pwm = 0;
  }

  if (open_loop) {
    for (int i = 0; i < NUM_MOTORS; i++) setMotorOutput(i, motors[i].pwm);
  } else {
    float tgt[NUM_MOTORS];
    CMD_LOCK();                          // all wheels from the same command
    for (int i = 0; i < NUM_MOTORS; i++) tgt[i] = motors[i].target;
    CMD_UNLOCK();
    for (int i = 0; i < NUM_MOTORS; i++) {
      slewTarget(i, tgt[i], dt);
      computePID(i, dt);
      setMotorOutput(i, motors[i].pwm);
    }
  }
  checkTrips();
}

// ═════════════════════════════════════════════════════════════════════
//  6. Non-blocking serial output
//
//  On AVR the hardware TX buffer is 64 bytes. A blocking 200-byte
//  telemetry line would stall loop(), and with it the control loop, for
//  ~17 ms at 115200 baud. Everything goes through this ring instead and is
//  drained as fast as the UART accepts it.
// ═════════════════════════════════════════════════════════════════════

static char tx_ring[TX_RING];
static uint16_t tx_head = 0, tx_tail = 0;
static unsigned long tx_stall_since = 0;
static uint16_t tx_dropped = 0;

static uint16_t txUsed() { return (uint16_t)((tx_head + TX_RING - tx_tail) % TX_RING); }
static uint16_t txFree() { return (uint16_t)(TX_RING - 1 - txUsed()); }

static void txPump() {
  if (tx_head == tx_tail) { tx_stall_since = 0; return; }
  int room = Serial.availableForWrite();
  if (room <= 0) {
    // Some cores never report room. Do not wait forever: after 20 ms,
    // write a small blocking chunk.
    if (!tx_stall_since) tx_stall_since = millis();
    if (millis() - tx_stall_since < 20) return;
    room = 16;
  }
  tx_stall_since = 0;
  while (room > 0 && tx_tail != tx_head) {
    uint16_t end = (tx_head > tx_tail) ? tx_head : TX_RING;
    uint16_t n = end - tx_tail;
    if (n > (uint16_t)room) n = (uint16_t)room;
    Serial.write((const uint8_t*)&tx_ring[tx_tail], n);
    tx_tail = (uint16_t)((tx_tail + n) % TX_RING);
    room -= n;
  }
}

// Queue a whole line or nothing. Telemetry may be dropped under load;
// replies wait for room (they matter more).
static bool txLine(const char* s, uint16_t n, bool must) {
  unsigned long t0 = millis();
  while (txFree() < n) {
    if (!must) { tx_dropped++; return false; }
    txPump();
    if (millis() - t0 > 200) { tx_dropped++; return false; }
  }
  for (uint16_t k = 0; k < n; k++) {
    tx_ring[tx_head] = s[k];
    tx_head = (uint16_t)((tx_head + 1) % TX_RING);
  }
  return true;
}

// A tiny line builder. Integer arithmetic for floats, because AVR's printf
// and scanf have no %f.
struct Line {
  char b[LINE_MAX];
  uint16_t n;
  Line() : n(0) {}
  void c(char ch) { if (n < LINE_MAX - 2) b[n++] = ch; }
  void s(const char* str) { while (*str) c(*str++); }
  void i(long v) {
    char t[12]; int k = 0;
    bool neg = v < 0;
    unsigned long u = neg ? (unsigned long)(-v) : (unsigned long)v;
    do { t[k++] = (char)('0' + (u % 10)); u /= 10; } while (u && k < 11);
    if (neg) c('-');
    while (k) c(t[--k]);
  }
  void f(float v, int dp) {
    if (v != v) { s("nan"); return; }
    long scale = 1;
    for (int k = 0; k < dp; k++) scale *= 10;
    if (v > 2.0e9f / scale) v = 2.0e9f / scale;
    if (v < -2.0e9f / scale) v = -2.0e9f / scale;
    long q = roundToLong(v * (float)scale);
    if (q < 0) { c('-'); q = -q; }
    i(q / scale);
    if (dp > 0) {
      c('.');
      long frac = q % scale;
      for (long d = scale / 10; d > 0; d /= 10) { c((char)('0' + (frac / d) % 10)); }
    }
  }
  void send(bool must) { c('\n'); txLine(b, n, must); n = 0; }
};

static void reply(const char* s) { Line l; l.s(s); l.send(true); }

// ═════════════════════════════════════════════════════════════════════
//  7. Telemetry
// ═════════════════════════════════════════════════════════════════════

static void sendTelemetry() {
  if (telemetry_mode == 0) return;
  Line l;
  l.i((long)millis());
  for (int i = 0; i < NUM_MOTORS; i++) {
    l.c(','); l.f(motors[i].slewed, 3);
    l.c(','); l.f(motors[i].actual, 3);
    l.c(','); l.i(motors[i].pwm);
  }
  if (telemetry_mode >= 2) {
    for (int i = 0; i < NUM_MOTORS; i++) {
      Motor& m = motors[i];
      l.c(','); l.f(m.error, 3);
      l.c(','); l.f(m.ff, 1);
      l.c(','); l.f(Ki * m.integral, 1);
      l.c(','); l.f((float)((double)m.total_counts * (2.0 * PI) / (double)ENCODER_CPR[i]), 4);
    }
  }
  l.send(false);
}

// ═════════════════════════════════════════════════════════════════════
//  8. Command parser
// ═════════════════════════════════════════════════════════════════════

static void setTargets(const float* v) {
  CMD_LOCK();
  if (open_loop) {       // leaving open loop: the old integral means nothing now
    open_loop = false;
    for (int i = 0; i < NUM_MOTORS; i++) { motors[i].integral = 0; motors[i].dfilt = 0; motors[i].slewed = 0; }
  }
  for (int i = 0; i < NUM_MOTORS; i++) {
    float t = v[i];
    if (t > max_wheel_speed) t = max_wheel_speed;
    if (t < -max_wheel_speed) t = -max_wheel_speed;
    motors[i].target = t;
  }
  CMD_UNLOCK();
}

static void printList(const char* tag, const float* vals, int dp) {
  Line l; l.c('['); l.s(tag);
  for (int i = 0; i < NUM_MOTORS; i++) { l.c(','); l.s(MOTOR_NAMES[i]); l.c('='); l.f(vals[i], dp); }
  l.c(']'); l.send(true);
}

static void printInfo() {
  Line l;
  l.s("[INFO,"); l.s(FIRMWARE_VERSION); l.c(','); l.s(ROBOT_NAME); l.c(']'); l.send(true);
  l.s("[MOTORS,"); l.i(NUM_MOTORS);
  for (int i = 0; i < NUM_MOTORS; i++) { l.c(','); l.s(MOTOR_NAMES[i]); }
  l.c(']'); l.send(true);
  l.s("[GAINS,Kp="); l.f(Kp, 3); l.s(",Ki="); l.f(Ki, 3); l.s(",Kd="); l.f(Kd, 3);
  l.s(",Hz="); l.i(CONTROL_HZ); l.c(']'); l.send(true);
  printList("FF", Kff, 3);
  printList("KSTAT", Kstat, 3);
  printList("CPR", ENCODER_CPR, 1);
  l.s("[LIMITS,Vmax="); l.f(max_wheel_speed, 3); l.s(",Accel="); l.f(max_wheel_accel, 3);
  l.s(",PWM_MAX="); l.i(PWM_MAX); l.s(",WD_MS="); l.i(WATCHDOG_MS); l.c(']'); l.send(true);
  l.s("[CONFIG,driver="); l.i(DRIVER_TYPE); l.s(",encoder="); l.s(ENCODER_BACKEND == ENC_PCNT ? "pcnt" : "isr");
  l.s(",decoding=x"); l.i(ENCODER_DECODING); l.s(",vel_window="); l.i(VEL_WINDOW);
  l.s(",baud="); l.i((long)SERIAL_BAUD); l.c(']'); l.send(true);
#if ENCODER_BACKEND == ENC_ISR
  if (enc_pin_error) { l.s("[ERR,ENC_PIN,"); l.i(enc_bad_pin); l.s(",not an interrupt pin]"); l.send(true); }
#endif
}

static void printState() {
  static const char* WHY[] = {"NONE", "COMMAND", "OVERSPEED", "RUNAWAY", "STALL"};
  Line l;
  l.s("[STATE,EN="); l.i(enabled); l.s(",WD="); l.i(watchdog_on); l.s(",TRIPS="); l.i(trips_on);
  l.s(",ESTOP="); l.i(estop); l.s(",WHY="); l.s(WHY[estop_why]);
  l.s(",MODE="); l.s(open_loop ? "OPENLOOP" : "PID"); l.s(",TXDROP="); l.i(tx_dropped); l.c(']');
  l.send(true);
  for (int i = 0; i < NUM_MOTORS; i++) {
    Motor& m = motors[i];
    l.c('['); l.s(MOTOR_NAMES[i]); l.s(",tgt="); l.f(m.target, 3); l.s(",slew="); l.f(m.slewed, 3);
    l.s(",act="); l.f(m.actual, 3); l.s(",pwm="); l.i(m.pwm); l.s(",err="); l.f(m.error, 3);
    l.s(",i="); l.f(m.integral, 4); l.s(",counts="); l.i((long)m.total_counts); l.c(']');
    l.send(true);
  }
}

static void printHelp() {
  static const char* const H[] = {
    "[HELP,<V,w0..wN-1>  wheel velocity targets rad/s (closed loop)]",
    "[HELP,<B,vx,vy,wz>  body twist; the MCU runs the inverse kinematics]",
    "[HELP,<M,p0..pN-1>  raw PWM; open loop until the next V/B/T. Send <W0> first for long holds]",
    "[HELP,<T,i,w>  one motor closed loop]",
    "[HELP,<S> E-STOP latches; <E1> enable and clear; <E0> disable]",
    "[HELP,<W1>/<W0> watchdog; <Y1>/<Y0> safety trips]",
    "[HELP,<G,kp,ki,kd>  <F,kff..>  <K,kstat..>  <A,accel>  <X,vmax>]",
    "[HELP,<L0> off  <L1[,hz]> basic  <L2[,hz]> extended telemetry]",
    "[HELP,<O> wheel angles  <R> zero them  <P> ping  <I> config  <?> state]",
  };
  for (unsigned k = 0; k < sizeof(H) / sizeof(H[0]); k++) reply(H[k]);
}

// Split "X,a,b,c" in place. Returns the number of fields.
static int splitFields(char* s, char** f, int maxf) {
  int n = 0;
  f[n++] = s;
  for (char* p = s; *p && n < maxf; p++) {
    if (*p == ',') { *p = 0; f[n++] = p + 1; }
  }
  return n;
}

static bool parseFloats(char** f, int count, float* out) {
  for (int k = 0; k < count; k++) {
    char* end;
    out[k] = (float)strtod(f[k], &end);
    if (end == f[k]) return false;
  }
  return true;
}

static void feedWatchdog() {
  last_cmd_ms = millis();
  watchdog_fired = false;
}

// Only motion commands (V, B, M, T) feed the watchdog. A status query or a
// telemetry change must never keep a stale velocity alive. (NarrowAisleBot's
// v3.0 fed it on every command; this is stricter on purpose.)
static void processCommand(char* cmd) {
  char* f[NUM_MOTORS + 4];
  int nf = splitFields(cmd, f, NUM_MOTORS + 4);
  char c0 = cmd[0], c1 = cmd[1];
  float v[NUM_MOTORS + 3];

  switch (c0) {
    case 'V':
      if (nf == NUM_MOTORS + 1 && parseFloats(f + 1, NUM_MOTORS, v)) { feedWatchdog(); setTargets(v); }
      else reply("[ERR,BAD_V]");
      break;

    case 'B':
      if (nf == 4 && parseFloats(f + 1, 3, v)) {
        float w[NUM_MOTORS], peak = 0;
        for (int i = 0; i < NUM_MOTORS; i++) {
          w[i] = IK_VX[i] * v[0] + IK_VY[i] * v[1] + IK_WZ[i] * v[2];
          if (absf(w[i]) > peak) peak = absf(w[i]);
        }
        if (peak > max_wheel_speed) for (int i = 0; i < NUM_MOTORS; i++) w[i] *= max_wheel_speed / peak;
        feedWatchdog();
        setTargets(w);
      } else reply("[ERR,BAD_B]");
      break;

    case 'M':
      if (nf == NUM_MOTORS + 1 && parseFloats(f + 1, NUM_MOTORS, v)) {
        feedWatchdog();
        CMD_LOCK();
        open_loop = true;
        for (int i = 0; i < NUM_MOTORS; i++) {
          int p = (int)roundToLong(v[i]);
          if (p > PWM_MAX) p = PWM_MAX;
          if (p < -PWM_MAX) p = -PWM_MAX;
          motors[i].target = motors[i].slewed = 0;
          motors[i].integral = 0;
          motors[i].pwm = p;
        }
        CMD_UNLOCK();
        Line l; l.s("[OK,M");
        for (int i = 0; i < NUM_MOTORS; i++) { l.c(','); l.i(motors[i].pwm); }
        l.c(']'); l.send(true);
      } else reply("[ERR,BAD_M]");
      break;

    case 'T':
      if (nf == 3 && parseFloats(f + 1, 2, v) && (int)v[0] >= 0 && (int)v[0] < NUM_MOTORS) {
        float w[NUM_MOTORS];
        for (int i = 0; i < NUM_MOTORS; i++) w[i] = open_loop ? 0 : motors[i].target;
        w[(int)v[0]] = v[1];
        feedWatchdog();
        setTargets(w);
        reply("[OK,T]");
      } else reply("[ERR,BAD_T]");
      break;

    case 'S':
      estop = true;
      estop_why = ES_COMMAND;
      stopAll();
      reply("[OK,ESTOP_LATCHED]");
      break;

    case 'E':
      if (c1 == '1') {
        enabled = true;
        estop = false;
        estop_why = ES_NONE;
        for (int i = 0; i < NUM_MOTORS; i++) resetMotorState(i);
        reply("[OK,ENABLED]");
      } else {
        enabled = false;
        stopAll();
        reply("[OK,DISABLED]");
      }
      break;

    case 'W': watchdog_on = (c1 == '1'); reply(watchdog_on ? "[OK,WDOG=1]" : "[OK,WDOG=0]"); break;
    case 'Y': trips_on = (c1 == '1'); reply(trips_on ? "[OK,TRIPS=1]" : "[OK,TRIPS=0]"); break;

    case 'G':
      if (nf == 4 && parseFloats(f + 1, 3, v)) {
        Kp = v[0]; Ki = v[1]; Kd = v[2];
        for (int i = 0; i < NUM_MOTORS; i++) motors[i].integral = 0;   // stale integral would kick
        Line l; l.s("[OK,GAINS,"); l.f(Kp, 3); l.c(','); l.f(Ki, 3); l.c(','); l.f(Kd, 3); l.c(']'); l.send(true);
      } else reply("[ERR,BAD_G]");
      break;

    case 'F':
    case 'K':
      if (nf == NUM_MOTORS + 1 && parseFloats(f + 1, NUM_MOTORS, v)) {
        float* dst = (c0 == 'F') ? Kff : Kstat;
        for (int i = 0; i < NUM_MOTORS; i++) dst[i] = v[i];
        printList(c0 == 'F' ? "OK,FF" : "OK,KSTAT", dst, 3);
      } else reply(c0 == 'F' ? "[ERR,BAD_F]" : "[ERR,BAD_K]");
      break;

    case 'A':
      if (nf == 2 && parseFloats(f + 1, 1, v) && v[0] >= 0) {
        max_wheel_accel = v[0];
        Line l; l.s("[OK,ACCEL="); l.f(max_wheel_accel, 3); l.c(']'); l.send(true);
      } else reply("[ERR,BAD_A]");
      break;

    case 'X':
      if (nf == 2 && parseFloats(f + 1, 1, v) && v[0] > 0 && v[0] <= 2.0f * MAX_WHEEL_SPEED) {
        max_wheel_speed = v[0];
        Line l; l.s("[OK,VMAX="); l.f(max_wheel_speed, 3); l.c(']'); l.send(true);
      } else reply("[ERR,BAD_X]");
      break;

    case 'L': {
      telemetry_mode = (c1 >= '0' && c1 <= '2') ? (uint8_t)(c1 - '0') : 0;
      if (nf >= 2 && parseFloats(f + 1, 1, v) && v[0] > 0) {
        unsigned long iv = (unsigned long)(1000.0f / v[0] + 0.5f);
        if (iv < 10) iv = 10;                       // 100 Hz ceiling
        telemetry_interval_ms = iv;
      }
      Line l; l.s("[OK,LOG="); l.i(telemetry_mode); l.s(",HZ="); l.f(1000.0f / telemetry_interval_ms, 1);
      l.c(']'); l.send(true);
      break;
    }

    case 'O': {
      Line l; l.s("[ODOM");
      for (int i = 0; i < NUM_MOTORS; i++) {
        l.c(','); l.f((float)((double)motors[i].total_counts * (2.0 * PI) / (double)ENCODER_CPR[i]), 4);
      }
      l.c(']'); l.send(true);
      break;
    }

    case 'R':
      for (int i = 0; i < NUM_MOTORS; i++) motors[i].total_counts = 0;
      reply("[OK,ODOM_ZEROED]");
      break;

    case 'P': reply("[PONG]"); break;
    case 'I': printInfo(); break;
    case '?': printState(); break;
    case 'H': printHelp(); break;
    default: {
      Line l; l.s("[ERR,UNKNOWN:"); l.c(c0); l.c(']'); l.send(true);
    }
  }
}

static char rx_buf[RX_MAX];
static int rx_len = 0;
static bool rx_in_frame = false;

static void readSerial() {
  int budget = 128;                    // bound the time spent here per call
  while (Serial.available() && budget-- > 0) {
    char ch = (char)Serial.read();
    if (ch == '<') { rx_in_frame = true; rx_len = 0; }
    else if (ch == '>' && rx_in_frame) {
      rx_in_frame = false;
      rx_buf[rx_len] = 0;
      if (rx_len > 0) processCommand(rx_buf);
    } else if (rx_in_frame) {
      if (rx_len < RX_MAX - 1) rx_buf[rx_len++] = ch;
      else { rx_in_frame = false; rx_len = 0; }      // overlong frame: drop it
    }
  }
}

// Everything the serial side does, once per pass.
static unsigned long last_tel_ms = 0;
static void serviceSerial() {
  readSerial();
  if (trip_report.pending) {
    static const char* WHY[] = {"NONE", "COMMAND", "OVERSPEED", "RUNAWAY", "STALL"};
    Line l; l.s("[TRIP,"); l.s(WHY[trip_report.why]); l.c(','); l.s(MOTOR_NAMES[trip_report.motor]);
    l.c(','); l.f(trip_report.v1, 2); l.c(','); l.f(trip_report.v2, 2); l.c(']'); l.send(true);
    if (trip_report.why == ES_RUNAWAY) reply("[TRIP,check motor_dir and encoder_dir for this wheel]");
    trip_report.pending = false;
  }
  if (watchdog_report) { watchdog_report = false; reply("[WARN,WATCHDOG,no command; stopping]"); }
  unsigned long now = millis();
  if (now - last_tel_ms >= telemetry_interval_ms) { last_tel_ms = now; sendTelemetry(); }
  txPump();
}

// ═════════════════════════════════════════════════════════════════════
//  9. Scheduling
// ═════════════════════════════════════════════════════════════════════

#ifdef KIT_ESP32
static void controlTask(void*) {
  TickType_t wake = xTaskGetTickCount();
  const TickType_t period = pdMS_TO_TICKS(1000 / CONTROL_HZ);
  unsigned long last_us = micros();
  for (;;) {
    vTaskDelayUntil(&wake, period);
    unsigned long now = micros();
    float dt = (now - last_us) * 1e-6f;
    last_us = now;
    if (dt < 0.5f * CTRL_DT || dt > 2.0f * CTRL_DT) dt = CTRL_DT;
    controlStep(dt);
  }
}
static void commsTask(void*) {
  for (;;) { serviceSerial(); vTaskDelay(1); }
}
#endif

void setup() {
  Serial.begin(SERIAL_BAUD);
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 1500) {}   // native-USB boards
  memset(motors, 0, sizeof(motors));
  for (int i = 0; i < NUM_MOTORS; i++) { Kff[i] = KFF_INIT[i]; Kstat[i] = KSTAT_INIT[i]; }
  setupMotorPins();
  stopAll();
  setupEncoders();
  last_cmd_ms = millis();                 // do not trip the watchdog before the Pi speaks
  reply("[BOOT,robot_kit_mcu]");
  printInfo();
  reply("[READY]");
#ifdef KIT_ESP32
  xTaskCreatePinnedToCore(controlTask, "ctrl", 4096, NULL, 3, NULL, 1);
  xTaskCreatePinnedToCore(commsTask, "comms", 4096, NULL, 1, NULL, 0);
#endif
}

#ifdef KIT_ESP32
void loop() { vTaskDelay(1000); }
#else
static unsigned long last_ctrl_us = 0;
void loop() {
  unsigned long now = micros();
  const unsigned long period_us = 1000000UL / CONTROL_HZ;
  if (last_ctrl_us == 0) last_ctrl_us = now;
  if (now - last_ctrl_us >= period_us) {
    float dt = (now - last_ctrl_us) * 1e-6f;
    if (now - last_ctrl_us > 5 * period_us) dt = CTRL_DT;   // we fell far behind: do not integrate the gap
    last_ctrl_us = now;
    controlStep(dt);
  }
  serviceSerial();
}
#endif
