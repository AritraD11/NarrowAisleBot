// Host stand-ins for the slice of the Arduino-ESP32 3.x API that
// aislebot_esp32.ino uses, so the real sketch can be compiled and stepped
// on a PC. Signatures follow arduino-esp32 3.x; behaviour is the minimum a
// test needs (a fake clock, a captured serial port, no-op tasks).
//
// This is NOT a substitute for an ESP32 build. It cannot catch a call
// whose signature differs on the real core, or anything timing-related.
#pragma once
#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <string>

using std::abs;

#define PI 3.1415926535897932384626433832795
#define HIGH 0x1
#define LOW  0x0
#define INPUT             0x01
#define OUTPUT            0x03
#define INPUT_PULLUP      0x05
#define OUTPUT_OPEN_DRAIN 0x13
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))

namespace hostsim {
struct Pin { int mode = 0; int level = HIGH; };
inline uint64_t now_us = 1000000;      // start at t = 1 s so 0 stays a sentinel
inline Pin      pins[64];
}

inline unsigned long millis() { return (unsigned long)(hostsim::now_us / 1000); }
inline unsigned long micros() { return (unsigned long)hostsim::now_us; }
inline void delay(uint32_t ms) { hostsim::now_us += (uint64_t)ms * 1000; }
inline void delayMicroseconds(uint32_t us) { hostsim::now_us += us; }
inline void pinMode(uint8_t pin, uint8_t mode) { hostsim::pins[pin].mode = mode; }
inline void digitalWrite(uint8_t pin, uint8_t val) { hostsim::pins[pin].level = val; }
inline int  digitalRead(uint8_t pin) { return hostsim::pins[pin].level; }
inline bool ledcAttach(uint8_t, uint32_t, uint8_t) { return true; }
inline bool ledcWrite(uint8_t, uint32_t) { return true; }

// ── FreeRTOS (1 tick = 1 ms, as on the robot) ──────────────────────────
typedef uint32_t TickType_t;
typedef int      BaseType_t;
typedef void*    TaskHandle_t;
typedef void (*TaskFunction_t)(void*);
#define pdPASS 1
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
inline TickType_t xTaskGetTickCount() { return (TickType_t)(hostsim::now_us / 1000); }
inline void vTaskDelay(TickType_t t) { hostsim::now_us += (uint64_t)t * 1000; }
inline void vTaskDelayUntil(TickType_t* last, TickType_t period) {
    TickType_t next = *last + period;
    uint64_t   at   = (uint64_t)next * 1000;
    if (hostsim::now_us < at) hostsim::now_us = at;
    *last = next;
}
inline BaseType_t xTaskCreatePinnedToCore(TaskFunction_t, const char*, uint32_t,
                                          void*, unsigned, TaskHandle_t*, BaseType_t) {
    return pdPASS;   // tasks are never started on the host; tests step them
}
struct portMUX_TYPE { int owner; };
#define portMUX_INITIALIZER_UNLOCKED {0}
inline void taskENTER_CRITICAL(portMUX_TYPE*) {}
inline void taskEXIT_CRITICAL(portMUX_TYPE*) {}

// ── Serial: captures every byte written, counts write() calls ──────────
class HostSerial {
public:
    std::string out;
    std::string in;
    unsigned    writes = 0;
    size_t      tx_buffer = 0;
    bool        begun = false;
    bool        tx_set_before_begin = false;

    size_t setTxBufferSize(size_t n) {
        tx_buffer = n;
        if (!begun) tx_set_before_begin = true;
        return n;
    }
    void begin(unsigned long) { begun = true; }
    int  available() { return (int)in.size(); }
    int  read() {
        if (in.empty()) return -1;
        int c = (unsigned char)in[0];
        in.erase(0, 1);
        return c;
    }
    size_t write(const uint8_t* b, size_t n) { out.append((const char*)b, n); writes++; return n; }
    size_t write(const char* b, size_t n) { return write((const uint8_t*)b, n); }
    size_t print(const char* s) { return write((const uint8_t*)s, strlen(s)); }
    size_t println(const char* s) { size_t n = print(s); return n + print("\r\n"); }
    size_t println() { return print("\r\n"); }
    size_t printf(const char* fmt, ...) __attribute__((format(printf, 2, 3))) {
        char buf[512];
        va_list ap;
        va_start(ap, fmt);
        int n = vsnprintf(buf, sizeof(buf), fmt, ap);
        va_end(ap);
        if (n < 0) return 0;
        return write((const uint8_t*)buf, (size_t)n < sizeof(buf) ? (size_t)n : sizeof(buf) - 1);
    }
};
inline HostSerial Serial;
