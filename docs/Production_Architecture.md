# Production Architecture — the self-contained AisleBot product

**Status: agreed direction, not yet built.** Written 21 Aug 2026 (§17.30) to
record the target the project is actually building toward, so that day-to-day
debugging work has something to aim at and so the sequencing decision below
isn't re-litigated every session.

---

## 1. The goal, in plain terms

One self-contained product running on the robot itself:

- **No laptop, no Foxglove, no third-party software.** Open a browser on a
  phone or tablet, connect to the robot's own WiFi, and everything is there.
- **Map-first UI.** The map the robot built is the screen — not a panel
  beside the screen. Controls float over it, semi-transparent, the way a
  mobile game overlays a joystick on the world.
- **Both modes, one interface.** Drive it by hand when you want to; tell it
  where to go and let it drive itself when you don't.
- **Goals by name, not coordinates.** "Go to Rack A3", not
  "go to (2.31, -1.74, 0.4)".
- **Avoids obstacles** — including ones that weren't there when the map was
  made (a pallet left in an aisle, a person walking past).

The deployment context is a narrow-aisle warehouse: the robot fetches and
carries cargo between known locations (racks, staging areas, a charging
spot), driven by an operator who knows the warehouse but not robotics.

## 2. Why independent, and what that rules out

Foxglove is a developer instrument. It requires a laptop on the same
network, manual panel configuration, knowledge of frame names and topic
names, and it renders raw robot state rather than an operator's view of the
job. It has been invaluable for debugging and will stay in the toolbox for
exactly that — but nothing in the shipped product may depend on it.

Concretely, that means the following must move into the robot's own
dashboard, because today they only exist in Foxglove:

- Seeing the map
- Seeing where the robot currently is on that map
- Sending a goal ("click-to-goal")

## 3. Key architectural decisions

### 3.1 Saved map + AMCL, not continuous SLAM — and why

This is the decision that everything else depends on, so it's worth being
precise about.

**Live SLAM creates a fresh map origin every time the robot boots.** The map
frame is anchored wherever the robot happened to be at its first scan
(§17.12/§17.18 spent two sessions proving this on this exact robot). So
coordinates `(2.31, -1.74)` refer to a different physical floor tile
tomorrow than they do today.

Named locations cannot survive that. "Rack A3" is only meaningful if the
coordinate system it's expressed in is the same one next week. **A saved map
loaded by `map_server`, with AMCL localizing against it, keeps the map frame
fixed forever.** That stability is the foundation the entire location
library rests on.

### 3.2 "Constant mapping" and obstacle avoidance are two different things

A natural assumption is that the robot must keep mapping continuously in
order to avoid obstacles that appear after the map was made. It doesn't, and
conflating the two would force the unstable-coordinates problem above for no
benefit.

Nav2 already separates these:

| Layer | Source | Purpose | Persists? |
|---|---|---|---|
| **Static layer** | the saved map | walls, racks, permanent structure | yes, fixed |
| **Obstacle layer** | live LiDAR (`/scan_reliable`) | whatever is there *right now* | no, transient |

The local costmap is rebuilt continuously from live LiDAR regardless of
whether SLAM is running. A pallet left in an aisle, or a person walking
past, appears in the obstacle layer within one scan and the controller
plans around it. This is already configured in `nav2_params.yaml` and is
already how `nav2_slam.launch.py` behaves today.

**So: the map is remembered and stable; obstacle avoidance is live and
reactive. Both, without continuous SLAM.**

Re-mapping is then an occasional, deliberate maintenance action — run when
the warehouse layout actually changes, not continuously.

### 3.3 Locations are taught by driving, not described

The robot is never told "there is a rack at these coordinates." It is
**driven to the spot once and the spot is given a name.** This is how
commercial AMRs do it, and it removes any need for the operator to think in
coordinates or to measure anything.

A location library — a JSON file on the Pi — holds the mapping:

```json
{
  "map": "warehouse_ground_floor",
  "locations": [
    {"name": "Rack A3",  "x": 2.31,  "y": -1.74, "yaw": 0.40},
    {"name": "Staging",  "x": 0.85,  "y":  3.10, "yaw": -1.57},
    {"name": "Home",     "x": 0.00,  "y":  0.00, "yaw": -1.5708}
  ]
}
```

Each entry is created by: drive there manually → tap "Save this spot" →
type a name. The dashboard reads the robot's live `map → base_link`
transform and writes the row. Nothing is measured by hand.

The library is tied to a specific saved map by name — re-mapping the site
invalidates the taught locations, which is correct and should be surfaced
in the UI rather than hidden.

## 4. The three phases of operation

| Phase | How often | What happens | Who |
|---|---|---|---|
| **Commission** | Once per site (or after a layout change) | Manual drive around the warehouse with SLAM running; save the map | Technician |
| **Teach** | Once per location | Drive to each rack/station; save it with a name | Technician |
| **Operate** | Every working day | Load saved map; AMCL localizes; operator taps a name; robot drives there | Operator |

The operator never sees SLAM, coordinates, frames, or ROS. They see a map,
a list of place names, a joystick, and a stop button.

## 5. The interface

One screen, layered:

- **Base layer — the map.** The saved occupancy grid, rendered as the
  background, filling the screen. Pan and zoom.
- **On the map:** the robot's live pose (position + heading), its planned
  path when driving autonomously, live LiDAR returns, and pins for every
  taught location.
- **Floating overlay — controls.** Semi-transparent, thumb-reachable:
  joystick for manual drive, speed selector, arm/UV controls, and a
  prominent E-STOP that is always visible in every mode.
- **Goal entry, two ways:** tap a named location from a list, or long-press
  anywhere on the map to send the robot to an arbitrary point.
- **Status, always visible:** what the robot is doing right now (idle /
  driving to X / arrived / blocked / stopped), and whether it is confident
  about where it is.

Design intent: an operator who has never seen ROS should be able to send the
robot somewhere within ten seconds of picking up the tablet, and should
never need to know that Nav2 exists.

## 6. Technical architecture

### 6.1 What already exists — more than expected

`phone_dashboard.py` is already the right shape for this:

- **A ROS 2 node** (`rclpy`) — so it can subscribe and publish directly, no
  bridge needed
- **A FastAPI + `uvicorn` web server** on port `8080`, reachable from any
  device on `AisleBot-Pi`
- **A live WebSocket** (`/ws`, with a tracked client set) already streaming
  between browser and robot
- Already publishes `/cmd_vel_manual` (manual drive), `/arm/command`,
  `/esp32/command`
- Already runs and stops the mapping stack as a managed subprocess

`twist_mux` (added §17.26, first run on hardware 21 Aug) arbitrates manual
input over autonomous output, so the manual joystick always wins over a
running goal — a safety property this product needs and now has.

Nav2's goal interface is a single topic: a `PoseStamped` on `/goal_pose`.
`goal_pose_adapter.py` already handles this robot's non-standard yaw
convention.

### 6.2 What has to be added

| Piece | What it does | Rough shape |
|---|---|---|
| **Map streaming** | Subscribe `/map` (`OccupancyGrid`), push to browser over the existing WebSocket | Convert the grid to a PNG server-side, send on change; metadata (resolution, origin) with it |
| **Live pose streaming** | Subscribe `/tf`, push `map → base_link` at ~10 Hz | Small JSON payload on the same socket |
| **Map canvas** | Render map + robot + path + scan in the browser | HTML5 canvas; world↔pixel transform from the grid metadata |
| **Goal sending** | Publish `/goal_pose` from a tap | Reuse `goal_pose_adapter`'s convention handling |
| **Location library** | Store, list, add, delete named locations | JSON file + REST endpoints |
| **Teach flow** | "Save current spot as…" | Read live TF, append to library |
| **Nav lifecycle control** | Start/stop the navigation stack from the UI | Same subprocess pattern the MAP button already uses |
| **Status reporting** | Surface Nav2 action feedback and AMCL confidence | Subscribe to the `NavigateToPose` action feedback |
| **UI rework** | Map-first layout, overlay controls, lighter theme | Replaces the current fixed-panel layout |

None of this requires new infrastructure — it is additive work on a server,
socket, and node that already run.

## 7. Build order — and the gate that comes first

**The reliability gate: goals must land where they are commanded.**

As of 21 Aug 2026 this is not true — commanded goals have been observed
driving off-target, and the journal's earlier "successful" goal runs
(§17.18/§17.19) predate significant config churn and, in one case
(§17.24), were explicitly recorded as never hardware-confirmed. A full
deploy audit that day also found the Pi had drifted from the repo in nine
files, including the SLAM config and the entire manual-override layer, and
found `esp32_bridge` pinning a CPU core at 99.9% since boot.

Building a location library and a goal-sending UI on top of navigation that
doesn't arrive accurately would mean putting a polished interface on an
unreliable robot, and would make the underlying problem *harder* to see, not
easier.

So:

```
  0.  Drive accuracy               <-- THE GATE. Nothing below is trustworthy until this passes.
      Goals land where commanded, repeatably, measured against tape.
        |
  1.  Mapping drive
      Wall-hugging manual drive; return to zero mark; error near zero.
        |
  2.  Save the map
      First saved map this project has ever produced.
        |
  3.  AMCL localization
      First hardware run of navigation.launch.py. Robot knows where it is
      on the saved map, across a restart.
        |
  4.  Location library + teach flow
      Backend first: JSON store, REST endpoints, save-current-pose.
        |
  5.  Map rendering in the dashboard
      The map, the robot, the scan — in the browser, not Foxglove.
        |
  6.  Goal sending from the dashboard
      Tap a name, robot goes. Foxglove no longer needed for anything.
        |
  7.  UI rework
      Map-first layout, overlay controls, lighter theme, status surface.
```

**Steps 5 and 6 are partially parallelizable** with 1–3: rendering `/map`
and the live pose in the browser depends on the map topic existing, not on
goals being accurate. If there is appetite to make visible product progress
while drive accuracy is being chased, map rendering is the safe piece to
start — it is useful as a debugging instrument regardless, and it is the
single biggest step toward cutting the Foxglove dependency.

## 8. Deliberately deferred

Recorded so they aren't forgotten, and so they don't expand today's scope:

- **Multi-robot / fleet coordination** — out of scope; single robot.
- **Cargo handling logic** (what to pick, inventory integration) — the arm
  exists and is controllable; deciding *what* to fetch is a layer above
  navigation and belongs after it works.
- **Autonomous exploration** (robot maps the site by itself) —
  `zero_point_scan.py` is a step in this direction, but commissioning by
  manual drive is simpler, more predictable, and sufficient.
- **Auto-docking / charging** — `opennav_docking` was deliberately removed
  from the launch stack (§17.17) since no dock hardware exists.
- **Off-site / cloud access** — the robot's own AP is the deployment
  network. No internet dependency in the product.
- **Hardware-independent E-STOP** — flagged in
  `Network_SelfHosted_AP.md`: since firmware v3.0 removed the ESP32's own
  WiFi, a dead Pi means the robot stops (watchdog) but cannot be driven.
  A physical RC E-STOP remains an open safety item for real deployment.
