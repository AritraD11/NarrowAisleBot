// Arduino.h - a minimal stand-in for the Arduino core, so robot_mcu.ino can
// be compiled with g++ on a PC or on the Pi and run against simulated motors
// (sim.cpp). Only what the sketch uses is here.
//
// This is NOT ESP32 or AVR. It exercises the portable path of the sketch
// (loop() scheduling, interrupt encoders, analogWrite PWM): the controller,
// the parser, the telemetry, the safety trips. The ESP32-only pieces
// (PCNT, ledc, FreeRTOS tasks) are not compiled here.
#pragma once
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <cstddef>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define CHANGE 1
#define NOT_AN_INTERRUPT -1
#ifndef PI
#define PI 3.14159265358979323846
#endif

namespace sim {
extern unsigned long now_us;
extern int pin_level[64];
extern int pin_pwm[64];
extern void (*pin_isr[64])();
void serial_write(const uint8_t* b, size_t n);
int serial_available();
int serial_read();
}

inline unsigned long micros() { return sim::now_us; }
inline unsigned long millis() { return sim::now_us / 1000UL; }
inline void pinMode(int, int) {}
inline void digitalWrite(int p, int v) { if (p >= 0 && p < 64) sim::pin_level[p] = v ? 1 : 0; }
inline int digitalRead(int p) { return (p >= 0 && p < 64) ? sim::pin_level[p] : 0; }
inline void analogWrite(int p, int v) { if (p >= 0 && p < 64) sim::pin_pwm[p] = v; }
inline int digitalPinToInterrupt(int p) { return (p >= 0 && p < 64) ? p : NOT_AN_INTERRUPT; }
inline void attachInterrupt(int irq, void (*fn)(), int) { if (irq >= 0 && irq < 64) sim::pin_isr[irq] = fn; }
inline void noInterrupts() {}
inline void interrupts() {}

struct SimSerial {
  void begin(long) {}
  int available() { return sim::serial_available(); }
  int read() { return sim::serial_read(); }
  size_t write(const uint8_t* b, size_t n) { sim::serial_write(b, n); return n; }
  int availableForWrite() { return 256; }
  explicit operator bool() const { return true; }
};
extern SimSerial Serial;
