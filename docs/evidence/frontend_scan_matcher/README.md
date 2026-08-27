# Evidence — the jumps are the front-end scan matcher

Three hardware recordings from 27 Aug 2026, the basis of
`Research_Journal.md` §17.40. They are what established that the pose-graph
jumps chased since §17.28 are **not loop closures** — they come from
`slam_toolbox`'s front-end scan matcher overruling correct wheel odometry.

**Every one was driven `W`/`S`/`D`/`A` only. `Q` and `E` were never pressed,
so no rotation was commanded at any point.** Every `NOSE` change in all three
videos is the matcher re-deciding which way the robot points while the robot
did not turn. Wheel odometry's yaw stays flat throughout.

Kept for the APS report, and because this is far easier to show than to
describe.

> **Read `03` first if you only watch one.** It is the one that carries the
> conclusion. `01` shows the phenomenon most clearly; `02` shows it worst.

---

## `01_ws_slow_three_resets.mp4` — the cleanest picture of the fault

Dashboard only, 44.6 s, **SLOW (0.05 m/s)**, forward and back on `W`/`S`.

The map pose rises at exactly the commanded 0.050 m/s, then is reset three
times. Read off the pose card at 1 Hz:

| # | Map `Y` before → after | Correction* | `NOSE` |
|---|---|---|---|
| 1 | 0.326 → 0.036 | **−0.340 m** | 0.0° → −2.8° |
| 2 | 0.386 → 0.096 | **−0.340 m** | −2.8° → −5.0° |
| 3 | −0.298 → −0.008 | **+0.340 m** | −5.1° → −3.8° |

\* frame-to-frame delta plus the 0.050 m the robot actually travelled in that
second.

**All three are 0.340 m, to the millimetre.** The deployed
`correlation_search_space_dimension` was `0.7`, i.e. a half-width of
**0.35 m**. The corrections are not varying with anything the robot did —
they are landing on the edge of the window the matcher is allowed to search.

Between resets the map pose tracks odometry exactly. The outbound leg never
gets past `Y ≈ 0.386` of a roughly 1 m drive, because it is reset twice
before it can.

## `02_wsda_med_with_odom_terminal.mp4` — worst case, with odometry beside it

Dashboard left, `ros2 run tf2_ros tf2_echo odom base_link` right, 55 s,
**NORMAL (0.10 m/s)**. Full square: `W` 1 m, `S` back, `D` 1 m, `A` back.

This is the one that proves the robot really moved while the map did not.
Odometry reads `+1.002 m` on `Y` for the forward leg with `X` pinned at
≤1 mm, and `+1.038 m` on `X` for the lateral leg with `Y` at ≤2 mm. The map
pose never exceeds 0.39 m on the forward leg.

**Seven corrections in 48 s: 0.36, 0.36, 0.37, 0.40, 0.42, 0.45, 0.40 m.**
Every one falls between the 0.7 m window's half-width (0.35) and its diagonal
reach (0.495). `NOSE` walks to **−14.2°** with nothing commanded.

Scoreboard for that drive, over ~4.0 m of path:

| | Final error from the mark |
|---|---|
| Wheel odometry | **4.3 cm** (1.1%) |
| SLAM map pose | **38.7 cm** |

This video also confirms §17.38's frame convention at metre scale, where it
had only ever been measured on ~180 mm moves: `W` → `+Y`, `D` → `+X`,
cross-axis coupling ≤ 2 mm over a metre.

## `03_wsda_slow_with_graph_residuals.mp4` — the one that settles it

Dashboard left, `tools/graph_residuals.py --watch` right, 82 s of a 153 s
run, **SLOW (0.05 m/s)**, `W`/`S`/`D`/`A`.

**`moved=0` and `max_shift=0.000` for the entire 153 seconds.** Not one
pose-graph node was ever moved by the optimiser — while the HUD threw three
corrections of **0.336 / 0.302 / 0.240 m** with `NOSE` stepping to −13.4°.

A back-end re-solve moves nodes. Nothing moved. **The corrections are the
front end.**

The two instruments also agree leg by leg, which is what makes this
conclusive rather than suggestive:

| | `W`/`S` leg | `D`/`A` leg |
|---|---|---|
| HUD tracked to | **0.988 m** of 1 m, back to 0.017 | jumps at `X` 0.357, 0.312, −0.313 |
| Corrections | ≤ 6 cm | **0.336 / 0.302 / 0.240 m** |
| `NOSE` | 0.0° → −0.6° | −0.8° → **−13.4°** |
| Graph node spacing | **0.37, 0.36, 0.36, 0.36 m** | **0.02, 0.00, 0.03 m** |
| Chain accumulated | **1.45 m** | **0.05 m** |

Where the matcher tracks, consecutive graph nodes land 36 cm apart. Where it
fails, node spacing collapses to nothing — and that is exactly where the HUD
jumps. The graph-node collapse and the HUD jump are the same event seen
twice.

---

## What these do and do not show

**They show** that the corrections are front-end scan matching, that their
magnitude is set by `correlation_search_space_dimension` rather than by any
motion of the robot, and that wheel odometry is by a wide margin the more
accurate of the two instruments over these distances.

**They retire** §17.39's "73% / 44% / 32% implied drift". Those corrections
do not cancel accumulated drift, they overrule correct odometry, so
`correction ÷ distance driven` was never a drift rate and had no reason to
stay below 100%.

**They do not show** that loop closure is fixed, or broken. No drive here was
long enough to produce a genuine closure — `loops=0` in `03` is partly
structural, since 8 nodes cannot contain an edge of span > 8. §17.28–§17.32's
loop-closure tuning is **out of scope for these events**, which is a
different claim from refuted.

**They do not settle whether strafe is the weak axis.** `03` fails on `D`/`A`
while `W`/`S` is clean, which looked like an axis effect — but `01` fails on
`W`/`S` at the same speed. So the failure is **intermittent rather than
axis-locked**, and the `03` asymmetry is one observation, not a pattern. Do
not build on it.

**They do not show the fix.** Stage C
(`correlation_search_space_dimension` 0.7 → 0.3, commit `2a3e83b`) was
committed after these were recorded and has not been deployed or tested. The
A/B against `03` is the next session's first task.
