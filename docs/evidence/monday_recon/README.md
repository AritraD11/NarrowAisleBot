# Evidence — Monday 31 Aug recon legs, and the spread between them

Two ~165 s drives from **31 Aug 2026**, the basis of `Research_Journal.md` §17.47.
They were reconnaissance for the commissioning drive, not commissioning attempts:
the room is cross-shaped with no single length × width, so the plan was to drive
out to the obstacle in each of two directions and read the extent off the floor
tiles (62 × 62 cm, tape-measured) rather than tape-measure an irregular room.

> **The reason this folder exists is not the room measurement.** It is that two
> drives on the *same configuration, same afternoon, same operator*, differing
> only in route, produced a **6.8× spread in return-to-mark** — and one of them
> is the first drive in this project's history to land inside the G4 return gate.

---

## The two legs, side by side

| | front leg (`run_20260831_155316`) | right leg (`run_20260831_191509`) | G4 gate |
|---|---|---|---|
| moving duration | ~166 s | ~162 s | — |
| wheel path | 9.61 m | 8.00 m | — |
| SLAM path | 11.7 m | 9.56 m | — |
| **return to mark** | **0.577 m** | **0.085 m** ✅ | < 0.15 m |
| wheel closure | 0.028 m | 0.019 m | — |
| **max single correction** | **0.678 m** | **0.280 m** | (G2: < 0.30 m) |
| net correction | 0.576 m | 0.072 m | — |
| cumulative ÷ wheel path | 0.562 m/m | 0.305 m/m | — |
| correction events | 21 | 13 | — |
| D2 doubled walls | 5.1% | 5.2% | < 1.0% |
| unknown | 73.8% | 79.4% | < 50% |
| map verdict | FOLDED | FOLDED | not FOLDED |

**Both maps still fail G4 on every map-quality measure.** What changed is the
trajectory: the right leg's SLAM estimate tracked the wheels closely, the front
leg's did not.

---

## `01_front_leg_dashboard_and_mastcam.mp4`

162.8 s, side by side: dashboard map view (left) and mast camera looking straight
down at the tiled floor (right). The drive runs zero → out to `Y ≈ 3.59 m` → back,
with continuous mixed motion — straight, wall-hugging, `W`+`Q`/`W`+`E` turns taken
while rolling, some strafing. **No stop-and-spin anywhere**, per rule 7.

Heading wanders between roughly +3° and −26° across the leg. It ends at
`X −0.56, Y 0.13, NOSE −11.9°`.

⚠ **The MAP session behind this video had been running since before S0.** The saved
pose log spans **2246 s**, of which only the first ~166 s contain motion; the
remaining ~35 minutes are the robot standing still while other work happened. Any
analysis of this run has to be trimmed to the moving window first — untrimmed,
`duration_s` and the correction-step percentiles are meaningless.

**A useful negative result from that idle tail:** across ~2080 s parked, the pose
graph produced **zero** correction events. All 21 fall between t+2.8 s and
t+151.0 s. Consistent with §17.44 — a stationary robot does not trigger
reprocessing — and it means S0's measured scan instability does **not** leak into
corrections while the robot is still.

## `02_right_leg.mp4`

The second leg, driven out along `+X` to about `X ≈ 3.4 m` and back, same style.
Clean log — 161.9 s, no idle tail.

This is the run that returned to **0.085 m**. In `right_leg_map_annotated.png` the
SLAM path (green) and wheel path (blue) run nearly on top of each other for the
whole leg; in `front_leg_map_annotated.png` they separate into a loop.

## `03_mastcam_setup_reference.mp4`

94.6 s, mast camera only. The rig itself — camera fixed to the mast looking
straight down, robot chassis centred in frame, floor tiles scrolling underneath as
it drives. The 62 cm tile pitch is what makes this a metric record: distance comes
from counting tile-line crossings, **not** from commanded speed × elapsed time,
which assumes no slip.

## `lab_floor_sketch.png`

The lab floor plan with the zero mark, `+X` / `+Y` axes and NOSE direction added by
hand. **NOSE points toward the Entrance, and that is also `+Y`** — confirmed by the
operator. The room is cross-shaped, which is why no single length × width was
recorded.

---

## Why the two legs differ — three live explanations, none yet separable

⛔ **Do not read this as "`+X` is good and `+Y` is bad."** That is the shape of the
"strafe is the weak axis" claim, **retracted 29 Aug** when a third recording failed
on the `W`/`S` leg at the same speed on the same day. This is n=1 per direction.

1. **Geometry** — the front leg threads a narrow furniture-flanked aisle (the
   Workstation 2 / HUB 5 corridor in the sketch), traversed twice in opposite
   directions minutes apart; the right leg runs a wide open stretch. Would extend
   §17.44's degenerate-geometry hypothesis from tight *turns* to narrow *aisles*,
   same underlying mechanism. 🔷 **hypothesis**
2. **Direction / axis** — the retracted claim's shape. Do not build on it.
3. **Intermittency** — already established as real on 29 Aug, and on its own
   sufficient to produce a 6.8× spread between any two drives. ✅ **measured that
   it exists**

**The test that separates them costs ~15 minutes:** drive each leg a second time.
If the front leg reproduces ~0.58 m and the right leg reproduces ~0.09 m, it is
route/geometry and route planning can help. If either flips, it is intermittency,
and no route plan rescues G4.

---

## A third `run_analyzer`-family false positive, found here

`run_report.py`'s **"Diagonal mismatch is visible"** (fired at FR−RL 1.214 and
FL−RR 1.070 rad/s against a fixed 0.3 threshold) is the same class of bug as the
two guarded in §17.46. Read from source: it is `RMS(FR_actual − RL_actual)` and
`RMS(FL_actual − RR_actual)`. On a mecanum chassis those diagonal pairs are exactly
what carries strafe and yaw, so a drive that deliberately strafed and turned makes
them large *by construction*.

Against it: all four motors 0.076–0.082 rad/s tracking error, **0% saturation, 0%
sign mismatch**, travel ratio 1.11. The drivetrain is healthy. The 0.3 threshold
appears to date from a straight-line open-loop stutter investigation
(`past_iterations/aislebot_pid_analysis_v2.py` calls it "the stutter source").

**Not patched.** Standing rule #9 — do not change an instrument mid-campaign
without re-running the baseline through both versions. Scheduled, not done.

---

## Not archived here

The auto-annotated overlay video produced from `03` by a browser tool. Its axis
markers are drawn at a **fixed screen position** rather than tracked, and its
"obstruction" boxes are a dark-pixel blob detector that will box a shadow as
readily as a table leg. It is illustrative, not measurement-grade, and 30 MB.
The raw footage above is what any real measurement should be taken from.
