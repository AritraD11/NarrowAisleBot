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
| Path was a closed circle, zero to zero, no in-place rotation | operator, describing the drive | reported, not yet independently reviewed frame-by-frame (see below) |
| Speed was NORMAL / 0.10 m/s (not SLOW) | dashboard screenshot, `COMMAND LIMIT: MED — 0.10 m/s` | confirmed, read directly off the screenshot |
| Dashboard pose at end of run: `X −0.001, Y 0.000, NOSE 0.1°`, `DRIFT 0.000 m`, `JUMPS 0` | dashboard screenshot | confirmed, read directly off the screenshot |
| `VALID 65% of 323`, `CHURN 16%/sweep`, `107 masked (rear wedge)` | dashboard screenshot | confirmed, read directly off the screenshot |
| Physical ground-truth offset from the zero mark: **−2°, −3.0 (cm? m?)** | operator's tape/protractor check | units not yet confirmed. Assumed cm (0.03 m) given the room scale and "which is good," but this needs to be stated explicitly before it goes anywhere near the report: 3 cm and 3 m are a very different result |
| Whether the map was saved (second **MAP** tap, the only action that persists it) vs. still running | not stated | unconfirmed. The screenshot's **STOP MAP** button is the one shown active, consistent with the session still being live at capture time |
| scan_relay gate state during this drive (RAW / leftover STRICT / something else) | not stated | unconfirmed |
| Actual driven path length (circle diameter times pi) | not measured | unconfirmed, and it matters: the whole odometry-closure prediction in §3.2 is a function of path length, and this wasn't the 8 m route that prediction was built for |

None of the above are corrections to what the operator said. They're the
specific follow-ups needed before this run's numbers can be used for
anything beyond "the robot completed a closed loop with a small measured
offset."

## `01_circular_loop_drive.mp4`

Screen recording of the dashboard during the drive, provided by the
operator. **Not yet reviewed frame-by-frame.** This environment has
neither `ffmpeg` nor a Python video-decoding library installed, and an
`apt-get install ffmpeg` attempt partially failed against the package
mirror. Filed here as the primary record; a proper pass (trajectory shape,
any visible fold in VIEW, timing of the churn/valid numbers through the
run rather than just the endpoint) needs that tooling first.

sha256: `beb159b9cc60084705793bcaa72fd1d263288f213cbae35c413dc3c226bf132a`
