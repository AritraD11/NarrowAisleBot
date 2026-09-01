# Stage F ablation — `use_scan_barycenter`

**Written 1 Sep 2026, BEFORE the drive.** Registered in advance so the result
cannot be rationalised afterwards, the same way §17.40's three-branch table was.

One value changes: `use_scan_barycenter: true → false` in
`system/slam_nodom_stageB.yaml`. Nothing else.

---

## Why this one

§17.44 measured cumulative `map→odom` correction across three parameter sets:
**2.80 / 2.85 / 2.86 m — invariant to 2%.** Every parameter in those sets
(`correlation_search_space_dimension`, `coarse_search_angle_offset`,
`angle_variance_penalty`, `minimum_travel_heading`) changes how the matcher
**searches**. None of them moved the total.

`use_scan_barycenter` changes **what gets registered**. With it on, karto seeds
from the centroid of the returned points rather than the sensor origin. §17.45
measured that cloud: **48.8% valid, 86.0% flicker while parked**, plus a
permanently masked rear 90°. A centroid over that moves scan to scan even with
the robot bolted down — and a moving reference point produces coupled
position-and-heading drift, which is exactly the 1 Sep signature.

## The baseline it is measured against

`run_20260901_184810`, 4.27 m of odometry path, three goals, tape-measured.

| quantity | baseline |
|---|---|
| correction events | 9 |
| cumulative \|step\| | **0.291 m** (0.068 m per metre driven) |
| net correction | **0.114 m** |
| share of net in a single axis | **99% X, 1% Y** |
| corr_x ↔ corr_yaw correlation | **+0.889** |
| odom motion during each jump | 1.7–4.7 mm |
| physical error, tape | **9 cm right, 0 cm fore/aft** |
| odometry's own estimate of it | 10.4 cm right, 1.6 cm forward |

Re-drive the **same route**: (0,0) → (0, 1.02) → (−0.16, 2.03) → (0, 0).

## Did the parameter actually take effect?

⛔ **RETRACTED 1 Sep, before the ablation was ever scored.** This section
originally claimed baseline corrections arrive every **0.175 ± 0.006 m** and
that the spacing should move toward 0.200 m with the barycenter off.

**That 0.175 m was measured wrong.** It came from differencing
`hypot(odom_x, odom_y)` — straight-line displacement from the origin — on an
out-and-back route, not distance travelled along the path. On a there-and-back
leg that quantity shrinks on the return, so the "spacing" was an artefact of
the route's shape. Measured properly along the path, the baseline spacing is
**0.441 m (sd 0.192)** and `run_20260901_193822` gives **0.391 m (sd 0.147)** —
indistinguishable, at any detection threshold from 0.5 mm to 5 mm.

**There is therefore no node-spacing test.** The only way to know whether
Stage F is live is the live node, during the session:

```bash
ros2 param get /slam_toolbox use_scan_barycenter      # must read false
```

A file on disk is not a value in the node — the rule this project already runs
on (§17.32), which this section briefly forgot.

## Pre-registered outcomes

| | condition | reading |
|---|---|---|
| **CONFIRMED** | net correction **< 0.06 m** AND tape error **< 5 cm** | the barycenter is a real contributor; keep it off, re-baseline everything |
| **REFUTED** | net correction **0.091–0.137 m** (±20% of baseline) | joins the invariance family; the mechanism is upstream of the matcher entirely, and the answer is the sensor |
| **AMBIGUOUS** | anything else | n=1, repeat before concluding |

A secondary signal worth recording either way: whether the **99% single-axis
dominance** survives. If the error stays one-dimensional, that is a property of
the room's geometry, not of the seeding.

## What this is not

Not a fix, and not expected to be one. `Where_We_Stand.md` grades the LiDAR 3/10
on measured spec — ±2% of range, no intensity, no dual return — and the ceiling
is hardware. This tests one mechanism that could be amplifying that ceiling.

**Do not deploy this as a setting on a CONFIRMED result alone.** Confirm it
twice, on the same route, per §17.47's rule that one drive on one geometry is a
property of that drive.
