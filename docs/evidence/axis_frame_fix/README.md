# Evidence — the map-frame rotation, and its fix

Two hardware recordings, both side-by-side (physical robot left, live map view
right), bracketing the fix described in `Research_Journal.md` §17.38–§17.39 and
`Axis_Convention.md`. Kept for the APS report and because the fault is far
easier to show than to describe.

Both were driven with **W/S/D/A only** — no `Q`/`E`, so no commanded rotation
at any point. Every run starts and ends physically on the zero mark.

---

## `01_fault_wsda_before_fix.mp4` — the fault

Recorded 26–27 Aug 2026, **before** the fix. The robot's painted axes are
visible in the left panel: `+Y` toward the marked nose, `+X` to its right.

Read off the pose card frame by frame:

| Key pressed | Physical motion | Map frame showed |
|---|---|---|
| `W` | forward | `X` 0.054 → 0.207, `Y` pinned at 0.000 |
| `S` | backward | `X` 0.207 → −0.005 |
| `D` | right | `Y` 0.000 → −0.211, `X` unchanged |
| `A` | left | `Y` −0.211 → −0.008 |

So the map answered `W→+X, S→−X, D→−Y, A→+Y` while the robot's own painted
axes said forward was `+Y`. The footprint on the canvas confirms it
independently: drawn **wide, long axis and heading arrow along map `+X`**,
for a chassis that is 1.12 m along its nose axis and 0.48 m across.

`NOSE` reads `0.0°` in this video only because the dashboard of the day added
a `+90°` display offset; raw `map→base_link` yaw was `−90°`.

## `02_square_wdsa_after_fix.mp4` — the fix, and what is still wrong

Recorded 27 Aug 2026 immediately after deployment. Run
`run_20260827_140207`; full telemetry in
`data/field_runs/run_20260827_140207_bundle.json`, openable in
`docs/tools/run_viewer.html`.

A closed square: **W → D → S → A**, forward, right, back, left, returning to
the mark. Segmented from wheel odometry:

| Leg | Δ on intended axis | Δ on other axis | Δyaw |
|---|---|---|---|
| `W` forward | **+0.2741 m** on `Y` | +0.0001 m | −0.01° |
| `D` right | **+0.3673 m** on `X` | −0.0002 m | −0.06° |
| `S` back | **−0.3118 m** on `Y` | −0.0004 m | −0.04° |
| `A` left | **−0.4065 m** on `X` | +0.0012 m | +0.03° |

Closure **2.58 cm**, total yaw drift **−0.10°** over the whole square. Legs
are unequal because the keys were held for different durations by hand; that
is manual driving, not a calibration result.

**This video also captures the problem that remains.** At **17→18 s** the
pose card jumps from `X 0.114, Y 0.304` to `X 0.012, Y 0.013` — a ~31 cm
discontinuity inside one 10 Hz sample, while wheel odometry moved 5 mm. That
matches jump event 3 in the bundle (`corr_m 0.327` at map `(0.14, 0.30)`)
and is a **loop-closure correction, not an axis problem**. Three such events
occur in the run. See §17.39.

---

## What these do and do not show

They show that the frame convention is correct and coherent end to end:
`base_link`, `odom` and `map` all use `+X = right, +Y = forward`.

They say **nothing** about map quality. `Axis_Convention.md` states this
explicitly and it is worth repeating here: frame convention and geometric
integrity are independent questions, and confidence in one is not evidence
about the other. Video 02's own pose jumps are the counter-example.
