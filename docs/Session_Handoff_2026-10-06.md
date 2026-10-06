# Session handoff, 6 Oct 2026

Read this first, then `Session_Handoff_2026-10-05.md` and `Axis_Refactor_Plan.md`.
Branch `claude/compassionate-turing-djz98e`, draft PR #28, last commit `99c4d55`.

## Where the axis refactor stands

The repo is finished: whole stack in REP-103 (+X nose, +Y left, yaw CCW), dashboard
map still nose-up through `DISPLAY_ROT = -pi/2`. The Pi is half switched, on purpose,
in stages. Do not treat it as done.

Deployed and hash-verified on the Pi (stage 2 and 3):

| file | sha256 (start) |
|---|---|
| odometry_publisher.py | 20d3e26c |
| aislebot.urdf | 9ced10d0 |
| scan_relay.py | f6c529ce |
| sensors.launch.py | 66b14a59 |
| nav2_slam.launch.py | fe70a625 |
| navigation.launch.py | 631c01ec |
| phone_dashboard.py | 6b482926...bb5394 (192010 bytes, the wide-screen fix) |

Staged on the Pi in `~/stage3_dl`, NOT deployed (stage 4):
`nav2_params.yaml` 1882c9dd, `cmd_vel_axis_adapter.py` e7ad1c7a (identity now),
`goal_pose_adapter.py` c1fca1ee, `tools/nav_goal.py` b2229641 (new frame).
Old-frame tool kept as `~/nav_goal_oldframe.py` (e98201c8...d32e).
Backups in `~/axis_backup_20261006`: the old six files, `phone_dashboard.py.old`
(89511c70, pre-refactor) and `phone_dashboard.py.stripes` (028ef1f7, first new dashboard).

Python modules run from `~/ros2_ws/build/mecanum_robot/mecanum_robot/` (copy to src AND
build, hash both). Launch files and URDF are linked from install to src.
`scan_relay.py` runs from `~/ros2_ws/src/scan_relay/`.

## Verified on hardware or on the live node this session

- W moves +x: 0.05 m/s for 5 s gave x +0.251, y 0.000, yaw about 0.
- Strafe signs: right makes y fall (about -0.23), left makes y rise (about +0.21).
- `/wheel_odom` (there is no `/odom` topic) runs at 19.998 Hz, interval 48 to 52 ms.
- New dashboard: grid fills the screen, X+ up, Y+ left, pose box 0, 0, 0.0 degrees.
  Running service serves the fixed page. Browser console clean, only `favicon.ico` 404.
  Journal since restart: no errors. 17 nodes with MAP running (11 without).
- Not yet verified: scan bearings (block front, right, left, read the bearing in
  `/scan_reliable`; expect 0, -90, +90 degrees). Needs MAP running.

## The live hazard

Nav2 is running with the OLD nav2_params (footprint) and the OLD swapping
cmd_vel_axis_adapter and goal_pose_adapter against NEW-frame odometry. Sending it a goal
mixes frames, so the robot can turn or drive sideways. A screenshot at the end of the
session showed the robot off the mark (X 0.147, Y -0.619, nose -127) with a cancelled
goal; the cause was not confirmed and the operator had not yet said what the robot did.

Until stage 4 is deployed: no Nav2 goals. Joystick and ZERO are fine.

Also: the CALIBRATE button starts `zero_point_scanner`, which rotates the robot and
nudges it. Never press it as a UI test. STOP CAL returns gracefully, E-STOP stops now.
The robot was running a calibration at the last screenshot; check the operator stopped it.

## Next steps, in order

1. Ask the operator what the robot physically did, confirm it is stopped and safe,
   put the nose on the zero mark, restart `aislebot.service` (the restart zeroes the pose).
2. Scan bearing check (above).
3. Stage 4: deploy the four staged files with per-file hashes before and after. Check the
   live footprint with `ros2 topic echo --once /local_costmap/published_footprint`
   (expect +-0.56 along x, +-0.24 along y). Then drives, prediction written first:
   0.3 m forward, then the 0.6 m regression goal, then 0.3 m sideways, then a 90 degree turn.
4. Stage 5: operator decision on BackUp (real reverse into the rear blind wedge: keep,
   remove from the tree, or accept). Reversing and holonomic motion must never be
   reduced to forward-only.
5. Stage 6: delete the adapter, update docs, add the Research_Journal entry (none yet).

## Regression drive, 0.6 m forward goal from the zero mark

Old frame baseline, three runs, deterministic: rightward bulge of 10 to 11 cm
(old +x is right), peak at y about 0.41 to 0.42, ends near (0.044, 0.579), about 21 s,
0 recoveries. Written prediction for the same drive after the switch: ends near
(x 0.579, y -0.044), peak y about -0.10 near x 0.42, about 21 s, 0 recoveries.
If the bulge does not follow the frame change, the cause is not the frame.

## Open items (not for this stage)

- Crawl: mean forward speed about 0.025 m/s against the 0.12 cap, unexplained.
- Bulge hypothesis: NavFn's own plan bends away from left-side obstacles. Test by
  capturing `/plan`.
- NavFn tolerance 0.5; Spin recovery in narrow aisles; velocity_smoother accel 0.3
  against MPPI 3.0; `install.sh` copies a scan-matching-on SLAM yaml; range consumers
  still at 5.0 / 8 / 9 m against the 2.5 m cap (clean up after a 60 s parked capture).
- Small blue square near x 0.5 m on the old dashboard; check whether it is still there.

## Operator workflow and the PC download problem

Files go GitHub, PC (`C:\Users\aritradas\Documents\NAB\for scp download`), `scp` to
`aritra@10.42.0.1`. The PC's `curl.exe` and `Invoke-WebRequest` failed against GitHub
from the IITB Ethernet path. Diagnosed 6 Oct: the TLS handshake completes, then
Windows' TLS library (Schannel) treats a TLS 1.3 follow-up message as a renegotiation
and drops the connection. Fix: `curl.exe -fSL --tls-max 1.2 -o <file> <url>`.
Tested, hash matched. Defender is not involved. Browser Ctrl+S saves were unreliable.
Dashboard: `http://10.42.0.1:8080`. Service: `aislebot.service`.
