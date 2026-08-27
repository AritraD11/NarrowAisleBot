# Axis Convention — the one authoritative reference

**The rule, locked down 26 Aug 2026 (Research_Journal.md §17.36 and the
session that follows it): physical AisleBot convention is authoritative.**

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
calibration. Every robot-facing frame and every user-facing coordinate is
coherent with it. Do not re-derive this from first principles, re-litigate
it, or accept a fix from anywhere (including another AI tool's independent
analysis) that quietly assumes REP-103 instead — read this file first.

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

There are exactly **three** such conversion points in the entire stack, no
more. Each is justified by an actual physical or mathematical constraint,
each is a single isolated node/function, and each was built in direct
response to a real, documented hardware incident — not accumulated
speculatively. If a fourth one ever seems necessary, that is a signal to
re-read this file before writing it, not a sign the pattern is running out.

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
| 5 | Odometry integration + publish | `odometry_publisher.py:183-268` | internal REP-103 → **published** TF/pose rotated `-90°` (`pub_theta = theta - π/2`, line 221), translation unchanged | re-derived algebraically: for a physical point to land at the same real position in `odom` computed either way, the published rotation must equal `theta_internal - 90°` exactly, which is what the code does. Twist (`pub_vx=-vy, pub_vy=vx`) checked the same way. |
| 6 | `odom→base_link`, `map→odom`, `map→base_link` | TF, composed automatically | inherits hop 5's already-correct convention | no separate conversion exists or is needed |
| 7 | Nav2 → `/cmd_vel_baselink` | `nav2_params.yaml` (MPPI `vx_max`/`vy_max`, `collision_monitor` polygon) | TF axes (`+X=right,+Y=forward`) throughout — Nav2 reads TF natively | comments explicit at lines ~284, ~286, ~695-696; footprint matches URDF chassis exactly |
| 8 | **Conversion point 1**: Nav2 → teleop | `cmd_vel_axis_adapter.py:129-138` | TF axes in → REP-103 out (`out.x=in.y, out.y=-in.x`) | built in response to a real incident: first autonomous goal travelled 0.956 m at 88.4° off-heading before E-STOP (§17.19) |
| 9 | **Conversion point 2**: goal orientation | `goal_pose_adapter.py:98-110` | TF-axes dragged yaw → REP-103-consistent `base_link` target (`published_yaw = dragged_yaw - 90°`) | opt-in on a separate topic (`/goal_pose_click`) specifically so it can never silently double-apply; dashboard's own GOAL button routes through this same node rather than re-implementing it (`phone_dashboard.py:1639-1641`) |
| 10 | **Conversion point 3**: LiDAR mirror | `scan_relay.py:15-49` | raw sensor bearing → TF/base_link-axes bearing, via `reported = 270° - true` | this is a **reflection**, not a rotation — confirmed by three measured bearings solving `reported + true = const`, not `reported - true = const`. A TF cannot express a reflection (rigid motions only), so this has to live in software, and does, in exactly one place. |
| 11 | Dashboard display | `phone_dashboard.py` `updateHud()` etc. | reads TF (hop 6, already correct) → relabels only the printed number, `dispX=-raw_y, dispY=raw_x`, so it reads as ordinary graph paper (right=+X, forward=+Y) | display-only; goals, camera-follow and the pose CSV all still use the raw TF value untouched — see §17.36 |

## Quick self-check

Parked at the ZERO mark (frame yaw `-90°`), from the dashboard:

| Key | Physical motion | `base_link` twist | Map-frame TF (raw) | Dashboard display (relabeled) |
|---|---|---|---|---|
| `W` | forward | `vy=+` (REP-103 in) | `x` increases | `y` increases |
| `D` | strafe right | `vx=+` (REP-103 in) | `y` decreases | `x` increases |
| `A` | strafe left | `vx=-` | `y` increases | `x` decreases |
| `S` | reverse | `vy=-` | `x` decreases | `y` decreases |

`Q`/`E` are yaw (rotate CCW/CW in place), not strafe — a common mix-up when
testing this table by hand (§17.36).

## What this file does NOT cover

This is the axis/frame convention only. It says nothing about mapping
quality, loop-closure reliability, or whether a given saved map is trustworthy
— see `Dashboard_Map_System.md` and `tools/map_integrity.py` for that. The
frame convention and the map's geometric integrity are independent
questions; do not let confidence in one stand in for the other.
