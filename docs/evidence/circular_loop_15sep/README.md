# Evidence: 15 Sep circular loop, unconfigured LiDAR gate

One drive, mid-morning 15 Sep 2026, after `slam_nodom.yaml` was confirmed
deployed and `use_scan_matching` confirmed `false` on the live node
(`docs/Session_Handoff_2026-09-15.md`, `Phase_234_Push.md` §4.1).

**This was not the §4.2 procedure as written, on two counts, both by the
operator's own account, not discovered after the fact:**

1. The lab floor didn't have room for the planned 8 m rectangular loop with
   rolled corners. The operator drove a continuous circle instead, no
   stop-and-rotate anywhere, which is the property the rectangle procedure
   was actually protecting (§3.2: rotation in place adds no pose-graph node
   and no map cell; a continuously-turning arc outperforms a
   perimeter-with-corners on coverage per minute). A circle is that same
   principle taken further, not a violation of it.
2. The scan_relay quality gate (LIDAR TUNER) was **not configured** for
   this run, left wherever it was from the previous session rather than
   deliberately set to a known preset before driving.

Because of (2) especially, and because no prediction was registered against
*this* procedure before the drive (§4.3's predictions were written against
the rectangular route), **this run is being kept as reconnaissance, not
scored as one of G4's three budgeted attempts**, the same call this
project made for `docs/evidence/monday_recon/` before the first real
commissioning attempt. It's useful, physically evidenced, worth keeping for
the report, and not the thing to grade against the G4 gate table.

---

## What's confirmed vs. what needs a follow-up check

| Claim | Source | Status |
|---|---|---|
| Path was a closed circle, zero to zero, no in-place rotation | operator, and confirmed by decoding the video (below) | ✅ confirmed independently |
| Speed was NORMAL / 0.10 m/s (not SLOW) | dashboard screenshot, `COMMAND LIMIT: MED — 0.10 m/s` | confirmed, read directly off the screenshot |
| Dashboard pose at end of run: `X −0.001, Y 0.000, NOSE 0.1°`, `DRIFT 0.000 m`, `JUMPS 0` | dashboard screenshot | confirmed, read directly off the screenshot |
| `VALID 65% of 323`, `CHURN 16%/sweep`, `107 masked (rear wedge)` | dashboard screenshot | confirmed, read directly off the screenshot |
| Physical ground-truth offset from the zero mark: **−2°, −3.0 cm** | operator's tape/protractor check | ✅ units resolved by geometry, not assumption: the fitted loop is ~1.0 m in diameter, so a 3.0 m offset is physically impossible for this drive. Must be cm. Also consistent with this project's own measured 1.1–1.5% closure band applied to the loop's actual path length (see below): predicts 3.5–4.7 cm, and 3 cm sits right at the bottom of that |
| Whether the map was saved (second **MAP** tap, the only action that persists it) vs. still running | operator confirmed, and `run_20260915_121818.pgm`/`.yaml` exist on the Pi | ✅ confirmed, saved |
| scan_relay gate state during this drive (RAW / leftover STRICT / something else) | not stated | not exactly known, but bounded by evidence now: CHURN ran 18–33% and VALID 58–70% across the whole drive (16 samples), both consistently looser than the 4–13% CHURN / 53–65% VALID seen earlier with STRICT applied. Whatever was running, it wasn't STRICT |
| Actual driven path length | not measured | ✅ measured by fitting the trajectory (below): **circle, radius 0.50 m, diameter 1.0 m, path length ≈ 3.14 m**, much shorter than the 8 m the §4.2 procedure was built around |

## `01_circular_loop_drive.mp4`

Screen recording of the dashboard during the drive, provided by the
operator, decoded with PyAV (bundles its own decoder, no system `ffmpeg`
needed, since the earlier `apt-get install ffmpeg` attempt had failed
against the package mirror). 38.1 s total; driving runs t=0 to ~30.5 s, the
remaining ~7.5 s is the robot sitting parked back at the mark.

16 frames sampled evenly across the clip and read off the dashboard's own
`ROBOT POSE · MAP FRAME` HUD:

| t (s) | X (m) | Y (m) | NOSE | VALID | CHURN |
|---|---|---|---|---|---|
| 0.0 | 0.006 | 0.078 | −8.9° | 63% | 29% |
| 2.6 | 0.118 | 0.323 | −40.2° | 62% | 27% |
| 5.1 | 0.322 | 0.469 | −68.9° | 58% | 22% |
| 7.6 | 0.570 | 0.498 | −97.8° | 61% | 27% |
| 10.2 | 0.802 | 0.403 | −126.6° | 66% | 26% |
| 12.7 | 0.963 | 0.199 | −156.5° | 70% | 27% |
| 15.2 | 1.003 | −0.047 | 174.6° | 63% | 20% |
| 17.8 | 0.918 | −0.282 | 145.8° | 63% | 26% |
| 20.3 | 0.730 | −0.447 | 117.1° | 59% | 29% |
| 22.9 | 0.465 | −0.501 | 85.9° | 60% | 20% |
| 25.4 | 0.229 | −0.422 | 57.0° | 63% | 27% |
| 27.9 | 0.059 | −0.238 | 28.3° | 62% | 33% |
| 30.5–37.9 | ≈0.00 | ≈0.00 | ≈0.3° | 63–65% | 18–32% |

Fitting a circle to the (X, Y) samples: every point sits 0.500–0.505 m
from a center at (0.5, 0), constant to within 5 mm across the whole loop.
Radius 0.50 m, diameter 1.0 m, path length ≈ π × 1.0 ≈ 3.14 m.

Not yet done: visual review of the actual rendered frames for anything
`map_integrity.py` wouldn't catch (e.g. VIEW showing a visible fold in
real time). The pose-HUD numbers above are exact; the visual read of the
map tiles themselves was only a glance across 16 stills, not a full
playback.

sha256: `beb159b9cc60084705793bcaa72fd1d263288f213cbae35c413dc3c226bf132a`

## `map_integrity.py` result on `run_20260915_121818`

```
run_20260915_121818   ->   SUSPECT
grid          195x198 @ 0.05 m = 9.8x9.9 m
cells         874 occupied / 7770 free / 29966 unknown
wall          43.7 m of occupied cells

D1 thickness  median 0.1 m, p95 0.2 m
D2 doubled    9 cells (1.03% of wall)
D3 forks      21 junctions (4.81/10 m), 109 endpoints (24.94/10 m)
D4 alignment  dominant axis -1.5 deg, manhattan 0.47, secondary peak +10 deg at 0.69 relative
D5 free space 1 regions, largest holds 100.0%
```

**Does not pass G4**, and unknown cells is the reason, not map quality:

| Gate | Threshold | Measured | Result |
|---|---|---|---|
| Verdict | not FOLDED | SUSPECT | borderline, see caveats below |
| Doubled walls | < 1.0% | 1.03% (9/874 cells) | fails narrowly; tool's own thresholds are stated as provisional |
| Unknown cells | < 50% | 77.6% | **fails badly** |
| Return to mark | < 0.15 m | ~0.03 m (tape) | passes comfortably |

A 3.14 m loop was never going to see enough of a 9.8×9.9 m cross-shaped
room. Switching the LiDAR gate to STRICT for the next attempt won't move
this number, since STRICT makes a map cleaner, not bigger.

⚠ **Superseded by run 2's analysis below:** STRICT does not merely fail to
help here, it actively makes unknown % worse, because a beam the gate drops
is a beam that no longer clears a cell. The correct setting for the failing
gate is a loose one.

The two `SUSPECT` flags (fork density, poor alignment to a single dominant
axis) haven't been visually checked against `docs/tools/map_viewer.html`
yet. One honest caveat on the alignment flag specifically: this room is a
cross-shaped junction with more than one wall orientation by construction,
not a single rectangular room, so a metric built around one dominant axis
may read low here even on a good map. Not claiming that's the explanation,
just flagging that it hasn't been ruled in or out.

This run is being kept as evidence, not counted against the three
budgeted G4 attempts, for the same reason as the video itself: it deviated
from the registered §4.2 procedure (path length, LiDAR gate) with no
prediction registered against this specific shape beforehand.

The same `run_20260915_121818_report.json` also carries a `"Diagonal
mismatch is visible"` warning from the motor/PID analyzer bundled into the
same file. That's an already-documented false positive for any drive that
turns continuously (same class as the one flagged in
`docs/evidence/monday_recon/README.md`), not a new finding, and not
patched by standing rule 9 (don't change an instrument mid-campaign).

---

# Run 2: `run_20260915_131800`, same circle, full telemetry

Second fresh-map circular run, 91.7 s, with pose CSV and map files supplied.
Archived here: `02_second_circular_loop.mp4`, `run_20260915_131800_pose.csv`,
`run_20260915_131800.pgm`, `run_20260915_131800.yaml`.

## The pose side is excellent

Computed directly from `run_20260915_131800_pose.csv` (918 rows):

| Quantity | Measured |
|---|---|
| Path length (odom) | **3.163 m** |
| Trajectory extent | X 0.00 to 1.00 m, Y -0.50 to +0.50 m (the same 1 m circle) |
| Closure error | **6.4 mm, 0.20 % of path** |
| Yaw closure | **-0.27 deg** |
| `map->odom` correction, max | **0.0000 m** |
| Samples with any nonzero correction | **0 of 885** |

Two things worth stating plainly. First, zero corrections across the entire
run is Stage G's registered prediction landing exactly: with
`use_scan_matching: false` the front end contributes nothing, and the pose
is pure wheel odometry.

Second, **0.20 % closure is far better than this project's own measured
1.1 to 1.5 % band.** A smooth continuous circle with no stops, no rotations
in place and no strafe reversals appears to be much kinder to mecanum
odometry than the out-and-back routes that produced the historical band.
That is a new observation, n=1, and it is what makes multi-lap driving
viable below.

## The map side, `map_integrity.py`

```
run_20260915_131800   ->   SUSPECT
grid          178x184 @ 0.05 m = 8.9x9.2 m
cells         521 occupied / 4511 free / 27720 unknown
wall          26.1 m of occupied cells
D2 doubled    4 cells (0.8% of wall)
D3 forks      5 junctions (1.92/10 m), 61 endpoints (23.42/10 m)
D4 alignment  dominant axis -1.5 deg, manhattan 0.46
flags: only 46% of wall within 10 deg of the dominant axis
```

Against G4, run 2 versus run 1:

| Gate | Threshold | Run 1 | Run 2 | Status |
|---|---|---|---|---|
| Verdict | not FOLDED | SUSPECT (2 flags) | SUSPECT (1 flag) | not folded, improved |
| Doubled walls | < 1.0 % | 1.03 % | **0.8 %** | **now passes** |
| Unknown cells | < 50 % | 77.6 % | **84.6 %** | fails, worse |
| Return to mark | < 0.15 m | ~0.03 m tape | **0.0064 m** | passes comfortably |

Three of four gates are effectively met. Only coverage fails.

## Is the coverage gate even reachable from a 1 m circle?

The operator has confirmed there is no room for a longer loop, so this had
to be measured rather than assumed. Ray-casting from the 75 distinct path
pixels, 720 rays each, 5 m range, stopping at known occupied cells:

| | cells | % of grid |
|---|---|---|
| Line of sight from the driven path | 24078 | 73.5 % |
| Unknown **with** line of sight (recoverable) | 19244 | 58.8 % |
| Unknown **without** line of sight (occluded) | 8476 | 25.9 % |

**Caveat, stated because it matters:** the ray-cast treats unknown cells as
transparent, so rays travel until they hit a *known* wall. Real unmapped
walls would stop them sooner. So 73.5 % is an optimistic ceiling, not a
forecast. What it does establish is that a large block of currently-unknown
grid is not occluded by anything the robot has actually mapped, which means
coverage is not obviously capped by geometry alone at this trajectory.

## Why so little free space is being painted

Free area observed is only **11.3 m²** out of an 8.9 x 9.2 m grid. The
mechanism is in this repo already, and the MathWorks material restates it:
an occupancy grid gets occupied evidence at a return **and free-space
evidence along the beam path**, accumulated over repeated observations. A
beam that returns nothing paints nothing, because
`invalid_range_is_inf: false` means no-return beams clear no free space.
At a measured 47 to 65 % valid-beam rate, most rays contribute nothing on
any given sweep.

**This inverts the earlier advice to use STRICT for the next run.**
`scan_relay.py`'s own documentation says it directly: every beam the gate
drops is a beam that no longer clears a cell. STRICT at 3-of-3 persistence
is the *worst* available setting for coverage. It buys map cleanliness,
which run 2 already passes on (0.8 % doubled), at the cost of the one gate
that is failing.

## The plan this produces

1. **Loose gate, not STRICT.** RAW, or AISLE at most. Cleanliness is not
   the failing gate; coverage is.
2. **Multiple laps of the same circle.** Repeated observation is how free
   space accumulates, and it needs no extra floor space. Enabled by the
   0.20 % closure measured above: at that rate 5 laps is 15.8 m and about
   3 cm of drift. **Escalate carefully**, because the historical 1.1 to
   1.5 % band applied to 15.8 m would give 17 to 24 cm and fail the return
   gate. Drive 3 laps first, measure closure, and only extend if it holds.
3. **Widen the circle if even 1.5 m diameter fits.** Area scales with the
   square of radius; path with the radius. Not assumed available.
4. Leave `invalid_range_is_inf` alone. It is the largest single lever on
   unknown %, and it is documented here as dangerous to flip without a
   per-consumer split, because inf clears through obstacles the sensor
   merely failed to see.

## A note on the gate itself

Unknown % is computed over the bounding box of everything observed, so
cells behind walls count against it permanently. In a small room entered
from one small circle, part of that number measures the room's shape rather
than the quality of the drive. If multi-lap running cannot close it, the
systems-engineering answer from the MathWorks §7 V-model discussion is to
restate the requirement against the physically achievable envelope and say
so explicitly in the report, not to quietly relax the threshold.

---

# Run 3: `run_20260915_140253`, deliberately wobbled, wider yaw excursions

Operator held the yaw slider at mid-deflection instead of driving a fixed
radius, intentionally not a clean circle, to see whether varying the
radius covers more of the room than a fixed one. 146.2 s.

## What the numbers actually show

| Quantity | Run 2 (clean 1 m circle) | Run 3 (wobbled) |
|---|---|---|
| Path length | 3.16 m | 4.03 m |
| Trajectory extent | 1.0 x 1.0 m | **1.20 x 1.32 m** |
| Radius | fixed 0.50 m | mean 0.50 m, sd 0.22, range 0.28 to 0.89 m |
| Closure error | 6.4 mm (0.20%) | 80.6 mm (2.00%) |
| Yaw closure | -0.27 deg | -2.01 deg |
| `map->odom` correction | 0 of 885 samples | 0 of 1430 samples |
| Unknown cells | 84.6% | 78.3% |
| Doubled walls | 0.8% | 0.7% |
| Fork density | 1.92 / 10 m | **7.31 / 10 m** |

**The honest read: the trajectory extent barely grew** (1.2 x 1.3 m against
1.0 x 1.0 m), despite the radius transiently reaching 0.89 m. Wobbling the
radius did not translate into meaningfully more floor covered, and unknown
% (78.3%) landed close to run 1's 77.6%, not meaningfully better than
either circle run. Closure got worse, as expected: a path with varying
curvature and uneven speed does not get the same clean-circle
benefit run 2 had, though 2.00% is still comfortably inside the 0.15 m gate
in absolute terms (80.6 mm). Fork density nearly quadrupled, which reads as
more fragmented wall detections from constantly-changing vantage angles,
not a G4 gate but a real cost.

## Why "bigger circle" is not actually the lever here

The map's outer boundary sits at essentially the same ~9.9 x 10 m across
all three runs, run 1's tiny circle included. That is because
`max_laser_range: 5.0` means the sensor already sees walls up to 5 m away
from very near the zero mark, in every direction, without the robot needing
to travel there. **The room's far walls are already inside sensor range
before the robot moves at all.** What differs run to run is not how much of
the room the sensor could reach, it is how many of those far, weak returns
actually survive to paint a cell, which needs a valid beam AND enough
repeated looks for a flickering beam to eventually register. The §5.3
ray-cast finding from run 2 (58.8% of the grid has line of sight but is
still unpainted) already pointed at this. Circle size is a minor lever.
Repetition is the main one.

## Revised recommendation

Drop the push toward a bigger circle. **Drive the same manageable loop
several times in a row instead**, with a loose LiDAR gate (RAW or AISLE,
not STRICT), and check unknown % after each pass rather than after one.
That is the lever the data actually supports.

---

# Run 4: `run_20260915_154615`, first run under the revised plan (RAW gate, 3 laps)

First drive following the reversed advice from run 2/3's analysis: LiDAR
panel set to RAW before driving (not STRICT, not left unconfigured), same
manageable circle, driven 3 times in a row rather than once. 228.7 s.

## Pose: the best closure of the day

Computed from `run_20260915_154615_pose.csv` (2288 rows):

| Quantity | Measured |
|---|---|
| Path length (odom) | 9.526 m (3 laps, matches 3 x ~3.14 m) |
| Closure error | 1.9 mm, 0.020% of path |
| Yaw closure | -0.03 deg (internal); operator's tape/protractor read ~-3 deg |
| `map->odom` correction | 0 of 2255 samples nonzero |

Better than run 2's single-circle 0.20%, over three times the distance.
Consistent with the emerging pattern that a smooth, continuously-turning,
no-stop trajectory is unusually kind to this platform's odometry.

## Coverage: moving in the right direction

From the bundled `_report.json` map stats (full `map_integrity.py` D2-D5
verdict not yet run, `.pgm` not supplied this round):

| Run | Path shape | Gate state | Unknown % |
|---|---|---|---|
| 1 (`_121818`) | 1 m circle, x1 | unconfigured | 77.6% |
| 2 (`_131800`) | 1 m circle, x1, clean | unconfigured | 84.6% |
| 3 (`_140253`) | wobbled, x1 | unconfigured | 78.3% |
| **4 (`_154615`)** | **1 m circle, x3 laps** | **RAW** | **73.0%, lowest yet** |

First run under the corrected plan, and the best coverage result so far.
Worth restating the run 2 ray-cast finding that makes this genuinely
encouraging rather than just marginally better: the theoretical floor from
this exact circle, with unlimited repetition, was calculated at ~26.5%
unknown. At 73.0% after 3 laps, there is real headroom left from more laps
of the *same* circle before that floor is anywhere close to binding.

The `"Diagonal mismatch is visible"` finding recurs (FR-RL RMS 1.323,
FL-RR RMS 1.158 rad/s), larger than on any previous run, consistent with
this being the longest, most-turning drive of the day (same documented
false positive, not a new issue).

## Next

More laps of the same circle (5-6), same RAW gate, watch whether unknown %
keeps falling or starts to plateau. `map_integrity.py`'s full verdict
(doubled walls, FOLDED/SUSPECT) on this run's `.pgm` still outstanding.

## `map_integrity.py` full result on `run_20260915_154615`

```
run_20260915_154615   ->   SUSPECT
grid          197x204 @ 0.05 m = 9.9x10.2 m
cells         1419 occupied / 9434 free / 29335 unknown
wall          71.0 m of occupied cells

D2 doubled    41 cells (2.9% of wall)
     cluster      5 cells ~0.25 m of wall, gap 0.45 m, at map (3.42, 1.27)
     cluster      4 cells ~0.2 m of wall, gap 0.46 m, at map (3.0, 0.98)
     cluster      4 cells ~0.2 m of wall, gap 0.3 m, at map (5.55, -0.35)
D3 forks      37 junctions (5.21/10 m), 137 endpoints (19.31/10 m)
D4 alignment  dominant axis -1.5 deg, manhattan 0.41
```

**Doubled walls regressed:** 2.9% against run 1-3's 0.7-1.03%, now a clear
fail rather than borderline. All three flagged clusters sit 3-5.5 m from
the zero mark, squarely in the range band `Phase2_Without_IMU.md` §5.2.1
already measured as unreliable (scatter 55-200 mm beyond ~2.5 m). Three
laps means that same distant wall got hit three times, and RAW admits
every one of those noisy far returns, including the ones that land a
little differently each pass. Coverage and cleanliness are now visibly in
tension, both driven by the same far-range noise: RAW helps the former,
hurts the latter.

Updated G4 status after this run:

| Gate | Threshold | Measured | Result |
|---|---|---|---|
| Verdict | not FOLDED | SUSPECT | unchanged |
| Doubled walls | < 1.0% | **2.9%** | fails, worse than runs 1-3 |
| Unknown cells | < 50% | **73.0%** | fails, best of 4 runs |
| Return to mark | < 0.15 m | 1.9 mm | passes, best of 4 runs |

**Next test, one variable changed:** AISLE preset (2-of-3 persistence)
instead of RAW, same 3 laps, same circle. AISLE is built to drop exactly
the single-sweep flicker that plausibly caused this doubling, without
STRICT's much heavier cost to coverage. Direct comparison against this
run: if unknown % holds near 73% and doubled walls drops, AISLE is the
better setting for this drive. If unknown % jumps back toward 80%, the
coverage cost is too high and RAW stands, accepting the doubling as a
cost worth paying while unknown % is still the far larger gap to the gate.

---

# Run 5: `run_20260915_164745`, AISLE preset, same trajectory as run 4

Controlled A/B against run 4: identical setup (fresh ZERO x2, fresh MAP,
same circle, 3 laps no break), one variable changed, LiDAR panel set to
AISLE instead of RAW. 312.4 s. Odom extent matches run 4 to the centimeter
(X -0.00..1.01, Y -0.51..0.51 vs run 4's -0.00..1.01, -0.50..0.51), so this
is a clean isolate-one-variable comparison, not a different drive.

## Pose: best closure yet, confirms pose is gate-independent

| Quantity | Run 4 (RAW) | Run 5 (AISLE) |
|---|---|---|
| Path length | 9.526 m | 9.530 m |
| Closure error | 1.9 mm (0.020%) | **2.5 mm (0.026%)** |
| `map->odom` correction | 0 of 2255 | 0 of 3092 |

Both essentially perfect. With `use_scan_matching: false`, pose comes
purely from wheel odometry, so the LiDAR gate has no path to affect it.
Confirms that directly with two independent runs.

## Map: `map_integrity.py` on `run_20260915_164745`

```
run_20260915_164745   ->   FOLDED
grid          196x199 @ 0.05 m = 9.8x10.0 m
wall          67.0 m of occupied cells

D2 doubled    15 cells (1.1% of wall)
D3 forks      49 junctions (7.31/10 m), 115 endpoints (17.16/10 m)
D4 alignment  dominant axis -1.5 deg, manhattan 0.41
D5 free space 2 regions, largest holds 99.8%

flags:
  - 2 disconnected regions of free space
```

| Gate | RAW (run 4) | AISLE (run 5) |
|---|---|---|
| Verdict | SUSPECT | **FOLDED, worse** |
| Doubled walls | 2.9% (fail) | **1.1%, big improvement** |
| Unknown cells | 73.0% | 74.6%, statistically flat |
| Return to mark | 1.9 mm | 2.5 mm, both pass comfortably |

**AISLE fixed the doubled-walls regression from run 4 by more than half,
confirming the persistence-filter hypothesis.** But it introduced a new
defect not seen in any run today: two disconnected free-space regions,
serious enough that `map_integrity.py` escalates the whole verdict to
FOLDED rather than SUSPECT. Working hypothesis, not confirmed: AISLE's
persistence gate likely rejected enough beams crossing a narrow connecting
area that a strip stayed "unknown" instead of "free," splitting one
physically-open room into two map-disconnected islands.

Unknown cells did not meaningfully improve (74.6% vs 73.0%), within the
noise already seen across single-lap runs (77.6-84.6%). So the gate choice
is not the lever that closes the dominant gap; more repetition still is.

**Verdict: revert to RAW for further laps.** RAW's failure mode (some
doubling, softer verdict) is preferable to AISLE's (a torn map, harder
verdict), and the coverage gain from AISLE was not real. Consistent with
`Phase2_Without_IMU.md`'s existing decision not to trade coverage for
cleanliness while unknown cells remains the larger gap to its gate.
