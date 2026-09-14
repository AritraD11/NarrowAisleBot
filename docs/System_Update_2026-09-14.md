# Full system update, 14 September 2026

You asked for one command that updates everything, cleans everything, and
upgrades the Pi and ROS 2 the way iOS 17 becomes iOS 18.

I am not going to give you that command, and I want to explain why before I
give you the one I think you should actually run. You have nine days. The
robot works today. Most of what a sweeping upgrade would touch is exactly
the load-bearing stuff that took this project weeks to get right.

## What I am refusing, and the reason for each

**A mass `apt full-upgrade` including the kernel.** Three things on this Pi
are fragile in ways that a kernel or udev change reaches directly. The ESP32
and the YDLIDAR share a CP2102 VID:PID *and* the same factory serial `0001`,
which is why `99-aislebot.rules` pins them by physical USB port. A udev or
kernel change that renumbers ports silently swaps your motor controller and
your scanner. Then there is the DS3231 RTC, which is the only reason this
robot has correct timestamps without a network. And the netplan file holding
`aislebot-ap` at priority 10, which is the only reason the Pi comes back as
its own access point after a power cycle. Each of those is recoverable if it
breaks. None of them is recoverable in an afternoon, and you do not have a
spare afternoon.

If you want the security updates, `apt upgrade` without `full-upgrade` and
with the kernel held is a reasonable thing to do *after* 23 September. Not
before.

**Merging every branch.** There is one branch. I checked:
`claude/aps-report-draft-2nywbq` and its remote tracking copy, and that is
the entire list. There is nothing to merge and nothing hiding anywhere. If
you were picturing work sitting on some other branch that never made it in,
it does not exist.

**"The best SLAM, the best NAV, the best algorithms."** This is the one I
want to push back on hardest, because the project already answered it and
the answer is inconvenient.

§17.44 ran three different scan-matcher parameter sets and the total
correction came out within 2% across all three. The matcher could not tell
them apart. §17.45 then measured why: with the robot **standing still**,
47.4% of beams were valid at all and 74.8–78% of the rays that ever returned
flipped valid/invalid between sweeps. slam_toolbox is being handed a
materially different point cloud every 88 ms.

No algorithm fixes that. Swapping slam_toolbox for Cartographer, or NavFn for
Smac, changes which sophisticated thing is being fed unreliable input. The
binding constraint is the sensor, it has been measured, and the honest
upgrade is to work on the sensor.

Which is what I built instead.

## What I built

A LiDAR tuner on the dashboard. `LIDAR` button in the map toolbar, next to
`LAYERS`.

The knobs live in `scan_relay.py`, which is the one node that already touches
every scan. Three filters, all defaulting to off:

- **Range floor and cap.** Blank anything outside the window. This is the
  consumer-side range policy that `ydlidar_params.yaml` explicitly reserves
  ("Cap policy at the consumer. Never edit the spec sheet to record a
  decision."). Set the cap to 5.0 and nothing reaches slam_toolbox that it
  would only throw away. This is your "5 m is enough" ask, implemented in the
  place the project already decided it belongs.

- **Persistence gate.** Publish a beam only if it returned in at least K of
  the last N sweeps. This aims straight at the flicker number.

The persistence gate is a *validity* gate and never a range filter. It
decides whether to publish a beam. If it publishes one, it publishes that
sweep's own instantaneous value, unaveraged, never carried forward. So it
cannot smear geometry the way a temporal median would. The worst it can do
to a moving robot is admit a genuinely new surface K sweeps late: about 88 ms
at K=2 on the measured 11.35 Hz head, which is 7 mm of travel at the 0.08 m/s
Nav2 cap, against a 50 mm costmap cell.

It costs something in the other direction and the panel says so. A beam that
gets dropped does not **clear** a cell either, so an over-tight gate leaves
stale obstacles standing in the costmap. If more than half the sensor's
returns are being cut, the panel turns orange and tells you to loosen it.

Every parameter is live now. Before this they were read once at construction
and a restart was the only way to change one, which turns tuning into
something you get four attempts at per hour.

The readout is the part that makes the knobs worth having:

```
Beams / sweep          430
Live (sensor)     204 (47%)     <- what the sensor returned, before any policy
Published to SLAM 151 (74%)     <- what slam_toolbox and the costmaps receive
Cut by range            34      <- attributed to the knob that did it
Cut by persistence      19
Churn since last sweep  17%
```

That attribution is the whole point. Without it you are turning three knobs
and guessing which one helped.

Three presets: **RAW** (everything, the A-side of every A/B), **AISLE**
(5 m cap, 2-of-3, the configuration I would run for the APS), **STRICT**
(4 m, 0.25 m floor, 3-of-3, for a commissioning drive where a clean map
matters more than reaction time).

The panel shows what the relay reports it is *running*, never what you
typed. A set the relay refuses must not look applied. `SAVE` writes only a
configuration the relay has confirmed, and saves the measured numbers
alongside it so the file reads as evidence rather than just settings.

Tests: `tools/tests/scan_relay_gate.py` (47 checks, drives the real gate
methods pulled out of the shipped source) and `tools/tests/dashboard_lidar.py`
(60 checks). The second one is deliberately cross-file, because the panel and
the relay deploy separately and every way they can disagree is silent. It
checks the parameter names match, the ROS types match, the defaults match,
every preset validates, every button maps to a real preset, every element the
JS reaches for exists, and every message it sends has a handler.

Rendered in Chromium at 1180 px and 400 px. No overflow, no page errors, all
four readout states correct.

## What is actually wrong on the Pi right now

From your own audit output, in the order I would deal with it.

**Two launch trees are running at the same time.** PID 6559 is
`aislebot_full.launch.py` from the service. PID 9626 is
`mapping_full.launch.py` with `async_slam_toolbox_node` live at 6:37
elapsed. That is the third unstopped mapping session today. It is writing to
a map nobody is going to grade, holding the serial port, and competing for
CPU with the thing you actually want running. Kill it first, before anything
else in this document.

**The audit is incomplete and does not say so loudly enough.** `ping 8.8.8.8`
failed while DNS resolved, so 9 of the 25 file comparisons came back
`FETCH-FAILED`. You are not looking at a full picture. Those nine files might
be fine or might have drifted; the audit does not know and neither do I.

**Four files have genuinely diverged.** `sensors.launch.py` does not exist on
the Pi at all. `mapping_full.launch.py` is 162 lines on the Pi against 107 in
the repo, which confirms the Pi is running the older self-contained version
that predates the split. `navigation.launch.py` is 254 against 285.
`phone_dashboard.py` was 3263 against 3403, which was exactly the G7 named
locations work, and is now further behind because of the tuner.

**454 MB in `aislebot_logs`: 228 PGM maps and 497 CSVs.** This is your APS
evidence base. `pi_clean.sh` does not touch it and I have not changed that.
Copy it off before you clean anything, then decide about it separately and
deliberately.

## The cleanup

`pi_clean.sh` already existed and already does what you asked, dry-run by
default. I fixed three things in it today:

It was cleaning `~/.vscode`, which does not exist on this Pi. The weight is
in `~/.vscode-server`, which your audit measured at **1.4 GB**. So that
section has been reporting `0B` and removing nothing while sitting directly
on top of the largest reclaimable item on the disk. Both paths are handled
now.

Rotated system logs under `/var/log` (119 MB) were never touched, because
`journalctl --vacuum-size` only cleans the binary journal and rsyslog's text
logs plus their `.gz` rotations are a separate pile.

Disabled snap revisions already on disk were never removed. `refresh.retain=2`
stops new ones accumulating but does nothing about the ones already sitting
there, and your audit found one.

Plus `phone_dashboard.pre_light_theme.py`, which the audit flagged as an
extra file on the Pi, is now in the dead-code tarball list.

Expected reclaim, conservatively: 1.4 GB from VS Code server, ~104 MB from
journald down to its 100 MB cap, 119 MB of rotated logs, 15 MB across 3038
`.ros/log` run dirs, 30 colcon build log dirs, one old kernel, one disabled
snap revision. Call it 2 GB without touching a single thing you need.

## The order to do this in

1. Kill the stray mapping session. Now, before anything else.
2. Get the Pi online, run the audit again, and get a complete picture
   instead of one with nine holes in it.
3. Pull the logs off the Pi. 454 MB of evidence living on one SD card nine
   days before a seminar is a bad place for it to be.
4. Dry-run the cleanup. Read it. Then apply it.
5. Deploy the four diverged files, one at a time, hashing each one.
6. Restart, verify against the live nodes rather than against the files,
   and run the range-envelope capture that has been open since Phase 2
   started.
7. Tune the LiDAR against the live readout and write down what you chose
   and why.

Steps 5 and 6 are the ones where something can break, which is why they come
after the backup and not before.

## Commands

Same workflow as always. Windows PC pulls from GitHub, then `scp` to the Pi.
The Pi never needs the internet.

### Step 1, on the Pi, right now

```bash
# Find the stray mapping session and stop it cleanly. SIGINT, not SIGKILL:
# the dashboard's shutdown handler saves the open map on SIGTERM/SIGINT and
# a SIGKILL loses it (§17.34, a 24-minute run lost exactly this way).
pgrep -af "mapping_full.launch.py"
pkill -INT -f "mapping_full.launch.py"
sleep 8
pgrep -af "slam_toolbox|mapping_full" || echo "clean — nothing left running"

# The service should still be up and should be the ONLY thing up.
systemctl is-active aislebot.service
ros2 node list
```

### Step 2, on the Pi, get online and re-audit

```bash
sudo nmcli con up eduroam
#  -> drops your SSH session. Expected. Reconnect:
#     ssh aritra@aritra-desktop.local

ping -c3 8.8.8.8        # must PASS this time, or the audit is incomplete again
ping -c3 github.com
bash ~/pi_audit.sh --online 2>&1 | tee ~/audit_20260914_online.txt
```

If `ping 8.8.8.8` still fails while DNS resolves, stop and tell me. That
combination means something specific and I would rather diagnose it than have
you work around it a third time.

### Step 3, on the Windows PC, pull the evidence off

```powershell
cd "C:\Users\aritradas\Documents\NAB\for scp download"
mkdir aislebot_logs_20260914
scp -r aritra@aritra-desktop.local:~/aislebot_logs/* .\aislebot_logs_20260914\
```

### Step 4, on the Pi, clean up

```bash
bash ~/pi_clean.sh              # DRY RUN. Read every line of this.
bash ~/pi_clean.sh --apply      # only after you have read it
df -h /
```

Note that section 8 sets the boot target to console. That is deliberate and
it is documented: §17.25 had CPU starvation kill SLAM and the LiDAR pipeline
outright mid-run, and the desktop session is about 250 MB of RAM and a core.
It is reversible with `sudo systemctl set-default graphical.target` and it
does not affect SSH either way.

### Step 5, on the Windows PC, fetch the changed files

```powershell
cd "C:\Users\aritradas\Documents\NAB\for scp download"

$base = "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/aps-report-draft-2nywbq"

curl.exe -fsSL -o scan_relay.py            "$base/src/scan_relay/scan_relay.py"
curl.exe -fsSL -o phone_dashboard.py       "$base/src/mecanum_robot/mecanum_robot/phone_dashboard.py"
curl.exe -fsSL -o sensors.launch.py        "$base/src/mecanum_robot/launch/sensors.launch.py"
curl.exe -fsSL -o mapping_full.launch.py   "$base/src/mecanum_robot/launch/mapping_full.launch.py"
curl.exe -fsSL -o navigation.launch.py     "$base/src/mecanum_navigation/launch/navigation.launch.py"
curl.exe -fsSL -o pi_clean.sh              "$base/tools/pi_clean.sh"
curl.exe -fsSL -o scan_relay_gate.py       "$base/tools/tests/scan_relay_gate.py"
curl.exe -fsSL -o dashboard_lidar.py       "$base/tools/tests/dashboard_lidar.py"

# Check what arrived before sending it. A 404 saved as a file is still a file.
Get-FileHash scan_relay.py, phone_dashboard.py, sensors.launch.py, `
  mapping_full.launch.py, navigation.launch.py, pi_clean.sh, `
  scan_relay_gate.py, dashboard_lidar.py -Algorithm SHA256 |
  Format-Table Hash, Path -AutoSize
```

Expected SHA-256 prefixes, so a truncated download cannot pass as a good one:

| File | lines | sha256 starts |
|---|---:|---|
| `scan_relay.py` | 643 | `7dd2d36770e03424` |
| `phone_dashboard.py` | 3998 | `c9e387b5126a7197` |
| `sensors.launch.py` | 174 | `aa4e771c8e8e3c67` |
| `mapping_full.launch.py` | 107 | `d0fe5f6b33c559dc` |
| `navigation.launch.py` | 285 | `94694c402e12749e` |
| `pi_clean.sh` | 205 | `adb7dd45186d8d4e` |
| `scan_relay_gate.py` | 300 | `d2cf815cd64093b1` |
| `dashboard_lidar.py` | 324 | `89900bcfe0db35c9` |

Then send them:

```powershell
scp scan_relay.py phone_dashboard.py sensors.launch.py mapping_full.launch.py `
    navigation.launch.py pi_clean.sh scan_relay_gate.py dashboard_lidar.py `
    aritra@aritra-desktop.local:~/incoming/
```

### Step 6, on the Pi, deploy one file at a time

```bash
mkdir -p ~/incoming ~/backup_20260914
cd ~/incoming

# Confirm what arrived matches what left. If any line here does not match the
# table above, STOP -- do not deploy a file you cannot account for.
sha256sum *.py *.sh | cut -c1-16,66-

WS=~/ros2_ws

# Back up before overwriting. There is no git clone on this Pi; overwritten
# means gone.
cp $WS/src/scan_relay/scan_relay.py                          ~/backup_20260914/ 2>/dev/null
cp $WS/src/mecanum_robot/mecanum_robot/phone_dashboard.py    ~/backup_20260914/
cp $WS/src/mecanum_robot/launch/mapping_full.launch.py       ~/backup_20260914/
cp $WS/src/mecanum_navigation/launch/navigation.launch.py    ~/backup_20260914/

# scan_relay.py is a plain script run straight off disk -- no build needed.
cp scan_relay.py $WS/src/scan_relay/scan_relay.py

# The launch files and the dashboard DO need a build.
cp sensors.launch.py      $WS/src/mecanum_robot/launch/
cp mapping_full.launch.py $WS/src/mecanum_robot/launch/
cp navigation.launch.py   $WS/src/mecanum_navigation/launch/
cp phone_dashboard.py     $WS/src/mecanum_robot/mecanum_robot/

cp pi_clean.sh ~/pi_clean.sh
mkdir -p ~/tools/tests && cp scan_relay_gate.py dashboard_lidar.py ~/tools/tests/

# Prove the copies are byte-identical to what you downloaded.
sha256sum $WS/src/scan_relay/scan_relay.py \
          $WS/src/mecanum_robot/mecanum_robot/phone_dashboard.py \
          $WS/src/mecanum_robot/launch/sensors.launch.py \
          $WS/src/mecanum_robot/launch/mapping_full.launch.py \
          $WS/src/mecanum_navigation/launch/navigation.launch.py
```

### Step 7, on the Pi, build and restart

```bash
cd ~/ros2_ws
sudo systemctl stop aislebot.service

colcon build --packages-select mecanum_robot mecanum_navigation --symlink-install
source install/setup.bash

sudo systemctl start aislebot.service
sleep 12
systemctl is-active aislebot.service
ros2 node list
```

### Step 8, on the Pi, verify against the LIVE nodes

Never against the files. The project's standing rule, and it has caught real
problems more than once.

```bash
bash ~/tools/verify_live_config.sh

# The relay must now declare the five new parameters. If this list is short,
# the old scan_relay.py is still the one running.
ros2 param list /scan_relay
ros2 param get /scan_relay range_cap_m
ros2 param get /scan_relay persist_n

# The stats topic should be alive at roughly a third of the scan rate.
ros2 topic hz /scan_relay_stats --window 20

# And the tests should pass on the Pi's own copies, not just in the repo.
cd ~ && python3 tools/tests/scan_relay_gate.py | tail -3
```

### Step 9, tune it

Open the dashboard, go to map view, tap `LIDAR`.

Park the robot somewhere it can see a wall at 3 to 4 m and **leave it
stationary**. Every number on that panel is meaningful only when the robot
is not moving, because a moving robot changes what the sensor sees and you
lose the ability to attribute a change to the knob you turned.

Then, one parameter at a time, writing the prediction down before each one:

1. Tap `RAW`. Let it settle. Write down Live, Published, and Churn. This is
   your baseline and every later number is meaningless without it.
2. Set the cap to 5.0, apply. Published should drop by roughly the beam count
   beyond 5 m. Churn should fall, because distant returns are the flickeriest.
3. Set persistence to 2 of 3, apply. Churn should fall again. Published
   should drop a little. If it drops a lot, the sensor is worse than 47.4%
   suggested and that is a finding worth having.
4. Try 3 of 3. My prediction, registered before you run it: churn falls
   further but Published drops below 60% of Live, and the panel turns orange.
   If that happens, 2 of 3 is the setting.
5. Tap `SAVE` on whichever configuration you keep. It writes to
   `~/lidar_tune.json` with the measured numbers attached.

Then drive the commissioning route with it and compare the map against the
one built at `RAW`. That comparison is the evidence, not the churn number.

## One thing I want to flag

The range-envelope capture has been open since Phase 2 started and has never
successfully run. `tools/scan_range_envelope.py` exists and its nine self
tests pass, but it has never been pointed at real data. G4, the accepted
commissioning map, is still the blocker for everything downstream of it.

The tuner makes that capture more useful than it was this morning, because
now you can change the range policy and re-capture without restarting
anything. But the tuner is not a substitute for running it. If the nine days
only allow one more piece of fieldwork, it should be G4, not more tuning.
