# Important Commands — Login, Deploy, Downloads

A copy-paste cheat sheet for the commands used over and over again once
the robot is up and running. For the *why* behind any of these, see
`Network_SelfHosted_AP.md` (networking) and `Research_Journal.md` Part XVI
(bringup, dashboard, and the automated report — §16.9–§16.15).

---

## 1. Logging in

**On the robot's own network (AisleBot-Pi AP)** — the normal case, fixed IP:
```bash
ssh aritra@10.42.0.1
```

**On eduroam instead** — DHCP hands out a different address every time, so
use the mDNS hostname rather than hunting for an IP:
```bash
ssh aritra@aritra-desktop.local
```

**Switching the Pi's network** (each switch drops your current SSH session —
expected, reconnect on the new one):
```bash
sudo nmcli con up eduroam        # -> internet, no direct robot LAN
sudo nmcli con up aislebot-ap    # -> back to the robot's own network
```
Full detail, including the "get online just long enough to sync the clock
and grab data" round trip: `Network_SelfHosted_AP.md`.

---

## 2. Deploying a code change from GitHub to the Pi

There's no persistent git clone on the Pi — deployed code lives only under
`~/ros2_ws/src` (see Research_Journal.md §16.7). To deploy a changed file,
pull it directly from GitHub's raw URL for the branch you're working on:

```bash
curl -sSL -o ~/ros2_ws/src/mecanum_robot/mecanum_robot/<file>.py \
  https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/<branch>/src/mecanum_robot/mecanum_robot/<file>.py
```

This needs the repo reachable — either the repo is public, or the Pi is on
a network with GitHub access (eduroam, not the AisleBot-Pi AP, which has no
internet uplink).

**Verify the copy landed correctly** before trusting it — compare against
the hash of the file in the repo (`sha256sum <path-in-your-local-checkout>`):
```bash
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/<file>.py
```

**Rebuild and restart** (always do this after any change, even a pure
Python file — a `setup.py` change needs the rebuild to register new
console_scripts entries, and it's cheap enough to just always run it):
```bash
cd ~/ros2_ws
colcon build --packages-select mecanum_robot
source install/setup.bash
sudo systemctl restart aislebot.service
```

**Confirm the new version is actually running:**
```bash
grep "Phone Dashboard" ~/aislebot_boot.log | tail -3
ros2 pkg executables mecanum_robot | grep <expected_new_executable>
```

---

## 3. Downloading data off the Pi to your PC

Run these **on your PC** (PowerShell), in a new terminal — not inside the
SSH session. Confirmed working, downloads straight into the ground-test
folder:

```powershell
scp aritra@10.42.0.1:~/aislebot_logs/*.csv "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
scp aritra@10.42.0.1:~/aislebot_logs/*.pgm "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
scp aritra@10.42.0.1:~/aislebot_logs/*.yaml "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
scp aritra@10.42.0.1:~/aislebot_logs/*_report.json "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

**Just one run's full set** — map, metadata, and the auto-generated report —
swap the glob for that run's timestamp:
```powershell
scp aritra@10.42.0.1:~/aislebot_logs/run_<timestamp>.* "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

**Everything, or just what's new since last time:**
```powershell
rsync -avz aritra@10.42.0.1:~/aislebot_logs/ "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

If you're not on the AisleBot-Pi AP (e.g. pulling from off-site over
eduroam), swap `10.42.0.1` for `aritra-desktop.local`. Pulling to a
different folder some other time, swap out the destination path — it's
just the last argument to `scp`/`rsync`.

---

## 4. Where things live on the Pi

| What | Path |
|---|---|
| Deployed ROS 2 code | `~/ros2_ws/src/mecanum_robot/` |
| Run data (CSV + map `.pgm`/`.yaml` + auto-report `.json`) | `~/aislebot_logs/run_<timestamp>.*` |
| Combined node log (not `journalctl` — that only shows systemd start/stop) | `~/aislebot_boot.log` |
| Manual SLAM config | `~/ros2_ws/slam_nodom.yaml` |

Every mapping run (pressing **Map** on the dashboard) produces four files
sharing one timestamp: `run_*.csv`, `run_*.pgm`, `run_*.yaml`,
`run_*_report.json` — see Research_Journal.md §16.14–§16.15.

---

## 5. Viewing a map

Don't open the raw `.pgm`. Use `docs/tools/telemetry_analyzer.html` — a
single self-contained file, no server or install needed:

1. Download it once (it lives in this repo, not on the Pi):
   ```powershell
   # save-as from a browser, or:
   curl -sSL -o telemetry_analyzer.html ^
     https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/docs/tools/telemetry_analyzer.html
   ```
2. Double-click to open it in any browser.
3. Drag in that run's `.csv`, then its `.pgm` + `.yaml` pair together onto
   the Map tab. It renders the occupancy grid and shows the same
   coverage/quality findings that get logged on the Pi automatically.

---

## 6. Live visualization (Foxglove)

`aislebot_full.launch.py` now starts `foxglove_bridge` on port 8765 by
default (Research_Journal.md §17.5) — a websocket that Foxglove Studio
connects to. This is the headless-friendly route because DDS multicast
doesn't cross this network, so RViz running directly on a laptop can't
see the robot's topics; Foxglove's plain-TCP websocket bridge can.

1. Install [Foxglove Studio](https://foxglove.dev/download) on your laptop
   (desktop app or the web app both work).
2. Make sure your laptop is on the same network as the Pi (AisleBot-Pi AP
   or eduroam, matching whichever the Pi is on).
3. In Foxglove Studio: **Open connection → Foxglove WebSocket**, then enter:
   ```
   ws://10.42.0.1:8765
   ```
   (swap the IP for `aritra-desktop.local` if you're both on eduroam.)
4. Add panels for `/map`, `/scan_reliable`, `/tf`, and a 3D panel with the
   robot model — same information RViz2 would show, just over a
   connection that actually works on this network.

If the connection fails, confirm the bridge is actually running:
```bash
ros2 node list | grep foxglove
ss -tlnp | grep 8765
```

---

## 7. Quick health checks

```bash
ros2 node list                              # what's actually running
ros2 topic hz /motor_telemetry_raw          # ESP32 telemetry arriving at all?
ros2 topic hz /wheel_velocities_actual      # parsed into odometry?
ros2 run tf2_ros tf2_echo odom base_link    # odom TF alive and tracking?
ros2 topic hz /map                          # SLAM producing a map? (~1 Hz is normal)
ps aux | grep mapping_full | grep -v grep   # confirm no orphaned mapping launch after stopping
```
