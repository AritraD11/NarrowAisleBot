# Session handoff, 5 Oct 2026

Read `CLAUDE.md` first, then this file. The earlier plan lives in
`docs/Session_Handoff_2026-10-01.md`; this one says what changed since.

Short version: three things landed on the Pi today (NAV2 button, a fixed 2.5 m
LiDAR cap, stock MPPI acceleration limits). A fourth, the switch of the whole
stack to standard REP-103 axes, is finished in the repo and has not been
deployed. Nothing about it has been tested on the robot yet.

## 1. What is on the Pi and verified

| What | Evidence |
|---|---|
| `phone_dashboard.py` with the NAV2 button (commit `192038f`), `scan_relay.py` with `range_cap_m` 2.5, `nav2_params.yaml` with MPPI accel 3.0 / -3.0 / 3.5 (commit `7472b5e`) | per-file hashes before and after, symlink-install, service restarted, odometry zeroed, new page served |
| MPPI accel change | live node read back 3.0 / -3.0 / 3.0 / -3.0 / 3.5. One goal of 0.6 m succeeded in 35 s on 2 Oct with these values, and the same goal crept at 4.4 mm/s and aborted with the old ones. One run each way, so it is a strong hint, not a measured mechanism. |
| NAV2 start and stop from the dashboard, E-STOP stopping Nav2 first | exercised in the 5 Oct run |

The step that was never reported back: opening the new dashboard in a real
browser with the console open (CLAUDE.md rule). Do it on the next deploy.

## 2. The 5 Oct run

Two goals in a cluttered spot, both ended without arriving. The log shows
progress-checker failures and optimizer failures in a tight space, and no sign
of an axis fault. The "ABORTED" labels on screen were the operator pressing
stop: Nav2 reports a dropped goal as ABORTED. The dashboard now says STOPPED
for that case and keeps ABORTED for a real abort.

Still open from that run, in the order I would look at them:

1. The 4.4 mm/s crawl may come back. If it does, the first thing to read is
   the MPPI loop rate (measured 5.5 to 14 Hz against 20 Hz requested, while
   `model_dt` assumes 20 Hz).
2. The footprint is 1.12 x 0.48 m. A cluttered room can put it in collision
   at the start, which looks like "no progress".
3. The new 2.5 m cap shortens what the planner sees. One command compares:
   `ros2 param set /scan_relay range_cap_m 0.0` and back to `2.5`.

The MP4 was never analysed (the video could not be opened in that session).

## 3. The axis refactor: what is done

Everything below is in the repo on branch `claude/compassionate-turing-djz98e`
and passes `python3 tools/verify_axis_chain.py` and every test in
`tools/tests/`. The audit and the order of work are in
`docs/Axis_Refactor_Plan.md`; the new reference is `docs/Axis_Convention.md`.

The target: `+X` nose, `+Y` left, yaw counter-clockwise from `+X`, for
`base_link`, `odom` and `map`. The dashboard map is spun by `-π/2` so the nose
still points up the screen. Old to new: `x_new = y_old`, `y_new = -x_old`,
yaw numerically unchanged.

Changed:

| File | What |
|---|---|
| `odometry_publisher.py` | publishes the internal frame as is (no -90 rotation) |
| `scan_relay.py` | `yaw_offset_deg` 270 to 180, mask 135 to -135 (wraps through 180, 91 beams at 1 degree). The mirror stays. |
| `aislebot.urdf` | chassis, cushion, wheels (spin axis Y), laser `(0.27, 0, 0.275)`, inertia |
| `nav2_params.yaml` | both footprints `[[0.56, 0.24], [0.56, -0.24], [-0.56, -0.24], [-0.56, 0.24]]`, comments |
| `cmd_vel_axis_adapter.py` | identity pass-through (deleted at stage 6) |
| `phone_dashboard.py` | `DISPLAY_ROT = -π/2`, `vecToYaw`/`yawToVec` plain, footprint and laser constants, STOPPED status, rear-wedge mask counted by bearing, old-frame `locations.json` ignored |
| `nav_goal.py`, `zero_point_scan.py`, `repeatability_test.py`, `trajectory_viz.py` | `body_to_map` in the standard form |
| `sensor_coverage.py` | converted, output numbers identical to before (diffed) |
| `wheel_forensics.py` | integrates in the standard frame, `--legacy-frame` for runs before 5 Oct |
| docs | `Axis_Convention.md` rewritten, `Firmware_Inventory.md`, superseded notes on the dated ones |

Not changed on purpose: wheel kinematics, `sendDrive()`, `twist_mux`, ESP32
firmware, the LiDAR mirror (a reflection of the sensor, not an axis choice).

Two extra things the refactor turned up:

- `~/locations.json` holds old-frame coordinates. A GOTO from it would drive to
  a point rotated 90 degrees from the taught one. The dashboard now treats a
  file without `"frame": "rep103"` as empty and copies it to
  `locations.json.pre_rep103` the first time a new location is saved.
- The HUD's "masked (rear wedge)" count included every NaN beam. With the 2.5 m
  cap that read as hundreds of beams. It now counts only the arc, so the VALID
  percentage honestly includes beams that returned nothing within the cap.

## 4. What is NOT proven

This is arithmetic and browser tests, not a drive. The gate cannot tell
whether a wheel really turns the way the sign says. The stages below are where
that gets answered. Also unproven: the headless Chromium render and the
screenshot looked right (nose up, X rows up, Y labels leftward, a left wall
drawn on the left), but the real phone browser has not seen it.

## 5. Next steps, in order

Write the prediction before each one. Hash every file before and after. One
step at a time.

**Before touching anything:** the plan wanted a clean 0.6 m regression goal in
the OLD convention as a baseline, about five repeats with a bag and tape
measurements. Today's runs in a cluttered spot do not count. Without it, a
failure after the switch cannot be blamed on the switch or cleared of it.
Cheapest version: three 0.6 m goals in a clear spot, in the old frame, before
stage 2.

**Stage 2, bench, Nav2 off.** Deploy together, all or none: `odometry_publisher.py`,
`aislebot.urdf`, `scan_relay.py`, `sensors.launch.py`, `nav2_slam.launch.py`,
`navigation.launch.py`. Restart the service, then MAP fresh (the old map frame
cannot be reused). Gate: `tf2_echo odom base_link` reads 0,0,0 at the mark; W
raises x, D lowers y; a block in front shows at bearing 0 in `/scan_reliable`,
a block on the right at -90, on the left at +90.

**Stage 3, dashboard.** `phone_dashboard.py` to the Pi, then
`python3 tools/tests/dashboard_html_syntax.py` first, then open it in a real
browser with the console open. Gate: nose up, a tapped goal lands under the
finger, W moves the robot up the screen, no console errors.

**Stage 4, Nav2.** Deploy `nav2_params.yaml` and `cmd_vel_axis_adapter.py`.
Read the live footprint with `ros2 topic echo --once /local_costmap/published_footprint`
(expect x ±0.56, y ±0.24 plus padding). First drive is 0.3 m forward, hand on
the E-STOP, then the 0.6 m regression goal, then 0.3 m sideways, then a 90
degree turn.

**Stage 5, reverse.** Decision needed from the operator: BackUp is a real 0.30
m reverse into the rear blind wedge after this change (it was a left strafe
before). Leave it, remove it from the behaviour tree, or accept it.

**Stage 6.** Delete `cmd_vel_axis_adapter` from both launch files and
`setup.py`, repeat the stage 4 drives, update the docs.

If any gate fails, stop at that stage. Rollback is the previous hashes from the
backup copies made at deploy time.

## 6. Open items that are independent of the axes

- NavFn `tolerance: 0.5` lets a blocked goal "succeed" up to 0.5 m short.
- Spin recovery is dangerous in a 0.6 to 1.1 m aisle. Remove or limit it
  before any aisle test.
- `velocity_smoother` still caps accel at 0.3 while MPPI plans at 3.0, and the
  progress checker needs 0.10 m in 10 s (about 10 mm/s), close to the final
  approach speed.
- `install.sh` still copies `system/slam_nodom.yaml` (scan matching ON). A
  reinstall would switch it back on. Check the live node.
- Range consumers (slam `max_laser_range` 5.0, costmaps 8 and 9, dashboard
  `scan_trust_range` 5.0) still disagree with the 2.5 m cap. Harmless, because
  the relay cuts first. Clean up after a 60 s parked capture of the 2.0 to 2.5 m
  band, which was never measured.
- Live check list for MPPI and the relay: `docs/MPPI_LiDAR_Audit_2026-10-05.md`
  section 4.
- The journal has no entry for this yet; the handoff and `Axis_Convention.md`
  are the record until it does.
