# Axis Convention — the one authoritative reference

**The rule, locked down 26 Aug 2026 (Research_Journal.md §17.36–§17.37) and
EXTENDED TO EVERY FRAME 27 Aug 2026 (§17.38): physical AisleBot convention
is authoritative.**

> **What changed on 27 Aug, and why this file's tables moved.** The rule
> below never changed and is not up for discussion. What changed is its
> *reach*. Until 27 Aug it held for `base_link` only: `odom` and `map`
> silently used REP-103's axes instead, because `odometry_publisher.py`
> rotated its published orientation and twist but **not** its published
> translation. Driving forward really did increase map `X`. A chain of
> −90° compensations downstream (dashboard canvas rotation, dashboard
> print-site relabel, `goal_pose_adapter` yaw offset, `ZERO_POINT_YAW`)
> each undid it for one consumer, which is why it read as correct
> anywhere anyone looked closely.
>
> §17.38 rotated the published translation too. `odom`, `map` and
> `base_link` now share one convention, the −90° is gone from TF, and
> every one of those compensations was deleted in the same commit.
> **`tools/verify_axis_chain.py` now proves this and fails if it is
> edited back out** — run it before trusting any table here.

```
                base_link
             +Y  FORWARD / NOSE
                    ↑
                    |
    -X  ←───────────0───────────→  +X
    LEFT                          RIGHT
                    |
                    ↓
             -Y  REAR
```

`+X = RIGHT`, `+Y = FORWARD/NOSE`, `+Z = UP`. This is **not** REP-103 (which
puts forward on `+X`) and that is deliberate — confirmed on hardware
(§17.10–§17.12) and matching the LiDAR's independently-validated scan
calibration. Do not re-derive this from first principles, re-litigate
it, or accept a fix from anywhere (including another AI tool's independent
analysis) that quietly assumes REP-103 instead — read this file first.

**Since §17.38 this holds for `base_link`, `odom` AND `map` alike.** The
three frames' axes are parallel; a freshly-zeroed robot on the ZERO mark
reads `[0, 0, 0] @ 0°`, not `@ -90°`. So the operator-facing rule is simply:

```
W / forward  → map +Y        D / right → map +X
S / reverse  → map -Y        A / left  → map -X
```

The only frame in the stack that still speaks REP-103 is the **wheel
kinematics** (`mecanum_teleop_asymmetric.py` and odometry's *internal*
integration), and exactly one node bridges to it — see conversion point 1
below. That is by design and is not a leftover.

If a `phone_dashboard.py`-shaped file, or any other axis-touching code,
shows up from outside this repo: **diff it against the repo copy before
trusting it.** Three independently-forked copies of the dashboard silently
disagreed with each other on exactly this (§17.36) — a Python class matching
byte-for-byte is not enough on its own, the JS/HTML is where forks drift.

## Why the wheel controller doesn't just also use +Y=forward

`mecanum_teleop_asymmetric.py` and the odometry integration math are older
than the `base_link` convention above and speak plain REP-103 internally
(`linear.x = forward, linear.y = left`). Rewriting them was rejected: both
conventions have independent hardware validation (the LiDAR/TF side via the
mirror calibration, footprint, and safety cushion; the teleop side via every
metre the robot has ever driven under manual control). §17.10's rule: when
two independently-validated conventions meet, convert explicitly and
isolate the conversion to one place — never silently touch the
already-validated side.

There are exactly **two** such conversion points left in the entire stack
(three until §17.38 retired the goal-orientation one by removing the frame
mismatch it corrected). Each is justified by an actual physical or
mathematical constraint, each is a single isolated node/function, and each
was built in direct response to a real, documented hardware incident — not
accumulated speculatively.

**If a new one ever seems necessary, that is the signal to re-read this
file, not to write it.** §17.38's lesson is exactly this: a genuine frame
fault upstream produced four separate downstream "fixes", each locally
reasonable, which together made the fault invisible for two weeks. Adding a
compensation is how you hide a bug; removing the mismatch is how you fix
one. Run `tools/verify_axis_chain.py` before and after any such change.

## The verified pipeline

Traced hop-by-hop against source on 26 Aug 2026 (not assumed, not taken from
any external tool's description) — file:line citations are exact as of that
date; re-check them if this file is old.

| # | Hop | File | Convention in / out | Verified |
|---|---|---|---|---|
| 1 | `base_link` geometry | `src/mecanum_robot/urdf/aislebot.urdf:6-27` | defines `+X=right,+Y=forward` | tape-measured, §17.12 |
| 2 | Dashboard/joystick drive → `/cmd_vel_manual` | `phone_dashboard.py` `sendDrive()` | REP-103 in, REP-103 out (no conversion) | matches teleop below |
| 3 | `twist_mux` → `/cmd_vel` | `config/twist_mux.yaml` | REP-103 in both inputs, REP-103 out — pure priority arbiter, **no axis math** | wiring read directly |
| 4 | Wheel kinematics | `mecanum_teleop_asymmetric.py:75-89` | REP-103 (`vx=forward,vy=left`) | inverse-kinematics formula is the algebraic inverse of odometry's internal forward kinematics (checked term-by-term) |
| 5 | Odometry integration + publish | `odometry_publisher.py:246-259` | internal REP-103 → **published** frame rotated `-90°` in **all three** quantities: translation (`pub_x=-self.y, pub_y=self.x`), orientation (`pub_theta = self.theta`, no constant), twist (`pub_vx=-vy, pub_vy=vx`) | `tools/verify_axis_chain.py`, which parses these three expressions out of the module and runs them. **This is the hop §17.38 fixed** — translation used to be published unrotated, which gave `odom` REP-103's axes and left a constant −90° seam. |
| 6 | `odom→base_link`, `map→odom`, `map→base_link` | TF, composed automatically | inherits hop 5's convention; all three frames now parallel | no separate conversion exists or is needed. A freshly-zeroed robot on the mark reads `[0,0,0] @ 0°` — verify with `ros2 run tf2_ros tf2_echo odom base_link` |
| 7 | Nav2 → `/cmd_vel_baselink` | `nav2_params.yaml` (MPPI `vx_max`/`vy_max`, `collision_monitor` polygon) | TF axes (`+X=right,+Y=forward`) throughout — Nav2 reads TF natively | comments explicit at lines ~284, ~286, ~695-696; footprint matches URDF chassis exactly |
| 8 | **Conversion point 1**: Nav2 → teleop | `cmd_vel_axis_adapter.py:129-138` | TF axes in → REP-103 out (`out.x=in.y, out.y=-in.x`) | built in response to a real incident: first autonomous goal travelled 0.956 m at 88.4° off-heading before E-STOP (§17.19) |
| 9 | ~~Conversion point 2~~: goal orientation — **RETIRED §17.38** | `goal_pose_adapter.py` | `yaw_offset_deg` now defaults to `0.0`; a dragged yaw already means "point the nose this way" | the −90° it applied was correcting hop 5's seam. With `map` and `base_link` sharing a convention there is nothing to correct. The node is kept as a parameterised pass-through so a future convention change is a launch argument, not a re-plumb — do not re-add a constant |
| 10 | **Conversion point 2**: LiDAR mirror | `scan_relay.py:15-49` | raw sensor bearing → TF/base_link-axes bearing, via `reported = 270° - true` | this is a **reflection**, not a rotation — confirmed by three measured bearings solving `reported + true = const`, not `reported - true = const`. A TF cannot express a reflection (rigid motions only), so this has to live in software, and does, in exactly one place. **Unaffected by §17.38**: it is calibrated in `base_link`, which did not move. |
| 11 | Dashboard display | `phone_dashboard.py` `updateHud()` etc. | reads TF (hop 6) → **prints it verbatim**. No relabel, `DISPLAY_ROT = 0` | since map axes *are* graph-paper axes now, the raw numbers already read correctly and a relabel would double-apply. The old `dispX=-raw_y, dispY=raw_x` and the canvas rotation were both deleted in §17.38. **Never re-add a display-side axis fix** — if the printed X/Y looks wrong, the frame is wrong upstream |

## Quick self-check

Parked at the ZERO mark (frame yaw **`0°`** since §17.38 — it was `-90°`
before), from the dashboard. **Map-frame TF and the dashboard display are
now the same numbers**, which is the whole point of the fix:

| Key | Physical motion | Twist on the wire (REP-103) | Map-frame TF = dashboard |
|---|---|---|---|
| `W` | forward | `vx=+` | **`y` increases** |
| `S` | reverse | `vx=-` | **`y` decreases** |
| `D` | strafe right | `vy=-` | **`x` increases** |
| `A` | strafe left | `vy=+` | **`x` decreases** |

`Q`/`E` are yaw (rotate CCW/CW in place), not strafe — a common mix-up when
testing this table by hand (§17.36).

Two ways to check it without driving anywhere:

```bash
python3 tools/verify_axis_chain.py            # the whole chain, as arithmetic
ros2 run tf2_ros tf2_echo odom base_link      # on the mark: [0,0,0] @ 0 deg
```

If `tf2_echo` says `-90°`, the robot is running a pre-§17.38
`odometry_publisher.py` — rebuild and restart before mapping, because any
map recorded that way is in the old frame.

## Maps recorded before 27 Aug 2026 are in the old frame

A saved `.pgm`/`.yaml` freezes the axes it was drawn in. Every map in
`~/slam_tests` and `data/field_runs`, including `run_20260825_151713` and
`run_20260825_113735`, was recorded when map `+X` was the start heading.
They remain **geometrically** valid — `tools/map_integrity.py`'s verdicts
still stand, since it measures wall thickness and parallelism, not axis
labels — but they are not in this convention, so re-map before relying on
"forward = +Y" against a remembered map.

## What this file does NOT cover

This is the axis/frame convention only. It says nothing about mapping
quality, loop-closure reliability, or whether a given saved map is trustworthy
— see `Dashboard_Map_System.md` and `tools/map_integrity.py` for that. The
frame convention and the map's geometric integrity are independent
questions; do not let confidence in one stand in for the other.
