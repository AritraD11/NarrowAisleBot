// Host stand-in for ESP-IDF's legacy PCNT driver (driver/pcnt.h). Only
// the names aislebot_esp32.ino uses; counters always read zero.
#pragma once
#include <cstdint>

typedef int esp_err_t;
typedef enum { PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3 } pcnt_unit_t;
typedef enum { PCNT_CHANNEL_0, PCNT_CHANNEL_1 } pcnt_channel_t;
typedef enum { PCNT_COUNT_DIS, PCNT_COUNT_INC, PCNT_COUNT_DEC } pcnt_count_mode_t;
typedef enum { PCNT_MODE_KEEP, PCNT_MODE_REVERSE, PCNT_MODE_DISABLE } pcnt_ctrl_mode_t;

typedef struct {
    int               pulse_gpio_num;
    int               ctrl_gpio_num;
    pcnt_ctrl_mode_t  lctrl_mode;
    pcnt_ctrl_mode_t  hctrl_mode;
    pcnt_count_mode_t pos_mode;
    pcnt_count_mode_t neg_mode;
    int16_t           counter_h_lim;
    int16_t           counter_l_lim;
    pcnt_unit_t       unit;
    pcnt_channel_t    channel;
} pcnt_config_t;

inline esp_err_t pcnt_unit_config(const pcnt_config_t*) { return 0; }
inline esp_err_t pcnt_set_filter_value(pcnt_unit_t, uint16_t) { return 0; }
inline esp_err_t pcnt_filter_enable(pcnt_unit_t) { return 0; }
inline esp_err_t pcnt_counter_pause(pcnt_unit_t) { return 0; }
inline esp_err_t pcnt_counter_clear(pcnt_unit_t) { return 0; }
inline esp_err_t pcnt_counter_resume(pcnt_unit_t) { return 0; }
inline esp_err_t pcnt_get_counter_value(pcnt_unit_t, int16_t* v) { *v = 0; return 0; }
