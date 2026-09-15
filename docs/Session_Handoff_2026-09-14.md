# Session handoff — 14 Sep 2026, end of day

Written at the pause point, with the robot's baseline service confirmed
running and nothing mid-drive. APS is 23 Sep, 14:30–15:30. **9 days left.**

---

## 0. THE ONE THING NOT TO SKIP TOMORROW

Before any G4 attempt: **`slam_nodom.yaml` was NOT touched today.** The Pi
is still running whatever scan-matcher configuration it had before this
session. `Phase_234_Push.md` §4.1 is explicit about why this matters — the
entire Stage G result (zero map-to-odom correction events over 698 s) only
holds if `use_scan_matching: false` actually landed on the robot, and if the
wrong file is deployed the whole day's drive is void without anyone noticing
until the map comes back folded.

```bash
# on the Pi, after scp'ing system/slam_nodom_stageB.yaml as slam_nodom.yaml
sha256sum ~/ros2_ws/slam_nodom.yaml
# expect 0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f

cd ~/ros2_ws && colcon build --packages-select mecanum_robot --symlink-install
sudo systemctl restart aislebot.service

# THEN verify against the LIVE node, never the file:
ros2 param get /slam_toolbox use_scan_matching                   # must be false
ros2 param get /slam_toolbox max_laser_range                     # must be 5.0
```

If `use_scan_matching` reads `true`, stop before driving anywhere. This is
step one of tomorrow, before coffee, before anything else.

---

## 1. What is physically true right now

- `aislebot.service` is **active**, running today's new code (confirmed —
  see §2). All baseline nodes up: `arm_bridge`, `esp32_bridge`,
  `foxglove_bridge`, `joy_node`, `joy_to_aislebot`, `lcd_display`,
  `odometry_publisher`, `phone_dashboard`, `robot_state_publisher`,
  `teleop_asym`, `twist_mux`.
- No mapping session running. The stray `mapping_full.launch.py` (PID 9626,
  running since morning) was killed cleanly with `SIGINT` and confirmed gone.
- The one-off `sensors.launch.py` verification test was also cleanly shut
  down; `ydlidar_ros2_driver_node` confirmed **not** running.
- The Pi's network state at pause: unconfirmed whether you switched back to
  `AisleBot-Pi` or are still on eduroam. Check first thing:
  `nmcli -t -f NAME,DEVICE con show --active`. Switch home with
  `sudo nmcli con up aislebot-ap` if still on eduroam.

---

## 2. What got done today (14 Sep)

**Built and shipped:** a live LiDAR quality tuner. `scan_relay.py` gained a
range floor/cap and a K-of-N persistence gate, both live-settable over
`ros2 param set` instead of restart-only. `phone_dashboard.py` gained a
`LIDAR` panel (toolbar, next to `LAYERS`) with three presets (RAW / AISLE /
STRICT) and a readout that attributes every dropped beam to the filter that
dropped it. 107 checks across two new test suites
(`tools/tests/scan_relay_gate.py`, `tools/tests/dashboard_lidar.py`), both
passing, both cross-checking the dashboard against the relay since they
deploy separately. Rendered and screenshotted in Chromium at desktop and
phone width — no layout bugs.

**Read and assessed:** Harchowdhury, Kleeman & Vachhani's nodding-LiDAR
paper (IEEE RA-L 2018, Vachhani is IIT Bombay SYSCON). Written up in
`docs/Nodding_LiDAR_Assessment.md` as a year-2 direction, explicitly not a
pre-APS change — doesn't transfer cleanly (their sample count is 1024/rev,
NAB's is ~430/rev, and NAB can't command its scan rate at all).

**Refused, with reasons, in `docs/System_Update_2026-09-14.md`:** a mass
kernel/apt upgrade (risks the CP2102 port pinning, the RTC, the AP netplan
priority — all load-bearing, none recoverable in an afternoon), merging
branches (there's only one), and "best SLAM/NAV algorithms" (§17.44/§17.45
already showed the sensor, not the algorithm, is what's binding).

**Fixed a real bug in `pi_clean.sh`:** it had been cleaning `~/.vscode`,
which doesn't exist on this Pi, while the 1.4 GB the audit measured sits in
`~/.vscode-server`. Also added rotated `/var/log` cleanup and disabled snap
revisions.

**On the actual hardware, this session:**
- Diagnosed why `pi_audit.sh --online` was returning 9× `FETCH-FAILED`:
  `raw.githubusercontent.com` is specifically blocked on this network (SSL
  handshake fails cleanly, "wrong version number"), while `github.com` and
  `api.github.com` both work fine. Not a general connectivity problem.
- Worked around it: `git clone --depth 1` straight onto the Pi at
  `~/repo_sync` (git-over-HTTPS uses `github.com`, not the blocked domain).
  This is now sitting there and can be `git pull`-ed again next time you're
  online, without needing the Windows-PC-then-scp round trip.
- Deployed five files from that clone into `~/ros2_ws`, backed up the old
  versions to `~/backup_20260914` first, verified every copy byte-identical
  with `cmp`:
  - `src/scan_relay/scan_relay.py`
  - `src/mecanum_robot/mecanum_robot/phone_dashboard.py`
  - `src/mecanum_robot/launch/sensors.launch.py` (was missing entirely)
  - `src/mecanum_robot/launch/mapping_full.launch.py`
  - `src/mecanum_navigation/launch/navigation.launch.py`
- First `colcon build` attempt failed (`sensors.launch.py` being a
  brand-new file confused `--symlink-install`). Fixed with the project's
  own documented remedy: `rm -rf build/mecanum_robot install/mecanum_robot
  build/mecanum_navigation install/mecanum_navigation`, then a clean
  rebuild — succeeded.
- Restarted `aislebot.service`, confirmed active, confirmed the **new**
  `scan_relay.py` is what's actually running by launching
  `sensors.launch.py` standalone and reading `ros2 param list /scan_relay`:
  all five new parameters present (`range_cap_m`, `range_floor_m`,
  `persist_n`, `persist_k`, `stats_enabled`). Shut it down cleanly after.

---

## 3. Left undone from today — check before assuming

- **`slam_nodom.yaml` deployment — see §0. This is the blocker.**
- `src/mecanum_navigation/config/nav2_params.yaml`'s deployed state on the
  Pi was **never checked today**. `Phase_234_Push.md` says
  `robot_model_type: "nav2_amcl::OmniMotionModel"` is "already correct" —
  that claim is about the *repo*, not confirmed against what's on the Pi.
  Verify against the live node before trusting it:
  `ros2 param get /amcl robot_model_type` (once AMCL is up).
- The two new test files (`scan_relay_gate.py`, `dashboard_lidar.py`) were
  **not** copied into `~/tools/tests` on the Pi — they exist in
  `~/repo_sync/tools/tests/` and can be copied from there in ten seconds
  whenever you need them on-device.
- The updated `pi_clean.sh` was **not** run, and the updated copy wasn't
  even placed at `~/pi_clean.sh` yet — it's sitting in `~/repo_sync/tools/`.
- The `aislebot_logs` backup (scp to the Windows PC) — you were given the
  command, not confirmed it ran.
- The optional `apt-get upgrade` (security-only, kernel held) — offered,
  never confirmed as wanted or run.
- The actual LiDAR tuning session (park near a wall, try RAW → AISLE →
  STRICT, watch the readout, save a preset) — not done yet. The tuner is
  deployed and verified working; it hasn't been used for real yet.

None of these block tomorrow's G4 work except §0.

---

## 4. Tomorrow: "complete Phase 2 and 3"

Full plan already written and sitting in the repo: **`docs/Phase_234_Push.md`**,
written earlier today for exactly this. Read it fully before starting — it
has the drive procedure, registered predictions, a time budget, and a
fallback ladder if G4 fails. Do not re-derive any of it.

The honest headline from that document, stated there before I say it again
here so it isn't a surprise: **Phase 3 (the commissioning map, G4) can
reach 100% in a day. Phase 2 (odometry / state estimation) can reach
roughly 75%, not 100% — full closure needs an IMU that hasn't been bought,
and no amount of lab time creates a part.** That's not new pessimism, it's
what got written down this morning before any of today's other work
happened. `docs/Phase2_Without_IMU.md` is the full argument for why 75%
characterized-not-optimal is a legitimate, defensible thing to present —
not a gap to apologize for.

In order, per `Phase_234_Push.md`:

1. **§0 here** — deploy `slam_nodom.yaml`, verify against the live node.
2. **Block A (G4)** — the commissioning map. Roll through corners, never
   rotate in place, target 8 m total path, close the loop on the zero mark.
   Budget three attempts. This is the gate; nothing after it means
   anything if it fails.
3. **§6, the Phase 2 track** — fits in the gaps around G4: plant ID is
   already done, run `wheel_forensics.py --csv` over every drive today
   (free, same encoder data), get a third phantom-yaw video replication.
4. **Blocks B/C (G5, G6)** — AMCL's first-ever launch, five tapped goals,
   tape-measured. Only if G4 lands.
5. **Block D (G7)** — named locations, teach three, full power cycle,
   recall three. The named-location code is already written and tested
   (20/20) and now deployed — this block is execution, not construction.

If G4 fails all three attempts, the document's own fallback ladder (§8)
says what to demonstrate instead. Don't spend the afternoon fighting it.

---

## 5. Repo state

Branch: `claude/aps-report-draft-2nywbq`, PR
[#14](https://github.com/AritraD11/NarrowAisleBot/pull/14) (draft), all
pushed to `origin`. Latest commit `b106653`.

Today's commits, newest first: `b106653` (fix a missing table row),
`4d265bf` (system update doc, pi_clean fixes, nodding-LiDAR assessment),
`bacbe86` (the LiDAR tuner).

Re-run before trusting anything: `python3 tools/tests/scan_relay_gate.py`,
`python3 tools/tests/dashboard_lidar.py`, `python3
tools/tests/dashboard_locations.py`.

---

## 6. Standing operating discipline — unchanged

- One step at a time, copy-pasteable, wait for the actual output.
- Verify configuration with `ros2 param get` against the **live node**,
  never by reading the YAML.
- Hash every transferred file on arrival, per file, not per batch.
- Write the prediction down before the test (`Phase_234_Push.md` §4.3
  already has tomorrow's filled in).
- Short and crisp in chat.
