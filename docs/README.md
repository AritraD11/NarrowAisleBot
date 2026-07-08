# NarrowAisleBot — Documentation Index

Markdown is the source of truth here (diffs cleanly, renders on GitHub, greppable). Original `.docx`/`.pdf` files are kept in `originals/` as the source of record.

| Document | What it covers | Currency |
|---|---|---|
| [`Research_Journal.md`](Research_Journal.md) | The living project journal — vision, mechanical/electrical design, control-system debugging narrative, hurdles catalogue, autonomy roadmap, firmware deep-dive, open TODOs. **This is the primary document — keep it updated as the project progresses.** | Last updated 9 June 2026 (most current of the four) |
| [`Master_Reference.md`](Master_Reference.md) | Deep hardware/wiring/firmware reference — pin assignments, power architecture, PID+FF parameters, serial protocol, commissioning checklist. | v4.0, March 2026 |
| [`LiDAR_SLAM_Bringup.md`](LiDAR_SLAM_Bringup.md) | YDLIDAR X4 Pro + slam_toolbox bringup guide — hardware gotchas, confirmed driver params, the manual 3-terminal launch sequence. | Verified 26 June 2026 |
| [`Network_SelfHosted_AP.md`](Network_SelfHosted_AP.md) | Self-hosted WiFi AP setup (`AisleBot-Pi` @ 10.42.0.1) and the ESP32's own backup AP. | Current |
| [`Setup_Manual.md`](Setup_Manual.md) | Narrative fresh-Pi setup manual. Largely superseded by the root `install.sh` one-liner — kept as historical reference. | Superseded, historical |

Where documents disagree on a fact, prefer the one with the later date — the Research Journal is generally authoritative for current project state.
