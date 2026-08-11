# LiDAR Orientation Calibration — What Happened and How It Was Fixed

11 Aug 2026. Companion to `Research_Journal.md` §17.8–§17.10. Photographic
evidence in `docs/robot_photos/2026-08-11_recalibration_cw/` and
`docs/robot_photos/2026-08-11_orientation_fix/`.

**This doc was rewritten the same day it was first written**, because the
fix it originally described was itself wrong. Left in as a full account of
both rounds rather than quietly edited to look right the first time — the
wrong turn is as much a part of the record as the correct answer, and it's
the reason the correct answer is trustworthy rather than a second guess.

## Summary

The LiDAR's scan data was **reflected** — objects to the robot's front and
rear were swapped, while left and right individually read correctly. Not a
mounting-angle error (a static transform could have fixed that) and not a
hardware fault: the sensor's own angle indexing didn't match the direction
it was physically bolted on facing. Fixed in software, in `scan_relay.py`,
which already sits between the driver and everything downstream.

**Final, confirmed values: `mirror = True`, `yaw_offset = 180°`.**

Getting to that number took two attempts. The first (180°, assuming
standard ROS convention) was correct but got second-guessed and replaced
with a wrong one (270°, based on an unverified claim about which way the
robot's own axes point) before deployment. The wrong version was deployed,
looked correct on its own test, then failed a second, independent test —
which is exactly what led back to 180°. That arc is the useful part of this
document, not just the final numbers.

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

## Round 1: the reflection, diagnosed correctly; the rotation, diagnosed wrong

A single opaque block, placed at one known bearing at a time, `Fixed
frame`/`Display frame` both set to `base_link` in Foxglove, `Theta` (camera
rotation) fixed at 0° throughout.

"Known bearing" was defined by an *asserted* driving convention — `W` moves
the robot toward `+Y`, `D` toward `+X` — said to be confirmed by watching
the robot and the live map together. This assertion turned out to be wrong
(see Round 2), but it produced an internally self-consistent set of
readings:

| Block truly at | Expected bearing (per the `W`/`D` claim) | Reported bearing |
|---|---:|---:|
| Right (`base_link` `+X`) | 0° | 270° |
| Front (`base_link` `+Y`) | 90° | 180° |
| Left (`base_link` `-X`) | 180° | 90° |

(`docs/robot_photos/2026-08-11_orientation_fix/block_at_right.jpg`,
`block_at_front.jpg`, `block_at_left.jpg`)

All three solved one relationship: $\text{reported} = 270° - \text{true}$.

**The reflection diagnosis drawn from this data was correct, and still
holds.** A rotation adds the *same* signed offset at every heading —
$\text{reported} - \text{true}$ would be constant. Here it wasn't (270°,
90°, 270° across the three headings). What *was* constant was
$\text{reported} + \text{true}$ (270° every time) — the signature of a
mirror about a fixed line, not a turn. That's why the correction has to
live in the scan data itself: `tf2` composes rotations and translations —
proper rigid motions — and a reflection is not one; no
`base_link -> laser_frame` static transform, at any angle, equals a mirror.

**What was wrong was the rotation constant**, because it was only as good
as the `W`/`D` claim it was built on. Solving for the fix under that claim
gave `mirror=True, yaw_offset=270°`. An earlier, independent derivation —
made before the `W`/`D` claim, assuming the standard ROS convention
(REP-103: forward on `+X`) instead — had produced `yaw_offset=180°`, 90°
away from this. At the time, 180° looked like the thing to discard: it
disagreed with the empirical-sounding `W`/`D` measurement, so 270° shipped.

**Deployed, and it appeared to work** — a live block-placement check after
deployment showed objects appearing at the expected bearing. But that check
shared its assumption with the fix it was checking (both used the same
`W`/`D` claim for "expected"), so agreement with it was not independent
confirmation. It could only ever pass.

## Round 2: an unrelated symptom exposes the real answer

Immediately after deployment, driving the robot forward made the
accumulated `/map` shift **sideways** relative to the robot, not backward
as a correctly-tracked forward move should look. This has nothing to do
with scan angles — it's whether the robot's *estimated direction of
travel* (odometry) matches its *real* direction of travel. An
angle-tracking fix should not have been able to cause a translation-tracking
symptom; that mismatch was reason enough to check rather than assume it was
unrelated noise.

**Checked against raw odometry, not a screenshot** —
`ros2 run tf2_ros tf2_echo odom base_link`, logged before and after two
controlled, single-axis, physically-confirmed moves:

| Move | dX | dY | Reads as |
|---|---:|---:|---|
| Forward only (`W`) | +0.257 m | +0.015 m | **94% of motion in X** |
| Strafe right only (`D`) | +0.011 m | −0.287 m | **96% of motion in Y** |

That is REP-103, exactly — `base_link`'s real `+X` is forward, `+Y` is left
— the opposite of the `W`/`D` claim Round 1 was built on, and the same
convention the *first*, discarded derivation had used.

**Re-solving Round 1's original three measurements with forward correctly
assigned to `+X`** reproduces that first derivation exactly, no residual:

| Block truly at | True bearing (REP-103) | Reported (raw, unchanged) |
|---|---:|---:|
| Right | −90° | 270° |
| Front | 0° | 180° |
| Left | 90° | 90° |

All three: $\text{reported} = 180° - \text{true}$.

## The fix, final

`src/scan_relay/scan_relay.py` — the node bridging `/scan` to
`/scan_reliable` for QoS reasons (§13.4), which now also re-indexes each
scan through a cached angle map built once per scan geometry:

```python
MIRROR = True
YAW_OFFSET = math.radians(180.0)   # true = -reported + 180 deg
```

Verified through the actual runtime index-remapping function — not just the
point algebra — against all three block measurements under the corrected
axis assignment. All pass; pass-through mode (`mirror=False,
yaw_offset=0`) remains the exact identity map.

## What actually decided this, and why it's worth remembering

"Measure, don't assume" is only as good as the measurement. A visual read
of a live display — watching the robot and a map together and judging
which arrow it moved toward — is a real measurement, better than a guess,
but it is a *weaker* one than a raw number logged before and after a
controlled, single-axis motion. Where the two disagreed here, the raw
number was the one that turned out to be right. The practical version of
this lesson: when a claimed convention is being used to calibrate
something, look for an independent way to check the claim itself before
trusting derivations built on it.

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
  same session) can help re-derive this if it's tackled directly.
- Re-run `tools/scan_bearing.py` against `/scan_reliable` post-fix as a
  numeric double-check, now that the tool and the corrected fix both exist.

See `Research_Journal.md` Appendix B.6 for these as tracked open items.
