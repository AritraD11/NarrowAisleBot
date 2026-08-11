# 11 Aug 2026 — LiDAR orientation bug: discovery and fix

The evidence trail behind `Research_Journal.md` §17.9 and the `scan_relay.py`
angle correction. Full technical write-up, math, and code:
[`docs/LiDAR_Orientation_Calibration.md`](../../LiDAR_Orientation_Calibration.md).

| Image / video | Caption |
|---|---|
| [`hand_drawn_axis_convention.jpg`](hand_drawn_axis_convention.jpg) | The first attempt to pin down "what does X/Y mean on this robot" — hand-drawn arrows on a printed top-down photo, done before realizing the question had to be answered empirically (by driving and measuring), not by convention alone. |
| [`paper_bag_obstacle_test.jpg`](paper_bag_obstacle_test.jpg) | An early sanity check: a paper bag placed beside the robot as a distinctive obstacle, to see whether it showed up in the map at all. It did — but this test predates knowing *where* it should show up, which is what the block-placement trial below actually pins down. |
| [`block_at_right.jpg`](block_at_right.jpg) | Reference block placed at the robot's physical right (same side as the user's own right, standing behind the robot facing its direction of travel). Foxglove: `Theta` (camera rotation) fixed at 0° throughout — this and the next two photos use one consistent viewing convention. Result: block appeared at screen-down, not screen-right. |
| [`block_at_front.jpg`](block_at_front.jpg) | Block placed directly ahead. Result: appeared at screen-left, not screen-up. |
| [`block_at_left.jpg`](block_at_left.jpg) | Block placed at the robot's physical left. Result: appeared at screen-up, not screen-left. |
| [`forward_drive_confirmation.mp4`](forward_drive_confirmation.mp4) | Side-by-side video (robot + live Foxglove map), block held at the front, driving forward (`W`) toward it. Confirms the block is genuinely physically ahead — ruling out "the block was never where you thought" as an explanation for the front/back mismatch above. |
| [`forward_drive_frame_start.jpg`](forward_drive_frame_start.jpg) | First frame of the video: robot and block both distant from the origin/each other. |
| [`forward_drive_frame_end.jpg`](forward_drive_frame_end.jpg) | Last frame: robot has closed the distance, block's map position has moved correspondingly closer to the origin. Direction of travel is toward the block in both the real-world and map panes — the geometry check that motivated ruling out a simple frame swap and pursuing the reflection hypothesis instead. |

**Result:** three placements (right/front/left) all solve one consistent
relationship — a reflection, not a rotation — fixed in `scan_relay.py` with
`mirror=True, yaw_offset_deg=270`. Confirmed by the user afterward: "now it
maps perfectly." Full derivation in
[`docs/LiDAR_Orientation_Calibration.md`](../../LiDAR_Orientation_Calibration.md).
