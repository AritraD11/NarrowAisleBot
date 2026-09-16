# Phases 2, 3 and 4: the two-day push

**Written 14 September 2026, before the lab day.** APS seminar is 23 September,
14:30 to 15:30. Companion to `Where_We_Stand.md` and `Autonomy_Endgame.md`,
and it supersedes the latter's Day 3 drive procedure for the reason in §3.2.

---

## 1. The honest headline, before anything else

Two of the three phases can close. One cannot, and the reason is not effort.

| Phase | Now | Achievable today | Why |
|---|---|---|---|
| **Phase 2**, odometry and state estimation | 55 % | **~75 %** | Completion needs an IMU. None has been procured. That is a purchase order, not a task, and no amount of lab time creates the part |
| **Phase 3**, perception and mapping | 60 % | **100 %** | G4 needs one accepted commissioning map. Two things changed since the last attempt and both attack the exact failure mode |
| **Phase 4**, autonomous navigation | 45 % | **~85 %** | G5 and G6 are reachable once G4 lands. G7's code is written and tested as of today, so it is deploy-and-test rather than build |

Phase 2 is stated first so it stops costing attention. The three things inside
it that *can* move today are cheap and they slot into gaps in the lab day
rather than competing with Phase 3. They are in §6.

**Phase 3 is the day.** Everything in Phase 4 is blocked on it, and the project
has been blocked on it since August.

---

## 2. What is already done, in the repo, as of this morning

This work happened at the desk so the lab day is execution rather than
construction. Deploy it, verify it, then drive.

| # | Item | State | Why it matters today |
|---|---|---|---|
| 1 | `robot_model_type: "nav2_amcl::OmniMotionModel"` | **Already correct** in `nav2_params.yaml:71` | The known G5 killer. The bare string `"omnidirectional"` aborts the whole `lifecycle_manager` bringup. It is already the full class name, so AMCL will not die on launch for this reason |
| 2 | `navigation.launch.py` starts the LiDAR | **Already fixed**, includes `sensors.launch.py` with `use_sensors` defaulting true | The launch-topology fault that made AMCL structurally impossible until 1 Sep. It would have launched, activated, and waited for a scan forever |
| 3 | Named-location library (G7) | **Written and tested today**, 20/20 | `save_location` / `goto_location` / `list_locations` in `phone_dashboard.py`, atomic JSON write, map-name guard. Run `python3 tools/tests/dashboard_locations.py` |
| 4 | `system/slam_nodom.yaml` marked superseded | **Banner added today** | This file still carries the pre-Stage-G values. Copying it to the Pi turns the scan matcher back on silently. Deploy `slam_nodom_stageB.yaml` under the name `slam_nodom.yaml`, as `pi_audit.sh` already expects |
| 5 | `xy_goal_tolerance: 0.05`, `batch_size: 300` | Already in `nav2_params.yaml` | Stage G values, already committed |

One parameter is still worth changing and it is in §5.2: `yaw_goal_tolerance`
is 0.05 rad, which is 2.9°, against a G6 gate of 10°.

---

## 3. The two changes that make today different from every previous attempt

Three sessions of scan-matcher tuning failed against G4. Nothing below is more
tuning.

### 3.1 The scan matcher is off, and that is measured rather than hoped

`use_scan_matching: false` produced **zero** map-to-odom correction events
across 698 seconds and 18.5 m of driving on two structurally different routes,
6,994 pose samples, zero to six decimal places. The drive it replaced had 48
correction events. The mechanism that folds the maps is not being tuned down,
it is absent.

### 3.2 The drive procedure inverts, and this is the part that is easy to get wrong

The old procedure was "perimeter, nose leading, **rotating at every corner**,
aim for 15 to 18 minutes, longer beats shorter." Every clause of that is now
wrong, and each for a separately measured reason.

**Roll through the corners. Never rotate in place.** Two full turns, 714° over
642 seconds, produced 43 occupied cells, which is 2.1 m of wall for ten and a
half minutes of work. Rotation in place adds no pose-graph node and no map
cell. A 111-second arc driven while translating produced 18 nodes and 77.2 m of
wall, 88 % of a full perimeter drive's coverage in 18 % of its time.

**Drive short.** This is the inversion that matters and it is not obvious.
"Longer beats shorter" was written when the matcher was on and loop closure was
expected to pull the estimate back. With the matcher off, the pose is pure
wheel odometry, so error accumulates monotonically with no mechanism to correct
it. Wheel odometry's measured closure band on this platform is **1.1 to 1.5 %
of path**: 0.229 m over ~18 m is 1.27 %, and the 621 s drive's 0.257 m over
18.14 m is 1.42 %. The G4 return-to-mark gate is 0.15 m. Taking the worst
measured rate rather than the typical one:

$$
\text{max path} = \frac{0.15\ \text{m}}{0.015} = 10.0\ \text{m}
\qquad\text{and at 1.27 \%,}\quad 11.8\ \text{m}
$$

**Ten metres is the ceiling, and it is a ceiling at the pessimistic end of the
measured band.** Target **8 m**, which lands at 0.088 to 0.120 m and keeps real
margin against a gate that has never once been met. Every previous
commissioning attempt ran 18 to 22 m. They were failing a criterion that the
drive length alone had already put out of reach, whatever the matcher was
doing.

This is not a new derivation. The 3 September journal entry registered the same
projection in advance: *"projected on a ~10 m perimeter, odometry alone gives
~0.13 m, inside G4's 0.15 m return gate, which five sessions of matcher tuning
never reached."* Today is the drive that tests it.

If loop closure fires and helps, the number comes in better. That is upside,
and it stays a hypothesis rather than an assumption, because loop closure
running on a separate matcher has never been confirmed to survive the Stage G
change.

> **A documentation fix for the report, found while checking this.** Several
> documents pair the figures as "0.229 m (1.27 %) over 21.85 m". Those do not
> divide: 0.229 / 21.85 is 1.05 %. The journal has it right at line 2824, where
> the closure is 0.229 m over **~18 m** and 21.85 m is the *total wheel path of
> the whole 1047 s drive*. Both numbers are real, the pairing is not. Fix it in
> `APS_Report_Draft_v2.md` §1 and §4.4 before submission, because a committee
> member doing the division in their head will land on 1.05 % and ask.

---

## 4. Block A: G4, the commissioning map

**This is the gate. Budget three attempts. Nothing after it means anything.**

### 4.1 Deploy and verify

Land the Stage G config under the name the launch file actually loads:

```bash
# on the Pi, after scp'ing system/slam_nodom_stageB.yaml as slam_nodom.yaml
sha256sum ~/ros2_ws/slam_nodom.yaml
# expect 0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f

cd ~/ros2_ws && colcon build --packages-select mecanum_robot --symlink-install
sudo systemctl restart aislebot.service
```

Then, against the **live node**, never the file:

```bash
ros2 param get /slam_toolbox use_scan_matching                   # false
ros2 param get /slam_toolbox correlation_search_space_dimension  # 0.3
ros2 param get /slam_toolbox coarse_search_angle_offset          # 0.175
ros2 param get /slam_toolbox max_laser_range                     # 5.0
```

If `use_scan_matching` reads `true`, stop. The wrong file landed and the whole
day is void. This is the §17.32 and §17.33 failure and it has cost this project
two sessions already.

### 4.2 The drive

1. **STOP MAP** if anything is running, and discard it.
2. Park on the physical zero mark. **ZERO** (two taps, must precede MAP).
3. **MAP**, then **VIEW**, and keep VIEW open for the entire run. A fold is
   visible while it happens.
4. Drive a closed loop of **8 m total path**, nose leading, 0.5 to 1.5 m
   off the walls, slow, one direction, **rolling through every corner**. Do not
   stop and rotate. Do not exceed 10 m; that is the ceiling, not a target.
5. Close the loop back on the zero mark.
6. **MAP again to stop.** This is the only action that saves the map. A
   `systemctl restart`, a reboot or a crash loses it entirely.

### 4.3 Predictions, registered before the drive

Fill the right column in after, not before. A prediction that cannot fail is
worth nothing.

| Quantity | Gate | Predicted | Basis | Measured |
|---|---|---|---|---|
| Verdict | not `FOLDED` | not FOLDED | the correction mechanism that folds maps measured zero events over 698 s | |
| Doubled walls | < 1.0 % | < 1.0 % | doubled walls are the geometry a false correction leaves behind; there are no corrections | |
| Unknown cells | < 50 % | 35 to 50 % | rolling turns gave 88 % of perimeter coverage in 18 % of the time; previous runs sat at 63 to 87 % using a procedure that discarded its own corner observations | |
| Return to mark | < 0.15 m | 0.088 to 0.120 m | the measured 1.1 to 1.5 % band applied to an 8 m path, with no loop-closure help assumed | |
| Path driven | ≤ 10 m | 8 m | the gate divided by the worst measured drift rate | |

The return-to-mark prediction is the tight one. If it comes in above 0.15 m,
check the path length first before touching any parameter.

### 4.4 Grade it, and be willing to throw it away

```bash
python3 ~/tools/map_integrity.py ~/aislebot_logs/run_<TS>.pgm ~/aislebot_logs/run_<TS>.yaml
```

Accept only on all four. If it fails, drive again. Three attempts are budgeted
and a bad map poisons every block after it.

Once accepted:

```bash
mkdir -p ~/maps
cp ~/aislebot_logs/run_<TS>.pgm  ~/maps/lab_commission_v1.pgm
cp ~/aislebot_logs/run_<TS>.yaml ~/maps/lab_commission_v1.yaml
sed -i 's|^image:.*|image: lab_commission_v1.pgm|' ~/maps/lab_commission_v1.yaml
cat ~/maps/lab_commission_v1.yaml
sha256sum ~/maps/lab_commission_v1.*
```

**Photograph the robot on the zero mark and tape-measure its offset from two
walls.** Thirty seconds now, unrecoverable later, and it is the ground truth
behind every claim in Blocks B, C and D.

### 4.5 If G4 fails all three attempts

Do not spend the afternoon on it. Descend the ladder in §8 and run Block D,
which needs no map, plus the whole Phase 2 track in §6. The day still produces
material.

---

## 5. Blocks B and C: G5 and G6, the first saved-map navigation

### 5.1 G5, AMCL's first breath

This code has never executed once. Expect a fault on the first launch. Both
known blockers are already cleared (§2), so anything that goes wrong is new
information rather than a known trap.

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml   # confirm the class exists

ros2 launch mecanum_navigation navigation.launch.py \
    map:=/home/aritra/maps/lab_commission_v1.yaml 2>&1 | tee ~/aislebot_logs/amcl_first.log
```

Wait for `Managed nodes are active`. Park on the zero mark, set the initial
pose, then drive **manually** for two minutes while watching:

```bash
ros2 topic hz /amcl_pose
ros2 run tf2_ros tf2_echo map base_link
```

**Pass:** the covariance diagonal shrinks as the robot drives and sees walls,
and `map->base_link` stays smooth. AMCL corrections should be centimetres,
because it corrects the robot inside a fixed map rather than rebuilding the
map around a drifting robot.

This is also the comparison the report wants: the same physical drive, once
under live SLAM and once under AMCL on the saved map, return-to-mark measured
both times.

### 5.2 One parameter to change before G6

```bash
ros2 param get /controller_server goal_checker.yaw_goal_tolerance   # 0.05 rad = 2.9 deg
ros2 param set /controller_server goal_checker.yaw_goal_tolerance 0.12
```

0.05 rad asks the controller to settle the nose inside 2.9° against a gate of
10°. It is achievable but it costs time on every single goal, and goal time is
what the 27 August attempts were fighting. 0.12 rad is 6.9°, inside the gate
with 3° of margin. Leave `xy_goal_tolerance` at 0.05; that one is already
right and 0.12 would leave only 3 cm against the 0.15 m gate.

### 5.3 G6, five tapped goals

**Do not drag.** Dragging sets a goal *orientation*, which costs roughly 50
extra seconds of nose-turning before the goal may be declared reached.

Mark each tapped point on the floor with tape *before* sending it, then
tape-measure where the robot actually stops.

| # | Tapped (m) | Reached (m) | Error (m) | Heading err | Time | Result |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

**Pass: 5 of 5 `Goal succeeded`, every one within 0.15 m.** That table is a
figure in the report exactly as it stands.

### 5.4 Block D: G7, named locations

The code is written and tested. This block is deploy, teach, power cycle,
recall.

```bash
# launch the dashboard knowing which map is loaded (this is the guard)
ros2 run mecanum_robot phone_dashboard --ros-args -p map_name:=lab_commission_v1
```

Drive to a spot, name it. Nothing is measured by hand. Teach three: `Home`,
`Aisle A`, `Staging`. Then:

```bash
cat ~/locations.json          # three rows, and "map": "lab_commission_v1"
```

**Full power cycle.** Not a service restart, a real power cycle, because that
is what proves the coordinate frame is fixed rather than an artefact of one
session. Bring everything back up, recall all three, tape-measure each.

**Pass: 3 of 3 recalled within 0.15 m after a power cycle.**

The library refuses to teach when `map->base_link` is absent, and refuses to
recall when a different map is loaded. Both refusals surface in the dashboard
notice line rather than failing quietly.

---

## 6. The Phase 2 track, which fits in the gaps

None of this needs a dedicated block. Run it while the stack is already up.

**Plant identification: done and verified, 14 Sep 2026.** τ ≈ 0.09 s
against the assumed 0.18 s. The two `Kp` candidates it implies (22, 26)
were swept closed-loop against the shipped 45 and both lost on overshoot,
16 of 16 setpoint-motor rows. `Kp` stays at 45; nothing gets flashed.
Objective 1.3 closes as *confirmed*. Full derivation, the reasoning for
why the open-loop prediction failed, and a tool bug found and fixed in
the same session (`settle(s)` printed `none` for every row of the sweep,
unrelated to the gains): `PID_Calibration.md` §5.

**The slip residual, free from drives already happening.** The residual
derived from the asymmetric geometry is an instrument nobody has pointed at
anything yet:

$$
s = \omega_{FR} + 1.142656\,\omega_{FL} - 1.142656\,\omega_{RR} - \omega_{RL}
$$

Run `wheel_forensics.py --csv` over every drive today. Per-wheel slip on a
non-collinear layout is Gap 3 in the report and nothing has been measured on
it. The data costs nothing extra; it is the same encoder stream the drives
produce anyway.

**A second phantom-yaw replication.** The result currently rests on two runs.
Any drive recorded on video today, measured against the floor grout with the
existing validated method, makes it three and moves the claim from two-run to
properly reproduced.

**What this does not do.** It does not fuse anything. Without an IMU there is
no second heading source, so Phase 2's actual deliverable stays open. Order
the sensor this week; it is the single highest-value purchase in the project
and §4.6.4 of the report gives a specific number to test it against.

---

## 7. Time budget for the lab day

| Time | Block | Slack |
|---|---|---|
| 09:30 to 10:15 | Deploy, hash, verify against the live node | the verify is not optional |
| 10:15 to 10:30 | Plant identification bench run | Phase 2 |
| 10:30 to 11:10 | **G4 attempt 1**: drive 8 to 10 m, grade it | |
| 11:10 to 11:50 | G4 attempt 2, if needed | |
| 11:50 to 12:30 | G4 attempt 3, if needed | after this, descend the ladder |
| 12:30 to 13:15 | Break, and promote the accepted map | |
| 13:15 to 14:00 | **G5**: AMCL first launch, manual drive, covariance | first ever execution |
| 14:00 to 14:45 | **G6**: five tapped goals, tape-measured | |
| 14:45 to 15:30 | **G7**: teach three, power cycle, recall three | |
| 15:30 to 16:15 | Capture: run bundles, wheel CSVs, map integrity report, photographs | this is the report material |

Two map retries are absorbed inside that. If the first map passes, the whole
afternoon gains 80 minutes and G7 stops being the thing that gets cut.

---

## 8. Fallback ladder

If a block fails, do not spend the next block on it. Descend one rung.

| Rung | What can still be demonstrated on 23 Sep | Needs |
|---|---|---|
| **A** | Name a location, robot drives there, on a saved map, after a power cycle | G4, G5, G6, G7 |
| **B** | Tap a point on a saved map, robot drives there | G4, G5, G6 |
| **C** | Tap a point during a live mapping session, robot drives there | **Already banked**: two goals, 25.9 s and 21.0 s, 27 August |
| **D** | Scripted goal via `nav_goal.py` | Already works |

Rung C is in hand whatever happens today, which is exactly why the day can be
spent going for A without risking having nothing to show. If rung C is what
gets demonstrated, say the caveat out loud: the robot completed its goals, and
it did not return to the origin, because the map frame was still moving. That
is a better thing to say than to hide, and it is true.

---

## 9. What each block turns into in the report

The point of the day is not the gates. It is what the gates let the report
claim.

| Block | Report change if it passes |
|---|---|
| G4 | §3.2 objective 1.8 flips from **Not achieved** to achieved. §4.6.5 stops being "why no map has been accepted" and becomes the accepted map with its four numbers. Figure 13 gains a fourth panel that is not sparse |
| G5 | §3.2 objective 1.6's dependency is partly answered, and the claim "localisation against a saved map has never run" is withdrawn from §3.3. Gate G5 in Appendix A flips from **Never executed** |
| G6 | Claim 14 in §3.3 upgrades from "works on a live map" to "works on a saved map", which is the claim that matters. The five-goal table becomes a figure |
| G7 | Phase 5 of the roadmap figure stops being 0 %. A named-location recall after a power cycle is the single most product-like thing this project can show a committee |
| Phase 2 track | Objective 1.3 closes. Gap 3 gains its first measurement. The phantom-yaw claim moves from two runs to three |

Update the report the same evening, while the numbers are still in hand and
before the next session's memory of them softens. The draft to edit is
`docs/aps_report/APS_Report_Draft_v2.md`.

---

## 10. The standing rules, because they were all earned here

1. **One parameter at a time.** Six at once cost three sessions.
2. **Write the prediction down before the test.** §4.3 is already filled in.
3. **Verify against the live node, never the file.**
4. **Hash every file on arrival, per file, never per batch.**
5. **Never fix an axis complaint in the dashboard.** That is what hid a real
   frame fault for two weeks.
6. **A symptom that changes character but does not disappear means there is a
   second fault.** It has happened twice and cost days both times.
