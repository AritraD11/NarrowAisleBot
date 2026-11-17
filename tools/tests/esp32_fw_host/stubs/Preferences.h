// Host stand-in for arduino-esp32's Preferences (NVS key-value storage).
// An in-memory map, plus a write counter so a test can see exactly when the
// firmware touched flash (on the robot an NVS write pauses both cores).
//
// Behaviour copied from the real class where the firmware depends on it:
//   * begin(name, readOnly=true) fails if nothing was ever written to the
//     namespace, as nvs_open(NVS_READONLY) does on a first boot
//   * getBytes() returns 0 if the buffer is smaller than the stored blob
//   * putBytes() returns the length written, 0 on failure
#pragma once
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace hostsim {
struct Nvs {
    std::map<std::string, std::vector<uint8_t>> kv;   // "namespace/key" -> bytes
    int  writes      = 0;       // putBytes and successful removes
    bool fail_writes = false;   // every putBytes returns 0
};
inline Nvs nvs;
}

class Preferences {
public:
    bool begin(const char* name, bool readOnly = false, const char* /*partition*/ = nullptr) {
        ns_ = name;
        ro_ = readOnly;
        open_ = true;
        if (readOnly) {
            bool any = false;
            for (const auto& e : hostsim::nvs.kv)
                if (e.first.rfind(ns_ + "/", 0) == 0) any = true;
            if (!any) { open_ = false; return false; }
        }
        return true;
    }
    void end() { open_ = false; }

    size_t putBytes(const char* key, const void* value, size_t len) {
        if (!open_ || ro_ || hostsim::nvs.fail_writes) return 0;
        const uint8_t* p = (const uint8_t*)value;
        hostsim::nvs.kv[ns_ + "/" + key] = std::vector<uint8_t>(p, p + len);
        hostsim::nvs.writes++;
        return len;
    }
    size_t getBytesLength(const char* key) {
        if (!open_) return 0;
        auto it = hostsim::nvs.kv.find(ns_ + "/" + key);
        return it == hostsim::nvs.kv.end() ? 0 : it->second.size();
    }
    size_t getBytes(const char* key, void* buf, size_t maxLen) {
        if (!open_) return 0;
        auto it = hostsim::nvs.kv.find(ns_ + "/" + key);
        if (it == hostsim::nvs.kv.end() || it->second.size() > maxLen) return 0;
        memcpy(buf, it->second.data(), it->second.size());
        return it->second.size();
    }
    bool remove(const char* key) {
        if (!open_ || ro_) return false;
        bool erased = hostsim::nvs.kv.erase(ns_ + "/" + key) > 0;
        if (erased) hostsim::nvs.writes++;
        return erased;
    }

private:
    std::string ns_;
    bool ro_   = false;
    bool open_ = false;
};
