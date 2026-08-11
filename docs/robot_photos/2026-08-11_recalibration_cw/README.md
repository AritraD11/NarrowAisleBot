# 11 Aug 2026 — Self-occlusion re-measurement (clockwise)

Second, cleaner pass at the self-occlusion trial first attempted in
[`2026-08-11_occlusion_trial_cw/`](../2026-08-11_occlusion_trial_cw/) — same
method (place a single reference block at a known bearing, rotate the robot in
place, watch where it appears/disappears in the live scan), redone with the
Foxglove display properly configured (`Fixed frame`/`Display frame` both
`base_link`, grid at 0.5 m resolution) so the readings could actually be
measured against the grid rather than eyeballed.

**⚠ These bearing numbers are superseded.** This trial was run *before* the
LiDAR orientation/mirror bug was found and fixed
(`2026-08-11_orientation_fix/`, `Research_Journal.md` §17.9). Every angle
recorded here is in the pre-fix, mirrored frame — the qualitative result
(there is a large, real blind sector caused by the rear mast) still stands,
but the specific degree values do not transfer to the corrected
`/scan_reliable` and must be re-measured before they're used for anything
(e.g. writing a scan mask). Tracked as an open item in Appendix B.6.

| Image | Caption |
|---|---|
| [`nab_cw_000.jpg`](nab_cw_000.jpg) | Physical robot, starting heading. |
| [`map_cw_000_marked.png`](map_cw_000_marked.png) | Corresponding scan, block position marked yellow. |
| [`nab_6cm_from_block_setup.jpg`](nab_6cm_from_block_setup.jpg) | The reference block placed 6 cm out — same clearance distance as the footprint cushion margin (`nav2_params.yaml`, §17.7), so this run does double duty as a danger-boundary check. |
| [`nab_cw_090.jpg`](nab_cw_090.jpg) / [`map_cw_090_marked.png`](map_cw_090_marked.png) | After 90° CW. |
| [`map_cw_180.png`](map_cw_180.png) | After 180° CW (no physical-robot photo taken at this heading). |
| [`nab_cw_270.jpg`](nab_cw_270.jpg) / [`map_cw_270.png`](map_cw_270.png) | After 270° CW. |
| [`nab_block_disappears_cw_side.jpg`](nab_block_disappears_cw_side.jpg) / [`map_block_disappears_boundary.png`](map_block_disappears_boundary.png) | The heading at which the block's return drops out of the scan, rotating CW — one edge of the blind sector. |
| [`nab_block_reappears_ccw_side.jpg`](nab_block_reappears_ccw_side.jpg) / [`map_block_appears_boundary.png`](map_block_appears_boundary.png) | The heading at which it reappears — the other edge. Noted at the time as "just a bit more than 270°," consistent with the 270° frame showing it already gone. |
| [`nab_cw_360.jpg`](nab_cw_360.jpg) / [`map_cw_360.png`](map_cw_360.png) | Full rotation complete — matches `cw_000`, confirming (again, independently of `2026-08-11_occlusion_trial_cw/`) that odometry and scan-matching close a full in-place rotation cleanly. |
| [`nab_extra_setup_view.jpg`](nab_extra_setup_view.jpg) | Additional setup/context view of the rig. |

**Result that does carry forward:** the blind sector is wide — roughly a
third of the full sweep — and centred on the mast side, not a thin wedge.
Re-running this same procedure post-fix is the next concrete step before any
scan-masking work (`Research_Journal.md` Appendix B.6).
