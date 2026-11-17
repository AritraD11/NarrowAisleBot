#!/bin/bash
# 06_wifi_ap.sh - make the Pi its own Wi-Fi access point, so the robot works
# anywhere with no router: join the SSID, open http://10.42.0.1:8080.
#
# Runs only if system.wifi_ap.enable is true. Needs NetworkManager (Ubuntu
# Desktop has it; on Ubuntu Server see manual 6.4 first).
# If you are connected over Wi-Fi, THIS DROPS YOUR SSH SESSION. That is
# expected: join the new network and ssh to 10.42.0.1.
source "$(dirname "$0")/common.sh"
load_env
step "6. Wi-Fi access point"
[ "$AP_ENABLE" = "true" ] || { ok "system.wifi_ap.enable is false: skipped"; exit 0; }
systemctl is-active --quiet NetworkManager || die "NetworkManager is not running (manual 6.4)"
[ ${#AP_PASSWORD} -ge 8 ] || die "wifi_ap.password must be at least 8 characters"
sudo iw reg set "$AP_COUNTRY" >> "$LOG" 2>&1 || warn "could not set Wi-Fi country $AP_COUNTRY"
if nmcli -t -f NAME con show | grep -qx robot-ap; then
    run sudo nmcli con delete robot-ap
fi
run sudo nmcli con add type wifi ifname wlan0 con-name robot-ap autoconnect yes ssid "$AP_SSID" \
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
    ipv4.method shared ipv6.method ignore \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$AP_PASSWORD"
# Higher than any client network, so the AP wins at boot whatever is in range.
run sudo nmcli con modify robot-ap connection.autoconnect-priority 10
ok "connection robot-ap created (SSID $AP_SSID)"
echo "  Bringing it up now. Over Wi-Fi SSH this disconnects you: join $AP_SSID, then ssh $USER@10.42.0.1"
sleep 2
sudo nmcli con up robot-ap >> "$LOG" 2>&1 && ok "AP up: http://10.42.0.1:$DASHBOARD_PORT" \
    || die "nmcli con up robot-ap failed (see $LOG)"
