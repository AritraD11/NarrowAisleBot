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

## Current status — persists across reboot

Confirmed as of 5 Aug 2026: the AP survives a reboot with no manual step. `aislebot-ap` is written into a real, persistent netplan file (`/etc/netplan/90-NM-*.yaml`, not the `/run` copy that gets wiped) with `connection.autoconnect: yes` and `connection.autoconnect-priority: 10`. Neither `eduroam` nor `IITB-Wireless` sets a priority (default 0), so `aislebot-ap` always wins the boot-time autoconnect race regardless of what other networks are in range. Power-cycle the Pi and it comes back on `AisleBot-Pi` / `10.42.0.1` on its own.

The manual command is still useful for the one real case it's needed — coming back from eduroam mid-session (see below):

```bash
sudo nmcli con up aislebot-ap
```

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

## Full round trip: get online, sync the clock, pull CSVs, come back home

The complete sequence for "I need real data off the Pi" — go online just long enough to fix the clock and grab logs, then return to the robot's own network. The `ssh`/`nmcli` steps run **on the Pi**; the `scp`/`rsync` step runs **on your PC**, outside any SSH session.

```bash
# 1. SSH in on whichever network you're currently on
ssh aritra@10.42.0.1                  # if already on AisleBot-Pi
#  or, if you don't know the current IP:
ssh aritra@aritra-desktop.local

# 2. On the Pi, switch to eduroam
sudo nmcli con up eduroam
#    -> drops the SSH session immediately. Expected, not a fault.

# 3. Reconnect. eduroam hands out a DHCP address, not a fixed one like
#    10.42.0.1, so don't go hunting for an IP — use the mDNS hostname:
ssh aritra@aritra-desktop.local

# 4. Confirm REAL internet, not just link-layer association, then sync
#    the clock. Don't skip straight to apt/ntp — narrow the failure first:
ping -c3 8.8.8.8              # raw L3 connectivity, bypasses DNS
ping -c3 google.com           # DNS resolution
sudo systemctl restart systemd-timesyncd
timedatectl status            # look for "System clock synchronized: yes"

# 5. From the PC — a NEW terminal, not the SSH session — pull the logs
scp aritra@aritra-desktop.local:~/aislebot_logs/*.csv .
#  or, to mirror the whole folder and skip files you already have:
rsync -avz aritra@aritra-desktop.local:~/aislebot_logs/ ./aislebot_logs/

# 6. Back on the Pi's SSH session, return to the robot's own network
sudo nmcli con up aislebot-ap
#    -> drops SSH again, expected. Reconnect at the fixed 10.42.0.1 once
#       the AP is back up (~10-15s).
```

**Do step 4 every round trip, not just when something looks wrong.** The Pi has no battery-backed RTC, so the clock drifts out of sync the moment it reboots without WAN — it doesn't announce this, a file's timestamp just quietly becomes untrustworthy. See `Research_Journal.md` Part XVI §16.4 for how this was found and why a hardware RTC (DS3231) is the real fix.

## What's unaffected by this

ROS2 runs exactly as before. CycloneDDS is bound to loopback, so node discovery never looked at WiFi in the first place. The dashboard code is unchanged; it binds to all interfaces and now just answers on `10.42.0.1`. The ESP32 serial bridge, the udev rules, and `aislebot.service` are all untouched.

## ⚠ Escape hatch — REMOVED in firmware v3.0 (4 Aug 2026)

**The ESP32 no longer hosts a WiFi network.** `AisleBot-Control` @ `192.168.4.1` does not exist on v3.0 firmware — the radio, WebSocket server, and joystick web page were all removed when the Pi became the sole command source (`Research_Journal.md` Part XVI). Any older note in these docs describing it as a live fallback is stale.

**What this changes, practically:** there is no longer a way to *drive* the robot with the Pi down. That was the escape hatch's whole purpose, and it is gone.

**What still protects you:**

| Layer | Behaviour | Works if the Pi is dead? |
|---|---|---|
| ESP32 command watchdog | No command for 750 ms → motors ramp to stop | **Yes** — this is on the ESP32 itself |
| ESP32 runaway / stall / overspeed trips | Latch E-STOP on fault | **Yes** |
| Pi dashboard E-STOP | Sends `<S>`, latches until `<E1>` | No |
| `Ctrl-C` in `nab_pid_logger.py` | Sends `<S>` then `<E0>` | No |
| Battery main disconnect (SSR / physical) | Cuts power | **Yes** — the true last resort |

So a dead Pi now means the robot **stops** (watchdog) rather than becoming drivable-by-other-means. That is the safer failure mode of the two, but it is a real capability loss: keep the battery disconnect physically reachable during ground testing, because it is now the only manual override that does not depend on the Pi.

Restoring a hardware-independent escape hatch — a cheap 2.4 GHz RC receiver on a spare ESP32 input, or re-adding a minimal WiFi E-STOP-only endpoint — is an open item, not a solved problem.

## Troubleshooting

If the dashboard won't load over `AisleBot-Pi`, first suspect the firewall:

```bash
sudo ufw status
```

If it's active and blocking 8080, that's the fix to chase.
