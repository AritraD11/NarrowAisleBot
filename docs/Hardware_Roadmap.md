# Hardware Roadmap — additions, not yet procured

**Status: planning document. Nothing in this file is installed on the robot.**
Per this project's own discipline (§17.32 and onward): a value in a doc is
not a value on the robot, and by the same rule, a part in this doc is not a
part in the parts bin. Every item below is a recommendation with its
reasoning attached, so the next session can buy against it rather than
re-derive it.

Written 3 Sep 2026, closing out Stage G. Nothing here changes what is
currently running — see `docs/StageG_Deploy.md` and `Research_Journal.md`
§17.50–§17.56 for what is actually deployed and measured.

---

## 0. How to read this document

Every recommendation carries the reasoning that produced it, and every
reasoning carries a grade in the project's own vocabulary:

| Grade | Means |
|---|---|
| ✅ **MEASURED** | A number from this robot's own logs or drives |
| 🟡 **PRINCIPLE** | Sound engineering reasoning, not yet tested on this robot |
| 🔷 **JUDGEMENT CALL** | A real trade-off with a recommended side, stated so it can be revisited |

Nothing below is graded MEASURED, because nothing below has been built yet.
That is the honest state of a roadmap.

---

## 1. Obstacle/collision hardware — carried forward from the Stage G session

This section supersedes the informal Tier 1/2/3 list worked out in chat
during the Stage G session. It is written down here for the first time so
it survives past this conversation.

### 1.1 IMU — BNO085 (or BNO055)

**Why.** §17.55 and §17.56 measured phantom yaw directly: the robot
returned to its true heading on video (validated against a known rotation
each time, agreement within 1°) while the odometry reported 3.85° and
4.49° of rotation that never physically happened. That is **0.4–0.6°/m of
estimator error**, the same order as §17.42's 10.53°/18 m figure this
project has been treating as physical slip. 🟡 PRINCIPLE, but with a
✅ MEASURED number behind it for the first time: a gyro reading integrates
yaw rate once; the encoder-only estimate currently has no independent check
on heading at all.

**Which part.** BNO085 over BNO055: same footprint, newer, and its "game
rotation vector" mode is gyro+accel with the magnetometer held out —
useful on a chassis with a 24 V/30 A motor bus nearby, where hard-iron and
dynamic magnetic interference are a real risk to a fused heading. Run
6-axis first; enable the magnetometer only if a measured comparison shows
it helps.

**Where it goes.** ESP32 I²C, G14 (SDA) / G13 (SCL) — the two pins
reserved for exactly this since Master_Reference v4.0. Host it on the
ESP32, not the Pi: one fewer serial hop into the EKF, and the ESP32 has a
100 Hz loop with headroom (§17.31's DOB/RLS roadmap already assumed this
much CPU margin exists).

### 1.2 Optical flow ground sensor — PMW3901 or PAA5100JE

**Why.** The IMU fixes yaw. It does nothing for translational slip, which
is the other half of the odometry error (§17.21: a 1.00 m strafe reads
1.245 m, twice, 3 mm apart). An optical flow sensor measures true ground
velocity and does not care what the wheels are doing.

**Which part.** PAA5100JE if ground clearance allows (10–35 mm); PMW3901
if not (needs ≥ 80 mm). **Ground clearance has never been measured on this
chassis — measure it before ordering.**

### 1.3 The 360°, ~1 m collision ring — this session's new spec

The operator's brief for this item is precise and worth restating exactly,
because it changes the part selection from the original Tier‑1 sketch:
**full 360° coverage, short range (~1 m is enough), not for path-planning,
purely a hard override that stops the robot when something enters the
cushioning zone — working alongside SLAM rather than inside it.**

This **replaces** the earlier narrower idea (a couple of VL53L5CX units
patching the rear mast wedge and the sub-LiDAR-plane blind spot). A full
ring subsumes both of those: the rear wedge is just one arc of the ring,
and mounting the ring below the LiDAR plane solves the sub-plane problem
for free, everywhere around the robot rather than only at the two
previously-identified trouble spots.

**Part choice: ToF (VL53L5CX), not ultrasonic. Reasoning below.**

Three real options for a full-perimeter short-range ring:

| Option | Reliability at ~1 m | Integration cost |
|---|---|---|
| Ultrasonic (HC-SR04-class) | 🔷 Real failure mode: specular reflection off cloth, foam, or any surface hit at an oblique angle sends the ping away instead of back. Warehouse cargo is exactly this kind of surface. | Low — cheap, simple GPIO trigger/echo |
| Analog IR (Sharp GP2Y-class) | Already ruled out earlier in this project's own hardware discussion — triangulation-based, noisy, reads differently depending on target colour | Low |
| **ToF (VL53L5CX)** | At 1 m, signal margin is large — this is a sensor rated to 4 m, being asked to work at a quarter of that, so the dark-material weakness that would matter at longer range is much less of a concern here | Higher — I²C bus, address multiplexing, more wiring around a narrow chassis |

The operator's brief says "reliable" explicitly. Ultrasonic's specular
failure mode against soft or angled cargo surfaces is a genuine risk for a
system whose entire job is "must not miss." ToF costs more in wiring
labour and buys back exactly that reliability. 🔷 JUDGEMENT CALL, made in
ToF's favour for that reason.

**Why VL53L5CX over VL53L1X for this specific job.** VL53L1X is
single-zone with a narrower 27° FoV — full 360° coverage needs roughly 14
units. VL53L5CX's 63° diagonal FoV (≈ 45° × 45° square, measured out in
this session's chat) covers the same 360° with roughly 8 units. The extra
8×8 zone data VL53L5CX provides is not needed for this job — a
"nearest point in this wedge" reduction in software is enough — but having
it costs nothing, and fewer physical units means fewer wiring runs on a
250 mm-wide chassis. Take the simpler harness.

**Count and placement — stated honestly as an estimate.** At 45° per unit,
360° needs 8 units minimum with no overlap margin. This chassis is
1000 mm long and asymmetric, with a rear mast that already needs its own
coverage (the existing masked wedge, §17.15) — a single mid-side sensor's
cone does not necessarily reach both ends of a 1 m-long side without a
gap, so expect the real number to land in the **8–12 unit** range once
placed against the physical chassis. This document does not claim a CAD
placement; that is a build-time decision, not a shopping-list one.

**Mounting height.** One ring, not two. Height chosen to catch the widest
practical obstacle silhouette (~25–35 cm — below LiDAR-plane cargo,
through human shin height) rather than doubling the unit count for a
second ring. Mounting it below the LiDAR plane resolves the sub-plane
blind spot as a side effect, without a separate sensor set for that
problem.

**How it plugs into software — no new architecture, just a new input.**
This must **not** touch `slam_toolbox`: that consumes exactly one
`LaserScan` topic, and stuffing a short-range point cloud into a fake scan
is a proven way to corrupt a map (this project's map already grades
`FOLDED` without any help). The correct integration point already exists:
`nav2_costmap_2d::RangeSensorLayer` on the **local** costmap, which is
`global_frame: odom` and does not touch `map→odom` at all — confirmed
architecture from the Stack Assessment's own §5 table. From there it
participates automatically in `collision_monitor`'s existing
`FootprintApproach` polygon, which is exactly "stop when something enters
the cushioning zone" already built and configured
(`src/mecanum_navigation/config/nav2_params.yaml`).

The one config change this earns: add the ring as a **second**
`observation_source` alongside `scan` in `collision_monitor`
(`observation_sources: ["scan", "ring"]`). That is a real, independent
safety win — this project has measured the LiDAR at 47% valid with
74–78% flicker; a ring that does not depend on SLAM, scan matching, or
`map→odom` being healthy at all is a second witness that fails
differently. That is the "last line of defence" character the brief asked
for.

### 1.4 Everything else already argued for in this session

Carried forward without re-litigating, since the reasoning stands and
nothing has changed it:

- **Hardware E-stop** — 22 mm latching mushroom, NC, in series with the
  SSR-50DD trigger, plus a wireless remote. There is currently no hardware
  stop; every path to stopping the robot runs through software already
  measured failing blind (§17.25).
- **INA226 current/voltage sensor** — see §2 below, now doing double duty.
- **USB data-only cable / VIN fix** for the ESP32, per Master_Reference
  §3.1, never actually done.
- **Pi 5 active cooling + verified 5 A supply** — a throttled Pi is
  indistinguishable from the CPU starvation already measured (§17.25,
  §17.43).
- **Shielded, locking LiDAR USB cable** — §16.8's corruption episode's
  leading suspect was a marginal connection under vibration, never pinned.
- **Contact bumper strip**, into the same hardware E-stop loop — the one
  sensor still working when the scan is stale and the CPU is gone.

---

## 2. Battery percentage on the Pi / dashboard

### 2.1 The problem, stated honestly first

Nothing on this robot currently measures battery voltage or current.
Confirmed by reading `aislebot_esp32.ino`: no ADC read, no divider,
nothing battery-related anywhere in the firmware.

**And a simple voltage-divider-to-percentage mapping will be genuinely
bad on this pack, for a reason this project already put in writing as a
*feature*.** `Adaptive_Control_Roadmap.md` §3 notes the LiFePO4 pack was
chosen specifically for its **flat discharge curve** — it sits near
nominal voltage for most of its usable capacity and only drops sharply
near empty. That flatness is good for motor consistency and bad for
voltage-based state-of-charge: in the middle of the curve, a large swing
in remaining capacity corresponds to a tiny, load-noise-sized swing in
voltage. A cheap voltage-divider "battery %" would be confidently wrong
for most of the pack's life.

### 2.2 The fix: reuse a part already on this document's list

**INA226**, already recommended earlier in this session as the instrument
to settle the "brownout under load" hypothesis behind the recurring ESP32
resets. It measures both voltage **and current**, bidirectionally, on a
shunt. The same part, wired into the main pack discharge path, gives:

- **Coulomb counting** — integrate measured current over time in software
  (`∫I·dt ÷ rated_Ah`) for the actual state-of-charge number, which is
  robust to the flat-curve problem because it never depends on reading
  voltage in the flat region at all.
- **A periodic open-circuit-voltage correction** — when current is near
  zero (robot parked, motors idle), voltage *is* meaningful again, and can
  correct any coulomb-counter drift against a coarse LiFePO4 OCV table
  (roughly 13.0 V near empty, 14.6 V near full for this 4-cell pack).
- **Charge detection for free** (see §3.4) — the same bidirectional
  measurement sees current reverse sign when a charger is pushing current
  in, with no extra sensor.

**Which module.** An INA226 breakout with a shunt rated for this pack's
real current range, not the default low-current modules sold for USB
power monitoring. The motors alone can draw up to 30 A stall each; the
SSR-50DD is the real ceiling at 50 A continuous. Look for an
"INA226 50 A" or "100 A" bidirectional current/power monitor module —
commonly stocked in India via Robu/Robokits under that description.

**Where it goes.** On the main pack discharge path, between the LiFePO4
terminals and the SSR-50DD, so it sees total system current (motors, Pi,
arm, UV lights all draw from the one 12.8 V bus per the power diagram in
`Master_Reference.md` §3.1). Same I²C bus as the LCD (0x27) and DS3231
(0x68) — INA226 defaults to 0x40 with address pins for up to 16 addresses,
so no conflict.

### 2.3 Software shape (not built yet — for the next session)

A small ROS 2 node publishing standard `sensor_msgs/BatteryState`
(percentage, voltage, current — an existing message type, not a custom
one), read over I²C the same way `lcd_display.py` already talks to its
own I²C peripheral. The dashboard subscribes to it the same way it now
subscribes to `/scan_reliable` for the live scan overlay — same pattern,
same WebSocket path, one more `type: 'battery'` payload and one more HUD
tile.

This publisher is also the trigger source for the 30% threshold in §3.

---

## 3. Autonomous charging docks

### 3.1 The honest framing first

Auto-docking is one of the harder subsystems in mobile robotics — precise
mechanical mating at the end of an imprecise navigation stack is a
well-known hard problem, not a shopping list problem. This section gives
a real path to it, but the fallback is worth stating up front: **get
battery percentage and a charging-status flag working first** (§2 — low
risk, immediately useful for reporting and for a manual "please plug me
in" alert), and treat autonomous docking as the next step after that,
not a prerequisite for it.

### 3.2 Physical contact — spring-loaded pogo-pin blocks

Standard approach across consumer and industrial docking robots (Roomba's
brass strips are the same idea at small scale). Spring-loaded pogo-pin
connector blocks tolerate a few millimetres of docking misalignment that
perfect pose-matching cannot guarantee.

**Current rating.** A sensible charge rate for a 30 Ah pack is roughly
0.2–0.5 C, i.e. 6–15 A. Rate the contacts at least 2× that — a
20–30 A-rated multi-pin pogo block. Two power pins (+/−) minimum; a third
sense/ID pin is worth adding if more than one dock location is planned,
so the robot can confirm which dock it mated with.

### 3.3 Fine alignment — IR docking beacon, camera/AprilTag as the alternative

SLAM/AMCL navigation gets the robot to *near* the dock — this project's
own measured pose accuracy (a few cm to ~10 cm depending on the drive) is
not tight enough to guarantee pogo pins land on their pads; a few
centimetres of miss means no contact or bent pins.

**Recommended: IR beacon docking**, the same principle iRobot popularized
— a beacon on the dock emits a directional IR field, and simple IR
receiver modules (TSOP38xx-class, the same chips used in remote controls)
on the robot report "aligned / drift left / drift right" during the final
approach. Cheap, well-proven, and needs no camera calibration.

**Alternative: a fixed front-facing camera reading an AprilTag/ArUco
marker at the dock.** Note this is a **different justification** from the
camera idea declined earlier in this project (§17.43's "no, `slam_toolbox`
has no camera input" — that was about feeding SLAM). A docking-only camera
never touches SLAM; it is a local visual servo for the last 20–30 cm, a
genuinely different use case with a genuinely different answer. Heavier
to integrate than IR beacons; consider it only if IR proves insufficiently
precise once tested.

### 3.4 The charger itself lives in the dock, not on the robot

A dedicated **LiFePO4-profile smart charger** (CC/CV to ~14.6 V for this
4-cell, 12.8 V-nominal pack — critically *not* a generic Li-ion charger
profile, which charges to a different voltage for a different chemistry)
sits in the stationary wall unit. The robot side stays simple: contacts
into the battery path, ideally through a controlled charge-enable
MOSFET rather than bare wire, so the robot does not blindly accept
whatever touches its terminals.

**Charging detection needs no new part** — see §2.2: the same INA226
already on the roadmap for battery % sees reversed current when the
charger is active, for free.

**One safety item to verify, not assume:** confirm the SM12830SL pack has
its own internal BMS (overcharge/overdischarge/overcurrent/short
protection). Branded LiFePO4 packs at this spec typically do, but this is
safety-relevant and belongs on the "verify before relying on it" list
rather than the "assumed" list.

### 3.5 Dock locations — software, not hardware

No new part needed. `Production_Architecture.md` §3.3 already designs a
named-location library for exactly this kind of thing ("Rack A3" etc.); a
charging dock is simply another entry with a `type: "charger"` field and
an approach-heading hint. This slots into infrastructure already designed,
not yet built.

---

## 4. What this document does not do

It does not add code. No ROS 2 node, launch file, or dashboard tile has
been written for any of §2 or §3 — those are next-session work, gated on
the parts actually being in hand, per this project's own rule that a
value in a doc is not a value on the robot. §1's collision ring similarly
needs the physical part count and placement settled against the real
chassis before `nav2_params.yaml` grows a `RangeSensorLayer` block.

## 5. Suggested order

1. INA226 — cheapest, fastest to integrate, unlocks battery % *and*
   settles the standing brownout hypothesis *and* is the free charge
   detector for §3. One part, three jobs.
2. Hardware E-stop — safety, not gated on anything else.
3. IMU — directly addresses a now-measured error (§17.55/§17.56), not a
   general hunch.
4. Collision ring — count and placement need the physical chassis in
   hand; start with a bench test of one VL53L5CX unit before committing
   to 8–12.
5. Optical flow — pending a ground-clearance measurement.
6. Charging dock — the largest single subsystem here; sequence last, and
   treat manual plug-in as an acceptable interim state rather than a
   reason to delay the demo.
