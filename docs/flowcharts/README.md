# Firmware flowcharts

Nine drawings of the running system, generated from one script so they stay consistent. They come from the code, not from older docs. See `QA_2026-10-02.md` for what was checked.

## Which file for which use

| Use | Files | Notes |
|---|---|---|
| Slides | `png/s1` to `png/s6` | 1760 x 990 drawn, PNG is 5280 x 2970. Text is 11.5 pt or larger when the figure fills a 13.33 in slide. |
| Report appendix, poster, A3 print | `png/h1` to `png/h3` | Dense. Text is 6 to 8 pt on a slide, so do not put these on one and expect people to read them. |
| Editing in PowerPoint, Illustrator, Inkscape | `svg/*.svg` | Vector. Fonts fall back to Segoe UI or Arial if IBM Plex is not installed. |

| File | What it shows |
|---|---|
| `s1_system_overview_slide` | The whole robot in 12 boxes: what runs at boot, what runs on demand, the two microcontrollers |
| `s2_drive_command_path_slide` | Manual and autonomous commands merging at `twist_mux`, down to the wheels, and the feedback loop back to odometry |
| `s3_navigation_chain_slide` | Goal click to Nav2 servers, smoother, collision monitor, axis adapter, `twist_mux` |
| `s4_perception_and_pose_slide` | LiDAR to `scan_relay` to `slam_toolbox`, odometry TF, TF tree |
| `s5_esp32_firmware_slide` | The two FreeRTOS tasks, PID chain, safety trips, latching E-STOP |
| `s6_boot_and_launch_slide` | systemd to start script to launch file, on-demand launches |
| `h1_whole_system_handout` | Every node and topic on one sheet |
| `h2_drive_paths_handout` | The two velocity paths with the watchdogs |
| `h3_esp32_firmware_handout` | ESP32 internals with the runtime tuning commands |

Colour code, same everywhere: blue manual drive, orange autonomous drive, black merged command to the wheels, green feedback and odometry, purple LiDAR and map, grey operator and control, dashed grey TF, red latent fault or safety.

## Rebuilding

```
python3 docs/flowcharts/flowcharts.py        # writes svg/ and runs the edge check
CHROMIUM=/path/to/chrome node docs/flowcharts/render_png.js 3     # writes png/ at 3x and runs the layout check
```

`render_png.js` needs Playwright and a Chromium. It exits non-zero if any text overflows its box, any band title overruns its band, or any label lands on a node or another label. `fonts/` holds the IBM Plex woff files (SIL Open Font License) so the PNGs render the same on any machine.

## Editing a figure

Each figure is one function in `flowcharts.py`. Nodes are placed with explicit coordinates and edges are lists of points, so a change is a coordinate edit. After any change run both commands above and look at the PNG; the checks catch overflow and collisions, not whether it reads well.

When the system changes (a node added, a topic renamed), update the figure and add a line to the QA file. The source of truth for what runs is the code and `docs/Firmware_Inventory.md`.
