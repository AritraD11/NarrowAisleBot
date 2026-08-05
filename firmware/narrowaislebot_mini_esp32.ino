/*
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║        NarrowAisleBot — MINI PROTOTYPE — ESP32 Controller         ║
 * ║                                                                  ║
 * ║  PID + Feedforward | Hardware PCNT | Asymmetric Mecanum IK        ║
 * ║  Dual-Core FreeRTOS | Latching E-STOP | Optional BNO055 IMU       ║
 * ║                                                                  ║
 * ║  Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar       ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * This is the small-scale sibling of aislebot_esp32.ino. The architecture,
 * pin map, and serial protocol are IDENTICAL to the full-size NAB — only the
 * physical constants change, selected by ROBOT_PROFILE below.
 *
 * MOTORS : 4× Pro-Range PG36M555-19.2K, 12 V, 262 RPM, 0.45 N·m
 * ENCODER: ME-37 Hall, 7 PPR ×4 (quad) ×19.2 (gear) = 537.6 CPR at the wheel
 * DRIVERS: 2× Cytron MDD10A (PWM + DIR, 3.3 V logic accepted directly)
 * WHEELS : 80 mm mecanum (r = 0.040 m)
 *
 * KEY DIFFERENCE vs NAB: the built-in Hall encoder is ~173× coarser than the
 * NAB's optical encoder. We compensate with strong feedforward, heavier
 * velocity filtering, and a small Kd. If low-speed velocity is jittery, drop
 * PID_LOOP_HZ to 25.0. See docs/Mini_Prototype_Architecture.md §2.1.
 *
 * LIBRARIES (Arduino Library Manager):
 *   WebSockets  by Markus Sattler (Links2004)
 *   ArduinoJson by Benoit Blanchon
 *   Adafruit BNO055 + Adafruit Unified Sensor   (only if ENABLE_IMU)
 *
 * BOARD: ESP32 Dev Module | 240 MHz | 4 MB flash | Upload 921600 | PSRAM off
 */

#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "driver/pcnt.h"

// ═══════════════════════════════════════════════════════════════════
// 0. ROBOT PROFILE  — the ONLY block that differs between NAB and MINI
// ═══════════════════════════════════════════════════════════════════
#define PROFILE_MINI      1
#define PROFILE_NAB       2
#define ROBOT_PROFILE     PROFILE_MINI

#define ENABLE_IMU        0   // set 1 once a BNO055 is wired to G14/G13
#define ENABLE_WIFI_JOY   1   // compact phone joystick for manual bench tests

#if ROBOT_PROFILE == PROFILE_MINI
  const char*  PROFILE_NAME  = "MINI";
  const float  WHEEL_RADIUS  = 0.040f;    // 80 mm mecanum
  const float  ROBOT_L1      = 0.150f;    // outer pair (FR, RL)
  const float  ROBOT_L2      = 0.120f;    // inner pair (FL, RR)
  const float  ROBOT_D       = 0.075f;    // half-track (150 mm track)
  const float  ENCODER_CPR   = 537.6f;    // 7 PPR ×4 ×19.2
  const float  MAX_WHEEL_SPEED   = 22.0f; // rad/s clamp (~80% of 27.44 hw max)
  const float  MAX_LINEAR_SPEED  = 0.45f; // m/s
  const float  MAX_ANGULAR_SPEED = 2.0f;  // rad/s
#else  // PROFILE_NAB (full-size, for reference)
  const char*  PROFILE_NAME  = "NAB";
  const float  WHEEL_RADIUS  = 0.0762f;
  const float  ROBOT_L1      = 0.403f;
  const float  ROBOT_L2      = 0.333f;
  const float  ROBOT_D       = 0.15769f;
  const float  ENCODER_CPR   = 93132.0f;
  const float  MAX_WHEEL_SPEED   = 6.28f;
  const float  MAX_LINEAR_SPEED  = 0.48f;
  const float  MAX_ANGULAR_SPEED = 1.0f;
#endif

const float K_OUTER = ROBOT_L1 + ROBOT_D;   // MINI: 0.225 m (FR, RL)
const float K_INNER = ROBOT_L2 + ROBOT_D;   // MINI: 0.195 m (FL, RR)

// ═══════════════════════════════════════════════════════════════════
// 1. PIN DEFINITIONS  (identical to the NAB — two MDD driver layout)
//    RIGHT side → driver PWM/DIR (3.3 V direct to MDD10A)
//    LEFT  side → Hall encoder A/B (3.3 V direct, NO level shifter)
// ═══════════════════════════════════════════════════════════════════
#define PWM1_PIN   4    // FR PWM → Driver 1 Ch1
#define DIR1_PIN  16    // FR DIR
#define PWM2_PIN  17    // FL PWM → Driver 1 Ch2
#define DIR2_PIN  18    // FL DIR
#define PWM3_PIN  19    // RR PWM → Driver 2 Ch1
#define DIR3_PIN  21    // RR DIR
#define PWM4_PIN  22    // RL PWM → Driver 2 Ch2
#define DIR4_PIN  23    // RL DIR

#define ENC1_A_PIN  36  // FR A
#define ENC1_B_PIN  39  // FR B
#define ENC2_A_PIN  34  // FL A
#define ENC2_B_PIN  35  // FL B
#define ENC3_A_PIN  32  // RR A
#define ENC3_B_PIN  33  // RR B
#define ENC4_A_PIN  25  // RL A
#define ENC4_B_PIN  26  // RL B

#define IMU_SDA_PIN 14
#define IMU_SCL_PIN 13

// ═══════════════════════════════════════════════════════════════════
// 2. MOTOR CONSTANTS
// ═══════════════════════════════════════════════════════════════════
#define FR 0
#define FL 1
#define RR 2
#define RL 3
#define NUM_MOTORS 4

const char* MOTOR_NAMES[NUM_MOTORS] = {"FR", "FL", "RR", "RL"};

const uint8_t PWM_PINS[NUM_MOTORS]   = {PWM1_PIN, PWM2_PIN, PWM3_PIN, PWM4_PIN};
const uint8_t DIR_PINS[NUM_MOTORS]   = {DIR1_PIN, DIR2_PIN, DIR3_PIN, DIR4_PIN};
const uint8_t ENC_A_PINS[NUM_MOTORS] = {ENC1_A_PIN, ENC2_A_PIN, ENC3_A_PIN, ENC4_A_PIN};
const uint8_t ENC_B_PINS[NUM_MOTORS] = {ENC1_B_PIN, ENC2_B_PIN, ENC3_B_PIN, ENC4_B_PIN};

// Set at commissioning. MOTOR_DIR_SIGN and ENC_DIR_SIGN MUST match per motor.
int8_t MOTOR_DIR_SIGN[NUM_MOTORS] = {-1, +1, -1, +1}; // FR,FL,RR,RL
int8_t ENC_DIR_SIGN[NUM_MOTORS]   = {-1, +1, -1, +1};

const pcnt_unit_t PCNT_UNITS[NUM_MOTORS] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

// ── PWM ──
const int PWM_MAX           = 255;
const int MIN_PWM_THRESHOLD = 15;    // deadband — recalibrate on the ground
const int PWM_FREQUENCY     = 5000;  // 5 kHz (raise to 18 kHz for silence)
const int PWM_RESOLUTION    = 8;

// ═══════════════════════════════════════════════════════════════════
// 3. PID + FEEDFORWARD  (retuned for the mini's coarse encoder)
// ═══════════════════════════════════════════════════════════════════
const float PID_LOOP_HZ          = 50.0f;   // drop to 25.0 if low-speed jitter
const float PID_LOOP_INTERVAL_MS = 1000.0f / PID_LOOP_HZ;
const float PID_DT               = 1.0f   / PID_LOOP_HZ;

float Kp = 25.0f;   // lower than NAB — coarse feedback, lean on Kff
float Ki = 15.0f;
float Kd = 0.3f;    // small — coarse encoder makes derivative noisy

// PWM per (rad/s). ~9.5 start (255 PWM ≈ 27.4 rad/s). RECALIBRATE per motor.
float Kff[NUM_MOTORS] = {9.5f, 9.5f, 9.5f, 9.5f};

const float INTEGRAL_MAX     = 200.0f;
const float D_FILTER_ALPHA   = 0.3f;
const float VEL_FILTER_ALPHA = 0.3f;   // heavier smoothing than NAB (0.5)

// ═══════════════════════════════════════════════════════════════════
// 4. TIMING & SAFETY
// ═══════════════════════════════════════════════════════════════════
const unsigned long WATCHDOG_TIMEOUT_MS   = 1000;
const unsigned long WIFI_CMD_TIMEOUT_MS   = 200;
const unsigned long TELEMETRY_INTERVAL_MS = 100;   // 10 Hz
const unsigned long SERIAL_BAUD           = 921600;

// ═══════════════════════════════════════════════════════════════════
// 5. WiFi (SoftAP)
// ═══════════════════════════════════════════════════════════════════
const char* WIFI_SSID = "MiniAisleBot";
const char* WIFI_PASS = "aislebot123";
const int   WEBSOCKET_PORT = 81;
const int   WEBSERVER_PORT = 80;

// ═══════════════════════════════════════════════════════════════════
// 6. STATE
// ═══════════════════════════════════════════════════════════════════
struct MotorState {
    float target_velocity, actual_velocity, raw_velocity;
    float error, integral, prev_error, filtered_derivative;
    int   pwm_output;
    float ff_output, pid_output;
};
MotorState motors[NUM_MOTORS];

volatile unsigned long last_any_cmd_ms  = 0;
volatile unsigned long last_wifi_cmd_ms = 0;
volatile bool motors_enabled   = true;
volatile bool watchdog_enabled = true;
volatile bool serial_logging   = false;
volatile bool estop_active     = false;

volatile float wifi_vx = 0, wifi_vy = 0, wifi_wz = 0;

#if ENABLE_WIFI_JOY
WebServer        webServer(WEBSERVER_PORT);
WebSocketsServer wsServer(WEBSOCKET_PORT);
#endif

#if ENABLE_IMU
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28, &Wire);
volatile float imu_yaw = 0, imu_wz = 0;
bool imu_ok = false;
#endif

// ═══════════════════════════════════════════════════════════════════
// 7. PCNT ENCODER — full quadrature (both channels, all edges)
// ═══════════════════════════════════════════════════════════════════
void setupPCNT(int idx) {
    pcnt_unit_t unit = PCNT_UNITS[idx];
    uint8_t pinA = ENC_A_PINS[idx], pinB = ENC_B_PINS[idx];

    pcnt_config_t c0 = {};
    c0.pulse_gpio_num = pinA; c0.ctrl_gpio_num = pinB;
    c0.channel = PCNT_CHANNEL_0; c0.unit = unit;
    c0.pos_mode = PCNT_COUNT_INC; c0.neg_mode = PCNT_COUNT_DEC;
    c0.lctrl_mode = PCNT_MODE_REVERSE; c0.hctrl_mode = PCNT_MODE_KEEP;
    c0.counter_h_lim = 32767; c0.counter_l_lim = -32768;
    pcnt_unit_config(&c0);

    pcnt_config_t c1 = {};
    c1.pulse_gpio_num = pinB; c1.ctrl_gpio_num = pinA;
    c1.channel = PCNT_CHANNEL_1; c1.unit = unit;
    c1.pos_mode = PCNT_COUNT_DEC; c1.neg_mode = PCNT_COUNT_INC;
    c1.lctrl_mode = PCNT_MODE_REVERSE; c1.hctrl_mode = PCNT_MODE_KEEP;
    c1.counter_h_lim = 32767; c1.counter_l_lim = -32768;
    pcnt_unit_config(&c1);

    pcnt_set_filter_value(unit, 100);   // glitch filter — good for Hall noise
    pcnt_filter_enable(unit);
    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

int32_t readEncoderDelta(int idx) {
    int16_t count = 0;
    pcnt_get_counter_value(PCNT_UNITS[idx], &count);
    pcnt_counter_clear(PCNT_UNITS[idx]);
    return (int32_t)count * ENC_DIR_SIGN[idx];
}

// ═══════════════════════════════════════════════════════════════════
// 8. MOTOR OUTPUT
// ═══════════════════════════════════════════════════════════════════
void setupMotorPins() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        pinMode(DIR_PINS[i], OUTPUT);
        digitalWrite(DIR_PINS[i], LOW);
        ledcAttach(PWM_PINS[i], PWM_FREQUENCY, PWM_RESOLUTION);
        ledcWrite(PWM_PINS[i], 0);
    }
}

void setMotorOutput(int idx, int pwm_value) {
    int adjusted = pwm_value * MOTOR_DIR_SIGN[idx];
    bool reverse = (adjusted < 0);
    int abs_pwm  = abs(adjusted);
    if (abs_pwm < MIN_PWM_THRESHOLD) abs_pwm = 0;
    if (abs_pwm > PWM_MAX)           abs_pwm = PWM_MAX;
    digitalWrite(DIR_PINS[idx], reverse ? HIGH : LOW);
    ledcWrite(PWM_PINS[idx], abs_pwm);
}

void stopAllMotors() {
    for (int i = 0; i < NUM_MOTORS; i++) {
        motors[i].target_velocity = 0;
        motors[i].integral = 0;
        motors[i].prev_error = 0;
        motors[i].filtered_derivative = 0;
        motors[i].pwm_output = 0;
        setMotorOutput(i, 0);
    }
}

// ═══════════════════════════════════════════════════════════════════
// 9. PID + FEEDFORWARD
// ═══════════════════════════════════════════════════════════════════
void computePID(int idx) {
    MotorState& m = motors[idx];
    m.ff_output = Kff[idx] * m.target_velocity;

    m.error = m.target_velocity - m.actual_velocity;
    float p = Kp * m.error;

    m.integral += m.error * PID_DT;
    m.integral  = constrain(m.integral, -INTEGRAL_MAX, INTEGRAL_MAX);
    if (fabsf(m.target_velocity) < 0.01f && fabsf(m.actual_velocity) < 0.15f)
        m.integral = 0.0f;
    float i = Ki * m.integral;

    float raw_d = (m.error - m.prev_error) / PID_DT;
    m.filtered_derivative = D_FILTER_ALPHA * raw_d +
                            (1.0f - D_FILTER_ALPHA) * m.filtered_derivative;
    float d = Kd * m.filtered_derivative;
    m.prev_error = m.error;

    m.pid_output = p + i + d;
    float total  = m.ff_output + m.pid_output;
    if (fabsf(m.target_velocity) < 0.01f) total = 0.0f;
    m.pwm_output = (int)constrain(roundf(total), -PWM_MAX, PWM_MAX);
}

// ═══════════════════════════════════════════════════════════════════
// 10. ASYMMETRIC MECANUM INVERSE KINEMATICS
//     ωFR = (vx + vy + wz·K_OUTER) / r     outer (FR, RL)
//     ωFL = (vx − vy − wz·K_INNER) / r     inner (FL, RR)
//     ωRR = (vx − vy + wz·K_INNER) / r
//     ωRL = (vx + vy − wz·K_OUTER) / r
// ═══════════════════════════════════════════════════════════════════
void mecanumIK(float vx, float vy, float wz, float* ws) {
    ws[FR] = ( vx + vy + wz * K_OUTER) / WHEEL_RADIUS;
    ws[FL] = ( vx - vy - wz * K_INNER) / WHEEL_RADIUS;
    ws[RR] = ( vx - vy + wz * K_INNER) / WHEEL_RADIUS;
    ws[RL] = ( vx + vy - wz * K_OUTER) / WHEEL_RADIUS;

    float max_spd = 0.0f;
    for (int i = 0; i < NUM_MOTORS; i++)
        if (fabsf(ws[i]) > max_spd) max_spd = fabsf(ws[i]);
    if (max_spd > MAX_WHEEL_SPEED) {
        float scale = MAX_WHEEL_SPEED / max_spd;
        for (int i = 0; i < NUM_MOTORS; i++) ws[i] *= scale;
    }
}

// ═══════════════════════════════════════════════════════════════════
// 11. CORE 1 — PID TASK (50 Hz)
// ═══════════════════════════════════════════════════════════════════
void pidControlTask(void*) {
    TickType_t xLastWake = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS((int)PID_LOOP_INTERVAL_MS);

    while (true) {
        for (int i = 0; i < NUM_MOTORS; i++) {
            int32_t delta = readEncoderDelta(i);
            float raw = ((float)delta / ENCODER_CPR) * (2.0f * PI) / PID_DT;
            motors[i].raw_velocity = raw;
            motors[i].actual_velocity =
                VEL_FILTER_ALPHA * raw +
                (1.0f - VEL_FILTER_ALPHA) * motors[i].actual_velocity;
        }

        if (estop_active || !motors_enabled) {
            for (int i = 0; i < NUM_MOTORS; i++) {
                motors[i].target_velocity = 0; motors[i].integral = 0;
                motors[i].pwm_output = 0; setMotorOutput(i, 0);
            }
            vTaskDelayUntil(&xLastWake, xPeriod);
            continue;
        }

        if (watchdog_enabled &&
            (millis() - last_any_cmd_ms > WATCHDOG_TIMEOUT_MS)) {
            for (int i = 0; i < NUM_MOTORS; i++) {
                motors[i].target_velocity = 0; motors[i].integral = 0;
            }
        }

        if (millis() - last_wifi_cmd_ms < WIFI_CMD_TIMEOUT_MS) {
            float ws[NUM_MOTORS];
            mecanumIK(wifi_vx, wifi_vy, wifi_wz, ws);
            for (int i = 0; i < NUM_MOTORS; i++)
                motors[i].target_velocity = ws[i];
        }

        for (int i = 0; i < NUM_MOTORS; i++) {
            computePID(i);
            setMotorOutput(i, motors[i].pwm_output);
        }
        vTaskDelayUntil(&xLastWake, xPeriod);
    }
}

// ═══════════════════════════════════════════════════════════════════
// 12. SERIAL COMMAND PARSER  (protocol identical to the NAB)
// ═══════════════════════════════════════════════════════════════════
char serialBuffer[256];
int  serialBufIdx = 0;
bool serialReceiving = false;

void processSerialCommand(const char* cmd) {
    last_any_cmd_ms = millis();
    switch (cmd[0]) {
        case 'V': {  // <V,fr,fl,rr,rl> wheel vel rad/s via PID
            float v[4];
            if (sscanf(cmd, "V,%f,%f,%f,%f", &v[0],&v[1],&v[2],&v[3]) == 4) {
                for (int i = 0; i < NUM_MOTORS; i++)
                    motors[i].target_velocity =
                        constrain(v[i], -MAX_WHEEL_SPEED, MAX_WHEEL_SPEED);
                Serial.printf("[OK,V,%.2f,%.2f,%.2f,%.2f]\n",v[0],v[1],v[2],v[3]);
            } else Serial.println("[ERR,BAD_V]");
            break;
        }
        case 'C': {  // <C,vx,vy,wz> body velocity → onboard asymmetric IK
            float vx,vy,wz;
            if (sscanf(cmd, "C,%f,%f,%f", &vx,&vy,&wz) == 3) {
                float ws[NUM_MOTORS];
                mecanumIK(vx, vy, wz, ws);
                for (int i = 0; i < NUM_MOTORS; i++)
                    motors[i].target_velocity = ws[i];
                Serial.printf("[OK,C,%.2f,%.2f,%.2f]\n", vx,vy,wz);
            } else Serial.println("[ERR,BAD_C]");
            break;
        }
        case 'M': {  // <M,fr,fl,rr,rl> direct PWM, bypass PID
            int p[4];
            if (sscanf(cmd, "M,%d,%d,%d,%d", &p[0],&p[1],&p[2],&p[3]) == 4) {
                for (int i = 0; i < NUM_MOTORS; i++) {
                    p[i] = constrain(p[i], -PWM_MAX, PWM_MAX);
                    motors[i].target_velocity = 0; motors[i].integral = 0;
                    motors[i].pwm_output = p[i]; setMotorOutput(i, p[i]);
                }
                Serial.printf("[OK,M,%d,%d,%d,%d]\n", p[0],p[1],p[2],p[3]);
            } else Serial.println("[ERR,BAD_M]");
            break;
        }
        case 'T': {  // <T,idx,vel> test one motor
            int idx; float vel;
            if (sscanf(cmd, "T,%d,%f", &idx, &vel) == 2 &&
                idx >= 0 && idx < NUM_MOTORS) {
                motors[idx].target_velocity =
                    constrain(vel, -MAX_WHEEL_SPEED, MAX_WHEEL_SPEED);
                Serial.printf("[OK,T,%d,%.2f]\n", idx, vel);
            } else Serial.println("[ERR,BAD_T]");
            break;
        }
        case 'S':  // <S> latching E-STOP
            estop_active = true; stopAllMotors();
            Serial.println("[OK,ESTOP_LATCHED]"); break;
        case 'P': Serial.println("[PONG]"); break;
        case 'I':
            Serial.printf("[INFO,MiniAisleBot_%s]\n", PROFILE_NAME);
            Serial.printf("[GAINS,Kp=%.1f,Ki=%.1f,Kd=%.1f]\n", Kp,Ki,Kd);
            Serial.printf("[FF,%.1f,%.1f,%.1f,%.1f]\n",
                          Kff[FR],Kff[FL],Kff[RR],Kff[RL]);
            Serial.printf("[GEOM,r=%.4f,K_OUT=%.4f,K_INN=%.4f,CPR=%.1f]\n",
                          WHEEL_RADIUS, K_OUTER, K_INNER, ENCODER_CPR);
            Serial.printf("[LIMITS,Wmax=%.2f,Lin=%.2f,Ang=%.2f]\n",
                          MAX_WHEEL_SPEED, MAX_LINEAR_SPEED, MAX_ANGULAR_SPEED);
            break;
        case '?':
            Serial.printf("[STATE,EN=%d,WD=%d,ESTOP=%d]\n",
                          motors_enabled, watchdog_enabled, estop_active);
            for (int i = 0; i < NUM_MOTORS; i++)
                Serial.printf("[%s,tgt=%.2f,act=%.2f,pwm=%d,err=%.3f]\n",
                    MOTOR_NAMES[i], motors[i].target_velocity,
                    motors[i].actual_velocity, motors[i].pwm_output,
                    motors[i].error);
            break;
        case 'G': {  // <G,Kp,Ki,Kd>
            float kp,ki,kd;
            if (sscanf(cmd, "G,%f,%f,%f", &kp,&ki,&kd) == 3) {
                Kp=kp; Ki=ki; Kd=kd;
                for (int i = 0; i < NUM_MOTORS; i++) motors[i].integral = 0;
                Serial.printf("[OK,GAINS,%.1f,%.1f,%.1f]\n", Kp,Ki,Kd);
            } else Serial.println("[ERR,BAD_G]");
            break;
        }
        case 'F': {  // <F,fr,fl,rr,rl>
            float f[4];
            if (sscanf(cmd, "F,%f,%f,%f,%f", &f[0],&f[1],&f[2],&f[3]) == 4) {
                for (int i = 0; i < NUM_MOTORS; i++) Kff[i] = f[i];
                Serial.printf("[OK,FF,%.1f,%.1f,%.1f,%.1f]\n",
                              f[0],f[1],f[2],f[3]);
            } else Serial.println("[ERR,BAD_F]");
            break;
        }
        case 'E':  // <E1>/<E0>
            if (cmd[1] == '1') {
                motors_enabled = true; estop_active = false;
                Serial.println("[OK,ENABLED]");
            } else { motors_enabled = false; stopAllMotors();
                     Serial.println("[OK,DISABLED]"); }
            break;
        case 'W': watchdog_enabled = (cmd[1] == '1');
                  Serial.printf("[OK,WDOG=%d]\n", watchdog_enabled); break;
        case 'L': serial_logging = (cmd[1] == '1');
                  Serial.printf("[OK,LOG=%d]\n", serial_logging); break;
        case 'H':
            Serial.println("=== MiniAisleBot Commands ===");
            Serial.println("<V,fr,fl,rr,rl> wheel vel rad/s (PID)");
            Serial.println("<C,vx,vy,wz>    body vel → asymmetric IK");
            Serial.println("<M,fr,fl,rr,rl> direct PWM -255..255");
            Serial.println("<T,idx,vel>     test single motor");
            Serial.println("<G,Kp,Ki,Kd> / <F,ff...> tune");
            Serial.println("<S> E-STOP | <E1>/<E0> | <W1/0> | <L1/0>");
            Serial.println("<P> ping | <I> info | <?> state");
            break;
        default: Serial.printf("[ERR,UNKNOWN:%c]\n", cmd[0]); break;
    }
}

void handleSerialInput() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '<') { serialReceiving = true; serialBufIdx = 0; }
        else if (c == '>' && serialReceiving) {
            serialReceiving = false; serialBuffer[serialBufIdx] = '\0';
            processSerialCommand(serialBuffer);
        } else if (serialReceiving) {
            if (serialBufIdx < (int)sizeof(serialBuffer) - 1)
                serialBuffer[serialBufIdx++] = c;
            else { serialReceiving = false; serialBufIdx = 0; }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
// 13. WiFi JOYSTICK  (compact — for manual bench testing)
// ═══════════════════════════════════════════════════════════════════
#if ENABLE_WIFI_JOY
const char WEBPAGE[] PROGMEM = R"HTML(
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>MiniAisleBot</title><style>
*{margin:0;padding:0;box-sizing:border-box;touch-action:none;-webkit-user-select:none;user-select:none}
body{height:100vh;background:#0a0e17;color:#e0e0e0;font-family:monospace;overflow:hidden;display:flex;flex-direction:column}
.h{height:36px;display:flex;align-items:center;justify-content:space-between;padding:0 12px;background:#111827;border-bottom:1px solid #1e3a5f}
.t{color:#38bdf8;font-weight:700;letter-spacing:1px;font-size:13px}
.d{width:9px;height:9px;border-radius:50%;background:#ef4444}.d.on{background:#22c55e;box-shadow:0 0 6px #22c55e}
.b{flex:1;display:flex}.j{flex:1;position:relative;background:#0f1729}
.ring{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:min(60vw,260px);height:min(60vw,260px);border:2px solid #1e3a5f;border-radius:50%}
.th{position:absolute;top:50%;left:50%;width:64px;height:64px;border-radius:50%;transform:translate(-50%,-50%);background:radial-gradient(circle at 35% 35%,#38bdf8,#0369a1)}
.r{width:96px;background:#0f1729;border-left:1px solid #1e3a5f;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.rt{width:24px;height:150px;background:#111827;border:1px solid #1e3a5f;border-radius:12px;position:relative}
.rth{position:absolute;left:50%;top:50%;width:40px;height:40px;border-radius:50%;transform:translate(-50%,-50%);background:radial-gradient(circle at 35% 35%,#f59e0b,#92400e)}
.es{width:64px;height:64px;border-radius:50%;border:2px solid #fca5a5;color:#fff;font-weight:700;font-size:11px;background:radial-gradient(circle at 40% 35%,#f87171,#7f1d1d)}
.es.on{background:radial-gradient(circle at 40% 35%,#4ade80,#14532d);border-color:#86efac}
</style></head><body>
<div class="h"><span class="t">MINI-AISLEBOT</span><span class="d" id="dot"></span></div>
<div class="b">
 <div class="j" id="ja"><div class="ring" id="ring"><div class="th" id="th"></div></div></div>
 <div class="r"><div class="rt" id="rt"><div class="rth" id="rth"></div></div>
  <button class="es" id="es">E<br>STOP</button></div>
</div>
<script>
let ws,ok=false;const U='ws://'+location.hostname+':81/';
function C(){ws=new WebSocket(U);ws.onopen=()=>{ok=1;dot.classList.add('on')};
ws.onclose=()=>{ok=0;dot.classList.remove('on');setTimeout(C,1000)};ws.onerror=()=>ws.close()}C();
function S(o){if(ok)ws.send(JSON.stringify(o))}
let jx=0,jy=0,rv=0,jA=0,rA=0,jid=null,rid=null;
const ring=document.getElementById('ring'),th=document.getElementById('th');
function jp(t){const r=ring.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,mr=r.width/2-32;
let dx=t.clientX-cx,dy=t.clientY-cy,ds=Math.hypot(dx,dy);if(ds>mr){dx=dx/ds*mr;dy=dy/ds*mr}
return{dx,dy,nx:dx/mr,ny:-dy/mr}}
const ja=document.getElementById('ja');
ja.addEventListener('touchstart',e=>{e.preventDefault();if(jA)return;const t=e.changedTouches[0];jA=1;jid=t.identifier;
const p=jp(t);jx=p.nx;jy=p.ny;th.style.transform=`translate(calc(-50% + ${p.dx}px),calc(-50% + ${p.dy}px))`},{passive:false});
ja.addEventListener('touchmove',e=>{e.preventDefault();for(const t of e.changedTouches){if(t.identifier!=jid)continue;
const p=jp(t);jx=p.nx;jy=p.ny;th.style.transform=`translate(calc(-50% + ${p.dx}px),calc(-50% + ${p.dy}px))`}},{passive:false});
ja.addEventListener('touchend',e=>{for(const t of e.changedTouches){if(t.identifier!=jid)continue;
jA=0;jid=null;jx=0;jy=0;th.style.transform='translate(-50%,-50%)';send()}},{passive:false});
const rt=document.getElementById('rt'),rth=document.getElementById('rth');
function ur(t){const r=rt.getBoundingClientRect(),p=Math.max(0,Math.min(1,(t.clientY-r.top)/r.height));
rth.style.top=(p*100)+'%';rv=-(p-0.5)*2}
rt.addEventListener('touchstart',e=>{e.preventDefault();if(rA)return;const t=e.changedTouches[0];rA=1;rid=t.identifier;ur(t)},{passive:false});
rt.addEventListener('touchmove',e=>{e.preventDefault();for(const t of e.changedTouches)if(t.identifier==rid)ur(t)},{passive:false});
rt.addEventListener('touchend',e=>{for(const t of e.changedTouches){if(t.identifier!=rid)continue;rA=0;rid=null;rv=0;rth.style.top='50%';send()}},{passive:false});
function dz(v){return Math.abs(v)<0.08?0:v}
function send(){S({type:'joy',vx:+dz(jy).toFixed(3),vy:+dz(-jx).toFixed(3),wz:+dz(rv).toFixed(3)})}
setInterval(()=>{if(jA||rA)send()},50);
let stp=0;const es=document.getElementById('es');
es.addEventListener('touchstart',e=>{e.preventDefault();e.stopPropagation();
if(!stp){stp=1;S({type:'stop'});es.classList.add('on');es.innerHTML='GO';}
else{stp=0;S({type:'resume'});es.classList.remove('on');es.innerHTML='E<br>STOP';}},{passive:false});
</script></body></html>
)HTML";

void webSocketEvent(uint8_t, WStype_t type, uint8_t* payload, size_t length) {
    if (type == WStype_DISCONNECTED) { wifi_vx=wifi_vy=wifi_wz=0; return; }
    if (type != WStype_TEXT) return;
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, payload, length)) return;
    const char* mt = doc["type"]; if (!mt) return;
    if (!strcmp(mt, "joy")) {
        wifi_vx = doc["vx"].as<float>() * MAX_LINEAR_SPEED;
        wifi_vy = doc["vy"].as<float>() * MAX_LINEAR_SPEED;
        wifi_wz = doc["wz"].as<float>() * MAX_ANGULAR_SPEED;
        last_wifi_cmd_ms = millis(); last_any_cmd_ms = millis();
    } else if (!strcmp(mt, "stop")) {
        estop_active = true; stopAllMotors(); wifi_vx=wifi_vy=wifi_wz=0;
    } else if (!strcmp(mt, "resume")) {
        estop_active = false; motors_enabled = true;
    }
}

void handleRoot() { webServer.send_P(200, "text/html", WEBPAGE); }

void setupWiFi() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(WIFI_SSID, WIFI_PASS);
    Serial.printf("  WiFi AP  : %s  (%s)\n", WIFI_SSID,
                  WiFi.softAPIP().toString().c_str());
    webServer.on("/", handleRoot); webServer.begin();
    wsServer.begin(); wsServer.onEvent(webSocketEvent);
}
#endif  // ENABLE_WIFI_JOY

// ═══════════════════════════════════════════════════════════════════
// 14. TELEMETRY  (10 Hz CSV to Pi when <L1>)
//     ts, FR_tgt,FR_act,FR_pwm, FL_..., RR_..., RL_... [, yaw, wz]
// ═══════════════════════════════════════════════════════════════════
void outputSerialTelemetry() {
    if (!serial_logging) return;
    Serial.printf("%lu", millis());
    for (int i = 0; i < NUM_MOTORS; i++)
        Serial.printf(",%.2f,%.2f,%d", motors[i].target_velocity,
                      motors[i].actual_velocity, motors[i].pwm_output);
#if ENABLE_IMU
    Serial.printf(",%.2f,%.3f", imu_yaw, imu_wz);
#endif
    Serial.println();
}

// ═══════════════════════════════════════════════════════════════════
// 15. CORE 0 — COMMUNICATION TASK
// ═══════════════════════════════════════════════════════════════════
void communicationTask(void*) {
    unsigned long lastTel = 0;
    while (true) {
#if ENABLE_WIFI_JOY
        wsServer.loop(); webServer.handleClient();
#endif
        handleSerialInput();
#if ENABLE_IMU
        if (imu_ok) {
            sensors_event_t ori, gyr;
            bno.getEvent(&ori, Adafruit_BNO055::VECTOR_EULER);
            bno.getEvent(&gyr, Adafruit_BNO055::VECTOR_GYROSCOPE);
            imu_yaw = ori.orientation.x;   // heading, degrees
            imu_wz  = gyr.gyro.z;          // yaw rate, rad/s
        }
#endif
        if (millis() - lastTel >= TELEMETRY_INTERVAL_MS) {
            lastTel = millis();
            outputSerialTelemetry();
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ═══════════════════════════════════════════════════════════════════
// 16. SETUP
// ═══════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(300);
    Serial.printf("\n== MiniAisleBot ESP32 (%s profile) ==\n", PROFILE_NAME);

    memset(motors, 0, sizeof(motors));
    setupMotorPins();
    for (int i = 0; i < NUM_MOTORS; i++) setupPCNT(i);
    Serial.printf("  PCNT: full quad, CPR=%.1f\n", ENCODER_CPR);

#if ENABLE_IMU
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
    imu_ok = bno.begin();
    Serial.printf("  BNO055: %s\n", imu_ok ? "OK" : "NOT FOUND");
    if (imu_ok) bno.setExtCrystalUse(true);
#endif

#if ENABLE_WIFI_JOY
    setupWiFi();
#endif

    xTaskCreatePinnedToCore(communicationTask, "Comms", 8192, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(pidControlTask,    "PID",   4096, NULL, 2, NULL, 1);

    last_any_cmd_ms = millis();
    Serial.printf("  Geometry: r=%.4f K_OUT=%.4f K_INN=%.4f\n",
                  WHEEL_RADIUS, K_OUTER, K_INNER);
    Serial.printf("  Limits: v=%.2f m/s  w=%.2f rad/s\n",
                  MAX_LINEAR_SPEED, MAX_ANGULAR_SPEED);
    Serial.println("  E-STOP <S> latches. Clear with <E1>.  <H> for help.");
    Serial.println("[READY]");
}

void loop() { vTaskDelay(pdMS_TO_TICKS(1000)); }
