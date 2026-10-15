// Host stand-in for arduino-esp32 3.x TwoWire, wired to a small register
// model of a BNO055 so the firmware's IMU driver can be stepped.
//
// The model mirrors only behaviour the driver depends on:
//   * CHIP_ID reads 0xA0, SW_REV reads 0x0311
//   * UNIT_SEL / AXIS_MAP writes are ignored outside CONFIG mode, as on
//     the real chip, so a missing CONFIG step makes the read-back fail
//   * SYS_TRIGGER bit 5 resets the register file to power-on defaults
//   * entering a fusion mode sets SYS_STATUS to 5 (fusion running)
//   * `fail_all` makes every transaction NACK, like a wedged bus
//   * `present = false` is an empty bus
#pragma once
#include "Arduino.h"
#include <vector>

namespace hostsim {
struct FakeBno {
    bool    present  = true;
    bool    fail_all = false;
    bool    addr29   = false;              // ADR high: answers at 0x29 instead
    int     sda_pin  = 14, scl_pin = 13;   // the pins the chip is wired to
    uint8_t regs[128] = {};
    uint8_t ptr = 0;
    int     soft_resets = 0;

    FakeBno() { power_on(); }
    void power_on() {
        memset(regs, 0, sizeof(regs));
        regs[0x00] = 0xA0;   // CHIP_ID
        regs[0x01] = 0xFB;   // ACC_ID
        regs[0x02] = 0x32;   // MAG_ID
        regs[0x03] = 0x0F;   // GYR_ID
        regs[0x04] = 0x11;   // SW_REV_ID_LSB
        regs[0x05] = 0x03;   // SW_REV_ID_MSB
        regs[0x34] = 25;     // TEMP
        regs[0x3B] = 0x80;   // UNIT_SEL default
        regs[0x41] = 0x24;   // AXIS_MAP_CONFIG default (P1)
        regs[0x42] = 0x00;   // AXIS_MAP_SIGN default
    }
    bool config_mode() const { return (regs[0x3D] & 0x0F) == 0; }
    void write_reg(uint8_t r, uint8_t v) {
        if (r == 0x3F && (v & 0x20)) { soft_resets++; power_on(); return; }
        if ((r == 0x3B || r == 0x41 || r == 0x42) && !config_mode()) return;
        if (r == 0x00 || r == 0x04 || r == 0x05) return;      // read-only IDs
        regs[r & 0x7F] = v;
        if (r == 0x3D) regs[0x39] = (v & 0x0F) >= 0x08 ? 5 : 0;
    }
};
inline FakeBno bno;
}

class TwoWire {
public:
    int      sda = -1, scl = -1;
    uint32_t freq = 0;
    uint16_t timeout_ms = 50;
    bool     running = false;
    int      begins = 0;

    bool begin(int sda_pin, int scl_pin, uint32_t frequency) {
        sda = sda_pin; scl = scl_pin; freq = frequency; running = true; begins++;
        return true;
    }
    bool end() { running = false; return true; }
    void setTimeOut(uint16_t ms) { timeout_ms = ms; }

    void beginTransmission(int addr) { addr_ = addr; tx_.clear(); }
    size_t write(uint8_t b) { tx_.push_back(b); return 1; }
    uint8_t endTransmission(bool /*sendStop*/) {
        if (!ok()) return 2;                                  // NACK on address
        if (!tx_.empty()) {
            hostsim::bno.ptr = tx_[0];
            for (size_t i = 1; i < tx_.size(); i++)
                hostsim::bno.write_reg((uint8_t)(tx_[0] + i - 1), tx_[i]);
        }
        return 0;
    }
    uint8_t endTransmission() { return endTransmission(true); }   // the core has both overloads
    uint8_t requestFrom(int addr, int len) {
        rx_.clear();
        addr_ = addr;
        if (!ok()) return 0;
        for (int i = 0; i < len; i++)
            rx_.push_back(hostsim::bno.regs[(hostsim::bno.ptr + i) & 0x7F]);
        return (uint8_t)len;
    }
    int available() { return (int)rx_.size(); }
    int read() {
        if (rx_.empty()) return -1;
        int v = rx_.front();
        rx_.erase(rx_.begin());
        return v;
    }

private:
    int addr_ = 0;
    std::vector<uint8_t> tx_, rx_;
    bool ok() const {
        return running && sda == hostsim::bno.sda_pin && scl == hostsim::bno.scl_pin &&
               addr_ == (hostsim::bno.addr29 ? 0x29 : 0x28) &&
               hostsim::bno.present && !hostsim::bno.fail_all;
    }
};
inline TwoWire Wire;
