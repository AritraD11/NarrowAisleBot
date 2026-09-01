# Evidence — Tuesday 1 Sep repeat test, and the intermittency verdict

One drive, `run_20260901_112335`, the basis of `Research_Journal.md` §17.48.
This was §17.47's repeat test: re-drive the front leg (zero → out toward
Entrance → back), same route, same style, same deployed config, to separate
route-geometry from intermittency as the explanation for the 6.8× spread
found the day before.

## The result

| | Front (31 Aug) | Front (repeat, 1 Sep) | Right (31 Aug) |
|---|---|---|---|
| Return to mark | 0.577 m | **0.209 m** | 0.085 m |
| Max correction | 0.678 m | **0.857 m** ← worst ever recorded | 0.280 m |
| Cumulative ÷ path | 0.562 m/m | 0.484 m/m | 0.305 m/m |
| D2 doubled | 5.1% | 2.8% | 5.2% |
| Corrections | 21 | 19 | 13 |

A third distinct number, on the identical route. Better on return-to-mark and
cumulative ratio, worse — the single worst in this project's history — on max
correction. **This is the intermittency verdict, not the route-geometry one:**
a stable route/geometry story predicts reproduction near 0.577 m; instead the
same aisle produced three different outcomes across three drives.

`front_leg_repeat_annotated.png` — red = doubled wall, blue = wheel path,
green = SLAM path, yellow = correction locations.

## The graph_residuals.py side-channel

Run alongside (log not recovered — lived only in the Pi's terminal scrollback,
not saved to a file that made it into this branch): **9 loop closures fired
over the 230 s drive, `moved=0` and `max_shift=0.000 m` throughout, every
closure at 0.0% implied drift.** The back end stayed perfectly healthy through
all of it. Consistent with §17.40/§17.42 — confirms yet again that the fault
is the front end (`map→odom`), not loop closure.

## What did not happen today

The actual S1 commissioning drive (wide outer-wall perimeter) was set up —
robot re-zeroed, MAP restarted — but the session concluded before it was
driven. G4 remains unattempted today beyond the repeat test.
