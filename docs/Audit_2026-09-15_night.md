# Where this project actually stands, 15 Sep 2026, night

Eight days to APS. 23 Sep, 14:30 to 15:30.

This is an audit, not a status report, so it leads with what is wrong.

---

## 1. The three things to fix first tomorrow

**The revert is not live on the robot.** `~/ros2_ws/slam_nodom.yaml` has the
correct hash (`a6b75d36…`, `use_scan_matching: false`) but `ros2 param get`
still returns `True` because MAP was never restarted. slam_toolbox reads
that file only at launch. Anyone who drives before restarting MAP is driving
Stage H again and will not know it. This is the §17.32 failure mode with the
direction reversed: the file reached the robot, and the robot is not running
it.

**Phase 2 did not close.** That was Job 2 of the session and it was never
started. It is still one `ls` and two tool invocations. The two 3 Sep
telemetry CSVs that produced the phantom-yaw observation are on the Pi and
not in the repo, so the elimination argument in `Phase2_Without_IMU.md`
§5.4.1 is currently inferred from four different drives rather than tested
on the runs that produced the anomaly. Nothing else in the project closes a
whole phase for that little work.

**There are two divergent report drafts and neither knows about the other.**
`APS_Report_Draft.md` was last edited 12 Sep, is what `README.md` says to
edit, is what the `.docx` builds from, and carries all 30 figures.
`APS_Report_Draft_v2.md` was last edited 14 Sep, is newer, and is
restructured around all three objectives, adding the worker-fatigue
framework that the first draft does not cover. The README's file table does
not mention v2 at all.

Eight days out, that is the single largest schedule risk in the project, and
it is a decision rather than a task. Deciding it wrong costs a day of
merging; deciding it late costs more.

---

## 2. What today actually produced

Six drive runs in the morning, one in the evening, and the evening one is
the valuable one.

**Stage H is a clean, decisively scored negative result.** Predictions
written before the drive, unconditional revert triggers, three of four
fired, and the revert is already committed with the reasoning recorded in
the config file itself. That is the shape of result an examiner respects,
and it is worth more to the report than a tuned parameter would have been.

The numbers, from `docs/evidence/stageH_15sep/README.md`:

| | matching OFF | matching ON | |
|---|---|---|---|
| Closure at mark | 6.4 mm | 206.7 mm | **32× worse** |
| `map_integrity` | SUSPECT | FOLDED | |
| Doubled walls | 0.8% | 6.6% | 8× worse |
| Occupied wall length | 26.1 m | 72.5 m | 2.8× more |

Two 3.16 m single circles, 1% apart in path length, same day, same RAW gate,
same config, one value changed. Plus a within-run control that kills the
obvious objection: the matching-on run's own odometry closed at
16.2 mm, 0.51% of path, so its odometry was healthy and the matcher is what
degraded it.

**The mechanism, which is better than the verdict.** All seventeen
corrections fired at a mean odometry cadence of 0.183 m with a 1 cm spread
across the whole run. They track pose-graph node creation, not scan
disagreement. §17.40 saw this metronome and it has now survived three
parameter sets and a range cap, which is the strongest available argument
that this was never a tuning problem.

It also explains the zero loop closures, and that explanation is new. A
closure arrives off-cadence. Not one of these did. And the pose graph was
confirmed alive before the drive, publisher count 1, so the previous
suspicion that matching-off suppressed graph construction is no longer
needed to explain closure never firing. Under matching-on the graph exists,
the matcher runs, and closure still does not happen on a circle that returns
to its own start.

**A third phantom-yaw data point, which overturned yesterday's reading.**
Distance is now the tightest of four proportionality models at 1.60× spread;
constant-per-run went from best to worst at 2.58×. §17.56 and tonight's run
turned through 364.5° and 361.7° and produced heading error differing by
2.6×, which is close to a direct refutation of any rotation-scaled
mechanism. The write-up in `DeepSeek_Response.md` §2 is marked superseded in
place rather than edited away.

**Three documentation faults of the same class, found by running things.**
`Important_Commands.md` §8 told the operator that a correct re-zero reads
−90.000°; it reads 0.000 and has since the 27 Aug frame fix. The dashboard
sends the entire mapping launch tree's stdout and stderr to `DEVNULL`, so
the handoff's instruction to watch slam_toolbox's log for closure messages
was unexecutable on the path the operator actually uses. And
`verify_live_config.sh` still expected Stage G, so it would have printed DO
NOT DRIVE on a correct Stage H deploy.

Yesterday found two more of these in tool interfaces. That is five in two
days. The pattern is worth naming: **a documented expected output is exactly
as stale-able as a documented command, and neither is evidence of anything
until someone runs it.**

**One blind spot found by reading source rather than driving.** Telemetry
publishes `actual_velocity`, the EMA-filtered one, and `odometry_publisher`
integrates those 20 Hz samples rectangularly against a ROS-side `dt`. The
exact unfiltered count integral, `position_rad`, exists on the ESP32 and is
not what pose is built from. `wheel_forensics.py` cannot see a bias
introduced there, because both sides of its comparison consume the same
already-filtered quantity. Its 0.0001 m agreement proves
`odometry_publisher` integrates faithfully, not that what it was handed is
what the wheels did. `Phase2_Without_IMU.md` §5.4.1's list of surviving
error classes needs a third entry.

Tonight's distance-proportional finding makes this less likely to be the
phantom yaw's cause than it looked yesterday, but it is still an unexamined
gap in an argument the report leans on.

---

## 3. Gates, honestly

| Gate | State | Change today |
|---|---|---|
| G1 file/param verification | **Passed** | reinforced; the verifier now also checks the pose graph |
| G2 correction magnitude | **Passed** on a short test | unchanged |
| G3 control loop ≥ 15 Hz | **Open**, 7.5 to 13.7 Hz | untouched |
| G4 map quality | **One of four, once** | no improvement; unknown still 72.6% against a 50% gate |
| G5 AMCL on a saved map | **Never executed** | still never executed |
| G6 five tapped goals | **Partially met** | untouched |
| G7 three taught locations | **Never executed** | still never executed |

Two gates have never been run on hardware at all, eight days out. G5's code
is written and has never executed. That is the largest technical gap, and it
is larger than anything scan matching was going to fix.

G4 has not moved all day. Six morning runs settled the gate question (RAW
wins) without moving unknown %, and tonight's run moved it only by smearing
walls. The bounding-box unknown metric remains the thing that fails, and the
outside review's point that it measures the room's shape rather than the
drive's quality is the correct diagnosis. Restating that gate honestly in
the report, before the exam, is cheaper and more defensible than trying to
pass it in a week.

---

## 4. The framing problem, which is now unavoidable

With matching reverted off, `map→odom` is constant, no loop closure has ever
fired on this robot, and the pose the map is built on is pure wheel
odometry. Calling that SLAM without qualification, to an examiner who then
discovers the front end is disabled, is the worst version of this
conversation.

The good news is that the honest description is now a stronger claim than
the vague one, because it is backed by a measurement taken today. Something
close to:

> The system runs a pose-graph SLAM back end with the front-end scan matcher
> deliberately disabled, because the front end was measured on this platform
> to degrade pose by a factor of 32 on an otherwise identical trajectory.
> The map is built from LiDAR returns under wheel-odometry pose. Loop
> closure is configured, the pose graph is confirmed to be constructed, and
> closure has never been observed to fire; the corrections the matcher did
> produce were shown to track pose-graph node creation on a fixed 0.183 m
> odometry cadence rather than scan disagreement, which is why.

That is a year-one result. It says what runs, what does not, and why, with
numbers behind each clause. It is considerably better than claiming a
working SLAM stack and being asked to demonstrate loop closure.

---

## 5. What I would do with eight days

Ordered by value per hour, not by interest.

**Tomorrow, no driving needed.** Close Phase 2 with the two 3 Sep CSVs.
Decide the report fork. Restart MAP so the revert is live. Retrieve
`rosout_stageH.txt` while the run is fresh, since it is the one artifact
from tonight that is still only on the Pi.

**Then the thing that is actually missing: G5.** First AMCL bringup on a
saved map. The code exists and has never run. A localisation stack that
reaches `active` and converges on a map you already have is a demonstrable
result; an untested one is a liability if anyone asks.

**Then the report.** Today's material is the best evidence in the project
and none of it is in the draft yet: the 32× A/B, the metronome, the
never-fires-closure result, the three-point phantom-yaw table, and the
honest SLAM framing above.

**Only if all of that lands:** the perimeter A/B with matching on and a
screen recording. It is the experiment that was designed and it is
genuinely unrun. But the metronome is geometry-independent by construction,
so predict in advance that it will look the same, and treat the drive as a
falsification attempt rather than a hope.

**Not worth the time:** more circles, the LiDAR gate, scan-matcher search
tuning, a frame refactor, an IMU before the exam. All either settled or too
expensive to land safely in eight days.

---

## 6. What is genuinely good here

Worth saying, because an audit that only lists faults misrepresents the
project.

The instrumentation discipline is the strongest part of this work and it is
what produced today's results. Predictions registered before drives. A
verifier that asks live nodes instead of files. `--selftest` on a tool
before its output is believed. Validation frames with known answers before
photogrammetry is trusted. Five stale-documentation faults found in two days
because things got run rather than cited.

Most year-one robotics projects cannot tell you why their estimator is
wrong. This one can, with a cadence measurement, a controlled A/B, and a
within-run control. That is the contribution, and the report should lead
with it rather than with the 1.9 mm closure that looks better and means
less.
