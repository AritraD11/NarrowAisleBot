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
this number, since STRICT makes a map cleaner, not bigger; only driving
further will.

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
