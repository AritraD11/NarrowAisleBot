# Evidence — rotation in place maps nothing, and the circle is the wrong test

Four hardware recordings from **29 Aug 2026**, the basis of
`Research_Journal.md` §17.44. Together they establish two things that change
how this robot has to be driven:

1. **`slam_toolbox` adds no pose-graph node and no map cell while the robot
   rotates in place.** Three independent runs. Every stop-and-spin corner
   driven since §17.39 contributed nothing to any map.
2. **A tight circle is a degenerate geometry for scan matching**, and three
   sessions of parameter tuning were spent against it before that was
   noticed. The perimeter drive — the one that passed **G2** — is the good
   case.

> **Watch `02` and `03` back to back if you only watch two.** `02` is 714° of
> rotation that produces 2.1 m of wall. `03` is the same rotation *with
> translation* and produces 77 m.

Every recording is dashboard on the left, an SSH pane on the right. Where the
right pane runs `graph_residuals.py --watch`, the `n=` column is the
pose-graph node count and is the number to read.

---

## `01_perimeter_start_node_freeze.mp4` — the anomaly, before we knew what it was

111.5 s, dashboard + `graph_residuals.py`. The opening of the 621 s
commissioning drive (`run_20260829_144619`).

Timebase: **`watcher_t = video_t + 49.5 s`**, verified at seven independent
sample points.

From watcher **t≈99.5 s to t≈171.5 s — 72 seconds — the graph is frozen**:
`n=7`, `e=7`, `driven=1.89 m`, unchanged. Over the same window the pose card
sweeps:

| watcher t | X | Y | NOSE |
|---|---|---|---|
| 103.5 | −0.251 | 1.793 | 30.4° |
| 111.5 | −0.269 | 1.832 | **59.3°** ← reversal |
| 123.5 | −0.265 | 1.943 | 1.7° |
| 131.5 | −0.270 | 2.067 | 4.9° |
| 159.5 | −0.270 | 2.067 | **164.0°** |

**~250° of accumulated rotation at a steady 5.7°/s, and the graph gained
nothing.** `minimum_travel_heading` was 0.2 rad (11.46°), which should have
fired roughly 21 times.

Occupied-cell count across eight frames from t=104 to t=160 is flat, and the
map region is **pixel-identical** between them. Note this is not independent
evidence — `slam_toolbox` only republishes the grid when nodes change — so
the single fact is that *the graph stopped accepting the rotation*.

---

## `02_two_rotations_no_map.mp4` — the same thing, deliberately

136.2 s. `run_20260829_152041`, 642 s total. Right pane is `topic hz`, not the
watcher, so this one cannot show node counts — read the saved map instead.

Two complete turns, unwrapping the pose card's NOSE:

| phase | span | rate |
|---|---|---|
| t=0 → 68 s | 0° → −359.9° (one full turn CW) | 5.6°/s |
| t=72 → 132 s | 0° → +354.0° (one full turn CCW) | 5.5°/s |

**X and Y never leave 0.000 ± 0.001 m across all 714°.**

What the session actually produced:

| | |
|---|---|
| duration | 642 s |
| **occupied cells** | **43 = 2.1 m of wall** |
| unknown cells | 21 650 |
| SLAM correction | **0.0 m net, 0.0 m cumulative, max step 0.0 m** |

Ten and a half minutes, two full sweeps of the room, **2.1 metres of wall**.

⚠ **A measurement error worth recording.** During analysis the map was first
judged to be *growing* in this video, from a dark-pixel count over the map
region. That metric counted trail lines and UI chrome as occupancy. The saved
grid — 43 cells — is the truth. Do not re-derive map coverage from a
screenshot.

**Physical check:** after the two turns, tape-measured **3 cm right, 2 cm
back = 3.6 cm** from the mark, while both odometry and SLAM reported
0.001 m. That is a real blind spot, quantified for the first time, and it is
small: ~0.45 cm per 90° of turn, at most ~14% of the terminal error on a
drive with eight corners. Recorded, not chased.

---

## `03_arc_w_plus_e_nodes_appear.mp4` — turning *while translating* works

77.2 s. `run_20260829_155447`. `W`+`E` held together throughout — forward and
clockwise at once, which the dashboard combines because held keys accumulate
in a `Set` (`phone_dashboard.py:975–999`).

Timebase: **`watcher_t = video_t + 18.6 s`**.

`n` climbs steadily — 1 → 18 — with nodes roughly every 0.09–0.15 m.

| run | duration | body path | nodes | occupied cells | wall |
|---|---|---|---|---|---|
| pure rotation (`02`) | 642 s | 0.09 m | **1** | 43 | 2.1 m |
| **this arc** | 111 s | 3.20 m | **18** | **1545** | **77.2 m** |
| perimeter drive | 621 s | 18.14 m | 48 | 1761 | 88.1 m |

**88% of the perimeter drive's wall coverage, in 18% of the time and 18% of
the distance** — against a full 360° spin that produced 2.1 m in ten minutes.

**The geometry, backed out of the wheel travel** (this matters, see the
caveat below): left wheels 6.29/6.73 m, right wheels 0.37/0.12 m, body path
3.2 m.

| | |
|---|---|
| mean of L and R travel | (6.50 + 0.25)/2 = 3.4 m ≈ 3.2 m ✓ |
| yaw from the difference | 6.25 / (K_o+K_i = 1.05) = 5.95 rad = **341°** ✓ |
| turn radius | 3.2 / 5.95 = **0.54 m** |

`K_o` = 0.56069 m. **The instantaneous centre of rotation landed on top of
the right-hand wheels**, so they sat at the pivot and barely turned.

---

## `04_arc_stageE_spiky_trail.mp4` — what the corrections look like

67.1 s. `run_20260829_164017`, the Stage E run
(`angle_variance_penalty` 1.2 → 0.6).

The robot drove a smooth circle. **The drawn trail is a starburst of radial
spikes.** The spikes are not motion — the trail is drawn in the `map` frame,
and `map→odom` jumps underneath a smooth odometry circle.

| | |
|---|---|
| wheel path (what the robot did) | **3.20 m** |
| SLAM path (what got drawn) | **5.63 m** |
| difference | **2.43 m** |
| cumulative correction | **2.86 m** |

**That 2.43 m of extra drawn path is the spikes.**

Sampling the trail region every 2 s, the frame-to-frame change alternates
between ~480 (smooth drawing) and 700–2800 (a leap), on a **~3.7 s period**.
The run's correction timestamps are 60.6, 64.3, 67.9, 71.6, 75.3, 78.9, 82.6,
86.3, 89.9, 93.5 s — **spacing 3.65 s**. Same cadence, and the same cadence
as node additions in the watcher.

**18 nodes. 17 corrections. One jump per node, every time.** This is not
occasional false closure — the matcher disagrees with odometry by
0.15–0.37 m on *every scan it accepts*.

> **Do not "fix" this at the display.** Smoothing the trail into a clean
> circle would delete the only signal that revealed the per-node
> disagreement. Standing rule #5, and §17.38 is the precedent: four separate
> −90° display compensations hid a real frame fault for two weeks.

---

## Why the circle was the wrong benchmark

Three arcs, identical driving, three parameter sets:

| | arc 1 | arc 2 | arc 3 (Stage E) |
|---|---|---|---|
| `minimum_travel_heading` | 0.2 | 0.1 | 0.1 |
| `angle_variance_penalty` | 1.2 | 1.2 | **0.6** |
| max correction | 0.367 m | 0.229 m | 0.366 m |
| max heading step | 10.42° | 5.71° | 10.23° |
| **cumulative correction** | **2.80 m** | **2.85 m** | **2.86 m** |
| return to mark | 0.292 m | 0.282 m | 0.276 m |
| wheel closure | 0.019 m | 0.013 m | 0.008 m |

**Cumulative correction is invariant to within 2% across every parameter set
tried.** The tuning moves the *distribution* of the error and never the
amount — the signature of something the search parameters do not touch.

The working explanation (**hypothesis**, §17.44): the robot circles inside a
~1 m disc at the centre of a ~10 m space, matching against walls several
metres out. At 5 m range, **1° of heading error is indistinguishable from
8.7 cm of translation**. Rotation and translation become poorly separable and
the matcher resolves the ambiguity in favour of heading — which odometry pins
down — dumping the residual into position. That predicts the measured
signature exactly: **heading right to ~4°, position 27.6 cm out**, with
wheels closing to 0.008 m.

The perimeter drive, with real translation and walls at 0.5–1.5 m, gives
**1.0 corrections/m and a 0.202 m maximum**. The circle gives **5.3
corrections/m and 0.367 m**.

---

## Two `run_analyzer.py` false positives these runs exposed

Both fire on every arc drive and both are wrong. Fixes are scheduled in
`Next_Session_Kickoff.md`.

1. **Wheel travel spread.** *"one wheel did much less work than another —
   slip, or a mechanical problem."* On a 0.54 m-radius arc the ICR sits on
   the inner wheels, so a 37–56:1 ratio is exactly correct. All four motors
   read 0.024–0.035 rms, 0% saturation, 0% sign error in every one of these
   runs. The heuristic assumes near-straight driving and needs a turn-rate
   guard.

2. **Correction / doubled-wall co-location.** *"a false closure with two
   independent witnesses."* In `run_20260829_164017` all seven flagged
   corrections reference the **same** 4-cell doubled wall — one wall counted
   seven times, not seven witnesses. Worse, on a 1 m circle the entire
   trajectory lies inside the 1.0 m coincidence radius, so the test has no
   discriminating power at that geometry.

---

## Not archived here

The dashboard **stills** shared during this session — the post-drive map
screenshots and the pose-card readings taken after the robot was manually
returned to the floor mark — were pasted into the conversation rather than
saved as files, so they are not in this folder. The pose readings they carry
are transcribed in §17.44 and in the tables above. If they are wanted for the
report, drop them into the Windows staging folder and they can be added.
