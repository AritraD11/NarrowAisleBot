# Axis Convention, the one authoritative reference

**Standard REP-103 everywhere, since 5 Oct 2026.** `base_link`, `odom` and
`map` all use the same axes, and so does every velocity command on the wire.

```
                base_link (seen from above)
             +X  FORWARD / NOSE
                    ↑
                    |
    +Y  ←───────────0───────────→  -Y
    LEFT                          RIGHT
                    |
                    ↓
             -X  REAR
```

`+X = forward (the nose)`, `+Y = left`, `+Z = up`. Yaw is the angle of the
nose from `+X`, counter-clockwise positive. A freshly zeroed robot on the
ZERO mark reads `[0, 0, 0] @ 0°`, and turning left (Q) increases yaw.

Operator rule, from the mark:

```
W / forward  → map +X        A / left   → map +Y
S / reverse  → map -X        D / right  → map -Y
```

`tools/verify_axis_chain.py` proves this as arithmetic, parsing the real
expressions out of the real files. Run it before trusting any table here and
before committing anything that touches an axis.

## Why this changed (and why it was the right call)

Until 5 Oct 2026 the robot ran a private convention: `+X` right, `+Y` forward,
chosen in Aug 2026 to match the LiDAR's labelling (Research_Journal §17.9,
§17.10) and made global in §17.38. It worked, and it cost real work every
time something assumed the textbook. Nav2 has no parameter for "which axis is
the nose", so BackUp, MPPI's PathAngle and PreferForward critics,
`velocity_smoother`, `collision_monitor`, GoalAlign and PathAlign were each
wrong by default and each had to be caught by reading its source (§17.14,
§17.17, §17.19, §17.23, and BackUp in the 30 Sep source read). Reversing,
holonomic and omnidirectional motion are this project's research contribution,
and under the old frame the stock "reverse" and "strafe" behaviours were
silently swapped.

The old convention's only real argument was that the LiDAR labelling matched.
That is a property of one sensor, and it belongs in the one node that handles
that sensor (`scan_relay`), not in every frame in the stack.

The full audit and the order of work are in `docs/Axis_Refactor_Plan.md`.

## The verified pipeline

| # | Hop | File | Convention |
|---|---|---|---|
| 1 | `base_link` geometry | `src/mecanum_robot/urdf/aislebot.urdf` | chassis 1.0 long on X by 0.36 wide on Y, cushion 1.12 x 0.48, wheels at `(±l, ±d)` with Y spin axes, laser at `(0.27, 0, 0.275)` |
| 2 | Dashboard joystick → `/cmd_vel_manual` | `phone_dashboard.py` `sendDrive()` | `vx = joyY`, `vy = -joyX`. This was already standard and did not change. |
| 3 | `twist_mux` → `/cmd_vel` | `config/twist_mux.yaml` | pure priority arbiter, no axis math |
| 4 | Wheel kinematics | `mecanum_teleop_asymmetric.py` | `vx` forward, `vy` left. Unchanged. |
| 5 | Odometry integration and publish | `odometry_publisher.py` | internal REP-103 and **published as-is**: `pub_x = self.x`, `pub_y = self.y`, `pub_theta = self.theta`, `pub_vx = vx`, `pub_vy = vy`. No rotation anywhere. |
| 6 | `odom→base_link`, `map→odom`, `map→base_link` | TF | parallel frames, nothing to convert |
| 7 | Nav2 → `/cmd_vel_baselink` | `nav2_params.yaml` | stock axes: footprint `[[0.56, 0.24], [0.56, -0.24], [-0.56, -0.24], [-0.56, 0.24]]` in both costmaps, MPPI `vx` = forward/reverse and `vy` = strafe, `velocity_smoother` arrays are `[forward, strafe, yaw]` |
| 8 | `cmd_vel_axis_adapter` | `cmd_vel_axis_adapter.py` | **identity** (`out.x = in.x`, `out.y = in.y`). Kept for one more stage so the topic wiring does not change in the same step as the axes, then deleted (Axis_Refactor_Plan stage 6). |
| 9 | Goal orientation | `goal_pose_adapter.py` | `yaw_offset_deg = 0.0`. A dragged yaw means "point the nose this way". |
| 10 | **The one real conversion**: LiDAR mirror | `scan_relay.py` | a reflection (`true = 180° - reported`), `yaw_offset_deg = 180`, mirror on. A TF cannot express a reflection, so it lives in software, in exactly this one place. Rear mask `135°` to `-135°` (90 wide, wraps through 180). |
| 11 | Dashboard display | `phone_dashboard.py` | prints TF verbatim. `DISPLAY_ROT = -π/2` is the only presentation choice: see below. |

The one thing that is still not "default" is the LiDAR itself: it is a
mirrored sensor, and `scan_relay` un-mirrors it. That is a fact about the
hardware, not an axis choice.

## The dashboard map still has the nose pointing up

The operator reads the map with the robot's nose up the screen, and that did
not change. The canvas is spun by `DISPLAY_ROT = -Math.PI / 2`, so world `+X`
draws screen-up and world `+Y` draws screen-left. Nothing printed is relabelled;
the X, Y and NOSE numbers are the real map frame, and every pointer is
un-rotated before it becomes a world coordinate. `tools/tests/
dashboard_goal_roundtrip.py` pins the expected answers in the standard frame
independent of `DISPLAY_ROT`, so a wrong rotation fails the test rather than
agreeing with itself.

If the printed X/Y ever looks wrong, the frame is wrong upstream. Do not add
a display-side fix.

## Quick self-check

Parked at the ZERO mark, from the dashboard:

| Key | Physical motion | Twist on the wire | Map-frame TF and dashboard |
|---|---|---|---|
| `W` | forward | `vx = +` | **`x` increases** |
| `S` | reverse | `vx = -` | **`x` decreases** |
| `D` | strafe right | `vy = -` | **`y` decreases** |
| `A` | strafe left | `vy = +` | **`y` increases** |

`Q` and `E` are yaw (rotate CCW and CW in place), not strafe, a common mix-up
when testing this table by hand (§17.36).

```bash
python3 tools/verify_axis_chain.py            # the whole chain, as arithmetic
ros2 run tf2_ros tf2_echo odom base_link      # on the mark: [0,0,0] @ 0 deg
```

If `tf2_echo` says `-90°` or the dashboard shows the robot sideways, a node is
still running the pre-5-Oct code. Rebuild, restart, and map again.

## Data from before 5 Oct 2026 is in the old frame

Saved maps, `~/locations.json`, pose CSVs, bags and recorded goals made before
5 Oct 2026 use `+X` right, `+Y` forward. They stay geometrically valid (wall
thickness, parallelism, loop closure do not care about axis labels), but their
numbers convert as

```
x_new =  y_old
y_new = -x_old
yaw_new = yaw_old        (numerically unchanged: 0 on the mark in both)
```

A saved map's occupancy grid is rotated by 90° clockwise to become the new
frame. Do not load an old map with the new stack as if it were current.
`tools/wheel_forensics.py --legacy-frame` compares an old run's wheel
integration against the old frame's CSV columns.

## What this file does not cover

The axis and frame convention only. Mapping quality, loop closure and map
trust are in `Dashboard_Map_System.md` and `tools/map_integrity.py`.
