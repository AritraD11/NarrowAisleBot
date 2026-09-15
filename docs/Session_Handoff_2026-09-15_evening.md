# Session handoff, 15 Sep 2026 evening

**Supersedes `Session_Handoff_2026-09-15.md` (mid-morning), which is now
stale.** Eight days to APS on 23 Sep, 14:30 to 15:30.

The operator's call at the end of this session, recorded as a decision rather
than as a conclusion drawn from data: **characterisation is done. The remaining
time goes into making SLAM and navigation actually work.** Stage H below turns
scan matching back on. Phase 2 closes next session.

---

## 0. THE ONE THING NOT TO SKIP

`system/slam_nodom_stageB.yaml` now has **`use_scan_matching: true`** (Stage H).
It has not been deployed. Until it lands on the Pi, the robot is still running
Stage G with matching off.

```bash
# expected sha256 of system/slam_nodom_stageB.yaml after Stage H
8c04491e6251b7a7ac4c17a3054199cdcf8c20210108f4d126e8a758549e4c02
```

Destination on the Pi is **`~/ros2_ws/slam_nodom.yaml`**, not
`slam_nodom_stageB.yaml`. `mapping_full.launch.py` loads the former. Land it
under the wrong name and the old file keeps running, silently. This has bitten
before.

Transfer path: Windows PC, `for scp download` folder, `scp` to the Pi at
`10.42.0.1`. Hash both ends, per file. Then verify against the **live node**,
never the YAML:

```bash
ros2 param get /slam_toolbox use_scan_matching     # expect True
ros2 param get /slam_toolbox do_loop_closing       # expect True
ros2 param get /slam_toolbox max_laser_range       # expect 5.0
```

---

## 1. What happened this session

Six drive runs, a settled LiDAR configuration, a closed Phase 2 gap, and two
documents that did not exist before.

**The LiDAR gate question is closed.** A controlled three-way A/B/C on an
identical trajectory, one variable changed: RAW wins outright. AISLE and STRICT
both tear the map into two disconnected free-space regions, which
`map_integrity.py` escalates to FOLDED. RAW does not have that defect at all.
Doubled walls does improve monotonically as the gate tightens (2.9 to 1.1 to
0.9%), but unknown cells barely moves across all three (73.0 / 74.6 / 75.9%), a
smaller spread than the run-to-run variance on nominally identical single-lap
drives (77.6 to 84.6%). Tightening the gate buys nothing on the gate that is
failing and risks the map. Full detail:
`docs/evidence/circular_loop_15sep/README.md`.

**Gap 3 closed, with no new driving.** `wheel_forensics.py` run over four of
today's telemetry CSVs. Slip residual median while moving is 0.035 rad/s, about
2.7% of drive speed, with zero episodes above threshold across all four runs
including a deliberately irregular one. Physical wheel slip is small and
bounded. Details in section 3.

**Two documentation bugs of the same class found and fixed.** `map_integrity.py`
takes one positional `.pgm`, not the two arguments `Phase_234_Push.md` §4.1
documents. `wheel_forensics.py` takes a positional run and writes `--csv` as
output, not the input form `Phase2_Without_IMU.md` §5.4 documented. Both docs
described interfaces the tools do not have. Both corrected in place. Worth
noticing as a pattern: a documented command that has never been run is not
evidence of anything.

**`docs/DeepSeek_Brief.md`** written for an outside model, carrying the open
self-criticism that does not belong in a status doc. It is also the best single
summary of what is actually uncertain here.

---

## 2. Stage H: scan matching goes back on

### What is not being reopened

Stage G's prediction was tested and it landed. Two runs on 3 Sep (698 s,
18.5 m, different route geometries) and six more today returned `map->odom`
corrections of **exactly zero, every sample**. The sequential front end was the
whole observed fault. That is settled and Stage H does not relitigate it.

### What is actually being tested

**The matcher has never run with the 5 m cap.** Stage G changed
`use_scan_matching` and `max_laser_range` in one drive, deliberately and with
stated reasons, but the consequence is that every measurement of matcher
behaviour in this project's history was taken at 10 m or 12 m. The cap is the
single largest change to what the matcher is fed that has ever been made here,
and its effect on matching is unmeasured. The config's own note under
`loop_match_minimum_response_*` says exactly this and was written before anyone
intended to act on it.

Three things changed since the matcher was last scored:

1. `max_laser_range` 10.0 to 5.0. The long, weak, flickering returns carrying
   error of the same order as the fault being chased are no longer admitted.
2. The quality gate settled on RAW, measured rather than assumed. The input is
   now a known quantity instead of whatever the panel happened to be set to.
3. The odometry prior is measured far better than when the search windows were
   widened: 9.526 m closing to 1.9 mm, with the offline reconstruction
   confirming the integration is faithful. A tight window over a good prior is
   the regime matching is supposed to work in, and it has never been tested
   here.

And the reason it cannot wait: with matching off there is no loop closure, so
the map cannot correct itself, and G5's AMCL would localise against a
dead-reckoned map carrying every accumulated error with no mechanism to remove
it.

### The risk

This map folded roughly 70 times under matching. That failure mode is being
deliberately re-admitted. The revert is one line.

### Pre-committed, written before the drive

**REVERT on any one of:**

- any single-step correction >= 0.15 m (the window half-width saturating, the
  exact §17.40 signature, meaning the tight window is still the wrong lever)
- `map_integrity.py` returns FOLDED
- return to mark > 0.15 m
- visible map tearing during the drive

**KEEP, Stage H succeeds, if all of:**

- corrections appear but stay small and frequent, tens of mm, well inside the
  0.15 m half-width
- **at least one loop closure actually fires.** This has never been observed on
  this robot and is the single most valuable thing the drive can produce
- closure at the mark <= 9.9 cm, the matching-off baseline
- doubled walls < 1.0%, verdict not FOLDED
- unknown % roughly unchanged, since matching changes where scans are drawn,
  not how many cells they paint

### Route: not the circle

**Do not test this on the 1 m circle.** §17.44 flagged tight-circle geometry as
degenerate for scan matching, and a circle shows the same walls from
continuously rotating vantage points.

Drive **§17.56's 12.04 m out-and-back perimeter** instead. It already has a
matching-off baseline on the same config era (9.9 cm closure over 12.04 m,
0.83% of path, heading -4.49 deg, zero corrections), it is structurally
different from a circle, and at 3.66 m from the mark it travels far enough to
reach `loop_match_minimum_chain_size: 8`, which needs about 1.6 m.

That gives a clean A/B on one route with one variable changed.

### How to tell whether loop closure fired

This is the thing the brief flagged as never verified, so check it directly
rather than inferring it.

- Watch `slam_toolbox`'s own log during the drive for loop closure messages.
- After the drive, the pose CSV carries `corr_x`, `corr_y`, `corr_yaw_deg`
  columns. With matching on these stop being identically zero. A **loop
  closure** shows as a step change, distinct from the small continuous
  corrections of sequential matching. Both being present is the success case.

---

## 3. Phase 2: Gap 3 is closed, one step still owed

`docs/evidence/gap3_slip_residual/` and `Phase2_Without_IMU.md` §5.4.1.

| Run | Trajectory | Median (moving) | p95 | Max | Episodes > 0.5 rad/s |
|---|---|---|---|---|---|
| `_140253` | wobbled, 1 lap | 0.0392 | 0.1244 | 0.3541 | **0** |
| `_154615` | 1 m circle, 3 laps, RAW | 0.0356 | 0.1123 | 0.2885 | **0** |
| `_164745` | same, AISLE | 0.0353 | 0.1140 | 0.2544 | **0** |
| `_172133` | same, STRICT | 0.0352 | 0.1113 | 0.2722 | **0** |

Physical slip is small and bounded, and stable across trajectory type. The
tool passed `--selftest` first (residual zero to 7.18e-15 over 20000 random
rigid twists), so the instrument was validated before the result was believed.

**The second finding, which was not what the run was for.** The same tool
re-integrates the recorded wheel velocities offline and compares against what
`odometry_publisher` published. Final divergence is 0.0000 to 0.0001 m on all
four runs. The integration is faithful. Nothing in this repo had ever checked
that.

**What the two do together.** On `_154615` the wheels, odom and SLAM all report
the robot finishing at (-0.002, -0.001) with yaw -0.02 to -0.03 deg. The
operator's protractor on that same run read about -3 deg. Three estimates agree
with each other because they consume the same wheel data, and all three
disagree with the floor. The residual eliminates significant physical slip. The
offline reconstruction eliminates an integration bug. What survives is the
error class the tool's own docstring names as invisible to it: encoder or
wheel-radius scale error, or a rigid-consistent slip mode where all four wheels
slip together. Both are structurally undetectable by every instrument fitted.

**This is a better IMU argument than the error budget in §3, and a different
one.** §3 argues from a budget that inertial sensing addresses a non-binding
term at 5 m. This argues from elimination: the wheel-only instrument set has a
blind spot, its extent is now bounded by measurement, and closing it needs
external ground truth or an independent heading source. That is the direct
answer to the phase deliverable's third clause, *"an explicit account of which
sensors are required,"* and it is measured rather than argued.

**Still owed, and it is one command.** These four runs are from today. The
phantom-yaw observation is from 3 Sep (§17.55, §17.56) and those CSVs are on
the Pi, not in the repo. Pull them and run the same tool:

```bash
ls ~/aislebot_logs/run_20260903_162401* ~/aislebot_logs/run_20260903_174352*
python3 tools/wheel_forensics.py run_20260903_162401.csv
python3 tools/wheel_forensics.py run_20260903_174352.csv
```

If wheels-vs-odom divergence is near zero on those too, the elimination is
tested on the runs that actually produced the anomaly instead of inferred from
different drives, and **Phase 2 closes.**

---

## 4. Repo state

Branch `claude/aps-report-draft-2nywbq`, PR #14 (draft, open). Working tree
clean, everything pushed.

New or changed this session:

- `docs/evidence/circular_loop_15sep/`, six runs, all raw data, videos, pose
  CSVs, motor CSVs, maps, `map_integrity.py` verdicts, the three-way gate
  comparison
- `docs/evidence/gap3_slip_residual/`, Gap 3, four runs, JSON and full output
- `docs/DeepSeek_Brief.md`, outside-opinion brief
- `docs/Project_Status.md`, living status, flowchart, chart, evidence index
- `docs/X4Pro_Datasheet_Findings.md`, the vendor spec correction
- `docs/Phase2_Without_IMU.md` §5.2.1 and §5.4.1: range envelope, Gap 3
- `system/slam_nodom_stageB.yaml`, **Stage H, not yet deployed**
- `tools/drive_circle.py`, written, never run on hardware

---

## 5. What the next session owes, in order

1. **Deploy Stage H and verify live.** Section 0. Nothing else until
   `ros2 param get` confirms it on the running node.
2. **Drive the §17.56 perimeter route.** Fresh ZERO twice, fresh MAP, RAW gate.
   Write the prediction down first; it is already written in section 2, so read
   it aloud and drive.
3. **Score it against the pre-committed criteria.** Keep or revert. Either
   outcome is a result worth having, and the revert is one line.
4. **Pull the two 3 Sep CSVs and close Phase 2.** Section 3, one command each.
5. Only after 1 to 4: G5, the first AMCL bringup on a saved map. Code is ready
   and has never been executed on hardware.

Not on this list, deliberately: more laps of the circle for G4 coverage. That
plan was correct under Stage G and is superseded by Stage H. Re-derive the
coverage question after matching is scored, because a map built with loop
closure is not the same map.

---

## 6. What not to re-litigate

- **The LiDAR gate.** RAW, settled by measurement three ways today. Do not
  re-run AISLE or STRICT comparisons.
- **Whether the front end caused the jumps.** Yes, measured, eight runs of zero
  corrections. Stage H tests a different question.
- **Scan-matcher search parameter tuning.** Five sessions, correction totals
  invariant to 2% across three parameter sets. Do not resume this. Stage H
  changes the input, not the search.
- **Bigger circles.** The map bounding box is identical across every run
  because the 5 m range already reaches the room's walls from the zero mark.
- **Phase 2's ceiling and the IMU decision.** Decided in
  `Phase2_Without_IMU.md`, and strengthened today by §5.4.1. An IMU is the
  right next purchase and is not what closes Phase 2.
- **The dashboard.** Frozen. Bug fixes only. See `CLAUDE.md` for why one
  apostrophe took the whole page down and what testing it actually requires.

---

## 7. Standing discipline

In `CLAUDE.md`, loaded automatically. The two that mattered most today:

**Verify against the live node, never the YAML.** A file in git is not a file on
the robot.

**Validate the instrument before believing its result.** `wheel_forensics.py`
`--selftest` passed before any of section 3 was written down. The photogrammetry
in §17.55 was only trusted after it recovered a known 28 degree rotation. A
number from an unvalidated tool is not a measurement.
