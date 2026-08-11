# 11 Aug 2026 — Self-occlusion trial, clockwise sequence

Ground-truth photographs of the robot's physical orientation at each stop of the
clockwise half of the self-occlusion trial (`Research_Journal.md` §17.8).

**Why these exist.** The trial's logic is that *real environment features move in
the laser frame as the robot rotates, while self-occlusion does not* — so the
scan comparison is only meaningful if the robot genuinely reached the headings
it is supposed to have reached. These photos are the independent check on that,
separate from odometry (which is one of the things being validated and so cannot
be its own witness).

The robot rotates in place; the LiDAR is the black cylinder on the blue battery
pack (Position 2 mount, §17.4). The green tape marker on the floor and the
right-angle floor markings are the fixed reference — track them between frames
to read the rotation.

| Image | Caption |
|---|---|
| [`base_position_marking.jpg`](base_position_marking.jpg) | Top-down of the chassis rear edge with the green tape reference marker set against it. Establishes the physical datum the rotation is measured from. Also a clear view of the rear wheels and the chassis plate whose width was tape-measured at 36 cm (§17.7). |
| [`cw_000.jpg`](cw_000.jpg) | Starting heading, 0°. Chassis runs diagonally across frame, LiDAR/battery toward the right, green marker at the right-hand end. The tall mast — chrome rails, white printed blocks, lift motor, electronics — stands immediately behind the LiDAR; this is the structure expected to occlude. |
| [`cw_090.jpg`](cw_090.jpg) | After 90° CW. Robot now points away from the camera, LiDAR/battery at frame centre. Green marker visible at the chassis's lower-left. |
| [`cw_180.jpg`](cw_180.jpg) | After 180° CW. Chassis diagonal again but mirrored relative to 0° — LiDAR/battery now toward the **left**, green marker at the right. The battery bank and drive electronics along the chassis spine are clearly visible from this side. |
| [`cw_270.jpg`](cw_270.jpg) | After 270° CW. Robot points toward the camera; chassis extends to the lower-left. |
| [`cw_360.jpg`](cw_360.jpg) | Full rotation complete. **Matches `cw_000` — same diagonal, LiDAR/battery right, green marker at the right end.** Independent physical confirmation that the rotation closed, corroborating the near-identical 0°/360° scans observed live in Foxglove. |

**Result this supports:** the CW rotation closed cleanly in both the physical
record and the scan data — in-place rotation is the motion that most punishes
bad odometry or a wrong LiDAR mount offset, and neither shows a problem here.

**Still outstanding:** the counter-clockwise half of the trial, and the numeric
`/scan_reliable` captures needed to convert "the mast occludes something" into
specific angular sectors for the scan mask. Photographs establish that the
geometry is as assumed; they cannot substitute for the range data.
