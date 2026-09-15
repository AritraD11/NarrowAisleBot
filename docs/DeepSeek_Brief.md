# Outside-opinion brief: NarrowAisleBot, September 2026

**Written 15 Sep 2026 for DeepSeek, or any model that has not seen this
repository.** It is self-contained. Every number in it is quoted from a
measurement recorded in the repo, and where a number is soft, thin or
contested that is said out loud next to it.

**APS (PhD comprehensive exam) is 23 Sep 2026, 14:30 to 15:30.** Eight days.
No parts can be ordered and arrive in time. The lab room is small and cannot
be made bigger.

---

## What I actually want from you

Not a review. A disagreement.

This project has been analysed heavily from the inside, and a second model
(ChatGPT) has already given a long opinion that largely agreed with the
internal conclusions. Agreement from a third direction would be pleasant and
nearly worthless. What is worth your time is the opposite:

1. **Find the assumption nobody has questioned.** Section 8 lists the ones I
   already suspect. The useful ones are the ones not on that list.
2. **Attack the no-IMU argument properly.** Section 3 is the load-bearing
   claim of the whole APS. It was written to be defended in a viva, which is
   exactly the condition under which motivated reasoning hides. Take the
   other side seriously.
3. **Say where the measurements do not support the conclusions drawn from
   them.** There are places in section 7 where I think this has already
   happened and the project has not noticed.
4. **Ignore the priority ordering if you think it is wrong.** Do not feel
   obliged to work inside the phase/gate structure. If the structure is the
   problem, say that.

If you conclude the current plan is basically right, say so briefly and spend
your effort on the parts you are least sure about instead. A confident
restatement of section 5 helps nobody.

---

## 1. The one-paragraph situation

A 45 kg four-wheel mecanum robot with an asymmetric wheelbase, driven by an
ESP32 running closed-loop motor PID, carrying one 2D triangulation LiDAR and
**no IMU**, is trying to pass a mapping acceptance gate (called G4) so that
autonomous navigation work can start. Motor control and wheel odometry both
work well. The SLAM front end (scan matching) was measured to make pose worse
than wheel odometry alone, so it was switched off on 3 Sep and has stayed off.
With it off the pose estimate is pure dead reckoning, and it closes a 9.5 m
three-lap circular drive to 1.9 mm. The map produced under that configuration
is geometrically sane but only covers about a quarter of its own bounding box,
and the coverage criterion is the one gate that keeps failing.

---

## 2. Hardware, exactly

| Item | Value | How it is known |
|---|---|---|
| Chassis | 4-wheel mecanum, **asymmetric wheelbase** | design |
| Outer lever arm `K_outer` | 0.5607 m | `mecanum_teleop_asymmetric.py` |
| Inner lever arm `K_inner` | 0.4907 m | same |
| Wheel radius | 0.0762 m | declared parameter |
| Footprint used by Nav2 | 1.12 x 0.48 m | tape-measured 8 Aug, corrected a wrong URDF |
| Mass | ~45 kg | weighed |
| Motor controller | ESP32, 100 Hz loop, PID + feedforward, `Kp=45 Ki=250` | `Kp` re-confirmed by closed-loop sweep 14 Sep |
| Encoders | front GTK08 **186264 CPR**, rear RMCS **93132 CPR** (exactly 2x apart) | firmware constant, hardware-verified |
| LiDAR | YDLIDAR X4 Pro, triangulation, rated 0.12 to 10 m | datasheet |
| Compute | Raspberry Pi 5, ROS 2 Jazzy, **no GPU** | |
| IMU | **none fitted** | this is the whole point of section 3 |

**Two LiDAR facts that surprise people:**

The scan head free-runs. `support_motor_dtr: false` means the driver never
commands motor speed, so the `frequency: 6.0` parameter in the config is inert.
Measured actual rate is **11.35 Hz**, stable to under 10% jitter. At
`sample_rate: 5` (5 kHz) that gives 5000/11.35 = 441 points per revolution,
and 430 were measured. The model checks out; the requested rate never did
anything.

A 90 degree rear wedge is permanently blanked. The robot's own mast sits inside
LiDAR range and would otherwise paint a phantom obstacle welded to the robot
frame, so `scan_relay.py` masks bearings -135 to -45 degrees to NaN.
**That removes 107 of about 430 beams, a quarter of every scan, permanently,
in a fixed body-relative direction.** This is real geometry, not a bug, and
software cannot recover those beams.

---

## 3. The claim everything rests on: closing Phase 2 with no IMU

This is the part I most want you to attack.

### The argument as the project states it

> The sensing question was narrowed this year from "add sensors" to a measured
> deficit. At the corridor scale this platform operates in, the binding error
> term is LiDAR precision, not odometry drift. An inertial sensor addresses the
> term that is not binding.

Supporting error budget, from `Phase2_Without_IMU.md` §3:

| Path or range | Wheel odometry drift over that path | LiDAR scatter at that range |
|---|---|---|
| 1.0 m | 11 to 15 mm | ~9 to 20 mm |
| 1.6 m | 18 to 24 mm | **22.8 mm, measured** |
| 3.0 m | 33 to 45 mm | ~60 to 80 mm |
| 5.0 m | 55 to 75 mm | ~100 to 222 mm |

Odometry drift rate comes from two measured runs: 0.229 m over ~18 m (1.27%)
and 0.257 m over 18.14 m (1.42%). The operating envelope for this APS is a 5 m
map. Inside it, the LiDAR term is the larger of the two and grows faster.

A second argument sits underneath: the platform **already carries an unused
second heading measurement**. The asymmetric wheelbase gives two independent
yaw estimates on different lever arms,

```
omega_outer = r (w_FR - w_RL) / (2 K_outer)
omega_inner = r (w_RR - w_FL) / (2 K_inner)
```

and the published yaw rate is their mean. Their difference is a slip residual.
The tool to compute it (`wheel_forensics.py`) exists and **has never once been
run against a campaign.** The argument is that adding a third heading source
while the second one sits unread is out of order.

### What the project admits it is not claiming

To its credit, the doc says plainly: the platform is not better off without an
IMU, fusion would reduce heading error (it cites roughly 88% heading-drift
reduction from the literature), an IMU should still be bought, and Phase 2
closes as *characterised* rather than *optimal*.

### Why I do not fully trust this argument, and neither should you

**It was constructed after the constraint existed.** No IMU was bought. Then a
document was written arguing an IMU is not what closes this phase. The
reasoning may well be correct. The order in which it was produced is exactly
the order that produces post-hoc justification, and the doc's own header says
it is "written to be defended in a review." Please pressure-test it as if a
hostile examiner were reading.

**The error budget compares two things that may not be comparable.** Odometry
drift is *cumulative and unbounded* in path length. LiDAR scatter is *bounded
and zero-mean per ray*, and it averages down over repeated observations of the
same wall. Putting them in one table as if 55 mm of accumulated dead-reckoning
error and 100 mm of per-ray scatter are the same kind of quantity may be a
category error. An occupancy grid integrates many noisy rays into one cell
estimate. Nothing integrates away a drift.

**The 5 m envelope is chosen, not given.** The claim "at the scale this robot
works in" is doing heavy lifting, and the scale was selected partly because the
room is small. A warehouse aisle, which is the actual application, is not 5 m.

**The strongest defence, and the one I actually believe:** with scan matching
off, there is no closed-loop correction of pose at all, so a heading error is
the error that never gets fixed. That argues *for* an IMU being urgent, not
against it. The doc reaches "not yet" rather than "not needed," and those are
different claims that partly blur together in the writing.

---

## 4. The anomaly I think is most interesting, and most under-exploited

**The odometry reports yaw rotation that physically did not happen.**

Measured twice by photogrammetry against world-static floor features (tile
grout lines, floor L-brackets), on two structurally different routes:

| Run | Odometry says | Floor says | Method validation on the same footage |
|---|---|---|---|
| 3 Sep, two circles, 723.8 deg commanded rotation | **-3.85 deg** | -0.03 deg | HUD -28.0 vs grout -27.07 (agrees to 1 deg) |
| 3 Sep, 12.04 m out-and-back, 364.5 deg rotation | **-4.49 deg** | +0.00 deg | HUD -19.4 vs grout -18.50 (agrees to 1 deg) |

The method was validated before its result was believed, and the first attempt
failed instructively: it measured the robot against a camera mounted on the
robot's own mast, which measures nothing. Redone against the floor it detects a
known 28 degree rotation correctly. Noise floor is 0.18 degrees against a
measured 2.4 px signal where 3.5 degrees would give 13 px, so the null result
is not a sensitivity failure.

**Why this matters more than the project has treated it.** The conclusion drawn
was "this makes the case for buying a gyro concrete." That is true but it is
the smaller half. The larger half: **a repeatable, same-sign, same-magnitude
error is the signature of a systematic term in the estimator, not of physical
slip.** Physical slip is not that consistent. A bug or a missing correction is.

Both replications are negative, roughly -4 degrees, on different routes. Nobody
has gone looking for the term. Here is where I would look, and I would like you
to tell me if this is wrong or if there is somewhere better:

The forward kinematics in `odometry_publisher.py` apply an empirical correction
to exactly one of three degrees of freedom:

```python
vx = (r/4) * (w_fr + w_fl + w_rr + w_rl)
vy = (r/4) * (w_fr - w_fl - w_rr + w_rl) * lateral_scale   # 0.92
wz = (r/4) * (w_fr/K_outer - w_fl/K_inner + w_rr/K_inner - w_rl/K_outer)
```

`lateral_scale = 0.92` was tape-derived on one floor to correct mecanum roller
scrub in the lateral direction. Roller scrub is a physical mechanism that does
not politely confine itself to `vy`. During a turn, and every drive in the G4
campaign is a continuous circle, the rollers scrub while the platform both
translates and rotates. `wz` carries no equivalent correction. Neither does
`vx`. **Is a single-axis empirical correction to a three-axis coupled slip
mechanism the source of a systematic yaw bias?** I do not know. It is testable
from data already on disk.

---

## 5. What was decided, and the evidence behind each decision

Listed so you can attack the reasoning rather than re-derive the history.

### 5.1 Scan matching was switched off (Stage G, 3 Sep)

`use_scan_matching: false` in slam_toolbox. Measured over the same 21.85 m
drive:

```
wheel odometry alone           0.229 m closure  (1.27%, on spec)
odometry + SLAM front end      0.706 m closure
the front end costs            0.477 m
```

Five earlier sessions of matcher tuning never reached the 0.15 m gate; the
cumulative-correction total was invariant to 2% across three different
parameter sets (2.80 / 2.85 / 2.86 m), which is the signature of a lever that
is not connected to the outcome.

After the change, across two runs totalling 698 s and 18.5 m on different route
geometries: **`map->odom` correction was exactly 0.000000, zero events.** That
has held on every run since, including all six on 15 Sep.

**The honest caveat, which the repo states less sharply than it should.** Of
course corrections went to zero. Disabling the correction mechanism produces
zero corrections tautologically. The real question is whether the *map* got
better, and the answer there is yes but partial: wall doubling improved, the
roughly 70 observed map foldings stopped, and closure improved. Still, what is
running now is **not really SLAM. It is mapping with dead-reckoned pose.**
Loop closure is configured and `do_loop_closing: true`, but zero corrections
across every run suggests loop closure is not firing either (the loop may be
too small to reach `loop_match_minimum_chain_size: 8`, which needs about 1.6 m
of travel). Nobody has verified whether loop closure can fire at all in this
configuration. **If you think calling this SLAM in a PhD viva is a problem,
say so directly.**

### 5.2 LiDAR range capped at 5 m for SLAM, driver left at 10 m

`max_laser_range: 5.0` in slam_toolbox, `range_max: 10.0` in the driver,
deliberately different so the cut is policy at the consumer and the data
survives for A/B comparison. Median scan range in this lab is 1.6 m, and 94.7%
of returns fall inside 5 m.

**Known unresolved inconsistency:** seven consumers disagree about the cap.
Costmaps mark obstacles to 8 m and raytrace-clear to 9 m using rays slam_toolbox
refuses to match beyond 5 m. Nothing errors. The planner plans against evidence
the mapper already judged untrustworthy.

### 5.3 The LiDAR quality gate is set to RAW

A controlled three-way A/B/C was run on 15 Sep with the same trajectory, same
speed, same three laps, one variable changed:

| | RAW | AISLE (2-of-3 persistence) | STRICT (3-of-3, 4 m cap) |
|---|---|---|---|
| map_integrity verdict | SUSPECT | **FOLDED** | **FOLDED** |
| Doubled walls (gate <1.0%) | 2.9% fail | 1.1% | 0.9% pass |
| Free space regions | 1 | **2 disconnected** | **2 disconnected** |
| Unknown cells (gate <50%) | 73.0% | 74.6% | 75.9% |
| Closure | 1.9 mm | 2.5 mm | 2.7 mm |

Tightening the gate improves wall cleanliness monotonically and buys
essentially no coverage, while tearing the map into disconnected free-space
regions, which the integrity checker treats as making the map unusable for
localisation. RAW stands.

The mechanism: an occupancy grid gets occupied evidence at a beam's return
**and free-space evidence along the beam's path**. Every beam a filter drops is
a beam that no longer clears a cell. With `invalid_range_is_inf: false`, a beam
that returns nothing clears nothing at all.

---

## 6. The blocker: coverage, and only coverage

G4 acceptance is four criteria. Current state after the best run:

| Criterion | Threshold | Best measured | Status |
|---|---|---|---|
| Verdict | not FOLDED | SUSPECT | acceptable |
| Return to mark | < 0.15 m | **1.9 mm** | passes by 80x |
| Doubled walls | < 1.0% | 0.7 to 2.9% depending on run | borderline |
| **Unknown cells** | **< 50%** | **73.0%** | **fails, every run** |

Six runs on 15 Sep gave unknown percentages of 77.6, 84.6, 78.3, 73.0, 74.6 and
75.9. The spread across three deliberately different gate settings (73.0 to
75.9) is *smaller* than the run-to-run spread on nominally identical single-lap
runs (77.6 to 84.6). Gate choice is not the lever. More laps might be.

**A ray-cast ceiling was computed** from the 75 distinct path pixels of one
run, 720 rays each, 5 m range, stopping at known occupied cells: 73.5% of the
grid has line of sight from the driven path, so the theoretical floor from this
exact circle with unlimited repetition is about 26.5% unknown. The caveat is
stated in the source and matters: the ray-cast treats unknown cells as
transparent, so it is an optimistic ceiling rather than a forecast.

Three laps under RAW reached 73.0%. There is headroom before the floor binds.
The next planned experiment is 5 or 6 laps of the same circle, nothing else
changed, to see whether unknown percentage keeps falling or plateaus.

**A question about the gate itself, which I think is legitimate and which the
project has flagged but not resolved.** Unknown percentage is computed over the
bounding box of everything observed. In a small room entered from one 1 m
circle, cells behind walls count against the number permanently. Part of that
73% measures the room's shape, not the drive's quality. Is a bounding-box
coverage fraction even the right acceptance criterion for a commissioning map?
If not, what is? The project's own position is that the honest move is to
restate the requirement against the physically achievable envelope and say so
in the report, rather than quietly relaxing the threshold.

---

## 7. Where I think the evidence does not support the conclusion

Flagged as open self-criticism. You may find more.

**7.1 Closure error on a closed circular path may be close to uninformative.**
Every G4 drive is a circle returning to its start. A systematic scale error on a
circle still closes: it just draws a circle of a different size. Several classes
of error cancel by symmetry on a symmetric closed loop. The 1.9 mm figure is an
*internal consistency* check on the estimator, not a measurement of whether the
robot physically came back. So the headline "0.02% of path" may be flattering
the estimator rather than measuring it.

**7.2 There is already a physical cross-check that disagrees, and it has not
been chased.** On run 4, internal yaw closure read **-0.03 deg** while the
operator's tape and protractor at the mark read **about -3 deg**. That is the
same magnitude as the phantom yaw in section 4 but with the disagreement in the
*opposite* direction: there, odometry over-reported rotation that did not
happen; here, odometry under-reported rotation that did. Two measurements,
opposite senses of error. Either one of them is wrong, or the error is not a
simple bias. **Nobody has resolved this**, and the tape-measured ground truth at
the mark has been an open item for over a week.

**7.3 The 50x improvement in closure has been accepted a bit easily.** The
historical band is 1.1 to 1.5% of path. Smooth circular drives produced 0.20%,
then 0.020%. The explanation offered is that continuous turning with no stops,
no in-place rotations and no strafe reversals is kinder to mecanum odometry.
That is plausible and probably partly true. It is also exactly what 7.1
predicts you would see if the metric had stopped being sensitive. Both
explanations fit the data. Only one has been written down.

**7.4 Half the scan does not return, and nobody has asked whether that is
normal.** Measured valid-beam rate is 47 to 65%. Measured flicker, meaning a
bearing that returns on some sweeps and not others while the robot is parked, is
75 to 86%. A quarter of that is the deliberate rear mask. The rest is not
explained. Is this normal for an X4 Pro in a small cluttered room, or is this
unit faulty, mis-mounted, mis-parameterised (`isSingleChannel: true`,
`intensity: false`, `sample_rate: 5`), or looking at surfaces below its
reflectivity threshold? The project has treated this as a fixed property of the
environment. **It has never been compared against another unit, another room, or
the vendor's own expected figure.** If half the beams are recoverable, the
coverage blocker in section 6 evaporates, and everything downstream changes.

**7.5 `invalid_range_is_inf: false` is called the largest single lever on
unknown percentage and has deliberately never been flipped.** With it false, a
no-return beam clears nothing. With it true, a no-return beam clears free space
out to max range. The stated reason for not touching it is that infinity clears
through obstacles the sensor merely failed to see, which is a real hazard.
Given that 35 to 53% of beams return nothing, this single boolean may dominate
the failing gate. The honest position is that nobody has measured what it does,
because it was judged too dangerous to try. **Is that judgement right? Is there
a per-consumer split (inf for the mapper, finite for collision checking) that
gets the coverage without the hazard?**

---

## 8. Assumptions nobody has challenged

The useful contribution is the item you add to this list.

1. **That `base_link` may stay non-standard.** This stack deliberately publishes
   `+X = right, +Y = forward`, which is not REP-103. The odometry node computes
   internally in standard REP-103 and rotates by -90 degrees on publication.
   Nav2, the dashboard, the goal handling, the scan calibration and the teleop
   path all carry compensations for this. It is documented as the stack's
   deepest architectural debt, and the stated permanent fix is to restore a
   standard `base_link` and push the sensor rotation into the sensor TF where it
   belongs. Everyone agrees it should be fixed. Everyone agrees it should not be
   fixed eight days before an exam. **Is that second agreement actually correct,
   or is the compensation chain now generating the bugs it is deferring?**

2. **That the room is a fixed constraint.** "There is no space for a bigger
   loop" has been accepted without a floor plan being measured. Furniture moves.

3. **That mapping quality must be solved before navigation starts.** The phase
   gating (G4 blocks G5 blocks G6) is a project-management structure, not a
   technical necessity. AMCL on a 73%-unknown map might work fine. Nobody has
   tried, because the gate says not to.

4. **That the trajectory should be a circle.** Circles were chosen because the
   room is small and a circle is repeatable. Circles also maximise the fraction
   of the drive where the rear mask points at the same part of the room, and
   they are the geometry a previous analysis already flagged as degenerate for
   scan matching. A figure-eight, a spiral, or a slow in-place rotation at three
   or four distinct positions would all paint the room differently.

5. **That the scan matcher was the cause rather than a victim.** The matcher was
   fed a cloud that is half-invalid, heavily flickering, and missing a fixed 90
   degree wedge. Its failure may have been a correct response to bad input. That
   would mean the current configuration is treating a symptom, and that matching
   becomes correct again the moment the input improves. This changes what "fix
   it properly" means.

6. **That per-run variance is noise.** Single-lap unknown percentage ranged 77.6
   to 84.6 across nominally similar drives. Nobody has explained the spread. It
   is larger than every effect the campaign has been trying to measure.

---

## 9. Already ruled out, please do not re-litigate

Save your effort for section 7 and 8.

- Scan-matcher parameter tuning: five sessions, correction totals invariant
  across three parameter sets. Dead end while the input is what it is.
- Tightening the LiDAR quality gate for coverage: measured three ways on
  15 Sep, makes things worse.
- Driving a bigger circle: map bounding box is essentially identical across
  every run because the 5 m sensor range already reaches the room's walls from
  the zero mark. Circle size is a minor lever.
- Driving a deliberately irregular wobbled path: tried, extent barely grew,
  closure got 10x worse, coverage did not improve.
- Rewriting Nav2, rewriting the motor firmware, redesigning the dashboard: all
  in reasonable shape, all frozen.
- Buying anything: eight days, nothing arrives.

---

## 10. What another model already said, so you can go elsewhere

ChatGPT was given similar material and concluded, in summary: freeze the
architecture, do not resume scan-matcher tuning, verify deployed config against
the live node rather than YAML, run the multi-lap coverage experiment with a
written prediction, keep RAW for mapping and strict filtering only for
collision checking, do not tighten the 5 m cap yet, buy the IMU after APS,
restore REP-103 frames after APS, consolidate the config files after APS, and
treat the research narrative (hypothesis, failure, controlled modification,
negative result, revised model) as the real APS contribution.

That is a sound and largely internal-consistent read. It agrees with the
project's own plan almost everywhere. **Which is why I would rather you looked
somewhere else.** If you find yourself writing those conclusions again, the
marginal value is near zero.

---

## 11. Specific questions, in the order I care about them

1. **Is the phantom yaw in section 4 a bug?** Same sign, same magnitude, twice,
   on different routes, validated instrument. If it is a systematic estimator
   term rather than physical slip, where in the kinematics does it live? My
   candidate is the single-axis `lateral_scale` on a three-axis coupled slip
   mechanism. Tell me if that is wrong, and what you would compute from
   existing encoder logs to settle it.

2. **Is 47 to 65% valid beams normal for this sensor, or is something wrong
   with the unit or its configuration?** This is the question with the largest
   downstream consequence and the least investigation behind it.

3. **Is `invalid_range_is_inf: false` the right call** given that a third to a
   half of beams return nothing, or is there a per-consumer split that gets the
   coverage without clearing through unseen obstacles?

4. **Is closure error on a closed circular path a valid drift metric?** If not,
   what is the cheapest valid one available in a room a few metres across with
   no external tracking?

5. **Is a bounding-box unknown-cell fraction the right acceptance criterion**
   for a commissioning map, or should the requirement be restated? If restated,
   to what, defensibly, in front of an examiner?

6. **Does the no-IMU argument in section 3 survive a hostile reading?** Not
   "should he buy an IMU" (yes, later, everyone agrees). Whether the specific
   claim that LiDAR precision binds before odometry drift at this scale is
   sound, given that one error is cumulative and the other averages down.

7. **With scan matching off and zero loop closures ever observed, is calling
   this system SLAM defensible in a PhD comprehensive exam?** If not, what is
   the accurate and non-damaging way to describe it?

8. **Anything in section 8, plus whatever should have been in section 8.**

---

## 12. Constraints on any advice

- Eight days. The exam is a hard date.
- No new hardware. Nothing ordered now arrives in time.
- The room is small, a few metres across, cross-shaped, cluttered, with 62 cm
  floor tiles that serve as the ground-truth reference.
- The Pi has no GPU and has previously run out of CPU and killed slam_toolbox
  outright.
- The Pi is normally on its own access point at 10.42.0.1 with no internet.
  Getting files onto it is a deliberate manual step, not a `git pull`.
- One operator, driving by phone dashboard, no second pair of hands.
- The standing working rule in this project is one variable per run, with the
  prediction written down before the drive rather than after.

---

*Repository context available on request: this brief is drawn from
`docs/Phase2_Without_IMU.md`, `docs/Project_Status.md`,
`docs/evidence/circular_loop_15sep/README.md`, `docs/Research_Journal.md`
sections 17.42 through 17.56, `system/slam_nodom_stageB.yaml`,
`system/ydlidar_params.yaml`, `src/mecanum_robot/mecanum_robot/odometry_publisher.py`
and `src/scan_relay/scan_relay.py`.*
