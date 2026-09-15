# Stage H: scan matching back on, scored and reverted

`run_20260915_202258`. 82.5 s, 3.193 m, one continuous circle
(−361.7° of odometry rotation). Deployed and verified against the live node
before the first metre: `use_scan_matching True`, `do_loop_closing True`,
`max_laser_range 5.0`, 12 pass / 0 fail / 1 warn.

**Verdict: REVERT.** Three of the four pre-committed revert triggers fired.
Not one of the five keep criteria was met except the one that was expected
to be neutral.

---

## 1. Read this caveat before the numbers

**This is not the drive that was planned, and the difference matters.**

The handoff specified §17.56's 12.04 m out-and-back perimeter, for a
one-variable A/B against an existing matching-off baseline on identical
geometry (9.9 cm closure, 0.83% of path, heading −4.49°, zero corrections).
What was driven was a continuous ~0.5 m radius circle.

§17.44 already flagged tight-circle geometry as degenerate for scan
matching: a circle shows the same walls from continuously rotating vantage
points. So a scan-matching failure here is partly what §17.44 predicts, and
this run cannot distinguish "the matcher is broken on this robot" from "the
matcher is broken on circles, which we already knew."

What it can do, it does decisively. The revert criteria were written
unconditionally and three of them fired, so the revert stands on its own
regardless of route. What the route costs is the other direction: this run
cannot rescue Stage H, and it cannot condemn it on the perimeter either.
**The perimeter A/B is still owed.**

Two further gaps, both from this run not being instrumented as planned:
there is no screen recording, so "visible map tearing" could not be scored;
and there is no photogrammetry, so the physical return heading is the
operator's eye rather than a measurement. §17.55 and §17.56 both had a
validated instrument for that. This one does not.

---

## 2. Scored against the pre-committed criteria

Written in `Session_Handoff_2026-09-15_evening.md` §2, before the drive,
and not edited after it.

### REVERT on any one of

| Trigger | Result |
|---|---|
| any single-step correction ≥ 0.15 m | **FIRED. 14 of 17 events. Max 309.2 mm** |
| `map_integrity.py` returns FOLDED | **FIRED** |
| return to mark > 0.15 m | **FIRED. 206.7 mm** |
| visible map tearing | not scored, no recording |

### KEEP only if all of

| Criterion | Result |
|---|---|
| corrections small and frequent, tens of mm | **FAILED. Smallest correction in the run was 106.7 mm** |
| at least one loop closure fires | **FAILED. Zero. See §4** |
| closure at mark ≤ 9.9 cm | **FAILED. 20.67 cm** |
| doubled walls < 1.0%, not FOLDED | **FAILED. 6.6%, FOLDED** |
| unknown % roughly unchanged | **held.** 72.6% against 73.0% on the RAW baseline |

The last row is the only prediction that landed, and it was the one
predicted to be neutral on the grounds that matching changes where scans
are drawn rather than how many cells they paint. That reasoning survives.

---

## 3. The head-to-head, on one drive

Both estimates come from the same 3.193 m of driving, same wheels, same
scans. The robot physically returned to the mark.

| Estimator | Final position | Error | As % of path |
|---|---|---|---|
| wheel odometry alone | (−0.0009, +0.0162) | **16.2 mm** | 0.51% |
| odometry + scan matching | (−0.1885, +0.0848) | **206.7 mm** | 6.47% |

**Scan matching made pose 12.8× worse on this drive.**

§17.49 measured the same thing on a 21.85 m drive at 10 m range: odometry
0.229 m, odometry plus matching 0.706 m, a factor of 3.1. At 5 m range, on
a circle, the factor is 12.8. The 5 m cap was the one thing that had never
been tried with the matcher on, and it did not rescue it.

The dashboard agreed with the CSV to the millimetre while the drive was
happening: DRIFT 0.201 m against a computed correction magnitude of
200.6 mm, JUMPS 17 against 17 correction events. The HUD is trustworthy on
both fields.

---

## 4. The metronome, which is the actual finding

This is the part worth taking to the exam.

Every correction event, with the odometry path length between it and the
one before:

```
 #   t(s)   path(m)  gap(m)   step(mm)
 1  16.80    0.189   0.189    167.38
 2  20.40    0.372   0.184    190.02
 3  24.10    0.557   0.185    174.23
 4  27.80    0.742   0.185    180.76
 5  31.40    0.923   0.180    194.71
 6  35.10    1.108   0.185    251.67
 7  38.70    1.289   0.181    255.42
 8  42.40    1.474   0.185    152.97
 9  46.10    1.659   0.185    309.20
10  49.60    1.835   0.176    130.07
11  53.30    2.020   0.185    106.72
12  57.00    2.206   0.186    117.90
13  60.60    2.386   0.181    168.92
14  64.30    2.569   0.182    166.70
15  67.90    2.749   0.181    172.34
16  71.60    2.934   0.185    159.86
17  75.20    3.115   0.181    165.14
```

Gap between events: mean 0.183 m, min 0.176, max 0.186. **A 1 cm spread
across seventeen events.**

`minimum_travel_distance` is 0.2 m. The corrections are not responding to
the scan disagreeing with the prior. They are firing once per pose-graph
node, on a fixed odometry-distance cadence, whether or not there is
anything to correct. That is §17.40's metronome replicating exactly, three
parameter sets and one range cap later.

**And it is why no loop closure fired.** A loop closure is a step change
that arrives off-cadence, when the graph recognises a place it has seen
before. Every one of these seventeen sits on the metronome. Not one is off
it. The pose graph exists this time (`verify_live_config.sh` §6 read
publisher count 1 on `/slam_toolbox/graph_visualization` before the drive,
so the graph is genuinely being built under Stage H), and closure still
never fires.

That narrows the question usefully. Under Stage G the suspicion was that
matching-off suppressed graph construction entirely, leaving nothing for
`do_loop_closing: true` to act on. Under Stage H the graph is built, the
matcher runs, and closure *still* does not fire on a circle that returns to
its own start. So the graph is not the blocker. Either the loop-match
response thresholds (0.25 coarse / 0.35 fine) are never met, or
`loop_match_minimum_chain_size: 8` is not reachable on a 3.2 m circle at
0.18 m per node, which gives only 17 nodes total.

The second explanation is testable and cheap, and it is another argument
for the perimeter route rather than the circle.

---

## 5. Map

`map_integrity.py`: **FOLDED**.

```
grid          187x192 @ 0.05 m = 9.3x9.6 m
cells         1450 occupied / 8390 free / 26064 unknown
wall          72.5 m of occupied cells
D1 thickness  median 0.05 m, p95 0.2 m
D2 doubled    95 cells (6.6% of wall)
D3 forks      72 junctions (9.93/10 m), 317 endpoints (43.72/10 m)
D4 alignment  dominant axis -27.5 deg, manhattan 0.31
D5 free space 1 regions, largest holds 100.0%
```

D5 is the interesting one. Free space is a **single connected region**, so
this is not the tear-into-two-components failure that AISLE and STRICT
produced on 15 Sep. The FOLDED verdict here comes from D2 and D3: 6.6%
doubled walls against a 1.0% gate, and 9.93 skeleton junctions per 10 m of
wall. Doubling at 6.6% is what seventeen 10-to-30 cm pose corrections
between passes of the same wall look like drawn on a grid.

For comparison, the matching-off RAW baseline on the same circle geometry
had 2.9% doubled walls. Matching tripled it.

---

## 6. Phantom yaw: a third data point, and it overturns yesterday's ranking

Odometry yaw closed at **−1.74°** over 361.7° of rotation and 3.193 m. The
robot physically returned to its start heading, by eye.

`DeepSeek_Response.md` §2 scored four proportionality models against the two
runs available yesterday and found the phantom yaw closest to constant per
run. **With a third point that ranking does not survive, and the correction
belongs here rather than buried.**

| Run | Rotation | Distance | Duration | Phantom yaw | °/m | °/deg rot | °/s |
|---|---|---|---|---|---|---|---|
| §17.55 | 723.8° | ~6.46 m | ~216 s | −3.85° | 0.596 | 0.00532 | 0.0178 |
| §17.56 | 364.5° | 12.04 m | 482 s | −4.49° | 0.373 | 0.01232 | 0.0093 |
| this run | 361.7° | 3.193 m | 82.5 s | −1.74° | 0.545 | 0.00481 | 0.0211 |

Spread, worst over best: **distance 1.60×**, time 2.27×, rotation 2.56×,
constant-per-run 2.58×.

Distance is now the tightest of the four and constant-per-run has gone from
best to worst. The cleanest single comparison is §17.56 against this run:
**near-identical rotation, 364.5° and 361.7°, and phantom yaw differing by
2.6× while distance differs by 3.8×.** Two runs that turned through the same
angle and accumulated very different heading error is about as direct a
refutation of a rotation-scaled mechanism as two runs can give.

So DeepSeek's actual claim, that this is not a multiplicative bias on yaw
rate, is not just intact but considerably stronger than when it was made.
The extension I put on top of it yesterday, that per-run constancy points at
once-per-maneuver accrual, was an over-read of two points and is withdrawn.

A distance-proportional heading error points back at wheel-radius or
encoder-scale error, which is exactly the class `wheel_forensics.py`'s own
docstring names as invisible to the slip residual. The velocity-path
hypothesis in `DeepSeek_Response.md` §4 is not killed by this, but it is no
longer the leading explanation, and the check proposed there
(`Δposition_rad` against `Σ(actual_velocity × dt)`) is now worth running
mostly because it cheaply separates the two.

**Weaker evidence than the other two rows, stated plainly.** §17.55 and
§17.56 had validated photogrammetry against tile grout for the physical
heading. This run has the operator's eye. A third point that flips a ranking
deserves better ground truth than that, and the perimeter re-drive should
carry a screen recording so it can be measured the same way.

---

## 7. What this does and does not settle

**Settles:** the 5 m cap does not rescue the matcher. That was Stage H's
actual question, since every prior measurement of matcher behaviour was
taken at 10 or 12 m, and the answer is no. It also settles that pose-graph
construction is alive under Stage H, so a missing graph is not why closure
never fires.

**Does not settle:** whether matching helps on non-degenerate geometry. The
circle was the wrong route and §17.44 had already called it degenerate. The
perimeter A/B against the 9.9 cm baseline remains the experiment that was
designed and it has not been run.

**Revert regardless.** The criteria were pre-committed and unconditional,
three of four fired, and the robot's own odometry beat the corrected pose by
a factor of 12.8 on the same drive.
