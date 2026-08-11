# LiDAR Orientation Calibration — What Happened and How It Was Fixed

11 Aug 2026. Companion to `Research_Journal.md` §17.8–§17.9. Photographic
evidence in `docs/robot_photos/2026-08-11_recalibration_cw/` and
`docs/robot_photos/2026-08-11_orientation_fix/`.

## Summary

The LiDAR's scan data was reflected — objects to the robot's front and rear
were swapped, while left and right were correct. Not a mounting-angle error
(which a static transform could fix) and not a hardware fault: the sensor's
own angle indexing didn't match the direction it was physically bolted on
facing. Diagnosed by placing a single reference block at three known
bearings and solving for the relationship between where it should appear and
where it did. Fixed in software, in `scan_relay.py`, which already sits
between the driver and everything downstream.

## How it was found

Investigating self-occlusion (which angular sectors the robot's own rear
mast blocks — `Navigation_Theory.md` §4) required rotating the robot in
place and watching a known reference object in the live scan
(`docs/robot_photos/2026-08-11_recalibration_cw/`). That trial went fine on
its own terms — a wide blind sector was measured, the rotation closed
cleanly — but a side observation didn't add up: a block placed in front of
the robot was showing up *behind* it in the map.

The first hypothesis was a translation-only static-transform bug (the live
`base_link -> laser_frame` transform was found to be an unset placeholder,
`(0, 0, 0.02)` with zero rotation, rather than the actual Position 2 mount
offset). But a translation error cannot cause a front/back swap — TF
transforms are rigid motions, and getting the position wrong doesn't
relabel directions. Something else was wrong, and it needed measuring, not
guessing.

## The measurement

A single opaque block, placed at one known bearing at a time, `Fixed
frame`/`Display frame` both set to `base_link` in Foxglove (so the display
is base_link's own axes, not an arbitrary camera frame), `Theta` (camera
rotation) fixed at 0° throughout so every reading uses the same visual
convention.

Critically, "known bearing" was defined *empirically*, by how the robot
actually drives — `W` moves it toward `+Y`, `D` moves it toward `+X`,
confirmed by watching the robot move and the map update together
(`docs/robot_photos/2026-08-11_orientation_fix/forward_drive_confirmation.mp4`)
— not assumed from the ROS/REP-103 textbook convention (which puts
"forward" on `+X`). This distinction mattered: an earlier pass at this fix,
derived by assuming REP-103, got a number 90° away from the one that
actually matches this robot. The textbook convention describes how *most*
ROS robots are wired; it doesn't describe this one for free, and the first
attempt at this fix would have been wrong had it shipped.

Three placements, three readings:

| Block truly at | Expected bearing | Reported bearing |
|---|---:|---:|
| Right (`base_link` `+X`) | 0° | 270° |
| Front (`base_link` `+Y`) | 90° | 180° |
| Left (`base_link` `-X`) | 180° | 90° |

(`docs/robot_photos/2026-08-11_orientation_fix/block_at_right.jpg`,
`block_at_front.jpg`, `block_at_left.jpg`)

## The math

All three solve one relationship:

$$\text{reported} = 270° - \text{true} \pmod{360°}$$

Check: $270 - 0 = 270$. $270 - 90 = 180$. $270 - 180 = 90$. All three, exactly.

**Why this is a reflection, not a rotation**, and why that distinction is
the whole point: a rotation adds the *same* signed offset at every heading —
$\text{reported} - \text{true}$ would be constant. Here it isn't (270°, 90°,
270°). What *is* constant is $\text{reported} + \text{true} = 270°$ at every
heading — the signature of a mirror about a fixed line, not a turn. Left and
right individually read correctly when checked alone; it's specifically
front and back that are swapped, which is exactly what reflecting about the
robot's left-right axis produces.

This is the fact that rules out a TF-based fix. `tf2` transforms compose
rotations and translations — proper rigid motions. A reflection is not a
rigid motion (it inverts handedness); no rotation, at any angle, equals a
mirror. So no `base_link -> laser_frame` static transform, correctly
measured or not, could have fixed this. The correction has to act on the
scan data's angle indexing directly.

Solving the same relationship for the fix (published bearing should equal
true bearing):

$$\text{true} = 270° - \text{reported}$$

which in `mirror`/`yaw_offset` form (see code below) is `mirror = True`,
`yaw_offset = 270°`.

**The number that was almost shipped instead:** an initial derivation,
before the empirical `W`/`D` measurement, assumed `base_link`'s forward axis
was `+X` (REP-103) and produced `yaw_offset = 180°`. Every one of the three
measurements above is 90° away from what that value would correct to. It was
never deployed — caught by insisting on driving-based measurement over
textbook assumption before locking anything in.

## The fix

`src/scan_relay/scan_relay.py` — already the one node sitting between the
driver's `/scan` and everything else's `/scan_reliable` (originally built to
bridge a QoS mismatch, §13.4). Re-indexes each incoming scan through a cached
angle map:

```python
MIRROR = True
YAW_OFFSET = math.radians(270.0)   # true = -reported + 270 deg
```

with the correction applied as an index remap (pull each output bin's value
from the appropriate input bin) rather than per-message trigonometry, so the
map is computed once per scan geometry and reused every message after that.

Verified two ways before deployment:
1. Algebraically, against all three measured points plus a fourth
   (untested) heading as a sanity check.
2. Through the actual index-remapping function used at runtime, not just
   the point arithmetic — confirming the implementation matches the derivation,
   not only the theory.

Both passed. Deployed, and confirmed by the user against a live map: "now
it maps perfectly."

## What's still open

- **The blind-sector measurements in
  `docs/robot_photos/2026-08-11_recalibration_cw/` predate this fix** and are
  in the old, mirrored frame. The qualitative finding (a wide blind sector
  from the rear mast) stands; the specific degree values need re-measuring
  against the corrected `/scan_reliable` before they're used for anything,
  e.g. writing a self-occlusion scan mask.
- **The `base_link -> laser_frame` translation is still wrong** — still the
  unset-placeholder `(0, 0, 0.02)` rather than Position 2's actual offset.
  This fix corrected the scan's *angle* convention, not the mount's
  *position* in TF; they're independent bugs. `tools/scan_bearing.py` (added
  same session) can help re-derive this if it's tackled directly, though the
  block-placement method used here worked without it.
- Re-run `tools/scan_bearing.py` against `/scan_reliable` post-fix as a
  numeric double-check, now that the tool and the fix exist together.

See `Research_Journal.md` Appendix B.6 for these as tracked open items.
