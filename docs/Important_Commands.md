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

**3D panel frame settings, for diagnosing motion/drift bugs specifically**
(confirmed working 11 Aug 2026, Research_Journal.md §17.11): set both
**Fixed frame** and **Display frame** to `base_link`, not the `map` default.
This holds the robot stationary at screen-center, so any accumulated map
drift becomes directly visible as map *motion* while driving — this exact
setting is what originally exposed the §17.10 sideways-drift symptom, and
what was used afterward to confirm the fix (map now slides away behind the
robot on forward drive, not sideways). Switch back to `map` for normal
"where is the robot in the world" viewing once you're not debugging motion.

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

---

## 8. Setting the zero point (re-zeroing on the floor mark)

**This is the procedure that makes map `(0,0)` mean the physical floor mark.**
Do it whenever the mark is moved, re-taped, or you want a fresh base map.

### Why it works — the part that is not obvious

Pressing **Map** does *not* set the zero point. `slam_toolbox` sets its
`map -> odom` link to *identity* at a mapping session's first scan — it does
**not** put the map origin under the robot. So map `(0,0)` lands on whatever
odometry's origin is, and odometry's origin is set **only when
`odometry_publisher` starts**, i.e. when `aislebot.service` last started.

Two sessions (§17.17–§17.19) were spent assuming otherwise. If the drive
stack started at 10:42 and you press Map at 10:56, map `(0,0)` is the
10:42 parking spot, not the mark.

### The procedure

```bash
# 1. Park the robot physically ON the floor mark.
# 2. Stop the mapping session (dashboard Map button) — do this BEFORE the
#    restart, so slam_toolbox isn't running while its TF parent vanishes.
# 3. Re-zero odometry at the mark:
sudo systemctl restart aislebot.service

# 4. Wait ~10 s, then verify. MUST read [0,0,0] and -90.000 degrees:
ros2 run tf2_ros tf2_echo odom base_link

# 5. Press Map to start a fresh mapping session.
# 6. Verify the map inherited it — also [0,0,0] @ -90 deg:
ros2 run tf2_ros tf2_echo map base_link
```

The `-90.000` is **correct, not an error**. `base_link` on this robot has
`+X` = right and `+Y` = nose (§17.10), so a perfectly-placed robot reads
−90° against the map grid. It will never read 0.

### Checking whether you are back home

The floor mark is underneath the chassis, so you cannot see it while
standing on it. Two ways that don't need eyes on the floor:

```bash
# Numeric: home is [0,0,0] @ -90 deg, same as step 6 above.
ros2 run tf2_ros tf2_echo map base_link
```

**Visual (Foxglove):** `mapping_full.launch.py` publishes a permanent
`zero_point` frame at the map origin, carrying the same −90° twist
`base_link` has. Enable both frames in the 3D panel's **Transforms** list.
When the two axis triads sit exactly on top of each other, you are home.
The marker is fixed to the map, so it stays put while you drive.

### Driving home automatically

Once the zero point is real, "return to zero" is a *constant* command — it
no longer has to be computed per-run the way `nav_goal.py` does. Requires
Nav2 running:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 0.0, y: 0.0, z: 0.0}, \
   orientation: {x: 0.0, y: 0.0, z: -0.7071068, w: 0.7071068}}}}"
```

The `z: -0.7071068, w: 0.7071068` quaternion is just −90° yaw written the
way ROS wants it — the same rotation `tf2_echo` prints as `[0, 0, -0.707,
0.707]`.

---

## 9. Autonomous base-map scan (the CALIBRATE button)

**Order of operations: MAP → launch Nav2 → CALIBRATE.**

```bash
# Nav2 must be up before CALIBRATE will do anything.
ros2 launch mecanum_navigation nav2_slam.launch.py
```

Then on the dashboard: **CALIBRATE** → **TAP AGAIN** to confirm.

It runs `tools/zero_point_scan.py`: at each of four 90° headings it checks
whether `/map` actually grew, nudges ≤ 0.15 m *only if it didn't*, and
returns to the exact start pose as its final action.

**Why 90° steps, i.e. four headings.** Not a round number — the rear
self-occlusion mask is a *measured* 90° wedge (§17.15), and a 360° LiDAR
already sees everything else from any single heading. Four headings sweep
that blind wedge across the full circle exactly once. Finer steps cost time
without covering more.

**Stopping it:**
- **CALIBRATE again** → SIGINT. The script traps it and *drives home* first.
- **E-STOP** → SIGKILL + cancel-all on `/navigate_to_pose`. Killing the
  script alone is not enough: Nav2 holds the last accepted goal and would
  resume the moment the E-STOP latch cleared.

**If the button is greyed out:** mapping isn't running. If it refuses on
tap, check the log — `ros2 node list | grep bt_navigator` (Nav2 down) is the
usual cause.

**Run log:** `~/aislebot_logs/calib_<timestamp>.log`, with the last lines
mirrored onto the phone while it runs.

```bash
tail -f ~/aislebot_logs/calib_*.log      # full detail from the terminal
```

### Foxglove click-to-goal

`nav2_slam.launch.py` starts `goal_pose_adapter`, which is **inert until you
opt in**. In the 3D panel settings, set the publish pose topic to:

| Topic | Drag arrow means |
|---|---|
| `/goal_pose` (old) | where the robot's **right side** faces — drag 90° clockwise of the heading you want |
| `/goal_pose_click` (adapter) | where the robot's **nose** faces — drag where you actually mean |

**The exact click-path, because none of it is discoverable** (first made to
work 21 Aug 2026, §17.31 — three things must all be right and each one fails
*silently*):

1. Open the 3D panel's settings (gear icon), scroll past **Topics** and
   **Custom layers** to the **Publish** section. It holds *three independent
   tools with three independent topic fields* — this is not the topic list.
2. The one that sends a goal is **"2D pose (geometry_msgs/PoseStamped)"**.
   Not "2D pose estimate" (that's `/initialpose`, for AMCL localisation), and
   not "2D point" (that's `/clicked_point`, which Nav2 ignores entirely).
3. Its Topic field is **free text with no dropdown** — type `/goal_pose_click`
   exactly and press Enter.
4. Click the **publish tool icon** in the 3D view's top-right toolbar, then
   pick **"Publish 2D pose (/goal_pose_click)"** from the flyout menu. The
   toolbar defaults to the *point* tool, so this step is mandatory.
5. On the map: **press and hold** at the target, **drag** to set the heading,
   **release** to send. A quick click may not fire — the arrow updates while
   held and only sends on release.

**Failure signature to recognise:** a yellow dot appears on the map, the robot
doesn't move, and nothing errors anywhere. That is the *point* tool still
armed (step 4 skipped) publishing a position-only `PointStamped`. Confirm a
real goal went out by watching Terminal 2 for `goal_pose_adapter: goal (x, y)
nose … -> base_link yaw …`.

Only the goal's *orientation* was ever affected; position always came from
the click point. That's why the old workaround was survivable — a mis-drag
sent the robot to the right place facing the wrong way, not to the wrong
place.

### Restricting goals to mapped (white) space

`nav2_params.yaml`'s planner sets `allow_unknown: true`, so it will route
through grey/unknown cells. That is deliberate — early maps were ~85%
unknown (§17.4) and `false` would make almost every goal unreachable. Once a
complete base map exists it is reasonable to flip it, but note that a single
unknown pixel across a corridor makes A* fail outright. Editable on the Pi
without internet:

```bash
nano ~/ros2_ws/src/mecanum_navigation/config/nav2_params.yaml   # allow_unknown
cd ~/ros2_ws && colcon build --packages-select mecanum_navigation
```

Until then, safety comes from the local costmap, the footprint check, and
`collision_monitor` — not from refusing to enter unmapped space
(`Navigation_Theory.md` §2).

---

**Caveat on the zero point, stated honestly:** `slam_toolbox` keeps correcting its own pose
estimate as it scan-matches, so after heavy driving with wheel slip the map
origin and the physical mark can separate (§17.19 measured 0.44 m after a
crash). The marker shows where the map *believes* zero is. Good enough to
navigate home to; not a survey monument. Re-run the procedure above if the
two visibly disagree.
