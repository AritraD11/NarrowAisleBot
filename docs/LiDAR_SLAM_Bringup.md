# AisleBot — LiDAR + SLAM Bringup (clean restart guide)

Everything below was verified working on **26 June 2026**. The hardware integration,
SDK, ROS driver, and configs are all permanent and survive reboots. A fresh session
only needs to *launch* things, not rebuild them.

> `scan_relay.py` and `slam_nodom.yaml`, referenced throughout below, are now vendored
> in this repo at `src/scan_relay/scan_relay.py` and `system/slam_nodom.yaml`
> respectively — both cross-checked against the live Pi copies on 8 July 2026 and
> confirmed identical. `install.sh` places them at the paths used below automatically.

Stack: Pi 5, Ubuntu 24.04, ROS2 Jazzy, YDLIDAR X4 Pro on `/dev/ydlidar`.

---

## The one thing that went wrong last time (check this FIRST)

On the final boot the lidar came up reading **Sample Rate 2.59K** instead of the
healthy **5.00K**, with a nonstop flood of `Checksum error` and point counts swinging
all over the place. That's real data corruption, not the normal first-second flicker.

It's almost certainly physical: a USB-C not fully seated, or the buck sagging and
starving the motor (an uneven spin wrecks the optical timing and trashes checksums).

So before anything else: reseat both USB cables (the data USB-C into the Pi, and the
power lead into the buck), push till they click, and watch the disc spin. It should
turn smooth and steady, not stutter or wobble.

A healthy lidar launch shows `Sample Rate: 5.00K` and settles near ~1258 points per
scan at ~11.5 Hz. If you see 2.59K and endless checksum errors, stop and fix power or
seating. Don't build a map on garbage scans.

---

## Two silent blockers found 6 Aug 2026 (check both before anything else)

**`ydlidar.service`.** A systemd unit exists on the Pi
(`/etc/systemd/system/ydlidar.service`, driven by `/home/aritra/start_lidar.sh`)
that auto-starts the lidar driver + `scan_relay.py` at boot, independent of
`aislebot.service`. It is **not vendored in this repo** — nothing in `system/`
or `install.sh` knows about it. If it's enabled, every manual Terminal 1 +
Terminal 2 launch below stacks a second `/ydlidar_ros2_driver_node` and
`/static_tf_pub_laser` on top of it, which corrupts scan data (checksum-error
floods that look identical to the cable/vibration signature below, but aren't)
and doubles `/scan_reliable`'s rate. Check first:
```bash
systemctl status ydlidar.service --no-pager
ros2 node list | sort | uniq -d      # any output here means a live duplicate
```
If it's `active (running)`, either work entirely through it (skip Terminal 1 +
2 below, they're redundant) or `sudo systemctl stop ydlidar.service &&
sudo systemctl disable ydlidar.service` first for a clean, fully-manual,
single-reader run. Don't mix manual terminals with this service left running.

**`esp32_bridge`'s telemetry gate.** `odometry_publisher` only ever broadcasts
the `odom → base_link` TF from inside its `/wheel_velocities_actual`
subscription callback — no timer, no fallback, no periodic heartbeat. That
topic only gets messages once `esp32_bridge` has sent the ESP32 `<L1>`
(enable telemetry), which is gated by its `telemetry_enabled` parameter
(now defaulted `True` in `aislebot_full.launch.py` as of this fix — if the Pi
is still running an older deployed copy of that launch file, it's `False`
there and needs redeploying, same drift pattern as §16.7 in the Research
Journal). Without it, `odom` doesn't just go stale — `tf2_echo` reports
"frame does not exist" — and since `slam_nodom.yaml` sets `odom_frame: odom`,
slam_toolbox will sit at `Activating` forever with **zero further log output,
no error**. This blocks mapping regardless of how healthy the lidar and relay
are, and driving the robot around doesn't fix it either — it's not about
motion, it's about the ESP32 never being told to start reporting at all.
Confirm before trusting a silent `Activating`:
```bash
ros2 run tf2_ros tf2_echo odom base_link
```
If it reports "frame does not exist", enable telemetry live with no restart:
```bash
ros2 topic pub --once /esp32/command std_msgs/msg/String "data: '<L1>'"
```

---

## Hardware facts worth not re-discovering

The X4 Pro adapter has two USB ports. USB-B is power (goes to your 5V buck), USB-C is
data (goes to the Pi). Both plugged at once is correct. The motor runs off the buck
through the power port, so it spins even with the data cable out.

The X4 Pro is a **single-channel** unit. It only streams; it ignores device-info and
health queries. So `Fail to get baseplate device information` in the logs is expected
and harmless. If you ever try to run it as two-way (`isSingleChannel: false`) it dies
with `Fail to start the lidar` and health code -2.

The udev naming was the gnarly part. Your ESP32 and the lidar adapter are both CP2102
chips with the *same* VID:PID (`10c4:ea60`) AND the same factory serial (`0001`), so
serial can't tell them apart. They're pinned by physical USB port instead. Which means:
**don't move the lidar cable to a different USB socket** or `/dev/ydlidar` vanishes
until you move it back. Current port map: ttyUSB0 = Mega, ttyUSB1 = ESP32 (port 4-1),
ttyUSB2 = lidar (port 2-2).

---

## Confirmed X4 Pro parameters

These are read off the hardware, not copied from a forum. They live in
`~/ros2_ws/src/ydlidar_ros2_driver/params/ydlidar.yaml`, and the repo's
copy of record is `system/ydlidar_params.yaml`, which `install.sh:220`
copies to that path (renaming it on the way in).

**Reproduce the file exactly as shown, wrapper included.** An earlier
version of this section listed only the values, without the
`ydlidar_ros2_driver_node: / ros__parameters:` nesting they sit under. On
13 Aug 2026 that listing was transcribed verbatim into
`system/ydlidar_params.yaml` as a flat file — and a flat parameter file
does not half-work in ROS 2, it binds nothing at all. The driver would
have fallen back to its compiled defaults (wrong `baudrate`, wrong
`lidar_type`, wrong `isSingleChannel` for an X4 Pro) with no obvious
error pointing at the cause. It never fired only because `install.sh` had
not run since 26 June. Corrected 24 Aug 2026, verified byte-identical to
the Pi's working copy (sha256 `049fbbe7bff9…`, 561 bytes).

```yaml
ydlidar_ros2_driver_node:
  ros__parameters:
    port: /dev/ydlidar
    frame_id: laser_frame
    ignore_array: ""
    baudrate: 128000
    lidar_type: 1
    device_type: 0
    isSingleChannel: true
    intensity: false
    intensity_bit: 0
    sample_rate: 5
    abnormal_check_count: 4
    fixed_resolution: true
    reversion: false
    inverted: false
    auto_reconnect: true
    support_motor_dtr: false
    angle_max: 180.0
    angle_min: -180.0
    range_max: 12.0
    range_min: 0.1
    frequency: 10.0
    invalid_range_is_inf: false
    debug: false
```

`range_max: 12.0` here is the **driver's** publishing limit and is
deliberately not the same number as `slam_nodom.yaml`'s
`max_laser_range: 10.0` (Stage B). The driver publishes returns out to
12 m; slam_toolbox chooses to ignore anything past 10 m when building the
graph. Both are correct as written.

---

## The QoS gotcha (why a relay exists)

The ydlidar driver publishes `/scan` as **best-effort**. rf2o and slam_toolbox both
subscribe as **reliable** by default, so they never connect and sit forever printing
"Waiting for laser_scans" even though `/scan` is clearly alive (`ros2 topic echo` and
`hz` work fine because they negotiate compatible QoS).

The fix is a tiny relay that re-publishes the scan with reliable QoS. It already exists
at `~/ros2_ws/src/scan_relay/scan_relay.py` (a plain python3 script, no build needed):
subscribe `/scan` best-effort, republish `/scan_reliable` reliable. Everything
downstream reads `/scan_reliable`.

Decision from last session: **rf2o is dropped.** It kept failing even through the relay
and was more trouble than it was worth on Jazzy. We map with slam_toolbox alone,
scan-matching only, no external odometry, for the first map. The relay still matters
because slam_toolbox hits the identical QoS wall.

---

## Bringup sequence (the actual restart)

**As of 6 Aug 2026, this collapses into one command**, now that the pipeline itself is
proven end-to-end (Research_Journal.md §16.8-16.9):
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch mecanum_robot mapping_full.launch.py
```
This runs the same three pieces below (lidar driver, QoS relay, slam_toolbox) as one
process tree instead of three manual terminals. It is **on-demand only, by design** —
nothing about it auto-starts at boot, matching how `ydlidar.service` auto-starting
independently of manual runs was the root cause of most of §16.8-16.9's debugging.
Launch it when you actually want to map, same as before. It still needs `odom->base_link`
TF already flowing from `aislebot.service` (see the telemetry gotcha below) — if that's
missing it will sit silently with slam_toolbox never reaching `Registering sensor`, same
failure mode as the manual path.

The per-terminal breakdown below is still the right tool for debugging a failure — it's
what originally diagnosed the QoS mismatch, the duplicate-node collision, and the
telemetry gate, and it's what actually caught the `/scan_reliable` rate doubling to
begin with. Reach for it if `mapping_full.launch.py` doesn't come up clean and you need
to isolate which piece is unhealthy.

Each long-running node holds its own terminal. Open them one at a time, confirm each is
healthy before the next.

**Terminal 1 — lidar:**
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch ydlidar_ros2_driver ydlidar_launch.py
```
Wait for `Lidar has started!`, confirm `Sample Rate: 5.00K`, then leave it scrolling
`Real points` lines. Don't touch it again. This launch ALSO publishes the
`base_link -> laser_frame` static transform, so the TF link is handled here.

**Terminal 2 — QoS relay:**
```bash
source ~/ros2_ws/install/setup.bash
python3 ~/ros2_ws/src/scan_relay/scan_relay.py
```
You want one line confirming it's forwarding, then silence. Verify with
`ros2 topic hz /scan_reliable` (should read ~11 Hz) from a spare terminal.

**Terminal 3 — slam_toolbox (note the ABSOLUTE path, no `~`):**
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=/home/aritra/ros2_ws/slam_nodom.yaml
```
A `~` here silently fails — the launch system won't expand it and slam falls back to
its defaults (wrong topic, expects odom). Watch for `Configuring` then `Activating`
with NO "is not a file" warning above them — but don't trust `Activating` on its
own, it only means the lifecycle node reached the active state, not that scans are
being consumed. Wait for the next line:
```
Registering sensor: [Custom Described Lidar]
```
That's the proof slam_toolbox actually processed a scan. If `Activating` appears but
this line never does, and there's no error either, check the `odom` TF gotcha above
before assuming it's a lidar or relay problem — that silent-hang symptom is exactly
what the telemetry gate produces.

**Verify the map is building:**
```bash
ros2 topic hz /map               # ~1 Hz is fine, map updates slowly
ros2 run tf2_ros tf2_echo map base_link   # should print numbers, not an error
```

**Save the map when it looks decent:**
```bash
ros2 run nav2_map_server map_saver_cli -f ~/aislebot_first_map
```

---

## A note on viewing the map (headless)

Your Pi runs CycloneDDS loopback-only, eduroam blocks DDS multicast, and a Windows
laptop on a different RMW won't discover topics anyway. So RViz-on-laptop won't see
`/scan` or `/map` over the network as-is. The headless-friendly route is Foxglove
Bridge: it runs a websocket on the Pi, and Foxglove Studio on the laptop connects to
`pi-ip:8765` over plain TCP. That wasn't set up yet — it's the natural next piece once
the map builds clean.

---

## Where this sits in the bigger roadmap

Done: lidar live, TF link up, relay solving QoS, slam config ready.
Today's finish line: a first occupancy grid you can save.

Not today (and why): Nav2 needs trustworthy localization, which needs real odometry.
Mecanum wheel odom drifts hard from roller slip, so that path runs through the ESP32
encoder bridge + a BNO055 IMU and EKF fusion before Nav2 with the MPPI controller makes
sense. That's a separate session.
