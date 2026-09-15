# Phase 2 without an IMU: the case, and how it gets validated

**Written 14 September 2026.** Decision: the first APS presents Phase 2
closed without inertial measurement. This document is the argument and the
measurement programme that backs it, and it is written to be defended in a
review rather than to excuse a missing part.

---

## 1. The argument, shortest form

> The sensing question was narrowed this year from "add sensors" to a
> measured deficit. The measurement shows that at the corridor scale this
> platform operates in, the binding error term is LiDAR precision, not
> odometry drift. An inertial sensor addresses the term that is not binding.

Everything below supports that sentence.

---

## 2. Phase 2's own deliverable does not ask for an IMU

The objective, as written in the report before any of this came up:

> **Establish localisation adequate for corridor-width clearances.**
> Deliverable: a pose estimate characterised against ground truth, with a
> stated drift figure over a stated distance, and an explicit account of
> which sensors are required to reach it.

Three clauses. The first two are measurement and both are already done. The
third is the research content, and it is a question about sensors rather than
a requirement to own one. Answering "which sensors are required" means
establishing what the platform achieves without them and where that stops
being enough.

Fitting an IMU first would destroy the ability to answer it. Fusion improves
the estimate, and with no characterised pre-fusion baseline at the operating
scale there is no way to say by how much or which error it removed. The
project's own standing rule covers this case exactly: **isolate before
tuning.** An unfused baseline is the isolation.

---

## 3. The error budget at 5 m, which is the scale that matters

The operating envelope for this APS is a 5 m map. Two error sources compete
inside it, and they scale differently.

**Wheel odometry** drifts at a measured **1.1 to 1.5 % of path**: 0.229 m
over roughly 18 m is 1.27 %, and 0.257 m over 18.14 m is 1.42 %. That is
linear in distance travelled.

**The LiDAR** is a triangulation scanner, so its range error grows with
distance faster than linearly. The measured stationary scatter is
**22.8 mm at the 1.6 m median range** of this lab.

| Path or range | Odometry drift over that path | LiDAR scatter at that range |
|---|---|---|
| 1.0 m | 11 to 15 mm | ~9 mm (quadratic fit) to 20 mm (2 % linear) |
| 1.6 m | 18 to 24 mm | **22.8 mm, measured** |
| 3.0 m | 33 to 45 mm | ~80 mm to 60 mm |
| 5.0 m | **55 to 75 mm** | **~222 mm to 100 mm** |

The two are comparable at about 1.6 m and they diverge after it. By 5 m the
LiDAR term is somewhere between 1.3 and 4 times the odometry term, depending
on which degradation model holds, and §5 measures which one does rather than
assuming.

So at the scale this robot works in, odometry is not the limiting instrument.
It is the better of the two, which is the same conclusion Stage G reached from
a different direction when disabling the scan matcher removed every pose
correction: over the same drive, wheel odometry alone closed 0.229 m while
odometry plus the SLAM front end closed 0.706 m.

Against G4's 0.15 m return-to-mark gate, an 8 m commissioning drive on
odometry alone predicts 88 to 120 mm. Inside the gate, with no inertial help.

---

## 4. The platform already carries a second heading measurement, and it is unused

The asymmetric wheelbase produces two independent yaw estimates, each on its
own lever arm:

$$
\hat{\omega}_{\text{outer}} = \frac{r(\omega_{FR} - \omega_{RL})}{2K_{o}},
\qquad
\hat{\omega}_{\text{inner}} = \frac{r(\omega_{RR} - \omega_{FL})}{2K_{i}}
$$

with $K_{o} = 0.5607$ m and $K_{i} = 0.4907$ m. Their mean is the published
yaw rate. Their difference, scaled by $2K_{o}/r$, is the slip residual

$$
s = \omega_{FR} + 1.142656\,\omega_{FL} - 1.142656\,\omega_{RR} - \omega_{RL}
$$

`wheel_forensics.py` computes this and it has never been pointed at a
campaign. An IMU would be a third heading source added while the second one
sits unread.

**State this carefully in the report.** A symmetric four-wheel mecanum
platform also has a residual of this form; the asymmetry does not create the
observable. What the asymmetry changes is that the two estimators sit on
different lever arms, 0.5607 m against 0.4907 m, so they have different noise
gains and different sensitivity to a given slip. On a symmetric platform the
two lever arms are equal and the pair carries no such asymmetry to exploit.
That is a narrower claim than "the geometry makes the drivetrain
self-diagnosing", and it is the one the mathematics actually supports.

---

## 5. What gets measured, and in what order

Four runs. None needs a part that is not already on the robot.

### 5.1 Phase 1: done and verified

```bash
./tools/nab_pid_logger.py --test plant --port /dev/esp32   # WHEELS IN THE AIR
```

Run 14 Sep 2026. τ measured at ≈0.09 s per motor, against the 0.18 s this
project had assumed, which recomputes `Kp` from 45 to a bracket of 22 to 26
holding `Ki = 250`. Both candidates were then swept closed-loop against the
shipped 45 (`--test sweep --gains "45,250,0.5 22,250,0.5 26,250,0.5"`) and
both lost on overshoot in all 16 setpoint-motor combinations, 43 to 54 %
worse on average. `Kp` stays at 45. Objective 1.3 closes as **confirmed**,
not changed; Phase 1 is 100 %. Full derivation, why the open-loop
prediction did not survive closed loop, and a settle-time tool bug found
and fixed the same session: `PID_Calibration.md` §5.

Ground-side plant ID (repeat the same run on the floor) is not needed to
close Phase 1 and is not today's priority. $K$ drops under load, so
$K_i = 1/(K\lambda)$ would rise, and the difference is the ground-load
correction measured directly rather than inferred from the 24 % feedforward
figure, but `Kp` was the open item, `Ki` was not, and `Kp` is now settled.
Worth doing if there is slack later in the week; do not let it delay G4.

### 5.2 The range envelope, which is the Phase 2 headline

Park the robot. Nothing moving in the room.

```bash
./tools/scan_quality.py --seconds 60 --save ~/aislebot_logs/env_park1.json
./tools/scan_range_envelope.py --load ~/aislebot_logs/env_park1.json \
                               --json ~/aislebot_logs/envelope1.json
```

This bins every ray by range and reports, per bin, how often that bearing
returns at all and how far it moves while the robot stands still. Two
budgets decide the cap, and both are read off the deployed configuration
rather than chosen:

- **Scatter 25 mm**, which is half the 0.05 m occupancy cell. A ray scattering
  more than half a cell votes for a different cell on consecutive sweeps, and
  that is the mechanism that thickens and doubles walls. Doubled walls under
  1.0 % is the G4 sub-criterion that keeps failing.
- **Validity 90 %**, because a bearing returning on fewer than nine sweeps in
  ten marks on some and clears on others, which is §17.45's global flicker
  finding restated per range.

Repeat from two or three different parking spots. A cap derived in one corner
of one room is a fact about that corner until it reproduces.

**This also settles a discrepancy in the project's own documentation.**
`StageG_Deploy.md` §1.1 says ray error "grows with the *square* of distance"
and then quotes 32 mm at 1.6 m, 100 mm at 5 m, 200 mm at 10 m. Those numbers
are exactly 2 % of range, which is linear, and they came from the datasheet
rather than from this unit. The quadratic model and the linear model disagree
by more than a factor of two at 5 m. One run settles it, and the answer
changes where the cap goes.

### 5.2.1 Result, 15 Sep 2026, two captures

Run 1, open room, 689 scans, 60 s parked. Run 2, same method, deliberately
parked with solid objects on three sides, 691 scans, per §5.2's own
instruction to repeat from a different spot before trusting a number.

| | Run 1 (open) | Run 2 (objects on 3 sides) |
|---|---|---|
| Median range | 1.6 m | 1.3 m |
| Stationary noise, p90 | 16.8 mm | 11.3 mm |
| Flicker | 79.6 % | 83.1 % |
| 1.0-1.5 m bin | 89.3 % valid, 14.3 mm | 97.7 % valid, 12.4 mm (passes) |
| 1.5-2.0 m bin | 96.0 % valid, 22.3 mm (passes) | 93.3 % valid, **31.9 mm (fails)** |
| Beyond 2.5 m | 70-200 mm, inconsistent | 55-124 mm, inconsistent |

**Reading the two together, not separately:** solid out to about 1.0-1.5 m in
both runs. The 1.5-2.0 m bin flips from pass to fail between the two, which
means the crossover is not a fixed distance, it depends on which surface
happens to sit in that band, consistent with everything else this project
has found about this unit being geometry-dependent rather than a clean
function of range alone. Beyond 2.5 m both runs agree it is unreliable.

**Neither run settles linear versus quadratic, and that is a finding, not a
gap.** Both models predict a single smooth curve. What was measured is a
region that behaves consistently (under 1.5 m) followed by a region that
does not reproduce between two otherwise-identical captures (1.5-2.5 m).
That is not the signature either model predicts. `scan_range_envelope.py`
computed a recommended cap of 1.5 m from run 2 alone; it is a real number
for what it measured, and it is not being applied to the deployed
config, for a reason worth stating precisely:

**`use_scan_matching` has been `false` since Stage G (3 Sep).** The reason a
tight cap normally matters, protecting the scan matcher from corrupting the
pose estimate with a bad long-range match, does not apply while nothing is
using long rays to correct pose. The measured cost of the current 5 m cap is
therefore not pose corruption, it is a marginal doubled-walls contribution,
and doubled walls has been passing (0.7-0.8 %, gate < 1.0 %) at 5 m through
every run so far. Meanwhile the gate that is actually failing, unknown cells
at 77-85 %, would fail far worse at a 1.5 m cap, which would stop the sensor
from contributing to the map at all past arm's reach. Tightening the cap now
would trade a passing gate's small margin for a much larger hit to the one
gate that is failing.

**Disposition: characterise now, revisit the number later.** This closes
Phase 2's headline measurement. The 1.5 m figure is filed as a candidate for
Phase 4 (AMCL, collision_monitor), where obstacle-range accuracy carries
real safety weight and scan matching is not in the loop the same way. It is
not applied to G4's configuration, which needs coverage, not precision,
right now.

### 5.3 Make every consumer agree on the cap

This is the finding that the range audit turned up, and it matters more than
the exact number chosen.

| Consumer | Parameter | Currently |
|---|---|---|
| ydlidar driver | `range_max` | 10.0 |
| slam_toolbox | `max_laser_range` | **5.0** |
| global costmap | `obstacle_max_range` | 8.0 |
| global costmap | `raytrace_max_range` | 9.0 |
| local costmap | `obstacle_max_range` | 8.0 |
| local costmap | `raytrace_max_range` | 9.0 |
| dashboard overlay | `scan_trust_range` | 5.0 |

**The costmaps currently mark obstacles out to 8 m and raytrace-clear out to
9 m, using rays that slam_toolbox refuses to match against past 5 m.** Nothing
errors. The planner simply plans against evidence the mapper has already
judged untrustworthy, and a bad long ray can clear a real obstacle it should
have marked. Whatever §5.2 returns, all seven settings take the same number.

### 5.4 The slip residual, free from drives already happening

```bash
./tools/wheel_forensics.py --csv ~/aislebot_logs/<run>_wheels.csv
```

Run it over every drive of the day. Per-wheel slip on a non-collinear layout
is Gap 3 in the report and nothing has been measured on it. The data is the
same encoder stream the drives produce anyway, so this costs nothing but the
command.

### 5.5 A third phantom-yaw replication

The phantom-yaw result currently rests on two runs, which grades as measured
but thinly. Any drive recorded on video today, measured against the floor
grout with the method already validated against frames of known rotation,
makes it three.

---

## 6. What this does not claim

Stated plainly so the report does not have to be walked back later.

The platform is **not** better off without an IMU. Fusion would reduce heading
error and Galati and co-workers report roughly 88 % heading-drift reduction
from it. The claim is narrower and it is about sequence: the sensing question
cannot be answered by a platform that has already been given the sensor, and
at a 5 m operating scale the unfused platform is inside its own error budget.

Phase 2 therefore closes as **characterised**, not as **optimal**. The
deliverable is a drift figure, a ground-truth comparison and a statement of
which sensors are required. All three are reachable this week. What stays open
for year 2 is the fusion itself, and it now has a specific number to be tested
against rather than a general expectation.

An IMU should still be ordered. It is the right next purchase, the phantom-yaw
measurement gives it a falsifiable target, and nothing here argues otherwise.
It is simply not what closes Phase 2.
