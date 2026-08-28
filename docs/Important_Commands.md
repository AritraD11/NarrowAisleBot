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

**On eduroam instead** — DHCP hands out a different address every time.
`aritra-desktop.local` is the documented route, but **Windows' mDNS
resolver fails on it often enough not to rely on it** (25 Aug: four
consecutive `Could not resolve hostname` from PowerShell while the Pi was
up and reachable by IP). Get the real address from the Pi and use it:

```bash
ip -4 -br addr          # on the Pi — read the wlan0 line
```
```bash
ssh aritra@<that-address>          # from the PC
ssh aritra@aritra-desktop.local    # mDNS, when it feels like working
```

**Check this at the start of every session.** The Pi's eduroam lease moved
twice in two days (`10.53.1.167` → `10.53.3.143`), and reusing yesterday's
address gives a `Connection timed out` that looks exactly like the Pi being
down. So does using `10.42.0.1` while the Pi is on eduroam — that address
only exists when it is hosting its own AP.

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

**`--retry` alone is not enough.** curl does not retry TLS handshake
failures — only transient HTTP responses and timeouts. eduroam has twice
produced repeated `curl: (35) OpenSSL … wrong version number` on this Pi
(a middlebox answering port 443 with something that is not TLS), and
`--retry 5` sailed straight past all five. Always include
`--retry-all-errors`:

```bash
curl -sSL --retry 5 --retry-delay 2 --retry-all-errors -o <dest> <url>
```

### 2.1 When the Pi cannot reach GitHub at all — relay via the PC

If the TLS errors persist rather than clearing on retry, stop fighting the
Pi's network. The PC downloads the file and hands it over; this works on
either network as long as both machines are on the same one.

```powershell
# On the PC
cd $HOME\Documents
curl.exe -sSL -o <file>.py https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/<path-in-repo>
Get-FileHash <file>.py -Algorithm SHA256
scp <file>.py aritra@<pi-address>:~/ros2_ws/src/mecanum_robot/mecanum_robot/<file>.py
```

Use `curl.exe` with the extension — bare `curl` in PowerShell is an alias
for `Invoke-WebRequest`, which takes different arguments and fails
confusingly. `Get-FileHash` prints uppercase; the hash is the same.

**Verify the copy landed correctly** before trusting it — compare against
the hash of the file in the repo (`sha256sum <path-in-your-local-checkout>`):
```bash
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/<file>.py
```

A truncated download that still compiles is how you get a mystery at 5pm.
On 25 Aug a failed fetch left the *old* file in place and the hash check
caught it immediately, before a build made it look deployed.

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

### 3.1 Staging folders — one per direction (28 Aug 2026)

**The Pi never needs internet, and should not be put on eduroam to get it.**
It hosts its own AP with no uplink, so it cannot reach GitHub at all. The
PC has internet; the PC and the Pi can always see each other on
`10.42.0.1`. So every file moves in two hops, and the PC is always the
one that talks to the outside world:

```
GitHub  ──curl──▶  Windows  ──scp──▶  Pi          (deploying code/config)
                   Windows  ◀──scp──  Pi          (pulling data to analyse)
```

**One folder per direction**, so a directory listing answers "what did I
just send" and "what did I just pull" separately:

| Direction | Folder |
|---|---|
| **To the Pi** — anything downloaded on Windows on its way to the robot | `C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download` |
| **From the Pi** — logs, bundles, maps, CSVs pulled back for analysis | `C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Analysis` |

Why staging folders at all: the alternative is what already happened once.
Files got downloaded to `$HOME\Documents`, and a batch of three `scp`s went
out with one of them silently mistyped — see the warning below.

Both are scratch space, not archives. Anything worth keeping gets committed
to the repo.

> **A `curl.exe` line in this repo's docs always runs on Windows, never on
> the Pi.** If one is ever pasted into the Pi's shell it will hang and then
> fail on DNS, which looks like a broken URL and is not.

> ⚠ **`scp` reporting `100%` does not mean the file arrived where you
> meant.** A password typed onto the end of a destination path before Enter
> produced `.../mapping_full.launch.py<PASSWORD-REDACTED>` — `scp` created it,
> reported `100%`, exited 0, and the real file was never touched. The build
> and restart that followed silently used the old file. **Hash every file
> on arrival, per file, not per batch** — two of the three in that batch
> landed correctly, which is exactly why a per-batch assumption fails:
>
> ```bash
> sha256sum ~/ros2_ws/src/.../<file>
> ```
>
> A destination path that ends in anything other than the filename you
> intended is the tell. §17.39.

---

## 3.2 The deploy recipe — one procedure, every time (28 Aug 2026)

**Every file that reaches the robot goes through these five steps, in this
order, with no step skipped.** The rule this encodes: *a value in the repo is
not a value on the robot* (§17.32), and *`scp` reporting `100%` says a file
arrived somewhere, not that it arrived where you meant* (§17.39).

```powershell
# 1. WINDOWS downloads.  Always Windows -- the Pi hosts its own AP with no
#    uplink and cannot reach GitHub.  A curl.exe line in these docs is never
#    a Pi command.
cd "C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download"
curl.exe -sSL --retry 3 --retry-all-errors -o <FILE> ^
  "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike/<REPO PATH>"

# 2. WINDOWS pushes.  Type the WHOLE destination path including the filename.
scp <FILE> aritra@10.42.0.1:<DEST PATH>
```

```bash
# 3. PI hashes ON ARRIVAL, per file, never per batch.  Two of three landing
#    correctly is exactly why a per-batch assumption fails (§17.39).
sha256sum <DEST PATH>
ls -la $(dirname <DEST PATH>)      # nothing with a password stuck on the end

# 4. PI rebuilds -- ONLY for files under ~/ros2_ws/src.  Tools in ~/tools run
#    from source and need no build.
cd ~/ros2_ws && colcon build --packages-select mecanum_robot --symlink-install
sudo systemctl restart aislebot.service

# 5. PI verifies against the LIVE NODE, never by reading the file back.
ros2 node list                                   # is it even running?
ros2 param get /<node> <param>                   # for a config change
ros2 run tf2_ros tf2_echo odom base_link         # for anything frame-touching
```

**Step 5 is the one people skip and it is the one that has caught every
silent failure this project has had** — §17.32's never-deployed config,
§17.34's inert parameter file, §17.39's mistyped `scp`, and §17.42's
`Parameter goal_checker.xy_goal_tolerance not found`.

### Currently pending deployment

| Repo file | Destination on the Pi | sha256 |
|---|---|---|
| `src/mecanum_robot/mecanum_robot/phone_dashboard.py` | `~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py` | `5b30a91dc7614d73848357bcedd66771cb332eddd12d1de06ed58dce47ad43d1` |
| `tools/wheel_forensics.py` | `~/tools/wheel_forensics.py` | `27858ce417f3f39e56db3b87b31644fc11a9292aba7247f1c8d9a2d80bf96236` |
| `src/mecanum_robot/urdf/aislebot.urdf` | `~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf` | `ea6619ff3999b856fc3c1632041bd3a151eb8732f9c782d90207831ce1b0a81c` |

`wheel_forensics.py` needs no rebuild. `phone_dashboard.py` needs step 4.
`aislebot.urdf` is comment-only (§17.42) — deploy it whenever the workspace
is next rebuilt for another reason, not on its own.

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

## 5. Saving and viewing a map

### 5.1 Saving a map — there is no separate save button

**Pressing STOP MAP on the dashboard saves the map.** `stop_mapping()` in
`phone_dashboard.py` shells out to `map_saver_cli` before it tears the
mapping stack down, so the save is part of stopping and always has been.
If you kill the stack any other way — `systemctl restart`, a reboot, a
crash — **the map is gone**, because it lived only in `slam_toolbox`'s
memory. STOP MAP is the only path that persists it.

One mapping run produces four files in `~/aislebot_logs/`, all sharing one
timestamp:

| File | What it is |
|---|---|
| `run_<stamp>.pgm` | the occupancy grid itself |
| `run_<stamp>.yaml` | its metadata — resolution, origin, thresholds |
| `run_<stamp>.csv` | 13-column per-wheel motor telemetry |
| `run_<stamp>_pose.csv` | `epoch_s, map_x, map_y, yaw_deg` (only on the post-`0bea474` dashboard) |

Confirm it actually landed before you power anything down:

```bash
ls -lt ~/aislebot_logs/ | head -6
```

### 5.2 Pulling it to the PC

Run on the **PC**, in a new PowerShell — not inside the SSH session.
Substitute the run's timestamp:

```powershell
scp aritra@10.42.0.1:~/aislebot_logs/run_<stamp>.* "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

On eduroam, swap `10.42.0.1` for the Pi's DHCP address. `aritra-desktop.local`
often fails to resolve from Windows — get the real address with
`ip -4 -br addr` on the Pi and use it directly rather than fighting mDNS.

### 5.3 Viewing it — use `map_viewer.html`, not the telemetry analyzer

**`telemetry_analyzer.html` cannot open a bare map.** Its map dropzone only
unlocks after it has loaded a valid 13-column run CSV, so it is the wrong
tool when all you want is to look at a `.pgm`. `docs/tools/map_viewer.html`
exists for exactly that (§17.32) and takes just the `.pgm` + `.yaml` pair.

1. Download it once — it lives in this repo, not on the Pi:
   ```powershell
   curl -sSL -o map_viewer.html https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/docs/tools/map_viewer.html
   ```
2. Double-click it. Any browser, no server, no install, works offline.
3. Drag the **`.pgm` and `.yaml` together** onto it. Both at once — the
   `.yaml` carries the resolution and origin, without which the grid has no
   scale and no world position.

Use `telemetry_analyzer.html` instead when you want the map *alongside* the
wheel telemetry for the same run — drop the `run_<stamp>.csv` in first,
then the map pair.

### 5.4 What to look for — the acceptance gate

§17.32 retired the old "no single-sample step > 10 cm" criterion: it cannot
tell a *correct* loop closure from a bad one, because a legitimate
correction of accumulated drift trips it just as hard as a false match. Step
size is a diagnostic now, not a pass/fail. Judge a commissioning map on
these three instead:

| Check | Pass condition |
|---|---|
| **Walls present** | the grid contains real occupied cells, not just free space and unknown. An open-floor drive produces a map with no wall geometry and is useless to AMCL. |
| **Map integrity** | no folds, tears, doubled walls, or forked corridors in `map_viewer.html`. This is the criterion that actually catches a bad closure. |
| **Return-to-mark** | drive back to the physical zero mark; the dashboard HUD should read ≈ `(0, 0)` and nose ≈ `-90°` |

A doubled wall or a corridor that forks into two parallel copies of itself
means a false loop closure fused two places that are not the same place.
That map cannot be used for localisation and the run has to be repeated.

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
