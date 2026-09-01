#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  AisleBot Phone Dashboard v2.5                                   ║
║  ROS2 Node + FastAPI WebSocket on port 8080                      ║
║                                                                    ║
║  Controls:                                                       ║
║    • Drive joystick (vx / vy) + separate yaw slider              ║
║    • Speed: SLOW (33%) / NORMAL (67%) / FAST (100%)              ║
║    • Arm: LIFT / LOWER / OPEN / CLOSE (hold to move)             ║
║    • Map -> mapping_full.launch.py + telemetry recording,        ║
║      together, one action -> ~/aislebot_logs/run_*.csv           ║
║    • E-STOP (latches) / CLEAR                                    ║
║                                                                    ║
║  FIXES in v2.1:                                                  ║
║    • Speed buttons: touchstart replaces onclick (mobile fix)     ║
║    • MAX_LINEAR lowered to 0.15 m/s (prevents motor saturation)  ║
║    • Auto-ENABLE arm on WebSocket connect                        ║
║    • ESTOP CLEAR also re-enables arm                             ║
║                                                                    ║
║  NEW in v2.2 -- desktop/PC support (no touchscreen needed):      ║
║    • All controls also bound to mouse (click + drag)             ║
║    • Hidden keyboard control, not shown anywhere in the UI:      ║
║        W/A/S/D  -> drive joystick                                ║
║        Q/E      -> yaw (Q = CCW, E = CW)                         ║
║        M        -> toggle mapping                                ║
║                                                                    ║
║  NEW in v2.3 -- Map button (Research_Journal.md Part XVI 16.11): ║
║    • Replaces RECORD RUN. One press starts mapping_full.launch.py║
║      (lidar + relay + slam_toolbox, as a managed subprocess      ║
║      group) AND telemetry/PID recording together -- every run    ║
║      is recorded by default, no separate toggle.                 ║
║    • Second press (or E-STOP) SIGINTs the launch tree's process  ║
║      group and stops recording, together.                        ║
║    • Same UI slot is a deliberate placeholder for a future        ║
║      "Autonomous Drive" button once SLAM is trusted -- not built  ║
║      yet, this is trigger-only.                                   ║
║                                                                    ║
║  NEW in v2.4 -- CALIBRATE button (Research_Journal.md 17.20-17.21)║
║    • Runs tools/zero_point_scan.py as a managed subprocess: at    ║
║      each of four 90-deg headings it checks whether /map actually ║
║      grew, nudges <=0.15 m ONLY if it did not, and returns to the ║
║      exact start pose as its final action. Fills the 360-deg base ║
║      map from the zero mark without hand-driving it.              ║
║    • THIS IS THE FIRST BUTTON THAT COMMANDS AUTONOMOUS MOTION.    ║
║      Everything below exists because of that, not for polish:     ║
║        - Two-tap arm. One stray tap cannot start a 45 kg robot.   ║
║        - Refuses to start unless mapping is live AND bt_navigator ║
║          is on the graph -- without both, the script would fail   ║
║          obscurely several seconds in rather than plainly now.    ║
║        - Second press = SIGINT, which the script traps to drive   ║
║          home before exiting. E-STOP = SIGKILL + a cancel-all on  ║
║          /navigate_to_pose, because killing the script alone      ║
║          leaves Nav2 still executing its last accepted goal.      ║
║        - stdout/stderr -> ~/aislebot_logs/calib_*.log, and the    ║
║          last lines are polled back to the phone, so a run that   ║
║          misbehaves is diagnosable afterwards rather than silent. ║
║                                                                    ║
║  NEW in v2.6 -- the display compensations are GONE, because the   ║
║  frame underneath them was fixed (Research_Journal.md §17.38):    ║
║    • odometry_publisher.py used to publish rotated orientation    ║
║      but UNrotated translation, which defined odom's axes to be   ║
║      REP-103's and left a constant -90 deg seam that map          ║
║      inherited. Forward drive really did increase map X. Every    ║
║      compensation in this file existed to hide that.              ║
║    • It is fixed at the source now: odom, map and base_link all   ║
║      share +X=right, +Y=forward. Forward drive increases map Y.   ║
║      So this file prints the raw map frame verbatim, and that IS  ║
║      ordinary graph paper -- no relabel, nothing to keep in sync. ║
║    • DISPLAY_ROT = 0. It existed to spin the canvas so forward    ║
║      looked like up while map +X was forward. Map +Y is forward   ║
║      now and screen-up is already map +Y, so the correct value    ║
║      is zero. The rotation-aware label helpers (drawUpright /     ║
║      labelXGridline / labelYGridline) are kept and still correct  ║
║      -- at rot 0 they are the identity -- so the garbled-text bug ║
║      cannot come back if anyone ever sets it non-zero again.      ║
║    • NOSE prints raw yaw. The old +90 deg existed so that "on the ║
║      mark" read 0 deg while raw yaw was -90; raw yaw on the mark  ║
║      is 0 now, so the offset would introduce the error it used to ║
║      remove.                                                      ║
║    • Do NOT re-add a display-side axis fix here. If the printed   ║
║      X/Y ever disagrees with the robot again, the frame is wrong  ║
║      upstream and this is the wrong file to change -- read        ║
║      docs/Axis_Convention.md first.                               ║
║    • The Python ROS/control class below is unchanged (verified    ║
║      byte-identical against the deployed fork, 27 Aug) -- only    ║
║      this HTML/JS presentation layer ever differed.               ║
║                                                                    ║
║  ROS2 Topics:                                                    ║
║    Publishes  /cmd_vel_manual   geometry_msgs/Twist  (drive) —   ║
║      goes through twist_mux (config/twist_mux.yaml) before       ║
║      reaching the wheels, so it wins over Nav2 whenever this     ║
║      is actively publishing.                                     ║
║    Publishes  /arm/command      std_msgs/String       (arm)      ║
║    Publishes  /esp32/command    std_msgs/String  (<L1>/<L0>/…)   ║
║    Subscribes /motor_telemetry  std_msgs/Float64MultiArray       ║
║                                                                    ║
║  Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Empty, String, Float64MultiArray
import tf2_ros
from tf2_ros import TransformException

import threading
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import asyncio
import base64
import json
import csv
import math
import os
import contextlib
import signal
import subprocess
import time
from datetime import datetime
from typing import Optional, Set

from .run_report import generate_report, write_report

# ═══════════════════════════════════════════════════════════════════
#  ROBOT CONSTANTS
#  FIX: MAX_LINEAR lowered from 0.48 → 0.15 m/s
#       At 0.48, forward drive needed 6.3 rad/s — 2x the motor cap.
#       0.15 m/s gives max wheel speed ~1.97 rad/s — safe headroom.
#       SLOW/MED/FAST are now clearly different and always within limits.
# ═══════════════════════════════════════════════════════════════════
MAX_LINEAR_SPEED  = 0.15   # m/s   — matches established working value
MAX_ANGULAR_SPEED = 0.30   # rad/s — matches joy_to_aislebot parameter

SPEED_MODES = [
    {"name": "SLOW",   "mult": 0.33, "label": "0.05 m/s"},
    {"name": "NORMAL", "mult": 0.67, "label": "0.10 m/s"},
    {"name": "FAST",   "mult": 1.00, "label": "0.15 m/s"},
]

# ═══════════════════════════════════════════════════════════════════
#  HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════════
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>AisleBot</title>

<style>
:root{
  --bg:#f4f6f8;--panel:#ffffff;--panel-2:#f8fafc;--line:#d0d5dd;
  --text:#17202a;--muted:#667085;--blue:#1677ff;--blue-soft:#eaf2ff;
  --green:#12b76a;--green-soft:#e9f8f1;--amber:#f79009;--amber-soft:#fff4e5;
  --red:#d92d20;--red-soft:#fff0ee;--shadow:0 6px 24px rgba(16,24,40,.08);
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-user-select:none;user-select:none;touch-action:none}
html,body{width:100vw;height:100vh;overflow:hidden;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
button{font:inherit}
.hdr{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;
  background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);gap:10px;flex-shrink:0}
.hdr-left{display:flex;align-items:center;gap:10px;min-width:0}.hdr-title{font-size:15px;font-weight:800;letter-spacing:1.4px;white-space:nowrap}.hdr-sub{font-size:9px;color:var(--muted);font-weight:700;letter-spacing:.8px;white-space:nowrap}
.status-pills{display:flex;gap:4px;overflow:hidden}.state-pill{font-size:9px;font-weight:800;border:1px solid var(--line);border-radius:999px;padding:4px 7px;background:#fff;color:var(--muted);white-space:nowrap}.state-pill.good{color:#087443;background:var(--green-soft);border-color:#b7e6d0}.state-pill.bad{color:#b42318;background:var(--red-soft);border-color:#f4c7c2}.state-pill.muted{color:#667085;background:#f2f4f7}
.hdr-right{display:flex;align-items:center;gap:8px}.speed-label{font-size:9px;color:var(--muted);font-weight:700}.spd-group{display:flex;gap:4px}.spd-btn{min-width:54px;padding:6px 8px;border-radius:7px;border:1px solid var(--line);background:#fff;color:#667085;font-size:9px;font-weight:800;cursor:pointer;touch-action:manipulation}.spd-btn.active-slow{background:#edf9f3;color:#087443;border-color:#9dd9ba}.spd-btn.active-normal{background:#fff5e8;color:#a15c00;border-color:#f2c27a}.spd-btn.active-fast{background:#fff0ee;color:#b42318;border-color:#efaaa3}
.view-btn{padding:7px 11px;border-radius:7px;border:1px solid var(--line);background:#fff;color:#344054;font-size:9px;font-weight:800;cursor:pointer;touch-action:manipulation}.view-btn.on{background:var(--blue-soft);color:#1457b9;border-color:#a8c8ff}
.map-badge{font-size:9px;font-weight:800;padding:4px 7px;border-radius:999px;background:var(--blue-soft);color:#1457b9;display:none}.map-badge.show{display:inline-block}
.status-dot{display:none}.spd-indicator{height:22px;display:flex;align-items:center;justify-content:center;background:#f8fafc;border-bottom:1px solid var(--line);font-size:9px;color:var(--muted);font-weight:700;letter-spacing:.5px;flex-shrink:0}.spd-indicator #spdValue{color:#1457b9}
.body{display:flex;height:calc(100vh - 54px - 22px - 74px);min-height:0}
.joy-area{flex:1;position:relative;display:flex;align-items:center;justify-content:center;background:var(--bg);overflow:hidden}
.drive-info{position:absolute;top:12px;left:12px;z-index:3;display:flex;gap:8px;align-items:stretch;pointer-events:none}.info-card{background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:9px;padding:7px 9px;box-shadow:var(--shadow);min-width:92px}.info-card .k{font-size:8px;color:var(--muted);font-weight:800;letter-spacing:.6px}.info-card .v{font-size:14px;font-weight:800;margin-top:2px}.info-card .s{font-size:9px;color:var(--muted);margin-top:1px}
.motion-card{position:absolute;right:12px;top:12px;z-index:3;background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:9px;padding:8px 10px;box-shadow:var(--shadow);pointer-events:none;min-width:128px}.motion-card .title{font-size:8px;color:var(--muted);font-weight:800;letter-spacing:.6px}.motion-state{font-size:12px;font-weight:900;margin:2px 0 5px}.cmd-row{display:grid;grid-template-columns:28px 1fr;gap:4px;font-size:9px;color:#475467}.cmd-row strong{font-weight:800;color:var(--text)}
.joy-ring{width:min(58vw,280px);height:min(58vw,280px);max-width:62vh;max-height:62vh;border-radius:50%;border:2px solid #b9c5d3;background:radial-gradient(circle,#fff 0%,#f7f9fb 65%,#eef2f5 100%);position:relative;flex-shrink:0;cursor:grab;box-shadow:inset 0 0 0 12px rgba(22,119,255,.025),0 10px 28px rgba(16,24,40,.06)}
.joy-ring::before,.joy-ring::after{content:'';position:absolute;background:#d7dee7;pointer-events:none}.joy-ring::before{width:1px;height:78%;left:50%;top:11%}.joy-ring::after{height:1px;width:78%;top:50%;left:11%}
.joy-thumb{width:66px;height:66px;border-radius:50%;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:radial-gradient(circle at 34% 30%,#5ea5ff,#1677ff 65%,#0f5fd1);box-shadow:0 7px 18px rgba(22,119,255,.28);transition:box-shadow .1s}.joy-thumb.active{box-shadow:0 10px 24px rgba(22,119,255,.42)}
.jlbl{position:absolute;font-size:8px;color:#98a2b3;font-weight:800;letter-spacing:.8px}.jlbl.t{top:6%;left:50%;transform:translateX(-50%)}.jlbl.b{bottom:6%;left:50%;transform:translateX(-50%)}.jlbl.l{left:5%;top:50%;transform:translateY(-50%)}.jlbl.r{right:5%;top:50%;transform:translateY(-50%)}
.right-panel{width:126px;display:flex;flex-direction:column;border-left:1px solid var(--line);background:#fff;flex-shrink:0;transition:width .18s ease}.right-panel .section-title{font-size:8px;color:#98a2b3;font-weight:800;letter-spacing:.8px;text-align:center}
body.map-mode .right-panel{width:70px}.yaw-wrap{flex:2;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:10px 0;gap:7px;border-bottom:1px solid var(--line)}.yaw-lbl{font-size:8px;color:#98a2b3;letter-spacing:1px;font-weight:800}.yaw-track{width:24px;flex:1;max-height:120px;background:#f2f4f7;border-radius:12px;border:1px solid #c9d2dc;position:relative;cursor:pointer;touch-action:none}.yaw-thumb{width:38px;height:38px;border-radius:50%;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);background:radial-gradient(circle at 35% 30%,#ffd591,#f79009 70%);box-shadow:0 6px 14px rgba(247,144,9,.25)}
.arm-section,.lift-section{display:flex;flex-direction:column;padding:7px;gap:6px;justify-content:center}.arm-section{flex:3;border-bottom:1px solid var(--line)}.lift-section{flex:2}body.map-mode .arm-section,body.map-mode .lift-section{display:none}body.map-mode .yaw-wrap{flex:1;border-bottom:none;padding:14px 0}.arm-btn,.lift-btn{flex:1;border-radius:7px;cursor:pointer;touch-action:manipulation;font-weight:800}.arm-btn{border:1px solid #b7e6d0;background:#f1fbf6;color:#087443;font-size:9px}.arm-btn:active,.arm-btn.held{background:#dff5e9}.lift-btn{border:1px solid #b9d5ff;background:#f3f7ff;color:#1457b9;font-size:10px}.lift-btn:active,.lift-btn.held{background:#e5efff}
.bottom{height:74px;display:flex;flex-shrink:0;border-top:1px solid var(--line);background:#fff;box-shadow:0 -4px 18px rgba(16,24,40,.04)}.bottom>button{flex:1;border:none;border-right:1px solid var(--line);background:#fff;cursor:pointer;touch-action:manipulation}.map-btn,.cal-btn,.uv-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;font-size:10px;font-weight:900}.map-btn{color:#1457b9}.map-btn.mapping{background:#edf5ff;color:#1457b9}.cal-btn{color:#a15c00}.cal-btn.disabled{color:#98a2b3;background:#f8fafc;pointer-events:none}.cal-btn.armed,.cal-btn.running{background:#fff5e8;color:#9a6700}.uv-btn{color:#7a4fb3}.uv-btn.on{background:#f7f1ff;color:#6d3ea0}.map-icon,.cal-icon,.uv-icon{font-size:18px;line-height:1}.estop-btn{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}.estop-circle{width:48px;height:48px;border-radius:50%;background:#fff0ee;border:2px solid #e99b93;color:#b42318;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:900;box-shadow:0 3px 10px rgba(217,45,32,.08)}.estop-btn:active .estop-circle{transform:scale(.92)}.estop-btn.armed .estop-circle{background:#d92d20;border-color:#b42318;color:#fff;box-shadow:0 5px 18px rgba(217,45,32,.25)}.estop-lbl{font-size:8px;color:#667085;font-weight:800}
.map-view{position:absolute;inset:0;background:#f4f6f8;display:none;z-index:6}.map-view.show{display:block}#mapCanvas{width:100%;height:100%;display:block;touch-action:none}.stale{opacity:.45;filter:grayscale(1)}.map-hud{position:absolute;top:11px;left:11px;background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:9px;padding:9px 10px;box-shadow:var(--shadow);font-size:10px;color:var(--text);pointer-events:none;min-width:175px}.hud-title{font-size:8px;font-weight:900;color:var(--muted);letter-spacing:.7px;margin-bottom:6px}.hud-grid{display:grid;grid-template-columns:42px 1fr;gap:4px 8px}.hud-grid span{color:var(--muted);font-weight:800;font-size:9px}.hud-grid strong{font-size:13px}.hud-muted{font-size:9px;color:var(--muted)}.map-status{position:absolute;left:12px;bottom:10px;background:rgba(255,255,255,.92);border:1px solid var(--line);border-radius:7px;padding:5px 8px;color:#667085;font-size:8px;font-weight:800;pointer-events:none}.map-tools{position:absolute;top:11px;right:11px;display:flex;flex-direction:column;gap:5px}.mt-btn{min-width:42px;height:30px;border-radius:7px;border:1px solid var(--line);background:rgba(255,255,255,.95);color:#344054;font-size:9px;font-weight:900;box-shadow:0 2px 8px rgba(16,24,40,.06);touch-action:manipulation}.mt-btn.armed,.mt-btn.active{background:var(--amber-soft);color:#9a6700;border-color:#f2c27a}.map-hint{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);font-size:9px;font-weight:800;letter-spacing:.4px;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,.94);color:#667085;border:1px solid var(--line);pointer-events:none;white-space:nowrap}.map-hint.armed{background:var(--amber-soft);color:#9a6700;border-color:#f2c27a}
.layer-panel{position:absolute;top:50px;right:58px;width:204px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);padding:10px;display:none;z-index:12}.layer-panel.show{display:block}.layer-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.layer-title{font-size:10px;font-weight:900}.layer-close{border:0;background:none;color:#667085;font-size:14px}.layer-row{display:flex;align-items:center;justify-content:space-between;padding:7px 2px;border-top:1px solid #eef2f6;font-size:9px;color:#475467}.layer-row input{accent-color:#1677ff}.layer-note{margin-top:8px;font-size:8px;line-height:1.35;color:#98a2b3}.layer-clear{width:100%;margin-top:9px;padding:7px 6px;border:1px solid var(--line);border-radius:7px;background:#fff;color:#475467;font-size:8px;font-weight:900;letter-spacing:.4px;cursor:pointer}.layer-clear:active{background:#f2f4f7}.research-chip{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:10;background:#17202a;color:#fff;border-radius:999px;padding:5px 10px;font-size:8px;font-weight:900;letter-spacing:.5px;display:none;pointer-events:none}.research-chip.show{display:block}
.cal-status{position:absolute;top:0;left:0;right:0;z-index:20;display:none;background:rgba(255,255,255,.97);border-bottom:1px solid #f2c27a;padding:7px 9px;font-size:8px;line-height:1.35;color:#9a6700;box-shadow:0 3px 12px rgba(16,24,40,.06);font-family:inherit;max-height:82px;overflow:hidden}.cal-status.show{display:block}.cal-status .cal-hd{font-weight:900;letter-spacing:.7px;color:#a15c00}
.flash{position:fixed;inset:0;background:rgba(217,45,32,.12);pointer-events:none;opacity:0;transition:opacity .25s;z-index:999}.flash.show{opacity:1}
@media (max-width:560px){.hdr-sub{display:none}.status-pills{max-width:150px}.speed-label{display:none}.spd-btn{min-width:48px;padding:6px 5px}.hdr{padding:0 9px}.drive-info{left:7px;top:7px;gap:5px}.motion-card{right:7px;top:7px;min-width:116px}.info-card{min-width:78px;padding:6px 7px}.info-card .v{font-size:12px}.motion-card{padding:7px 8px}.layer-panel{right:55px;width:190px}}
</style>

</head>
<body>
<div class="hdr">
  <div class="hdr-left">
    <div><div class="hdr-title">AISLEBOT</div><div class="hdr-sub">NARROW-CHASSIS MOBILE ROBOT</div></div>
    <div class="status-pills"><span class="state-pill bad" id="rosPill">ROS ×</span><span class="state-pill muted" id="mapPill">MAP —</span><span class="state-pill muted" id="posePill">POSE —</span></div>
  </div>
  <div class="hdr-right">
    <span class="speed-label">SPEED</span>
    <div class="spd-group"><button class="spd-btn active-slow" id="spd0">SLOW</button><button class="spd-btn" id="spd1">NORMAL</button><button class="spd-btn" id="spd2">FAST</button></div>
    <button class="view-btn" id="viewBtn">VIEW</button>
    <span class="map-badge" id="mapBadge">MAP</span>
    <span class="status-dot" id="dot"></span>
  </div>
</div>
<div class="spd-indicator">COMMAND LIMIT: <span id="spdValue">SLOW — 0.05 m/s</span></div>
<div class="body">
  <div class="joy-area" id="joyArea">
    <div class="drive-info">
      <div class="info-card"><div class="k">MAP X</div><div class="v" id="liveX">—</div></div>
      <div class="info-card"><div class="k">MAP Y</div><div class="v" id="liveY">—</div></div>
      <div class="info-card"><div class="k">NOSE</div><div class="v" id="liveNose">—</div></div>
      <div class="info-card"><div class="k">PATH</div><div class="v" id="liveDist">0.00 m</div></div>
    </div>
    <div class="motion-card">
      <div class="title">MOTION COMMAND</div><div class="motion-state" id="motionState">IDLE</div>
      <div class="cmd-row"><span>Vx</span><strong id="cmdVx">0.00 m/s</strong></div>
      <div class="cmd-row"><span>Vy</span><strong id="cmdVy">0.00 m/s</strong></div>
      <div class="cmd-row"><span>Wz</span><strong id="cmdWz">0.00 rad/s</strong></div>
    </div>
    <div class="research-chip" id="researchChip">RESEARCH VIEW</div>
    <div class="joy-ring" id="joyRing"><span class="jlbl t">FWD</span><span class="jlbl b">REV</span><span class="jlbl l">LEFT</span><span class="jlbl r">RIGHT</span><div class="joy-thumb" id="joyThumb"></div></div>
    <div class="cal-status" id="calStatus"><div class="cal-hd" id="calHd">CALIBRATING</div><div id="calTail"></div></div>
    <div class="map-view" id="mapView">
      <canvas id="mapCanvas"></canvas>
      <div class="map-hud" id="mapHud">WAITING FOR /map</div>
      <div class="map-status" id="mapStatus">MAP GRID WAITING</div>
      <div class="map-tools">
        <button class="mt-btn" id="btnZoomIn" aria-label="Zoom in">+</button>
        <button class="mt-btn" id="btnZoomOut" aria-label="Zoom out">−</button>
        <button class="mt-btn" id="btnFollow">CENTER</button>
        <button class="mt-btn" id="btnGoal">GOAL</button>
        <button class="mt-btn" id="btnZero">ZERO</button>
        <button class="mt-btn" id="btnLayers">LAYERS</button>
        <button class="mt-btn" id="btnResearch">RESEARCH</button>
      </div>
      <div class="layer-panel" id="layerPanel">
        <div class="layer-head"><div class="layer-title">VIEW SETTINGS</div><button class="layer-close" id="btnLayersClose">×</button></div>
        <label class="layer-row">Grid <input id="layer-grid" type="checkbox" checked></label>
        <label class="layer-row">Scale bar <input id="layer-scale" type="checkbox" checked></label>
        <label class="layer-row">Trajectory &mdash; current <input id="layer-trajectory" type="checkbox"></label>
        <label class="layer-row">Trajectory &mdash; past runs <input id="layer-pastTrails" type="checkbox"></label>
        <label class="layer-row">Goal markers <input id="layer-goals" type="checkbox" checked></label>
        <label class="layer-row">Robot footprint <input id="layer-footprint" type="checkbox" checked></label>
        <label class="layer-row">Map axes <input id="layer-axes" type="checkbox"></label>
        <label class="layer-row">Zero mark <input id="layer-zero" type="checkbox" checked></label>
        <label class="layer-row">Research mode <input id="researchToggle" type="checkbox"></label>
        <button class="layer-clear" id="btnClearTrails">CLEAR TRAILS &amp; GOALS</button>
        <div class="layer-note">A new run starts at MAP or re-ZERO; the previous trail moves to &ldquo;past runs&rdquo;. Clearing is display-only &mdash; it discards nothing ROS has recorded, and no option here changes ROS behavior.</div>
      </div>
      <div class="map-hint" id="mapHint">DRAG TO PAN · PINCH TO ZOOM</div>
    </div>
  </div>
  <div class="right-panel">
    <div class="yaw-wrap"><span class="section-title">YAW</span><span class="yaw-lbl">CCW</span><div class="yaw-track" id="yawTrack"><div class="yaw-thumb" id="yawThumb"></div></div><span class="yaw-lbl">CW</span></div>
    <div class="arm-section"><button class="arm-btn" id="btnOpen">ARM<br>OPEN</button><button class="arm-btn" id="btnClose">ARM<br>CLOSE</button></div>
    <div class="lift-section"><button class="lift-btn" id="btnUp">▲ LIFT</button><button class="lift-btn" id="btnDown">▼ LOWER</button></div>
  </div>
</div>
<div class="bottom">
  <button class="map-btn" id="mapBtn"><span class="map-icon" id="mapIcon">▦</span><span id="mapLabel">MAP</span></button>
  <button class="cal-btn disabled" id="calBtn"><span class="cal-icon" id="calIcon">⟳</span><span id="calLabel">CALIBRATE</span></button>
  <button class="uv-btn" id="uvBtn"><span class="uv-icon" id="uvIcon">☼</span><span id="uvLabel">UV LIGHTS</span></button>
  <button class="estop-btn" id="estopBtn"><div class="estop-circle" id="estopCircle">E-STOP</div><span class="estop-lbl" id="estopLbl">TAP TO STOP</span></button>
</div>
<div class="flash" id="flash"></div>
<script>

// ── CONFIG ────────────────────────────────────────────────────────
// FIX: MAX_LINEAR lowered from 0.48 → 0.15 m/s to prevent motor saturation.
// Old: SLOW=0.12, MED=0.29, FAST=0.48 → MED and FAST both hit the 3 rad/s
//      wheel speed cap and felt identical.
// New: SLOW=0.05, MED=0.10, FAST=0.15 → all clearly different, all safe.
const MAX_LINEAR  = 0.15;   // m/s
const MAX_ANGULAR = 0.30;   // rad/s
const DEADZONE    = 0.07;
const SPEEDS      = [0.33, 0.67, 1.00];
const SPD_LABELS  = ['SLOW — 0.05 m/s', 'MED — 0.10 m/s', 'FAST — 0.15 m/s'];
const SPD_ACTIVE  = ['active-slow', 'active-normal', 'active-fast'];

// ── STATE ─────────────────────────────────────────────────────────
let ws, wsOk = false;
let speedIdx    = 0;
let joyX = 0, joyY = 0, joyActive = false, joyTouchId = null;
let yawVal = 0, yawActive = false, yawTouchId = null;
let estopped  = false;
let mapping   = false;
let armInterval = null;

// ── Cosmetic / operator-view state (does not alter ROS commands) ──
const mapLayers = {
  grid: true,
  scale: true,
  trajectory: false,
  pastTrails: false,
  goals: true,
  footprint: true,
  axes: false,
  zero: true,
};
let mapResearchMode = false;

// TRAILS. `trajectory` is the CURRENT run only. Completed runs move into
// `pastTrails` as separate polylines rather than being concatenated, so a
// re-zero or a fresh MAP does not draw a straight line across the room
// between where the old run ended and the new one starts. Each is toggled
// independently: after several attempts the accumulated past trails are
// what makes the canvas unreadable, and that is exactly when you still
// want to see the live one.
let trajectory = [];
let pastTrails = [];
let lastTrajectoryPose = null;
let pathLength = 0;

// GOALS. goalDrag is transient (only while placing). activeGoal is the one
// actually SENT and survives the release, because "where did I tell it to
// go" is worth seeing while it drives there. Superseded goals fall back to
// pastGoals so a sequence of commands stays legible.
let activeGoal = null;
let pastGoals  = [];

// Bounded so a long session cannot grow these without limit.
const MAX_TRAIL_PTS   = 2500;
const MAX_PAST_TRAILS = 8;
const MAX_PAST_GOALS  = 12;
const MIN_TRAIL_KEEP  = 4;    // shorter than this is a twitch, not a run

// Close the current trail and start a new one. Called on the events that
// genuinely begin a new run — MAP start and re-zero — never on a goal,
// because a trail records where the robot went, not why.
function startNewTrail() {
  if (trajectory.length >= MIN_TRAIL_KEEP) {
    pastTrails.push(trajectory);
    while (pastTrails.length > MAX_PAST_TRAILS) pastTrails.shift();
  }
  trajectory = [];
  lastTrajectoryPose = null;
  pathLength = 0;
}

function clearAllTrails() {
  trajectory = []; pastTrails = [];
  lastTrajectoryPose = null; pathLength = 0;
  activeGoal = null; pastGoals = [];
  if (mapView) drawMap();
}

// ── Operator display helpers ──────────────────────────────────────
function updateLivePoseCard() {
  if (!robotPose) return;
  const x = document.getElementById('liveX');
  const y = document.getElementById('liveY');
  const n = document.getElementById('liveNose');
  const d = document.getElementById('liveDist');
  // Raw map frame, printed verbatim: since §17.38 map +X is right and
  // map +Y is forward, so the raw numbers already read as ordinary graph
  // paper. No relabel here or in updateHud() -- if one ever looks needed,
  // the frame upstream is wrong. See docs/Axis_Convention.md.
  if (x) x.textContent = robotPose.x.toFixed(3) + ' m';
  if (y) y.textContent = robotPose.y.toFixed(3) + ' m';
  const noseDeg = ((robotPose.yaw * 180 / Math.PI + 180) % 360 + 360) % 360 - 180;
  if (n) n.textContent = noseDeg.toFixed(1) + '°';
  if (d) d.textContent = pathLength.toFixed(2) + ' m';
}

function updateDriveCommandCard(vx, vy, wz) {
  const ex = document.getElementById('cmdVx');
  const ey = document.getElementById('cmdVy');
  const ew = document.getElementById('cmdWz');
  if (ex) ex.textContent = `${vx.toFixed(2)} m/s`;
  if (ey) ey.textContent = `${vy.toFixed(2)} m/s`;
  if (ew) ew.textContent = `${wz.toFixed(2)} rad/s`;
  const moving = Math.abs(vx) > 0.001 || Math.abs(vy) > 0.001 || Math.abs(wz) > 0.001;
  const ms = document.getElementById('motionState');
  if (ms) ms.textContent = moving ? (Math.abs(wz) > 0.02 && Math.hypot(vx, vy) < 0.01 ? 'ROTATING' : 'MOVING') : 'IDLE';
}

function setPill(id, state, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'state-pill ' + state;
  el.textContent = text;
}

function updateConnectionUI() {
  setPill('rosPill', wsOk ? 'good' : 'bad', wsOk ? 'ROS ●' : 'ROS ×');
  setPill('mapPill', (wsOk && mapGrid) ? 'good' : 'muted', mapGrid ? 'MAP ●' : 'MAP —');
  // POSE used to read green off `robotPose` alone, so a dropped socket left
  // the last coordinate on screen looking live -- and those numbers are what
  // the operator drives by. robotPose is deliberately NOT cleared (the trail
  // and the last known position are still worth seeing); the pill and the
  // card just stop claiming they are current.
  const fresh = wsOk && !!robotPose;
  setPill('posePill', fresh ? 'good' : 'muted',
          robotPose ? (fresh ? 'POSE ●' : 'POSE ⌛') : 'POSE —');
  document.querySelectorAll('.info-card, .map-hud')
          .forEach(el => el.classList.toggle('stale', !!robotPose && !wsOk));
}

function syncLayerPanel() {
  for (const [k, v] of Object.entries(mapLayers)) {
    const el = document.getElementById('layer-' + k);
    if (el) el.checked = v;
  }
  const research = document.getElementById('researchToggle');
  if (research) research.checked = mapResearchMode;
}

function openLayers() {
  const p = document.getElementById('layerPanel');
  if (p) p.classList.toggle('show');
}

// ── MAP STATE ─────────────────────────────────────────────────────
// base_link on this robot is NOT REP-103: +X is the robot's RIGHT and +Y is
// its NOSE (§17.10). So in nav2_params.yaml's footprint polygon
//   [[0.24, 0.56], [0.24, -0.56], [-0.24, -0.56], [-0.24, 0.56]]
// the 0.24 is half the WIDTH and the 0.56 is half the LENGTH — the long axis
// runs along +Y. Getting this backwards draws the robot sideways in its own
// aisle, and this is the sixth place the convention has bitten the project.
const FOOT_HALF_X = 0.24;   // half width  (left..right)
const FOOT_HALF_Y = 0.56;   // half length (tail..nose)

let mapView    = false;
let mapGrid    = null;   // {w,h,res,ox,oy}
let mapBitmap  = null;   // offscreen canvas holding the rendered cells
let robotPose  = null;   // {x,y,yaw} in the map frame
let camX = 0, camY = 0, camScale = 55;   // camScale = screen px per metre
let mapFollow  = true;
let goalArmed  = false;
let goalDrag   = null;   // {wx,wy,yaw} while placing a goal
const ptrs     = new Map();
let pinchBase  = null;
let zeroArmed  = false;
let zeroTimer  = null;
let noticeTimer = null;

// ── WEBSOCKET ─────────────────────────────────────────────────────
function connect() {
  const url = 'ws://' + location.host + '/ws';
  ws = new WebSocket(url);
  ws.onopen = () => {
    wsOk = true;
    document.getElementById('dot').classList.add('on');
    updateConnectionUI();
    // Auto-enable the arm on connect so no manual ENABLE button is needed --
    // BUT NEVER BEHIND A LATCHED E-STOP. This used to send ENABLE
    // unconditionally, so a Wi-Fi blip while the operator had the robot
    // E-STOPped re-armed it with nobody touching anything, and the button
    // still read CLEAR / TAP TO RESUME. Re-assert the stop instead: if the
    // drive stack restarted during the outage its own latch is gone, so
    // re-sending is strictly safer than assuming it held.
    if (estopped) send({ type: 'estop' });
    else          send({ type: 'arm', cmd: 'ENABLE' });
  };
  ws.onmessage = (ev) => {
    let m;
    try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.type === 'notice') {
      goalHint(m.text, /FIRST|CANNOT/.test(m.text));
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => goalHint(defaultHint(), false), 4000);
    } else if (m.type === 'pose') {
      robotPose = { x: m.x, y: m.y, yaw: m.yaw };
      updateLivePoseCard();
      if (lastTrajectoryPose) {
        const d = Math.hypot(m.x - lastTrajectoryPose.x, m.y - lastTrajectoryPose.y);
        if (d >= 0.005) {
          pathLength += d;
          trajectory.push({ x: m.x, y: m.y });
          if (trajectory.length > MAX_TRAIL_PTS) trajectory.shift();
          lastTrajectoryPose = { x: m.x, y: m.y };
        }
      } else {
        trajectory.push({ x: m.x, y: m.y });
        lastTrajectoryPose = { x: m.x, y: m.y };
      }
      if (mapFollow) { camX = m.x; camY = m.y; }
      if (mapView) drawMap();
    } else if (m.type === 'map') {
      ingestMap(m);
      if (mapView) drawMap();
      updateConnectionUI();
    }
  };
  ws.onclose = () => {
    wsOk = false;
    document.getElementById('dot').classList.remove('on');
    updateConnectionUI();
    setTimeout(connect, 1500);
  };
  ws.onerror = () => ws.close();
}
connect();

// Returns TRUE only if the command actually reached the socket. This used to
// be `if (wsOk) ws.send(...)` with no return and no notice, so a GOAL or an
// E-STOP tapped while the socket was down vanished silently and the UI went
// on to report success. A control surface that swallows an E-STOP and then
// says "TAP TO RESUME" is lying about the state of a 45 kg robot.
//
// wsOk alone is not enough: it is set in onopen and cleared in onclose, which
// leaves a window in CLOSING where ws.send() throws. Check readyState too.
//
// quiet=true is for the 20 Hz drive loop, which must not spam the hint line.
// A dropped socket there is already covered three ways: the ROS pill, the
// velocity_smoother's 1.0 s velocity_timeout, and esp32_bridge's own 500 ms
// watchdog, which stops the wheels when commands stop arriving (§17.14).
function send(obj, quiet) {
  if (wsOk && ws && ws.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify(obj)); return true; } catch (e) { /* fall through */ }
  }
  wsOk = false;
  updateConnectionUI();
  if (!quiet) goalHint('NOT CONNECTED — COMMAND NOT SENT', true);
  return false;
}

// ── SPEED MODE ────────────────────────────────────────────────────
// FIX: Speed buttons now use touchstart event listeners instead of onclick.
// onclick has a 300ms delay on mobile and fails entirely when touch-action:none
// is set globally. touchstart fires instantly and reliably.
function setSpeed(idx) {
  speedIdx = idx;
  for (let i = 0; i < 3; i++) {
    const btn = document.getElementById('spd' + i);
    SPD_ACTIVE.forEach(c => btn.classList.remove(c));
    if (i === idx) btn.classList.add(SPD_ACTIVE[i]);
  }
  document.getElementById('spdValue').textContent = SPD_LABELS[idx];
}

// Attach touchstart (not onclick) to speed buttons — phone behavior unchanged
[0, 1, 2].forEach(i => {
  const btn = document.getElementById('spd' + i);
  btn.addEventListener('touchstart', e => {
    e.preventDefault();
    e.stopPropagation();
    setSpeed(i);
  }, { passive: false });
  // Desktop: plain click. Browsers suppress the synthetic click that would
  // follow a touchstart once preventDefault() has fired, so this never
  // double-fires on the phone — it only fires for real mouse clicks.
  btn.addEventListener('click', () => setSpeed(i));
});

// ── JOYSTICK ──────────────────────────────────────────────────────
const joyArea  = document.getElementById('joyArea');
const joyRing  = document.getElementById('joyRing');
const joyThumb = document.getElementById('joyThumb');

function getJoyOffset(touch) {
  const r   = joyRing.getBoundingClientRect();
  const cx  = r.left + r.width  / 2;
  const cy  = r.top  + r.height / 2;
  const max = r.width / 2 - 32;
  let dx = touch.clientX - cx;
  let dy = touch.clientY - cy;
  const dist = Math.hypot(dx, dy);
  if (dist > max) { const s = max / dist; dx *= s; dy *= s; }
  return { dx, dy, nx: dx / max, ny: -dy / max };
}

joyArea.addEventListener('touchstart', e => {
  e.preventDefault();
  // #mapView is a CHILD of #joyArea, so every touch on the map canvas
  // bubbles here. z-index makes the map cover the joystick visually; it
  // does NOT stop event propagation. Without this guard, panning the map
  // drove the robot — confirmed on phone and desktop. The map handlers
  // also stopPropagation(); this is the second line of defence, and the
  // one that cannot be defeated by event-ordering quirks between
  // pointer* and touch* on a given browser.
  if (mapView) return;
  if (joyActive) return;
  const t = e.changedTouches[0];
  joyTouchId = t.identifier;
  joyActive  = true;
  joyThumb.classList.add('active');
  const p = getJoyOffset(t);
  joyX = p.nx; joyY = p.ny;
  joyThumb.style.transform = `translate(calc(-50% + ${p.dx}px), calc(-50% + ${p.dy}px))`;
}, { passive: false });

joyArea.addEventListener('touchmove', e => {
  e.preventDefault();
  if (mapView) return;
  for (const t of e.changedTouches) {
    if (t.identifier !== joyTouchId) continue;
    const p = getJoyOffset(t);
    joyX = p.nx; joyY = p.ny;
    joyThumb.style.transform = `translate(calc(-50% + ${p.dx}px), calc(-50% + ${p.dy}px))`;
  }
}, { passive: false });

joyArea.addEventListener('touchend', e => {
  for (const t of e.changedTouches) {
    if (t.identifier !== joyTouchId) continue;
    joyActive = false; joyTouchId = null;
    joyX = 0; joyY = 0;
    joyThumb.classList.remove('active');
    joyThumb.style.transform = 'translate(-50%, -50%)';
    sendDrive();
  }
}, { passive: false });

// Desktop: mousedown starts the drag. 'mouse' is a sentinel id that can
// never collide with a real touch.identifier (always numeric), so we can
// safely reuse joyActive/joyTouchId from the touch code above unchanged.
joyArea.addEventListener('mousedown', e => {
  if (mapView) return;          // see the touchstart guard above
  if (joyActive) return;
  joyTouchId = 'mouse';
  joyActive  = true;
  joyThumb.classList.add('active');
  const p = getJoyOffset(e);
  joyX = p.nx; joyY = p.ny;
  joyThumb.style.transform = `translate(calc(-50% + ${p.dx}px), calc(-50% + ${p.dy}px))`;
});

// ── YAW SLIDER ────────────────────────────────────────────────────
const yawTrack = document.getElementById('yawTrack');
const yawThumb = document.getElementById('yawThumb');

yawTrack.addEventListener('touchstart', e => {
  e.preventDefault();
  if (yawActive) return;
  yawActive   = true;
  yawTouchId  = e.changedTouches[0].identifier;
  updateYaw(e.changedTouches[0]);
}, { passive: false });

yawTrack.addEventListener('touchmove', e => {
  e.preventDefault();
  for (const t of e.changedTouches) {
    if (t.identifier === yawTouchId) updateYaw(t);
  }
}, { passive: false });

yawTrack.addEventListener('touchend', e => {
  for (const t of e.changedTouches) {
    if (t.identifier !== yawTouchId) continue;
    yawActive = false; yawTouchId = null; yawVal = 0;
    yawThumb.style.top = '50%';
    sendDrive();
  }
}, { passive: false });

// Desktop: mousedown starts the drag (same 'mouse' sentinel pattern as joystick)
yawTrack.addEventListener('mousedown', e => {
  if (yawActive) return;
  yawActive  = true;
  yawTouchId = 'mouse';
  updateYaw(e);
});

// ── MOUSE DRAG (desktop) — shared move/release for joystick + yaw ───
// Bound on document, not the element, so dragging past the edge of the
// joystick ring or yaw track (very normal with a mouse) still tracks.
document.addEventListener('mousemove', e => {
  if (joyTouchId === 'mouse' && joyActive) {
    const p = getJoyOffset(e);
    joyX = p.nx; joyY = p.ny;
    joyThumb.style.transform = `translate(calc(-50% + ${p.dx}px), calc(-50% + ${p.dy}px))`;
  }
  if (yawTouchId === 'mouse' && yawActive) {
    updateYaw(e);
  }
});

document.addEventListener('mouseup', () => {
  if (joyTouchId === 'mouse') {
    joyActive = false; joyTouchId = null;
    joyX = 0; joyY = 0;
    joyThumb.classList.remove('active');
    joyThumb.style.transform = 'translate(-50%, -50%)';
    sendDrive();
  }
  if (yawTouchId === 'mouse') {
    yawActive = false; yawTouchId = null; yawVal = 0;
    yawThumb.style.top = '50%';
    sendDrive();
  }
});

function updateYaw(touch) {
  const r   = yawTrack.getBoundingClientRect();
  const pct = Math.max(0, Math.min(1, (touch.clientY - r.top) / r.height));
  yawThumb.style.top = (pct * 100) + '%';
  yawVal = -(pct - 0.5) * 2;
}

// ── DRIVE SEND LOOP (20 Hz) ──────────────────────────────────────
function applyDead(v) { return Math.abs(v) < DEADZONE ? 0 : v; }

function sendDrive() {
  const m  = SPEEDS[speedIdx];
  const vx = applyDead(joyY)   * m * MAX_LINEAR;
  const vy = applyDead(-joyX)  * m * MAX_LINEAR;
  const wz = applyDead(yawVal) * m * MAX_ANGULAR;
  updateDriveCommandCard(vx, vy, wz);
  // quiet: this fires at 20 Hz; a dead socket is reported by the ROS pill,
  // not by 20 hint updates a second. See send().
  send({ type: 'drive', vx: +vx.toFixed(3), vy: +vy.toFixed(3), wz: +wz.toFixed(3) }, true);
}

setInterval(() => {
  if ((joyActive || yawActive || kbDriveActive || kbYawActive) && !estopped) sendDrive();
}, 50);

// ── ARM BUTTONS (hold to move, release stops) ─────────────────────
function armHold(cmd) {
  send({ type: 'arm', cmd });
}

function armRelease() {
  send({ type: 'arm', cmd: 'STOP' });
}

function bindHold(id, cmd) {
  const btn = document.getElementById(id);

  const start = () => {
    btn.classList.add('held');
    armHold(cmd);
    if (armInterval) clearInterval(armInterval);
    armInterval = setInterval(() => armHold(cmd), 200);
  };
  const stop = () => {
    btn.classList.remove('held');
    if (armInterval) { clearInterval(armInterval); armInterval = null; }
    armRelease();
  };

  btn.addEventListener('touchstart', e => { e.preventDefault(); start(); }, { passive: false });
  btn.addEventListener('touchend',    stop, { passive: false });
  btn.addEventListener('touchcancel', stop, { passive: false });

  // Desktop: mousedown/mouseup do the same hold-while-pressed job.
  // mouseleave covers dragging the cursor off the button while still held
  // down, which has no touch equivalent (touchcancel handles that case
  // on phones) but is a real thing with a mouse.
  btn.addEventListener('mousedown', start);
  btn.addEventListener('mouseup',   stop);
  btn.addEventListener('mouseleave', stop);
}

bindHold('btnOpen',  'OPEN');
bindHold('btnClose', 'CLOSE');
bindHold('btnUp',    'LIFT');
bindHold('btnDown',  'LOWER');

// ── MAP (mapping_full.launch.py + recording, together) ────────────
// One button: starts the lidar+relay+slam_toolbox launch tree and PID/
// telemetry recording as a single action, stops both together. Every
// mapping run is recorded by default — there's no separate record toggle.
// Placeholder slot for a future "Autonomous Drive" button once SLAM is
// trusted; this is trigger-only, no autonomy behavior here.
function mapReset() {
  mapping = false;
  document.getElementById('mapBtn').classList.remove('mapping');
  document.getElementById('mapIcon').textContent  = '▦';
  document.getElementById('mapLabel').textContent = 'MAP';
  document.getElementById('mapBadge').classList.remove('show');
  calSyncEnabled();
}

function toggleMapping() {
  if (estopped) return;
  if (mapping) {
    send({ type: 'map_stop' });
    mapReset();
  } else {
    mapping = true;
    // A new mapping session re-anchors the map frame, so the old trail is
    // no longer in the same coordinates as the new one. Close it off.
    startNewTrail();
    send({ type: 'map_start' });
    document.getElementById('mapBtn').classList.add('mapping');
    document.getElementById('mapIcon').textContent  = '⏹';
    document.getElementById('mapLabel').textContent = 'STOP MAP';
    document.getElementById('mapBadge').classList.add('show');
  }
  calSyncEnabled();
}

const mapBtnEl = document.getElementById('mapBtn');
mapBtnEl.addEventListener('touchstart', e => { e.preventDefault(); toggleMapping(); }, { passive: false });
mapBtnEl.addEventListener('click', toggleMapping);

// ── CALIBRATE (tools/zero_point_scan.py) ──────────────────────────
// The first control here that makes the robot drive itself, so it is the
// only one with a two-tap arm: tap once to arm (4 s window), tap again to
// commit. A single stray tap on a phone in a pocket cannot start it.
let calArmed = false, calRunning = false, calArmTimer = null, calPoll = null;

function calSetLabel(t) { document.getElementById('calLabel').textContent = t; }

function calDisarm() {
  calArmed = false;
  clearTimeout(calArmTimer);
  document.getElementById('calBtn').classList.remove('armed');
  if (!calRunning) calSetLabel('CALIBRATE');
}

function calReset() {
  calRunning = false;
  calDisarm();
  clearInterval(calPoll); calPoll = null;
  const b = document.getElementById('calBtn');
  b.classList.remove('running');
  document.getElementById('calIcon').textContent = '⟳';
  calSetLabel('CALIBRATE');
  document.getElementById('calStatus').classList.remove('show');
  calSyncEnabled();
}

// Enabled only while mapping is live — zero_point_scan.py measures map
// growth, so without /map it has nothing to decide on. The server enforces
// this too (calib_preflight); this just stops the tap being offered.
function calSyncEnabled() {
  const b = document.getElementById('calBtn');
  if (mapping || calRunning) b.classList.remove('disabled');
  else { b.classList.add('disabled'); calDisarm(); }
}

function calPollStatus() {
  fetch('/calib_status').then(r => r.json()).then(s => {
    document.getElementById('calHd').textContent =
      'CALIBRATING — ' + (s.state || '').toUpperCase();
    document.getElementById('calTail').innerHTML =
      (s.tail || []).map(l => l.replace(/[<>&]/g, '')).join('<br>');
    if (!s.active) {
      document.getElementById('calHd').textContent =
        'CALIBRATION ' + (s.state || '').toUpperCase();
      setTimeout(calReset, 4000);
      clearInterval(calPoll); calPoll = null;
    }
  }).catch(() => {});
}

function calTap() {
  if (estopped) return;
  if (calRunning) { send({ type: 'calib_stop' }); calSetLabel('RETURNING…'); return; }
  if (!mapping) return;
  if (!calArmed) {
    calArmed = true;
    document.getElementById('calBtn').classList.add('armed');
    calSetLabel('TAP AGAIN');
    calArmTimer = setTimeout(calDisarm, 4000);
    return;
  }
  calDisarm();
  calRunning = true;
  send({ type: 'calib_start' });
  const b = document.getElementById('calBtn');
  b.classList.add('running');
  document.getElementById('calIcon').textContent = '⏹';
  calSetLabel('STOP CAL');
  document.getElementById('calStatus').classList.add('show');
  document.getElementById('calHd').textContent = 'CALIBRATING — STARTING';
  document.getElementById('calTail').textContent = '';
  clearInterval(calPoll);
  calPoll = setInterval(calPollStatus, 1500);
  setTimeout(calPollStatus, 700);
}

const calBtnEl = document.getElementById('calBtn');
calBtnEl.addEventListener('touchstart', e => { e.preventDefault(); calTap(); }, { passive: false });
calBtnEl.addEventListener('click', calTap);

// Recover button state on load. Both MAP and CALIBRATE previously tracked
// their state only in this page's memory, so a refresh — or reopening the
// dashboard on a second device — showed "MAP" while mapping was actually
// running, and left CALIBRATE greyed out with no way to enable it short of
// stopping and restarting a healthy mapping session.
function syncFromServer() {
  fetch('/calib_status').then(r => r.json()).then(s => {
    if (s.mapping && !mapping) {
      mapping = true;
      document.getElementById('mapBtn').classList.add('mapping');
      document.getElementById('mapIcon').textContent  = '⏹';
      document.getElementById('mapLabel').textContent = 'STOP MAP';
      document.getElementById('mapBadge').classList.add('show');
    }
    if (s.active && !calRunning) {
      calRunning = true;
      document.getElementById('calBtn').classList.add('running');
      document.getElementById('calIcon').textContent = '⏹';
      calSetLabel('STOP CAL');
      document.getElementById('calStatus').classList.add('show');
      clearInterval(calPoll);
      calPoll = setInterval(calPollStatus, 1500);
    }
    calSyncEnabled();
  }).catch(() => {});
}
syncFromServer();

// ── UV LIGHTS (staged on the Mega: T1, +5s T2, +10s T3) ──────────
let uvOn = false;
let uvTimers = [];

function uvClearTimers() { uvTimers.forEach(t => clearTimeout(t)); uvTimers = []; }
function uvLabel(txt)    { document.getElementById('uvLabel').textContent = txt; }

function uvReset() {
  uvClearTimers();
  uvOn = false;
  document.getElementById('uvBtn').classList.remove('on');
  uvLabel('UV LIGHTS');
}

function toggleUv() {
  if (estopped) return;                       // no UV while latched
  uvOn = !uvOn;
  if (uvOn) {
    send({ type: 'uv', cmd: 'on' });
    document.getElementById('uvBtn').classList.add('on');
    // Cosmetic mirror of the firmware staircase — real timing lives on the Mega.
    uvLabel('TUBE 1');
    uvTimers.push(setTimeout(() => uvLabel('TUBE 1\u00b72'), 5000));
    uvTimers.push(setTimeout(() => uvLabel('ALL ON'),       10000));
  } else {
    send({ type: 'uv', cmd: 'off' });
    uvReset();
  }
}

const uvBtnEl = document.getElementById('uvBtn');
uvBtnEl.addEventListener('touchstart', e => { e.preventDefault(); toggleUv(); }, { passive: false });
uvBtnEl.addEventListener('click', toggleUv);

// ── E-STOP ────────────────────────────────────────────────────────
const estopBtn    = document.getElementById('estopBtn');
const estopCircle = document.getElementById('estopCircle');
const estopLbl    = document.getElementById('estopLbl');
const flash       = document.getElementById('flash');

function toggleEstop() {
  if (!estopped) {
    // Latch locally FIRST, unconditionally, then try to send. If the socket
    // is down the stop did not reach the robot, and the operator has to know
    // that rather than read TAP TO RESUME on a robot that is still driving.
    // The latch still sets, so the reconnect handler re-asserts it the
    // moment the socket returns.
    estopped = true;
    const stopSent = send({ type: 'estop' });
    uvReset();                       // firmware drops UV on <S>; mirror it here
    calReset();                      // server already SIGKILLed it; clear the UI
    joyX = 0; joyY = 0; yawVal = 0;
    joyActive = false; yawActive = false;
    joyThumb.style.transform = 'translate(-50%,-50%)';
    yawThumb.style.top = '50%';
    if (mapping) { send({ type: 'map_stop' }); mapReset(); }
    estopBtn.classList.add('armed');
    estopCircle.textContent = 'CLEAR';
    estopLbl.textContent    = stopSent ? 'TAP TO RESUME' : 'NOT SENT ×';
    if (!stopSent) goalHint('E-STOP NOT DELIVERED — NO LINK TO ROBOT', true);
    flash.classList.add('show');
    setTimeout(() => flash.classList.remove('show'), 400);
  } else {
    estopped = false;
    send({ type: 'estop_clear' });
    estopBtn.classList.remove('armed');
    estopCircle.textContent = 'E-STOP';
    estopLbl.textContent    = 'TAP TO STOP';
    // FIX: Re-enable arm after clear (ESP32 ESTOP latches, <E1> un-latches)
    send({ type: 'arm', cmd: 'ENABLE' });
  }
}

estopBtn.addEventListener('touchstart', e => {
  e.preventDefault();
  e.stopPropagation();
  toggleEstop();
}, { passive: false });
estopBtn.addEventListener('click', toggleEstop);

// ── KEYBOARD (desktop) ───────────────────────────────────────────
// Not shown anywhere in the UI on purpose. W/A/S/D drive the joystick,
// Q/E are yaw, R toggles record. Keyboard yields to an active mouse/touch
// drag on the same control rather than fighting it. UV lights stay
// click/tap-only — no keyboard shortcut for that on purpose.
const keysDown = new Set();
let kbDriveActive = false, kbYawActive = false;

function kbApplyDrive() {
  let kx = 0, ky = 0;
  if (keysDown.has('w')) ky += 1;
  if (keysDown.has('s')) ky -= 1;
  if (keysDown.has('a')) kx -= 1;
  if (keysDown.has('d')) kx += 1;
  const mag = Math.hypot(kx, ky);
  if (mag > 1) { kx /= mag; ky /= mag; }
  kbDriveActive = (kx !== 0 || ky !== 0);
  if (joyActive) return;          // a real drag on the joystick wins
  joyX = kx; joyY = ky;
  const r   = joyRing.getBoundingClientRect();
  const max = r.width / 2 - 32;
  joyThumb.style.transform = kbDriveActive
    ? `translate(calc(-50% + ${kx * max}px), calc(-50% + ${-ky * max}px))`
    : 'translate(-50%, -50%)';
  joyThumb.classList.toggle('active', kbDriveActive);
}

function kbApplyYaw() {
  let kz = 0;
  if (keysDown.has('q')) kz += 1;   // CCW
  if (keysDown.has('e')) kz -= 1;   // CW
  kbYawActive = (kz !== 0);
  if (yawActive) return;            // a real drag on the slider wins
  yawVal = kz;
  yawThumb.style.top = (50 - kz * 50) + '%';
}

window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 'm') {
    if (!e.repeat) toggleMapping();
    e.preventDefault();
    return;
  }
  if (!'wasdqe'.includes(k)) return;
  e.preventDefault();
  keysDown.add(k);
  kbApplyDrive();
  kbApplyYaw();
  sendDrive();
});

window.addEventListener('keyup', e => {
  const k = e.key.toLowerCase();
  if (!'wasdqe'.includes(k)) return;
  keysDown.delete(k);
  kbApplyDrive();
  kbApplyYaw();
  sendDrive();
});

// Don't leave a key "stuck" if the window loses focus mid-press
window.addEventListener('blur', () => {
  if (keysDown.size === 0) return;
  keysDown.clear();
  kbApplyDrive();
  kbApplyYaw();
  sendDrive();
});
// ═══════════════════════════════════════════════════════════════════
//  MAP VIEW  (§17.32 — replaces Foxglove for seeing the map + pose)
// ═══════════════════════════════════════════════════════════════════

const mapCanvas = document.getElementById('mapCanvas');
const mctx      = mapCanvas.getContext('2d');
let   cssW = 0, cssH = 0, dpr = window.devicePixelRatio || 1;

function sizeCanvas() {
  const r = mapCanvas.getBoundingClientRect();
  if (!r.width || !r.height) return;
  dpr = window.devicePixelRatio || 1;
  cssW = r.width; cssH = r.height;
  mapCanvas.width  = Math.round(cssW * dpr);
  mapCanvas.height = Math.round(cssH * dpr);
  // Transform reset ONLY (no rotation here) -- drawMap() re-applies the
  // rotated transform every frame from this same baseline, since setTransform
  // replaces the matrix outright rather than composing with what came before.
  mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', () => { sizeCanvas(); if (mapView) drawMap(); });

// THE RESIZE EVENT IS NOT ENOUGH, and the gap is a real click-accuracy bug.
// sizeCanvas() caches cssW/cssH, and s2w()/w2s() work off that cache while
// the pointer handler reads a LIVE getBoundingClientRect() for r.left. The
// canvas backing store is cssW*dpr px, which the browser then rescales to
// the element's real CSS width -- so when the two disagree the marker lands
// at sx * (r.width / cssW): zero error at the left edge, growing to the
// right. That is the "goal marker sits right of my mouse" report.
//
// Two ways the cache goes stale with no resize event: the handler above
// bails out via `if (!r.width || !r.height) return` every time the map view
// is hidden (display:none => a 0x0 rect), and a devicePixelRatio change from
// dragging the window to a monitor with different scaling does not reliably
// fire resize at all. A ResizeObserver watches the element itself and closes
// both. Guarded because it is absent on very old browsers, where the
// pointerdown check below still catches it.
if (window.ResizeObserver) {
  new ResizeObserver(() => { sizeCanvas(); if (mapView) drawMap(); })
    .observe(mapCanvas);
}

// ── Map-frame display orientation ────────────────────────────────────────
// This whole section used to carry two compensations. Both are gone, and
// the history is kept here because the temptation to re-add them is exactly
// what this comment exists to stop.
//
// The map frame used to have REP-103's axes (map +X = whichever way the
// robot faced when odometry was zeroed) while base_link had +X=right,
// +Y=forward. odometry_publisher.py rotated its published orientation but
// not its published translation, and that mismatch WAS the -90 deg. So:
//   - the canvas was spun -90 deg to make forward look like up, and
//   - every printed number was relabeled dispX = -raw_y, dispY = raw_x.
// Both were display-side patches over a frame that was genuinely rotated.
//
// §17.38 fixed the frame instead. odom, map and base_link now all use
// +X=right, +Y=forward. Screen-up is already map +Y, which is already
// forward, so the correct canvas rotation is ZERO, and the raw numbers are
// already ordinary graph paper, so the correct relabel is NONE.
//
// If the printed X/Y ever looks wrong again, do not fix it here. A display
// patch would hide a real frame fault for a second time. Read
// docs/Axis_Convention.md, then check odometry_publisher.py.
//
// drawUpright() and the labelXGridline()/labelYGridline() helpers below are
// KEPT even though DISPLAY_ROT is 0 (where they reduce to the identity).
// They are what makes rotated-canvas text land upright and in the right
// place, and a previous fork's attempt to fix garbled labels by zeroing the
// rotation instead is how the display drifted from the frame in the first
// place. Keeping them means setting DISPLAY_ROT non-zero stays safe.
const DISPLAY_ROT = 0;

// ── THE ROBOT'S YAW CONVENTION, IN ONE PLACE ────────────────────────────
// base_link yaw is measured from +Y (the NOSE), not from +X. Every standard
// 2-D helper -- Math.atan2, cos/sin -- measures from +X, so any conversion
// between "a direction on the map" and "a robot yaw" carries a 90 deg term.
//
// THIS PAIR EXISTS BECAUSE THE TWO DIRECTIONS ONCE DISAGREED (§17.49).
// drawRobot() drew the nose from +Y while drawGoalMarker() drew the goal
// arrow from +X -- same canvas, same frame, 90 deg apart -- and the drag
// handler wrote a raw atan2 angle into the very variable that
// robotPose.yaw initialises. Every goal dragged more than 5 cm went out
// with its heading 90 deg wrong, and the marker drawn on screen agreed
// with the wrong value, so it looked right.
//
// Route EVERY vector<->yaw conversion through these two. They are exact
// inverses, so the renderers and the command path cannot drift apart
// again. Do NOT add a compensating offset anywhere else -- least of all in
// goal_pose_adapter, whose yaw_offset_deg is 0.0 and must stay 0.0
// (§17.38). A display-side offset is what hid the last frame fault for
// two weeks.
function vecToYaw(dx, dy) { return Math.atan2(dy, dx) - Math.PI / 2; }
function yawToVec(yaw)    { return { x: -Math.sin(yaw), y: Math.cos(yaw) }; }

// Draws text upright in real screen space at the real-screen point that
// local point (localX, localY) maps to under DISPLAY_ROT -- use this for
// any fillText() call made while the map canvas is in its rotated state.
function drawUpright(text, localX, localY, align, dxReal, dyReal) {
  const c = Math.cos(DISPLAY_ROT), s = Math.sin(DISPLAY_ROT);
  const dx = localX - cssW / 2, dy = localY - cssH / 2;
  const realX = cssW / 2 + (dx * c - dy * s) + (dxReal || 0);
  const realY = cssH / 2 + (dx * s + dy * c) + (dyReal || 0);
  mctx.save();
  mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  mctx.textAlign = align || 'left';
  mctx.fillText(text, realX, realY);
  mctx.restore();
}

function w2s(wx, wy) {
  return { x: cssW / 2 + (wx - camX) * camScale,
           y: cssH / 2 - (wy - camY) * camScale };   // canvas y grows DOWN
}
function s2w(sx, sy) {
  return { x: camX + (sx - cssW / 2) / camScale,
           y: camY - (sy - cssH / 2) / camScale };
}
// Raw pointer coords (canvas-relative) -> the local space w2s/s2w assume.
// Undoes DISPLAY_ROT around the canvas centre. Rotation is linear, so the
// same formula applied to a DELTA (no centre offset) undoes it for that too
// -- used for pan-dragging, where only the difference between two points
// matters.
function unrotatePtr(sx, sy) {
  const dx = sx - cssW / 2, dy = sy - cssH / 2;
  const c = Math.cos(DISPLAY_ROT), s = Math.sin(DISPLAY_ROT);
  // Apply the inverse canvas rotation to recover local map coordinates.
  return {
    x: cssW / 2 + c * dx + s * dy,
    y: cssH / 2 - s * dx + c * dy,
  };
}
function unrotateDelta(dx, dy) {
  const c = Math.cos(DISPLAY_ROT), s = Math.sin(DISPLAY_ROT);
  return { x: c * dx + s * dy, y: -s * dx + c * dy };
}

// ── Decode one OccupancyGrid into an offscreen bitmap ──────────────
function ingestMap(m) {
  const bin = atob(m.data);
  const n   = bin.length;
  mapGrid = { w: m.w, h: m.h, res: m.res, ox: m.ox, oy: m.oy };

  const img = new ImageData(m.w, m.h);
  const px  = img.data;
  for (let gy = 0; gy < m.h; gy++) {
    // OccupancyGrid row 0 is the LOWEST y; ImageData row 0 is the TOP.
    const irow = m.h - 1 - gy;
    for (let gx = 0; gx < m.w; gx++) {
      const v = bin.charCodeAt(gy * m.w + gx);   // int8 shipped raw: -1 -> 255
      const o = (irow * m.w + gx) * 4;
      let r, g, b;
      // Palette rule: luminance rises with occupancy probability, so the
      // map reads darkest-is-emptiest at a glance. UNKNOWN is deliberately
      // OFF-HUE (neutral slate, no blue) because it is not a low
      // probability of occupancy — it is the absence of a measurement, a
      // different kind of thing, and should not sit on the same ramp.
      //
      // The old palette put free at rgb(12,40,64) against unknown at
      // rgb(16,22,36): a WCAG contrast ratio of 1.20:1, which is why
      // drivable space and never-seen space looked identical on a phone in
      // daylight. Ratios now: free/unknown 3.8:1, occupied/free 3.6:1,
      // occupied/unknown 13.6:1.
      if (v === 255)     { r = 228; g = 231; b = 236; }   // unknown  - light neutral
      else if (v >= 65)  { r =  52; g =  64; b =  78; }   // occupied - dark structure
      else if (v <= 25)  { r = 248; g = 250; b = 252; }   // free     - clean floor
      else               { r = 152; g = 162; b = 176; }   // uncertain- between the two
      px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255;
    }
  }
  const off = document.createElement('canvas');
  off.width = m.w; off.height = m.h;
  off.getContext('2d').putImageData(img, 0, 0);
  mapBitmap = off;
}

// ── Draw ───────────────────────────────────────────────────────────
function drawMap() {
  if (!cssW || !cssH) { sizeCanvas(); if (!cssW) return; }

  mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  mctx.translate(cssW / 2, cssH / 2);
  mctx.rotate(DISPLAY_ROT);
  mctx.translate(-cssW / 2, -cssH / 2);

  mctx.fillStyle = '#f4f6f8';
  mctx.fillRect(0, 0, cssW, cssH);

  if (mapBitmap && mapGrid) {
    const tl = w2s(mapGrid.ox, mapGrid.oy + mapGrid.h * mapGrid.res);
    mctx.imageSmoothingEnabled = false;
    mctx.drawImage(mapBitmap, tl.x, tl.y,
                   mapGrid.w * mapGrid.res * camScale,
                   mapGrid.h * mapGrid.res * camScale);
  }

  if (mapLayers.grid) drawGrid();
  if (mapLayers.axes) drawAxes();
  // Past first, so the live trail always draws on top of the clutter.
  if (mapLayers.pastTrails) drawPastTrails();
  if (mapLayers.trajectory) drawTrajectory();

  // Zero mark is a coordinate reference, never a command.
  if (mapLayers.zero) drawZeroMark();

  if (mapLayers.goals) drawGoals();
  // The goal being placed right now is always drawn, toggle or not: it is
  // direct feedback on a gesture in progress, not a display layer.
  if (goalDrag) drawGoalMarker(goalDrag, true);
  if (mapLayers.footprint && robotPose) drawRobot(robotPose);

  updateHud();

  // Screen-fixed overlays: not rotated with the map.
  mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (mapLayers.scale) drawScaleBar();
  drawMapModeBadge();
}

function worldBounds() {
  const corners = [unrotatePtr(0, 0), unrotatePtr(cssW, 0),
                   unrotatePtr(0, cssH), unrotatePtr(cssW, cssH)];
  const lx = corners.map(c => c.x), ly = corners.map(c => c.y);
  const tl = s2w(Math.min(...lx), Math.min(...ly));
  const br = s2w(Math.max(...lx), Math.max(...ly));
  return { minX: tl.x, maxX: br.x, minY: br.y, maxY: tl.y };
}

function niceGridStep() {
  // Choose a physical interval that lands in a readable 70–150 px range.
  const targetPx = 105;
  const raw = targetPx / Math.max(camScale, 1);
  const powers = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50];
  let best = powers[powers.length - 1];
  let bestErr = Infinity;
  for (const p of powers) {
    const err = Math.abs(Math.log((p * camScale) / targetPx));
    if (err < bestErr) { bestErr = err; best = p; }
  }
  return best;
}

function formatMeters(v) {
  if (v >= 10) return `${v.toFixed(0)} m`;
  if (v >= 1) return `${v.toFixed(v % 1 === 0 ? 0 : 1)} m`;
  return `${v.toFixed(2)} m`;
}

function drawGrid() {
  if (camScale < 8) return;
  const b = worldBounds();
  const step = niceGridStep();
  const minor = step / 5;

  mctx.lineWidth = 1;
  mctx.font = '10px Inter, Arial, sans-serif';
  mctx.textBaseline = 'top';

  // Minor grid only when it remains visually useful.
  if (minor * camScale >= 18) {
    mctx.beginPath();
    mctx.strokeStyle = 'rgba(52, 73, 94, 0.10)';
    for (let x = Math.floor(b.minX / minor) * minor; x <= b.maxX + minor; x += minor) {
      const p = w2s(x, 0);
      mctx.moveTo(p.x, 0); mctx.lineTo(p.x, cssH);
    }
    for (let y = Math.floor(b.minY / minor) * minor; y <= b.maxY + minor; y += minor) {
      const p = w2s(0, y);
      mctx.moveTo(0, p.y); mctx.lineTo(cssW, p.y);
    }
    mctx.stroke();
  }

  // Major grid.
  mctx.beginPath();
  mctx.strokeStyle = 'rgba(22, 119, 255, 0.20)';
  for (let x = Math.floor(b.minX / step) * step; x <= b.maxX + step; x += step) {
    const p = w2s(x, 0);
    mctx.moveTo(p.x, 0); mctx.lineTo(p.x, cssH);
  }
  for (let y = Math.floor(b.minY / step) * step; y <= b.maxY + step; y += step) {
    const p = w2s(0, y);
    mctx.moveTo(0, p.y); mctx.lineTo(cssW, p.y);
  }
  mctx.stroke();

  // Coordinate labels on major gridlines. Map axes ARE display axes now
  // (§17.38), so a constant-world-X line is labelled "X <value>" and a
  // constant-world-Y line "Y <value>" -- no relabel, no sign flip.
  //
  // These are MARGIN labels (anchored to a screen EDGE, not to a world
  // point), so drawUpright()'s small-local-offset trick does not apply: a
  // small LOCAL offset is a large offset from the rotation centre on a
  // non-square viewport and lands the text somewhere else entirely. That
  // exact bug shipped and was fixed live on hardware 26 Aug. The helpers
  // below therefore clip each gridline in REAL screen space and pin the
  // label to where it actually leaves the canvas -- correct at DISPLAY_ROT
  // 0, and still correct if it is ever set non-zero again.
  mctx.fillStyle = '#3b4754';
  mctx.font = '10px Inter, Arial, sans-serif';
  for (let x = Math.ceil(b.minX / step) * step; x <= b.maxX; x += step) {
    labelXGridline(`X ${x.toFixed(x % 1 === 0 ? 0 : 1)}`, x);
  }
  for (let y = Math.ceil(b.minY / step) * step; y <= b.maxY; y += step) {
    labelYGridline(`Y ${y.toFixed(y % 1 === 0 ? 0 : 1)}`, y);
  }
}

// Real on-screen position of a local (pre-rotation) canvas point.
function localToReal(lx, ly) {
  const c = Math.cos(DISPLAY_ROT), s = Math.sin(DISPLAY_ROT);
  const dx = lx - cssW / 2, dy = ly - cssH / 2;
  return { x: cssW / 2 + (dx * c - dy * s),
           y: cssH / 2 + (dx * s + dy * c) };
}

// Clip the infinite line P + t*D to the canvas rect. Returns [tMin, tMax]
// or null when the line misses the canvas entirely.
function lineClipToCanvas(px, py, dx, dy) {
  let tMin = -Infinity, tMax = Infinity;
  const slabs = [[dx, -px, cssW - px], [dy, -py, cssH - py]];
  for (const [d, lo, hi] of slabs) {
    if (Math.abs(d) < 1e-9) { if (lo > 0 || hi < 0) return null; continue; }
    let a = lo / d, b2 = hi / d;
    if (a > b2) { const t = a; a = b2; b2 = t; }
    if (a > tMin) tMin = a;
    if (b2 < tMax) tMax = b2;
  }
  return tMin <= tMax ? [tMin, tMax] : null;
}

// Draws one margin label for a gridline, given a local anchor point on the
// line and the line's local direction. `preferBottom` picks which end of
// the visible span the label sits at.
function labelGridline(text, localAnchorX, localAnchorY, localDirX, localDirY,
                       preferBottom) {
  const c = Math.cos(DISPLAY_ROT), s = Math.sin(DISPLAY_ROT);
  const P = localToReal(localAnchorX, localAnchorY);
  const D = { x: localDirX * c - localDirY * s,
              y: localDirX * s + localDirY * c };
  const span = lineClipToCanvas(P.x, P.y, D.x, D.y);
  if (!span) return;
  const e0 = { x: P.x + span[0] * D.x, y: P.y + span[0] * D.y };
  const e1 = { x: P.x + span[1] * D.x, y: P.y + span[1] * D.y };
  const e = preferBottom ? (e0.y > e1.y ? e0 : e1)
                         : (e0.x < e1.x ? e0 : e1);
  mctx.save();
  mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  mctx.textAlign = 'left';
  mctx.fillText(text,
                Math.min(Math.max(e.x + 3, 3), cssW - 26),
                Math.min(Math.max(e.y - 4, 12), cssH - 10));
  mctx.restore();
}

// A constant-world-X gridline: local vertical line, labelled at the bottom.
function labelXGridline(text, worldX) {
  const p = w2s(worldX, 0);
  labelGridline(text, p.x, cssH / 2, 0, 1, true);
}
// A constant-world-Y gridline: local horizontal line, labelled at the left.
function labelYGridline(text, worldY) {
  const p = w2s(0, worldY);
  labelGridline(text, cssW / 2, p.y, 1, 0, false);
}

function drawAxes() {
  const o = w2s(0, 0);
  if (o.x < -40 || o.x > cssW + 40 || o.y < -40 || o.y > cssH + 40) return;
  // X+ is map +X (right), Y+ is map +Y (forward). Since §17.38 those are
  // the real map axes, so the arrows point at the world coordinates they
  // are named after -- no swap, which is what they used to need.
  const ax = w2s(0.65, 0);
  const ay = w2s(0, 0.65);
  mctx.lineWidth = 2;
  mctx.strokeStyle = '#3b82f6';
  mctx.beginPath(); mctx.moveTo(o.x, o.y); mctx.lineTo(ax.x, ax.y); mctx.stroke();
  mctx.strokeStyle = '#12b76a';
  mctx.beginPath(); mctx.moveTo(o.x, o.y); mctx.lineTo(ay.x, ay.y); mctx.stroke();
  mctx.font = 'bold 10px Inter, Arial, sans-serif';
  mctx.fillStyle = '#2563eb'; drawUpright('X+', ax.x + 4, ax.y, 'left');
  mctx.fillStyle = '#059669'; drawUpright('Y+', ay.x + 4, ay.y, 'left');
}

function drawZeroMark() {
  const o = w2s(0, 0);
  mctx.strokeStyle = '#f79009';
  mctx.lineWidth = 2;
  mctx.beginPath();
  mctx.moveTo(o.x - 8, o.y); mctx.lineTo(o.x + 8, o.y);
  mctx.moveTo(o.x, o.y - 8); mctx.lineTo(o.x, o.y + 8);
  mctx.stroke();
  mctx.fillStyle = '#9a6700';
  mctx.font = 'bold 10px Inter, Arial, sans-serif';
  drawUpright('ZERO (0,0)', o.x + 10, o.y + 4, 'left');
}

function strokePolyline(pts) {
  if (pts.length < 2) return;
  mctx.beginPath();
  pts.forEach((p, i) => {
    const q = w2s(p.x, p.y);
    if (i === 0) mctx.moveTo(q.x, q.y); else mctx.lineTo(q.x, q.y);
  });
  mctx.stroke();
}

function drawTrajectory() {
  if (trajectory.length < 2) return;
  mctx.strokeStyle = 'rgba(22, 119, 255, 0.68)';
  mctx.lineWidth = 2.5;
  strokePolyline(trajectory);

  const start = w2s(trajectory[0].x, trajectory[0].y);
  mctx.fillStyle = '#12b76a';
  mctx.beginPath(); mctx.arc(start.x, start.y, 4, 0, Math.PI * 2); mctx.fill();
}

// Past runs: thinner and grey, and each drawn as its OWN polyline so no
// line is ever drawn between the end of one run and the start of the next.
// Older runs fade further, so the most recent past run stays readable
// underneath the live one.
function drawPastTrails() {
  const n = pastTrails.length;
  pastTrails.forEach((pts, i) => {
    const age = n > 1 ? i / (n - 1) : 1;          // 0 = oldest, 1 = newest
    mctx.strokeStyle = 'rgba(102, 112, 133, ' + (0.16 + 0.26 * age).toFixed(3) + ')';
    mctx.lineWidth = 1.6;
    strokePolyline(pts);
  });
}

// Goal markers. The active goal is the one currently commanded; past goals
// are drawn hollow and faint so a sequence reads as a sequence.
function drawGoalMarker(g, active) {
  const a = w2s(g.wx, g.wy);
  mctx.strokeStyle = active ? '#f79009' : 'rgba(247, 144, 9, 0.32)';
  mctx.lineWidth = active ? 2.5 : 1.4;
  mctx.beginPath(); mctx.arc(a.x, a.y, active ? 9 : 6, 0, 6.2832); mctx.stroke();
  const r = active ? 0.6 : 0.35;
  // yawToVec, NOT cos/sin -- this arrow and drawRobot()'s nose line must
  // come from the same function or they disagree by 90 deg (§17.49).
  const v = yawToVec(g.yaw);
  const b = w2s(g.wx + v.x * r, g.wy + v.y * r);
  mctx.beginPath(); mctx.moveTo(a.x, a.y); mctx.lineTo(b.x, b.y); mctx.stroke();
}

function drawGoals() {
  pastGoals.forEach(g => drawGoalMarker(g, false));
  if (activeGoal) drawGoalMarker(activeGoal, true);
}

function drawScaleBar() {
  const candidates = [0.1, 0.2, 0.5, 1, 2, 5, 10];
  let step = candidates[candidates.length - 1];
  for (const c of candidates) {
    const px = c * camScale;
    if (px >= 70 && px <= 170) { step = c; break; }
  }
  const px = step * camScale;
  const x = 18, y = cssH - 34;
  mctx.strokeStyle = '#17202a';
  mctx.fillStyle = 'rgba(255,255,255,.88)';
  mctx.lineWidth = 3;
  mctx.beginPath(); mctx.moveTo(x, y); mctx.lineTo(x + px, y); mctx.stroke();
  mctx.lineWidth = 1;
  mctx.beginPath();
  mctx.moveTo(x, y - 5); mctx.lineTo(x, y + 5);
  mctx.moveTo(x + px, y - 5); mctx.lineTo(x + px, y + 5);
  mctx.stroke();
  mctx.font = 'bold 11px Inter, Arial, sans-serif';
  mctx.fillText(formatMeters(step), x + px / 2 - 18, y - 22);
}

function drawMapModeBadge() {
  const pad = 10;
  const label = mapResearchMode ? 'RESEARCH VIEW' : 'OPERATOR VIEW';
  mctx.fillStyle = 'rgba(255,255,255,.92)';
  mctx.strokeStyle = '#d0d5dd';
  mctx.lineWidth = 1;
  mctx.beginPath(); mctx.roundRect(cssW - 142, 10, 132, 28, 7); mctx.fill(); mctx.stroke();
  mctx.fillStyle = '#344054';
  mctx.font = '700 10px Inter, Arial, sans-serif';
  mctx.fillText(label, cssW - 132, 20);
}

function drawRobot(p) {
  const c = Math.cos(p.yaw), s = Math.sin(p.yaw);
  const corners = [[ FOOT_HALF_X,  FOOT_HALF_Y], [ FOOT_HALF_X, -FOOT_HALF_Y],
                   [-FOOT_HALF_X, -FOOT_HALF_Y], [-FOOT_HALF_X,  FOOT_HALF_Y]];
  mctx.beginPath();
  corners.forEach(([bx, by], i) => {
    const pt = w2s(p.x + bx * c - by * s, p.y + bx * s + by * c);
    i ? mctx.lineTo(pt.x, pt.y) : mctx.moveTo(pt.x, pt.y);
  });
  mctx.closePath();
  mctx.fillStyle = 'rgba(22,119,255,.18)';
  mctx.strokeStyle = '#1677ff';
  mctx.lineWidth = 2.2;
  mctx.fill(); mctx.stroke();

  const ctr = w2s(p.x, p.y);
  // Same helper the goal marker uses. Numerically identical to the old
  // inline (-sin, +cos); shared so the two can never diverge again.
  const nv = yawToVec(p.yaw), nl = FOOT_HALF_Y + 0.22;
  const nose = w2s(p.x + nv.x * nl, p.y + nv.y * nl);
  mctx.beginPath();
  mctx.moveTo(ctr.x, ctr.y); mctx.lineTo(nose.x, nose.y);
  mctx.strokeStyle = '#17202a'; mctx.lineWidth = 2.5; mctx.stroke();
  mctx.beginPath(); mctx.arc(nose.x, nose.y, 3.8, 0, 6.2832);
  mctx.fillStyle = '#17202a'; mctx.fill();
}

function updateHud() {
  const hud = document.getElementById('mapHud');
  if (!mapGrid && !robotPose) { hud.innerHTML = '<strong>WAITING FOR /map</strong>'; return; }
  const status = document.getElementById('mapStatus');
  if (robotPose) {
    // Raw map frame, verbatim. Since §17.38 map +X is right and map +Y is
    // forward, so these numbers already read as ordinary graph paper and
    // agree with the physical +X/+Y marked on the robot. NOSE is raw yaw:
    // on the ZERO mark that is 0 deg, which is what the old +90 deg offset
    // used to produce artificially.
    const noseDeg = ((robotPose.yaw * 180 / Math.PI + 180) % 360 + 360) % 360 - 180;
    hud.innerHTML = `
      <div class="hud-title">ROBOT POSE · MAP FRAME</div>
      <div class="hud-grid">
        <span>X</span><strong>${robotPose.x.toFixed(3)} m</strong>
        <span>Y</span><strong>${robotPose.y.toFixed(3)} m</strong>
        <span>NOSE</span><strong>${noseDeg.toFixed(1)}°</strong>
      </div>`;
    if (status) status.textContent = mapGrid ? `${mapGrid.w} × ${mapGrid.h} · ${mapGrid.res.toFixed(2)} m/cell` : 'MAP GRID WAITING';
  } else {
    hud.innerHTML = '<div class="hud-title">ROBOT POSE</div><div class="hud-muted">NO POSE (map → base_link)</div>';
  }
}

// ── View toggle ────────────────────────────────────────────────────
function setMapView(on) {
  mapView = on;
  document.body.classList.toggle('map-mode', on);
  if (on) {
    // Entering map view with a drag in flight would otherwise leave the
    // joystick latched at its last value and the robot rolling.
    if (joyActive || yawActive) {
      joyActive = false; joyTouchId = null; joyX = 0; joyY = 0;
      yawActive = false; yawTouchId = null; yawVal = 0;
      joyThumb.classList.remove('active');
      joyThumb.style.transform = 'translate(-50%, -50%)';
      sendDrive();
    }
  }
  document.getElementById('mapView').classList.toggle('show', on);
  document.getElementById('viewBtn').classList.toggle('on', on);
  document.getElementById('viewBtn').textContent = on ? 'DRIVE' : 'VIEW';
  if (on) {
    if (mapFollow && robotPose) { camX = robotPose.x; camY = robotPose.y; }
    sizeCanvas(); drawMap();
  } else {
    goalDisarm();
  }
}
document.getElementById('viewBtn').addEventListener('click',
  () => setMapView(!mapView));

// Research/display controls are cosmetic only: they change rendering layers,
// never ROS publishers or command semantics.
document.getElementById('btnLayers').addEventListener('click', openLayers);
document.getElementById('btnResearch').addEventListener('click', () => {
  mapResearchMode = !mapResearchMode;
  document.getElementById('btnResearch').classList.toggle('active', mapResearchMode);
  mapLayers.trajectory = mapResearchMode;
  mapLayers.axes = mapResearchMode;
  syncLayerPanel();
  if (mapView) drawMap();
});
for (const key of Object.keys(mapLayers)) {
  const el = document.getElementById('layer-' + key);
  if (el) el.addEventListener('change', () => {
    mapLayers[key] = el.checked;
    if (mapView) drawMap();
  });
}
document.getElementById('researchToggle').addEventListener('change', (e) => {
  mapResearchMode = e.target.checked;
  document.getElementById('btnResearch').classList.toggle('active', mapResearchMode);
  mapLayers.trajectory = mapResearchMode;
  mapLayers.axes = mapResearchMode;
  syncLayerPanel();
  if (mapView) drawMap();
});
document.getElementById('btnClearTrails').addEventListener('click', (e) => {
  e.preventDefault();
  clearAllTrails();
  goalHint('TRAILS AND GOAL MARKERS CLEARED', false);
});

document.getElementById('btnLayersClose').addEventListener('click', () => {
  document.getElementById('layerPanel').classList.remove('show');
});


// ── Zoom / centre ──────────────────────────────────────────────────
function zoom(f) {
  camScale = Math.max(6, Math.min(400, camScale * f));
  drawMap();
}
document.getElementById('btnZoomIn').addEventListener('click',  () => zoom(1.35));
document.getElementById('btnZoomOut').addEventListener('click', () => zoom(1 / 1.35));
document.getElementById('btnFollow').addEventListener('click', () => {
  mapFollow = true;
  if (robotPose) { camX = robotPose.x; camY = robotPose.y; }
  drawMap();
});

// ── Click-to-goal ──────────────────────────────────────────────────
// Two-tap arm, exactly like CALIBRATE: one stray tap must never start a
// 45 kg robot. Gesture then matches Foxglove's 2D Pose tool, which the
// operator already knows: tap to place, drag to aim the NOSE, release.
function defaultHint() { return 'DRAG TO PAN · PINCH TO ZOOM'; }
function goalHint(txt, armed) {
  const h = document.getElementById('mapHint');
  if (!h) return;   // send() can call this before the map view exists
  h.textContent = txt;
  h.classList.toggle('armed', !!armed);
}
function goalDisarm() {
  goalArmed = false; goalDrag = null;
  document.getElementById('btnGoal').classList.remove('armed');
  goalHint(defaultHint(), false);
  if (mapView) drawMap();
}
document.getElementById('btnGoal').addEventListener('click', () => {
  if (estopped) { goalHint('E-STOP ACTIVE — CLEAR FIRST', true); return; }
  goalArmed = !goalArmed;
  document.getElementById('btnGoal').classList.toggle('armed', goalArmed);
  goalHint(goalArmed ? 'TAP MAP TO PLACE · DRAG TO AIM NOSE'
                     : defaultHint(), goalArmed);
});

// ── Re-zero (Important_Commands.md §8, without a terminal) ─────────
// Two-tap armed like CALIBRATE and GOAL. It doesn't move the robot, but it
// redefines what every coordinate on this map means, so a stray tap must
// not do it.
function zeroDisarm() {
  zeroArmed = false;
  clearTimeout(zeroTimer);
  document.getElementById('btnZero').classList.remove('armed');
}
document.getElementById('btnZero').addEventListener('click', () => {
  if (!zeroArmed) {
    zeroArmed = true;
    document.getElementById('btnZero').classList.add('armed');
    goalHint('TAP ZERO AGAIN — MAKES THIS SPOT MAP (0,0)', true);
    zeroTimer = setTimeout(() => { zeroDisarm(); goalHint(defaultHint(), false); }, 5000);
    return;
  }
  zeroDisarm();
  // Re-zero redefines what every coordinate on this map means, so points
  // recorded before it cannot be plotted against points recorded after.
  startNewTrail();
  send({ type: 'rezero' });   // server replies over the notice channel
});

// ── Pointer handling: pan, pinch, or place-a-goal ──────────────────
mapCanvas.addEventListener('pointerdown', (e) => {
  e.stopPropagation();
  mapCanvas.setPointerCapture(e.pointerId);
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });

  if (goalArmed && ptrs.size === 1) {
    const r = mapCanvas.getBoundingClientRect();
    // Belt-and-braces behind the ResizeObserver: a goal is the one gesture
    // where a stale cssW puts the commanded point somewhere the operator did
    // not click, so re-sync before converting rather than trusting the cache.
    // Costs one float compare on a gesture that happens seconds apart.
    if (Math.abs(r.width - cssW) > 0.5 || Math.abs(r.height - cssH) > 0.5) sizeCanvas();
    const p = unrotatePtr(e.clientX - r.left, e.clientY - r.top);
    const w = s2w(p.x, p.y);
    goalDrag = { wx: w.x, wy: w.y, yaw: robotPose ? robotPose.yaw : 0 };
    drawMap();
  } else if (ptrs.size === 2) {
    const p = [...ptrs.values()];
    pinchBase = { d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y), s: camScale };
  }
});

mapCanvas.addEventListener('pointermove', (e) => {
  e.stopPropagation();
  if (!ptrs.has(e.pointerId)) return;
  const prev = ptrs.get(e.pointerId);
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });

  if (goalDrag && ptrs.size === 1) {
    const r = mapCanvas.getBoundingClientRect();
    const p = unrotatePtr(e.clientX - r.left, e.clientY - r.top);
    const w = s2w(p.x, p.y);
    const dx = w.x - goalDrag.wx, dy = w.y - goalDrag.wy;
    // vecToYaw, NOT a bare atan2: this writes into the same field that
    // pointerdown initialises from robotPose.yaw, so both must be in the
    // robot's convention (0 = nose along +Y). See vecToYaw above (§17.49).
    if (Math.hypot(dx, dy) > 0.05) goalDrag.yaw = vecToYaw(dx, dy);
    drawMap();
    return;
  }

  if (ptrs.size === 2 && pinchBase) {
    const p = [...ptrs.values()];
    const d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
    if (pinchBase.d > 0) {
      camScale = Math.max(6, Math.min(400, pinchBase.s * (d / pinchBase.d)));
      drawMap();
    }
    return;
  }

  if (ptrs.size === 1) {                     // pan
    mapFollow = false;
    const d = unrotateDelta(e.clientX - prev.x, e.clientY - prev.y);
    camX -= d.x / camScale;
    camY += d.y / camScale;
    drawMap();
  }
});

function endPtr(e) {
  e.stopPropagation();
  if (goalDrag && ptrs.size === 1) {
    // yaw is where the NOSE should end up, already in base_link's
    // convention (0 = +Y) via vecToYaw. goal_pose_adapter adds NOTHING --
    // its yaw_offset_deg is 0.0 and the live node logs "yaw +0.0 deg". The
    // comment that used to sit here claimed the adapter applied a -90,
    // which stopped being true at §17.38 and is why nobody looked at this
    // line while every dragged heading came out sideways.
    const sent = !estopped &&
                 send({ type: 'goal', x: goalDrag.wx, y: goalDrag.wy,
                        yaw: goalDrag.yaw });
    if (estopped) {
      goalHint('E-STOP ACTIVE — GOAL NOT SENT', true);
    } else if (sent) {
      // Keep the sent goal on the canvas. Previously goalDrag was nulled on
      // release and the marker disappeared the instant it was commanded,
      // which is the one moment you most want to see where it is heading.
      if (activeGoal) {
        pastGoals.push(activeGoal);
        while (pastGoals.length > MAX_PAST_GOALS) pastGoals.shift();
      }
      activeGoal = { wx: goalDrag.wx, wy: goalDrag.wy, yaw: goalDrag.yaw };
      goalHint('GOAL SENT → ' + goalDrag.wx.toFixed(2) + ', ' +
               goalDrag.wy.toFixed(2), false);
    }
    // send() has already put NOT CONNECTED on the hint line. Stay ARMED in
    // that one case so a retry costs one tap instead of a re-arm; disarm on
    // success and on the E-STOP refusal, where re-arming is the point.
    goalDrag = null;
    if (sent || estopped) {
      goalArmed = false;
      document.getElementById('btnGoal').classList.remove('armed');
    }
    drawMap();
  }
  ptrs.delete(e.pointerId);
  if (ptrs.size < 2) pinchBase = null;
}
mapCanvas.addEventListener('pointerup', endPtr);
mapCanvas.addEventListener('pointercancel', endPtr);

// A pointerdown that calls preventDefault() does NOT suppress the touch*
// events that follow it, so the pointer handlers above cannot close the
// touch path on their own. These do, at the map-view boundary.
['touchstart', 'touchmove', 'touchend', 'touchcancel'].forEach(evt => {
  document.getElementById('mapView').addEventListener(
    evt, e => e.stopPropagation(), { passive: false });
});

// Desktop convenience; harmless on touch.
mapCanvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12);
}, { passive: false });



// Initial cosmetic sync.
syncLayerPanel();
updateConnectionUI();
updateLivePoseCard();

</script>
</body>
</html>
"""
# ═══════════════════════════════════════════════════════════════════
#  ROS2 NODE
# ═══════════════════════════════════════════════════════════════════

class PhoneDashboard(Node):

    def __init__(self):
        super().__init__('phone_dashboard')

        self.declare_parameter('port',    8080)
        self.declare_parameter('log_dir', '~/aislebot_logs')

        # ── Calibration (zero_point_scan.py) tunables ──────────────
        # 90 deg steps, i.e. four headings, is NOT an arbitrary round
        # number: this robot's rear self-occlusion mask is a measured 90 deg
        # wedge (§17.15), and a 360 deg LiDAR sees everything else from any
        # single heading. Four headings 90 deg apart therefore sweep that
        # blind wedge across the full circle exactly once, with no
        # redundant stops. Finer steps cost time without covering more.
        self.declare_parameter('calib_step_deg',     90.0)
        self.declare_parameter('calib_max_duration', 150.0)
        self.declare_parameter('zero_point_scan_path',
                               '~/ros2_ws/tools/zero_point_scan.py')

        self.port    = self.get_parameter('port').value
        self.log_dir = os.path.expanduser(
            self.get_parameter('log_dir').get_parameter_value().string_value
        )
        os.makedirs(self.log_dir, exist_ok=True)

        # ── Publishers ────────────────────────────────────────────
        self.cmd_vel_pub   = self.create_publisher(Twist,             '/cmd_vel_manual', 10)
        self.arm_pub       = self.create_publisher(String,            '/arm/command',   10)
        self.esp32_cmd_pub = self.create_publisher(String,            '/esp32/command', 10)

        # /goal_pose_click, NOT /goal_pose. goal_pose_adapter already owns the
        # -90 deg nose-vs-base_link conversion (§17.20); publishing straight to
        # /goal_pose would duplicate that rule in a second place, which is
        # exactly how the §17.19 axis bug happened. Yaw sent here means "point
        # the NOSE this way", in the map frame.
        self.goal_pub      = self.create_publisher(PoseStamped, '/goal_pose_click', 10)
        self.odom_reset_pub = self.create_publisher(Empty, '/odom/reset', 10)

        # ── Subscribers ───────────────────────────────────────────
        self.create_subscription(
            Float64MultiArray, '/motor_telemetry',
            self._telemetry_callback, 10
        )

        # ── Telemetry / Recording ─────────────────────────────────
        self.recording     = False
        self._csv_file     = None
        self._csv_writer   = None
        self._sample_count = 0
        self._run_path     = ''

        # ── Mapping (mapping_full.launch.py, subprocess-managed) ────
        self.mapping_active = False
        self._mapping_proc: Optional[subprocess.Popen] = None

        # ── Calibration (zero_point_scan.py, subprocess-managed) ────
        self.calib_active = False
        self.calib_state  = 'idle'      # idle|running|done|failed|aborted
        self._calib_proc: Optional[subprocess.Popen] = None
        self._calib_log_path = ''
        self._calib_log_file = None
        self._calib_kill_after = 0.0    # monotonic deadline after a SIGINT

        # Reaps the calibration subprocess without blocking the WebSocket
        # handler. stop_calibration() only signals and returns; this timer
        # notices the exit and escalates to SIGKILL if the graceful return
        # to zero overruns. Doing the wait inline would stall the event loop
        # for as long as the robot takes to drive home.
        self.create_timer(1.0, self._calib_watchdog)

        # ── Map + live pose streaming (§17.32, Dashboard_Map_System §E) ────
        # /map is LATCHED. A default (volatile) subscription silently receives
        # nothing at all, because slam_toolbox published its last grid before
        # this node ever subscribed. transient_local + reliable is not
        # optional here.
        map_qos = QoSProfile(
            depth       = 1,
            history     = QoSHistoryPolicy.KEEP_LAST,
            reliability = QoSReliabilityPolicy.RELIABLE,
            durability  = QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(OccupancyGrid, '/map', self._map_callback, map_qos)

        # Written by ROS callbacks, read by the FastAPI broadcast task. Whole
        # objects are replaced rather than mutated, so a reader either sees the
        # old dict or the new one and never a half-updated one — no lock
        # needed, and no cross-thread asyncio scheduling from a ROS callback.
        self.latest_map:  Optional[dict] = None
        self.latest_pose: Optional[dict] = None
        self.map_dirty = False

        # map->base_link log, written alongside the motor-telemetry CSV for
        # the duration of a mapping run. The telemetry CSV answers "what did
        # the wheels do"; this one answers "what did SLAM think the robot's
        # pose was", which is the series every jump analysis so far has had
        # to get from a separately-launched terminal tool.
        self._pose_csv_file   = None
        self._pose_csv_writer = None
        self._pose_path       = ''

        # One-line status pushed to the browser. Seq (not text) is what marks
        # it new, so repeating the same message twice still reaches the page.
        self.notice     = ''
        self.notice_seq = 0

        self.tf_buffer   = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.create_timer(0.1, self._pose_timer)      # 10 Hz

        self.ws_clients: Set[WebSocket] = set()

        self.get_logger().info(f'Phone Dashboard v2.4 — port {self.port}')
        self.get_logger().info(f'Log directory: {self.log_dir}')

    # ── Drive ─────────────────────────────────────────────────────

    def publish_drive(self, vx: float, vy: float, wz: float):
        msg = Twist()
        msg.linear.x  = float(vx)
        msg.linear.y  = float(vy)
        msg.angular.z = float(wz)
        self.cmd_vel_pub.publish(msg)

    # ── Map / pose streaming ──────────────────────────────────────

    def _map_callback(self, msg: OccupancyGrid):
        """Cache /map as a base64 blob the browser can render directly.

        OccupancyGrid.data is int8: -1 unknown, 0 free, 100 occupied. It is
        shipped as raw bytes, so -1 arrives in the browser as 255 — the client
        maps it back. Sending the grid rather than a server-rendered PNG keeps
        the Pi's CPU out of it (§17.25 killed slam_toolbox by starvation) and
        lets the client redraw on pan/zoom without a round trip.
        """
        data = msg.data
        try:
            raw = data.tobytes()          # array.array('b') — two's complement
        except AttributeError:
            raw = bytes((v & 0xFF) for v in data)

        self.latest_map = {
            'w':    msg.info.width,
            'h':    msg.info.height,
            'res':  msg.info.resolution,
            # Pose of cell (0,0) in the map frame. Generally NOT (0,0) —
            # slam_toolbox grows the grid in all directions, so every
            # world<->pixel conversion has to go through this.
            'ox':   msg.info.origin.position.x,
            'oy':   msg.info.origin.position.y,
            'data': base64.b64encode(raw).decode('ascii'),
        }
        self.map_dirty = True

    def _lookup(self, parent, child):
        """(x, y, yaw) of `child` in `parent`, or None if that TF is absent.

        Returns None rather than raising so a caller can log the transforms
        that do exist: during mapping all three below are present, but odom
        exists before SLAM does and map does not, and neither case should
        stop the other from being recorded.
        """
        try:
            tf = self.tf_buffer.lookup_transform(parent, child, rclpy.time.Time())
        except (TransformException, Exception):
            return None
        q = tf.transform.rotation
        return (tf.transform.translation.x,
                tf.transform.translation.y,
                math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                           1.0 - 2.0 * (q.y * q.y + q.z * q.z)))

    def _pose_timer(self):
        """Sample the three transforms that describe where the robot is, 10 Hz.

        map -> base_link   where SLAM believes the robot is
        odom -> base_link  where the WHEELS alone believe it is (dead
                           reckoning, no scan matching, drifts but never jumps)
        map -> odom        the correction SLAM has applied to the wheels

        Logging all three is what makes every run self-diagnosing. §17.32's
        Stage A had to record a rosbag and run a separate tool once to find a
        39.57 cm map->odom jump; the third column below is that same quantity,
        sampled on every run for free. And the pairing is what identifies the
        culprit: wheel odometry is smooth by construction, so if map jumps
        while odom does not, the pose graph moved, not the robot.

        The transforms legitimately do not exist before the stack is up, so a
        failed lookup is skipped silently rather than logged — the dashboard
        must not spam or crash while the map stack is down.
        """
        pose = self._lookup('map', 'base_link')
        odom = self._lookup('odom', 'base_link')
        corr = self._lookup('map', 'odom')

        if pose is not None:
            self.latest_pose = {'x': pose[0], 'y': pose[1], 'yaw': pose[2]}

        if self._pose_csv_writer is None:
            return
        if pose is None and odom is None:
            return                       # nothing to say yet

        def f(v, n=4):
            return '' if v is None else ('{:.%df}' % n).format(v)

        def deg(v):
            return '' if v is None else '{:.2f}'.format(math.degrees(v))

        try:
            self._pose_csv_writer.writerow([
                '{:.3f}'.format(time.time()),
                f(pose and pose[0]), f(pose and pose[1]), deg(pose and pose[2]),
                f(odom and odom[0]), f(odom and odom[1]), deg(odom and odom[2]),
                f(corr and corr[0]), f(corr and corr[1]), deg(corr and corr[2]),
            ])
        except Exception:
            # A logging failure must never take down the pose sampler the
            # live dashboard map is drawn from.
            pass

    # ── Status line to the browser ────────────────────────────────

    def say(self, text: str):
        self.notice = text
        self.notice_seq += 1

    # ── Re-zero (Important_Commands.md §8, from the dashboard) ────

    def rezero(self) -> str:
        """Make the robot's current spot odom's origin.

        Returns '' on success, or a refusal reason.

        REFUSES WHILE MAPPING IS ACTIVE, and that is the whole point of the
        guard: slam_toolbox pins map->odom to identity at its first scan, so
        re-zeroing underneath a live session moves odom's origin without
        moving map's, silently breaking the "map (0,0) is the floor mark"
        property the whole commissioning procedure rests on. §17.17-§17.19
        were spent on that exact confusion. Stop mapping, re-zero, then
        start mapping — in that order, every time.
        """
        if self.mapping_active:
            reason = 'STOP MAPPING FIRST — RE-ZERO MUST COME BEFORE THE MAP RUN'
            self.say(reason)
            return reason
        if self.calib_active:
            reason = 'CALIBRATION RUNNING — CANNOT RE-ZERO'
            self.say(reason)
            return reason
        self.odom_reset_pub.publish(Empty())
        self.say('RE-ZEROED — THIS SPOT IS NOW (0, 0)')
        self.get_logger().info('Re-zero requested — odom origin moved to this spot')
        return ''

    # ── Goal ──────────────────────────────────────────────────────

    def publish_goal(self, x: float, y: float, yaw: float):
        """Send one navigation goal. `yaw` is where the NOSE should end up."""
        msg = PoseStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.orientation.z = math.sin(float(yaw) / 2.0)
        msg.pose.orientation.w = math.cos(float(yaw) / 2.0)
        self.goal_pub.publish(msg)
        self.get_logger().info(
            f'Goal sent (map frame): x={x:.3f} y={y:.3f} nose={math.degrees(yaw):.1f} deg')

    # ── Arm ───────────────────────────────────────────────────────

    def publish_arm(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.arm_pub.publish(msg)

    # ── Raw ESP32 serial command ──────────────────────────────────

    def send_esp32_raw(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.esp32_cmd_pub.publish(msg)

    # ── Record run: start ─────────────────────────────────────────

    def start_recording(self) -> str:
        if self.recording:
            return self._run_path
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._run_path   = os.path.join(self.log_dir, f'run_{ts}.csv')
        self._csv_file   = open(self._run_path, 'w', newline='')
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow([
            'pi_time_s',
            'FR_target_rads', 'FR_actual_rads', 'FR_pwm',
            'FL_target_rads', 'FL_actual_rads', 'FL_pwm',
            'RR_target_rads', 'RR_actual_rads', 'RR_pwm',
            'RL_target_rads', 'RL_actual_rads', 'RL_pwm',
        ])
        self._sample_count = 0
        self.recording = True
        self.send_esp32_raw('<L1>')
        self.get_logger().info(f'Recording started → {self._run_path}')
        return self._run_path

    # ── Record run: stop ──────────────────────────────────────────

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.send_esp32_raw('<L0>')
        if self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file   = None
            self._csv_writer = None
        self.get_logger().info(
            f'Recording stopped — {self._sample_count} samples → {self._run_path}'
        )

    # ── Map: start (mapping_full.launch.py + recording, together) ──

    def start_mapping(self) -> str:
        """Launch the mapping stack and begin recording as one action.

        Every mapping run is recorded by default (Research_Journal.md
        §16.11) — there is no separate record toggle anymore.
        """
        if self.mapping_active:
            return self._run_path
        try:
            self._mapping_proc = subprocess.Popen(
                ['ros2', 'launch', 'mecanum_robot', 'mapping_full.launch.py'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
        except Exception as e:
            self.get_logger().error(f'Failed to launch mapping_full.launch.py: {e}')
            return ''
        self.mapping_active = True
        path = self.start_recording()

        # Pose log, named off the same run so the two CSVs and the saved map
        # are obviously one artefact set.
        try:
            self._pose_path = os.path.splitext(path)[0] + '_pose.csv' if path else ''
            if self._pose_path:
                self._pose_csv_file = open(self._pose_path, 'w', newline='')
                self._pose_csv_writer = csv.writer(self._pose_csv_file)
                self._pose_csv_writer.writerow(
                    ['epoch_s',
                     'map_x', 'map_y', 'map_yaw_deg',
                     'odom_x', 'odom_y', 'odom_yaw_deg',
                     'corr_x', 'corr_y', 'corr_yaw_deg'])
        except Exception as e:
            self.get_logger().warn(f'Could not open pose log: {e}')
            self._pose_csv_file = self._pose_csv_writer = None

        self.get_logger().info(
            f'Mapping started (pid {self._mapping_proc.pid}) + recording → {path}'
        )
        return path

    # ── Map: stop ────────────────────────────────────────────────

    def _write_map_from_cache(self, map_prefix: str) -> bool:
        """Write .pgm + .yaml straight from the cached /map grid.

        §17.34: map_saver_cli is a separate process that SUBSCRIBES to /map,
        so it only works while slam_toolbox is still alive to publish. On a
        `systemctl restart` systemd SIGTERMs the whole control group at once
        — slam_toolbox is dying at the same instant map_saver_cli is trying
        to read from it — and the save times out. A 30-second test drive was
        lost that way even after the shutdown handler itself was fixed.

        This has no such dependency. _map_callback already caches every grid
        for the live view, so the bytes are sitting in memory and need no IPC,
        no subprocess, and nothing else in the launch tree to still be
        running. Output is byte-compatible with map_saver_cli's trinary mode.
        """
        m = self.latest_map
        if not m:
            self.get_logger().warn('no /map cached — nothing to write')
            return False
        try:
            w, h, res = m['w'], m['h'], m['res']
            raw = base64.b64decode(m['data'])
            # int8 arrives unsigned here: 255 == -1 == unknown.
            # map_saver_cli trinary: occupied -> 0, free -> 254, unknown -> 205.
            lut = bytes(
                0   if (v <= 100 and v >= 65) else
                254 if (v <= 25)              else
                205
                for v in range(256)
            )
            cells = raw.translate(lut)
            # OccupancyGrid row 0 is the LOWEST y; PGM row 0 is the TOP.
            rows = [cells[y * w:(y + 1) * w] for y in range(h)]
            body = b''.join(reversed(rows))
            with open(f'{map_prefix}.pgm', 'wb') as fh:
                fh.write(b'P5\n# CREATOR: phone_dashboard from cached /map\n')
                fh.write(f'{w} {h}\n255\n'.encode())
                fh.write(body)
            with open(f'{map_prefix}.yaml', 'w') as fh:
                fh.write(
                    f'image: {os.path.basename(map_prefix)}.pgm\n'
                    f'mode: trinary\n'
                    f'resolution: {res:.3f}\n'
                    f'origin: [{m["ox"]:.3f}, {m["oy"]:.3f}, 0]\n'
                    f'negate: 0\n'
                    f'occupied_thresh: 0.65\n'
                    f'free_thresh: 0.196\n')
            self.get_logger().info(
                f'map written from cache → {map_prefix}.pgm ({w}x{h})')
            return True
        except Exception as e:
            self.get_logger().error(f'writing map from cache failed: {e}')
            return False

    def _save_map(self, map_prefix: str) -> bool:
        """Save the live /map. Prefers map_saver_cli, which is the canonical
        producer, and falls back to writing the cached grid directly when it
        fails — which it reliably does during a signal-driven shutdown, since
        its publisher is being killed alongside it."""
        if self._save_map_via_cli(map_prefix):
            return True
        self.get_logger().warn('falling back to writing the map from cache')
        return self._write_map_from_cache(map_prefix)

    def _save_map_via_cli(self, map_prefix: str) -> bool:
        """Save via map_saver_cli. Must run before the launch tree is killed —
        slam_toolbox (and therefore /map) dies with it."""
        try:
            result = subprocess.run(
                ['ros2', 'run', 'nav2_map_server', 'map_saver_cli', '-f', map_prefix],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
            )
            if result.returncode != 0:
                self.get_logger().warn(
                    f'map_saver_cli exited {result.returncode} — report will have no map block')
                return False
            return True
        except subprocess.TimeoutExpired:
            self.get_logger().warn('map_saver_cli timed out — report will have no map block')
            return False
        except Exception as e:
            self.get_logger().warn(f'map_saver_cli failed: {e} — report will have no map block')
            return False

    def stop_mapping(self):
        """Stop the mapping launch tree and recording together, then run
        the same post-run analysis pass as telemetry_analyzer.html —
        automatically, so every run gets one without a manual step
        (Research_Journal.md §16.11 item 3)."""
        if not self.mapping_active:
            return
        self.mapping_active = False
        proc, self._mapping_proc = self._mapping_proc, None
        run_path = self._run_path

        # Close the pose log before the launch tree dies — once slam_toolbox
        # is gone map->base_link stops resolving and the sampler goes quiet
        # anyway, but leaving the handle open would risk a truncated file.
        writer, self._pose_csv_writer = self._pose_csv_writer, None
        pose_file, self._pose_csv_file = self._pose_csv_file, None
        del writer
        if pose_file is not None:
            try:
                pose_file.close()
                self.get_logger().info(f'Pose log written → {self._pose_path}')
            except Exception:
                pass

        map_prefix = os.path.splitext(run_path)[0] if run_path else ''
        map_saved = bool(map_prefix) and self._save_map(map_prefix)

        if proc is not None and proc.poll() is None:
            # SIGINT to the whole process group == a terminal Ctrl+C, so
            # ros2 launch cascades a clean shutdown to lidar/relay/slam_toolbox.
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.get_logger().warn(
                    'mapping_full.launch.py did not exit on SIGINT, sending SIGKILL')
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.stop_recording()
        self.get_logger().info('Mapping stopped')

        if run_path:
            self._write_run_report(run_path, map_prefix if map_saved else None)

    # ── Calibrate: the 360° zero-point scan ───────────────────────

    def calib_preflight(self) -> str:
        """Return '' if it is safe to start, else a human-readable reason.

        Both checks below are things zero_point_scan.py would otherwise
        discover several seconds in, after the operator has already
        committed and looked away from the phone — /map never arrives, or
        the action server never appears. Failing here instead turns a
        confusing hang into a sentence on the button.
        """
        if not self.mapping_active:
            return 'press MAP first — no /map to measure growth against'
        # bt_navigator owns /navigate_to_pose, which is the only motion path
        # this script uses. Checked via the node graph rather than by
        # building an ActionClient, so mecanum_robot gains no nav2_msgs
        # dependency for what is a liveness question.
        if 'bt_navigator' not in self.get_node_names():
            return 'Nav2 is not running — launch nav2_slam.launch.py first'
        script = os.path.expanduser(
            self.get_parameter('zero_point_scan_path')
            .get_parameter_value().string_value)
        if not os.path.isfile(script):
            return f'script not found: {script}'
        return ''

    def start_calibration(self) -> str:
        """Start the zero-point scan. Returns '' on success, else a reason."""
        if self.calib_active:
            return 'already running'
        reason = self.calib_preflight()
        if reason:
            self.get_logger().warn(f'Calibration refused: {reason}')
            self.calib_state = 'failed'
            return reason

        script = os.path.expanduser(
            self.get_parameter('zero_point_scan_path')
            .get_parameter_value().string_value)
        step = self.get_parameter('calib_step_deg').value
        dur  = self.get_parameter('calib_max_duration').value

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._calib_log_path = os.path.join(self.log_dir, f'calib_{ts}.log')
        try:
            # Line-buffered, and stderr folded into stdout: rclpy logging
            # goes to stderr, so without the merge the log would capture
            # everything except the per-heading progress we actually want.
            self._calib_log_file = open(self._calib_log_path, 'w', buffering=1)
            self._calib_proc = subprocess.Popen(
                ['python3', '-u', script,
                 '--step-deg', str(step), '--max-duration', str(dur)],
                stdout=self._calib_log_file, stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )
        except Exception as e:
            self.get_logger().error(f'Failed to launch zero_point_scan.py: {e}')
            self._close_calib_log()
            self.calib_state = 'failed'
            return str(e)

        self.calib_active = True
        self.calib_state  = 'running'
        self._calib_kill_after = 0.0
        self.get_logger().info(
            f'Calibration started (pid {self._calib_proc.pid}, '
            f'step {step}°, budget {dur}s) → {self._calib_log_path}')
        return ''

    def stop_calibration(self, graceful: bool = True):
        """Stop the scan. Never blocks — _calib_watchdog does the reaping.

        graceful=True  SIGINT. The script traps it and its finally block
                       drives back to the exact start pose before exiting,
                       which is the whole point of stopping it this way.
        graceful=False SIGKILL now, plus a cancel-all on /navigate_to_pose.
                       Used by E-STOP. Killing the script alone is NOT
                       enough: Nav2 holds the last accepted goal and would
                       keep driving to it, and would resume the moment the
                       E-STOP latch was cleared.
        """
        if not self.calib_active or self._calib_proc is None:
            return
        pid = self._calib_proc.pid
        try:
            if graceful:
                os.killpg(os.getpgid(pid), signal.SIGINT)
                # Generous: the return-to-zero goal is a real drive.
                self._calib_kill_after = time.monotonic() + 45.0
                self.calib_state = 'returning'
                self.get_logger().info(
                    'Calibration interrupted — returning to zero, then exiting')
            else:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                self.calib_state = 'aborted'
                self.get_logger().warn('Calibration KILLED (E-STOP)')
        except ProcessLookupError:
            pass
        if not graceful:
            self.cancel_nav_goals()

    def cancel_nav_goals(self):
        """Cancel every in-flight /navigate_to_pose goal.

        An all-zero CancelGoal request means "cancel all" per
        action_msgs/srv/CancelGoal. Fired as a detached subprocess rather
        than a service client so this stays non-blocking on the E-STOP
        path — an E-STOP must never wait on a service round-trip.
        """
        try:
            subprocess.Popen(
                ['ros2', 'service', 'call',
                 '/navigate_to_pose/_action/cancel_goal',
                 'action_msgs/srv/CancelGoal', '{}'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.get_logger().warn(f'cancel_goal call failed: {e}')

    def _close_calib_log(self):
        if self._calib_log_file is not None:
            try:
                self._calib_log_file.close()
            except Exception:
                pass
            self._calib_log_file = None

    def _calib_watchdog(self):
        """1 Hz: reap the scan when it exits, escalate if it overruns."""
        if not self.calib_active or self._calib_proc is None:
            return
        rc = self._calib_proc.poll()
        if rc is None:
            if self._calib_kill_after and time.monotonic() > self._calib_kill_after:
                self.get_logger().warn(
                    'zero_point_scan.py did not exit after SIGINT — SIGKILL')
                try:
                    os.killpg(os.getpgid(self._calib_proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self._calib_kill_after = 0.0
            return
        # Exited.
        if self.calib_state not in ('aborted',):
            self.calib_state = 'done' if rc == 0 else 'failed'
        self.calib_active = False
        self._calib_proc = None
        self._calib_kill_after = 0.0
        self._close_calib_log()
        self.get_logger().info(
            f'Calibration finished (rc={rc}, {self.calib_state}) '
            f'— log: {self._calib_log_path}')

    def calib_tail(self, n: int = 6) -> list:
        """Last n log lines, for the phone's status strip."""
        if not self._calib_log_path or not os.path.isfile(self._calib_log_path):
            return []
        try:
            with open(self._calib_log_path, 'r', errors='replace') as f:
                return [ln.rstrip() for ln in f.readlines()[-n:] if ln.strip()]
        except Exception:
            return []

    def _write_run_report(self, csv_path: str, map_prefix: Optional[str]):
        """Generate and log the automatic post-run report (PID + map
        findings) — the Python port of telemetry_analyzer.html's analysis,
        run headless since there's no browser on the Pi to open it in."""
        pgm_path = f'{map_prefix}.pgm' if map_prefix else None
        yaml_path = f'{map_prefix}.yaml' if map_prefix else None
        try:
            report = generate_report(csv_path, pgm_path, yaml_path)
            out_path = os.path.splitext(csv_path)[0] + '_report.json'
            write_report(report, out_path)
        except Exception as e:
            self.get_logger().warn(f'Post-run report generation failed: {e}')
            return
        self.get_logger().info(
            f"Run report → {out_path}  (health={report['health']}, "
            f"{report['samples']} samples, {report['duration']:.1f}s)"
        )
        for finding in report['findings']:
            self.get_logger().info(f"  [{finding['level'].upper()}] {finding['title']}")
        if report['map']:
            s = report['map']['stats']
            self.get_logger().info(
                f"  map: {s['unknownPct']:.1f}% unknown, {s['freePct']:.1f}% free, "
                f"{s['occupiedPct']:.1f}% occupied"
            )
            for finding in report['map']['findings']:
                self.get_logger().info(f"  [{finding['level'].upper()}] {finding['title']}")

    # ── Telemetry callback ────────────────────────────────────────

    def _telemetry_callback(self, msg: Float64MultiArray):
        if not self.recording or self._csv_writer is None:
            return
        data = list(msg.data)
        if len(data) < 12:
            return
        row = [f'{time.time():.4f}'] + [f'{v:.4f}' for v in data[:12]]
        self._csv_writer.writerow(row)
        self._sample_count += 1
        if self._sample_count % 50 == 0:
            self._csv_file.flush()


# ═══════════════════════════════════════════════════════════════════
#  FASTAPI APP
# ═══════════════════════════════════════════════════════════════════

app   = FastAPI()
_node: Optional[PhoneDashboard] = None


@app.get('/')
async def index():
    return HTMLResponse(DASHBOARD_HTML)


@app.get('/calib_status')
async def calib_status():
    """Polled by the phone while a scan runs.

    A plain GET rather than a WebSocket push because this dashboard's
    socket has only ever carried client -> server messages; adding a
    server -> client broadcast path for one status strip would mean new
    plumbing (and a second place for the connection to go stale) for no
    gain over a 1.5 s poll that only runs while calibrating.
    """
    if _node is None:
        return {'active': False, 'state': 'no_node', 'tail': []}
    return {
        'active':  _node.calib_active,
        'state':   _node.calib_state,
        'tail':    _node.calib_tail(),
        # Also the page's only way to recover button state across a reload.
        # The dashboard is a phone browser held next to a moving robot;
        # a dropped connection or an accidental refresh previously left the
        # UI claiming "MAP" while mapping was in fact still running.
        'mapping': _node.mapping_active,
    }


# ═══════════════════════════════════════════════════════════════════
#  SERVER -> CLIENT BROADCAST
#
#  Until §17.32 this socket was client -> server only. The ROS node spins on
#  its own thread while uvicorn owns the asyncio loop, so pushing directly
#  from a ROS callback would mean cross-thread asyncio — a known source of
#  subtle breakage. Instead ROS callbacks write plain node attributes and
#  this single task reads them on a timer: one writer, one reader, no locks,
#  no cross-thread scheduling.
# ═══════════════════════════════════════════════════════════════════

@app.on_event('startup')
async def _start_broadcast():
    asyncio.create_task(_broadcast_loop())


async def _broadcast_loop():
    tick = 0
    last_notice = 0
    while True:
        await asyncio.sleep(0.1)
        if _node is None or not _node.ws_clients:
            continue

        payloads = []
        if _node.notice_seq != last_notice:
            last_notice = _node.notice_seq
            payloads.append({'type': 'notice', 'text': _node.notice})
        # Pose is small and wants to look smooth: every tick, 10 Hz.
        if _node.latest_pose:
            payloads.append({'type': 'pose', **_node.latest_pose})

        # The map is large and changes slowly (map_update_interval: 1.0), so
        # it goes at 1 Hz AND only when it actually changed.
        tick += 1
        if tick % 10 == 0 and _node.map_dirty and _node.latest_map:
            payloads.append({'type': 'map', **_node.latest_map})
            _node.map_dirty = False

        for p in payloads:
            dead = []
            for client in list(_node.ws_clients):
                try:
                    await client.send_json(p)
                except Exception:
                    dead.append(client)
            for client in dead:
                _node.ws_clients.discard(client)


@app.websocket('/ws')
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    if _node:
        _node.ws_clients.add(websocket)
        # Send the current map straight to THIS client. The broadcast loop
        # only fires on map_dirty, so a browser that connects (or reloads)
        # after the last grid arrived would otherwise sit blank until
        # slam_toolbox happened to publish again.
        if _node.latest_map:
            try:
                await websocket.send_json({'type': 'map', **_node.latest_map})
            except Exception:
                pass
        # FIX: Auto-enable arm on every new browser connection from the server side.
        # This is the server-side counterpart to the client-side send on ws.onopen.
        # Ensures arm is enabled even if the client-side message is lost during connect.
        _node.publish_arm('ENABLE')
        _node.get_logger().info('Dashboard client connected — arm ENABLE sent')
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            _dispatch(msg)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if _node:
            _node.ws_clients.discard(websocket)


def _dispatch(msg: dict):
    """Route incoming WebSocket messages to the ROS2 node."""
    if _node is None:
        return

    t = msg.get('type', '')

    if t == 'drive':
        _node.publish_drive(
            msg.get('vx', 0.0),
            msg.get('vy', 0.0),
            msg.get('wz', 0.0),
        )

    elif t == 'arm':
        cmd = msg.get('cmd', '')
        if cmd:
            _node.publish_arm(cmd)

    elif t == 'uv':
        cmd = msg.get('cmd', '')
        if cmd == 'on':
            _node.publish_arm('UV_ON')
        elif cmd == 'off':
            _node.publish_arm('UV_OFF')

    elif t == 'map_start':
        path = _node.start_mapping()
        _node.get_logger().info(f'Dashboard: map start → {path}')

    elif t == 'map_stop':
        # A scan in flight is driving the robot using this map. Kill it
        # first, hard — dropping /map out from under an active
        # NavigateToPose goal is worse than an abort.
        if _node.calib_active:
            _node.stop_calibration(graceful=False)
        _node.stop_mapping()

    elif t == 'rezero':
        reason = _node.rezero()
        if reason:
            _node.get_logger().info(f'Dashboard: re-zero refused — {reason}')

    elif t == 'goal':
        # Client already applied the two-tap arm; this is a committed goal.
        _node.publish_goal(msg.get('x', 0.0), msg.get('y', 0.0), msg.get('yaw', 0.0))

    elif t == 'calib_start':
        reason = _node.start_calibration()
        _node.get_logger().info(
            'Dashboard: calibrate start' if not reason
            else f'Dashboard: calibrate refused — {reason}')

    elif t == 'calib_stop':
        _node.stop_calibration(graceful=True)

    elif t == 'estop':
        # Order matters. Cut the motors at the hardware latch FIRST, then
        # tear down whatever is still issuing commands — not the reverse.
        _node.publish_drive(0.0, 0.0, 0.0)
        _node.send_esp32_raw('<S>')
        _node.publish_arm('ESTOP')
        _node.stop_calibration(graceful=False)
        _node.stop_mapping()

    elif t == 'estop_clear':
        _node.send_esp32_raw('<E1>')
        # FIX: Re-enable arm after ESTOP clear
        _node.publish_arm('ENABLE')
        _node.get_logger().info('ESTOP cleared — arm re-enabled')


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def _shutdown_cleanly(reason):
    """Stop the scan and SAVE THE MAP. Safe to call more than once —
    stop_mapping() and stop_calibration() both no-op when inactive.

    §17.34: this used to live only after uvicorn.run() returned, and under
    systemd it never ran. `systemctl restart` sends SIGTERM to the whole
    control group; uvicorn catches it and begins a *graceful* shutdown,
    which waits for open connections — and the dashboard's whole point is
    that a phone is holding a WebSocket open. ros2 launch and systemd
    SIGKILL the process before that wait finishes, so uvicorn.run() never
    returned and every line after it was dead code. A 24-minute mapping run
    was lost that way, with no map written and nothing in the log between
    the previous run stopping and the next process starting.

    Saving here, straight out of the signal handler, does not depend on
    uvicorn unwinding at all."""
    if _node is None:
        return
    try:
        _node.get_logger().info(f'Shutting down ({reason}) — saving map if one is open')
        _node.stop_calibration(graceful=False)
        _node.stop_mapping()
    except Exception as exc:                      # never block exit on this
        try:
            _node.get_logger().error(f'Shutdown cleanup failed: {exc}')
        except Exception:
            pass


def main(args=None):
    global _node

    rclpy.init(args=args)
    _node = PhoneDashboard()

    ros_thread = threading.Thread(target=rclpy.spin, args=(_node,), daemon=True)
    ros_thread.start()

    # Own the signals rather than letting uvicorn own them. uvicorn installs
    # its own SIGTERM/SIGINT handlers inside run(); ours has to survive that,
    # so drive the Server object directly and disable its installer.
    #
    # Guarded, because this uses more of uvicorn's API than uvicorn.run()
    # does and it could not be verified against the version on the robot
    # before shipping. If any of it is missing, fall back to the old call —
    # that loses the map on restart exactly as before, which is bad, but a
    # dashboard that does not start at all is far worse.
    _node.get_logger().info(f'uvicorn {getattr(uvicorn, "__version__", "?")}')
    server = None
    try:
        config = uvicorn.Config(
            app,
            host      = '0.0.0.0',
            port      = _node.port,
            log_level = 'warning',
        )
        server = uvicorn.Server(config)
        for attr in ('should_exit', 'run'):
            if not hasattr(server, attr):
                raise AttributeError(f'uvicorn.Server has no {attr}')
        # uvicorn renamed this. Up to ~0.29 it was install_signal_handlers(),
        # a plain method; newer versions (0.46 on the robot) use
        # capture_signals(), a context manager wrapped around serve().
        # Stubbing the wrong one silently leaves uvicorn owning SIGTERM,
        # which is the whole bug, so require one of them explicitly.
        if hasattr(server, 'capture_signals'):
            server.capture_signals = lambda: contextlib.nullcontext()
        elif hasattr(server, 'install_signal_handlers'):
            server.install_signal_handlers = lambda: None
        else:
            raise AttributeError(
                'uvicorn.Server exposes neither capture_signals nor '
                'install_signal_handlers')
    except Exception as exc:
        _node.get_logger().warn(
            f'uvicorn Server API unavailable ({exc}) — falling back to '
            'uvicorn.run(). MAP WILL NOT SURVIVE A RESTART; press STOP MAP '
            'before restarting or rebooting.')
        server = None

    if server is not None:
        def _on_signal(signum, _frame):
            # Save FIRST, exit second. map_saver_cli takes a couple of
            # seconds and systemd's default TimeoutStopSec (90 s) leaves
            # ample room; the old path spent that budget waiting on a
            # WebSocket that a connected phone never closes.
            _shutdown_cleanly(f'signal {signum}')
            server.should_exit = True

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT,  _on_signal)
        server.run()
    else:
        uvicorn.run(
            app,
            host      = '0.0.0.0',
            port      = _node.port,
            log_level = 'warning',
        )

    # Still called for a normal (non-signal) exit. Idempotent, so a signal
    # shutdown that already ran it does no work here.
    _shutdown_cleanly('server exit')
    _node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()