> Converted from `AisleBot_Network_SelfHosted_AP.md.pdf`. Original preserved at `docs/originals/AisleBot_Network_SelfHosted_AP.pdf`.

# NarrowAisleBot — Self-Hosted Network (AP mode)

The Pi is its own WiFi network. No router, no eduroam, no IP hunting. Power it on, it broadcasts `AisleBot-Pi`, you join, you work.

| Setting | Value |
|---|---|
| Network name (SSID) | `AisleBot-Pi` |
| Password | `aislebotpi5` |
| Pi address (always) | `10.42.0.1` |
| Dashboard | http://10.42.0.1:8080 |
| SSH | `ssh aritra@10.42.0.1` |

`10.42.0.1` never changes. NetworkManager's shared mode always puts the AP host at that address, so the dashboard and SSH targets are the same every single session. Your phone and PC get `10.42.0.x` handed out automatically by the Pi's own DHCP.

## Connecting

1. Power the Pi. Give it about 30 seconds to boot and bring the radio up in AP mode.
2. On phone and/or PC, join `AisleBot-Pi` (password `aislebotpi5`).
3. Phone: browser to http://10.42.0.1:8080 for the dashboard.
4. PC: `ssh aritra@10.42.0.1` for a terminal.

Phone and PC can both be on it at the same time. Drive from the phone, watch logs over SSH on the PC, no conflict.

## Current status — manual start only

Right now the AP does **not** start automatically on boot. Autoconnect is off, left over from testing as a safety net. If you reboot the Pi today it goes back to eduroam, and `10.42.0.1` won't exist until you bring the AP up by hand:

```bash
sudo nmcli con up aislebot-ap
```

This Pi runs networking through netplan (NetworkManager is just the renderer underneath), and its live profiles sit in `/run`, which is wiped on every reboot. So locking the AP in as the permanent default means writing it into netplan's config, not relying on the autoconnect flag. That's the next step (not done yet).

## Getting the Pi online

The Pi has one radio. As its own AP it has no path to the internet. To go online for a task, switch it back to eduroam:

```bash
sudo nmcli con up eduroam
```

Your PC then rejoins eduroam and reaches the Pi at its `10.53.x.x` address. Switch back home with:

```bash
sudo nmcli con up aislebot-ap
```

Each switch drops your current SSH session, because the radio is changing networks. Reconnect on the new one — that's expected, not a fault.

## What's unaffected by this

ROS2 runs exactly as before. CycloneDDS is bound to loopback, so node discovery never looked at WiFi in the first place. The dashboard code is unchanged; it binds to all interfaces and now just answers on `10.42.0.1`. The ESP32 serial bridge, the udev rules, and `aislebot.service` are all untouched.

## Escape hatch — the ESP32's own AP

The ESP32's own AP stays. It is the escape hatch for when the Pi itself is dead: crash, SD corruption, kernel panic, USB drop. The PID lives on the ESP32, so even with the Pi gone you connect straight to it and drive the robot out of an aisle or stop it.

| Setting | Value |
|---|---|
| SSID | `AisleBot-Control` |
| Password | `aislebot123` |
| Address | http://192.168.4.1 |

To use it, switch your phone off `AisleBot-Pi` and onto `AisleBot-Control`. You're on one network at a time, so reaching the backup is a deliberate "the Pi is down, switch networks" move.

## Troubleshooting

If the dashboard won't load over `AisleBot-Pi`, first suspect the firewall:

```bash
sudo ufw status
```

If it's active and blocking 8080, that's the fix to chase.
