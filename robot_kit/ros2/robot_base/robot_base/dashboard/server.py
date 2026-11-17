#!/usr/bin/env python3
"""
dashboard - the phone UI. Drive, E-STOP, map, navigate, log, talk to the MCU.

    ros2 run robot_base dashboard                    (normally started by base.launch.py)
    python3 -m robot_base.dashboard.server --mock    (no ROS: a simulated robot,
                                                      for trying the page on a laptop)

Open http://<pi-address>:8080 on a phone on the same network.

Layout of the code
    static/index.html, app.js, style.css   the page. Plain files, served as they
                                           are on disk. NOT a string inside this
                                           Python file: on 15 Sep 2026 a single
                                           escaped apostrophe inside such a string
                                           took NarrowAisleBot's whole dashboard
                                           offline while every server-side check
                                           said "fine" (CLAUDE.md). Keep it out.
    RosIO      the ROS 2 side: subscribers, publishers, TF, process control
    MockIO     the same interface over a simulated robot
    the app    FastAPI + one WebSocket (/ws) carrying JSON both ways

What the buttons do
    E-STOP      zero /cmd_vel_manual, send <S> (latches in the firmware), cancel
                every Nav2 goal. Mapping keeps running: a stop should not cost
                you the map. CLEAR sends <E1>.
    MAP         start/stop mapping.launch.py. Stop saves the map first.
    SAVE        save the map now, keep mapping.
    NAV         start/stop nav2.launch.py (needs MAP running).
    GOAL        tap the map for a goal; drag to set the heading.
    RE-ZERO     odometry (0, 0, 0) where the robot stands. Refused while MAP or
                NAV runs: slam_toolbox pinned map -> odom at its first scan.
    REC         log /mcu/telemetry to <log_dir>/dash_<stamp>.csv
    console     send a raw command to the MCU, e.g. <?> or <G,20,100,0>
"""

import argparse
import asyncio
import base64
import json
import math
import os
import signal
import subprocess
import threading
import time
from collections import deque
from datetime import datetime

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


# ══════════════════════════════════════════════════════════════════════
#  Process control (shared by RosIO and MockIO)
# ══════════════════════════════════════════════════════════════════════

class Procs:
    """Start/stop launch files in their own process groups, with their
    output in a log file (not /dev/null: you will want it)."""

    def __init__(self, log_dir, notify, mock=False):
        self.log_dir = os.path.expanduser(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.notify = notify
        self.mock = mock
        self.procs = {}

    def running(self, name):
        p = self.procs.get(name)
        if self.mock:
            return bool(p)
        return p is not None and p.poll() is None

    def start(self, name, launch_file):
        if self.running(name):
            self.notify("info", f"{name} already running")
            return False
        if self.mock:
            self.procs[name] = True
            self.notify("info", f"[mock] started {launch_file}")
            return True
        log = os.path.join(self.log_dir, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        fh = open(log, "w")
        self.procs[name] = subprocess.Popen(["ros2", "launch", "robot_base", launch_file],
                                            stdout=fh, stderr=subprocess.STDOUT,
                                            start_new_session=True)
        self.notify("info", f"started {launch_file} (log: {log})")
        return True

    def stop(self, name, timeout=10.0):
        p = self.procs.pop(name, None)
        if self.mock:
            if p:
                self.notify("info", f"[mock] stopped {name}")
            return
        if p is None or p.poll() is not None:
            return
        try:
            os.killpg(p.pid, signal.SIGINT)
            p.wait(timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            self.notify("warn", f"{name} did not stop in {timeout:.0f} s; killed")
        except ProcessLookupError:
            pass
        self.notify("info", f"stopped {name}")


def write_pgm(grid, path_base):
    """Fallback map save from the cached OccupancyGrid (trinary, like
    map_saver_cli). grid = dict(width, height, resolution, origin, data[int])."""
    w, h = grid["width"], grid["height"]
    px = bytearray(w * h)
    for j in range(h):
        for i in range(w):
            v = grid["data"][j * w + i]
            px[(h - 1 - j) * w + i] = 205 if v < 0 else (0 if v >= 65 else (254 if v <= 25 else 205))
    with open(path_base + ".pgm", "wb") as fh:
        fh.write(f"P5\n{w} {h}\n255\n".encode() + bytes(px))
    ox, oy, oyaw = grid["origin"]
    with open(path_base + ".yaml", "w") as fh:
        fh.write(f"image: {os.path.basename(path_base)}.pgm\nmode: trinary\n"
                 f"resolution: {grid['resolution']}\norigin: [{ox}, {oy}, {oyaw}]\n"
                 f"negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n")


# ══════════════════════════════════════════════════════════════════════
#  Common state
# ══════════════════════════════════════════════════════════════════════

class BaseIO:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.notices = deque(maxlen=200)
        self.notice_seq = 0
        self.pose = None            # (x, y, yaw, frame)
        self.odom = None            # (x, y, yaw)
        self.wheels = None          # dict(target, actual, pwm)
        self.scan = []              # [(x, y)] in the pose frame
        self.grid = None            # dict(width, height, resolution, origin, data)
        self.map_version = 0
        self.estop = False
        self.mcu_seen = 0.0
        self.nav_status = ""
        self.goal = None
        self.rec = None
        self.procs = Procs(cfg["log_dir"], self.notify, mock=isinstance(self, MockIO))
        self.last_drive = 0.0
        self.drive_nonzero = False

    def notify(self, level, text):
        with self.lock:
            self.notice_seq += 1
            self.notices.append((self.notice_seq, level, text))
        print(f"[dashboard] {level}: {text}", flush=True)

    # ── commands from the page ────────────────────────────────────────
    def drive_from_stick(self, x, y, r):
        """x, y: joystick, -1..1, right and up. r: turn input, -1..1, + = left."""
        c = self.cfg
        x, y, r = (max(-1.0, min(1.0, float(v))) for v in (x, y, r))
        if c["holonomic"]:
            vx, vy, wz = y * c["max_linear"], -x * c["max_linear"], r * c["max_angular"]
        else:
            vx, vy, wz = y * c["max_linear"], 0.0, (r - x) * c["max_angular"]
            wz = max(-c["max_angular"], min(c["max_angular"], wz))
        if self.estop:
            vx = vy = wz = 0.0
        self.publish_twist(vx, vy, wz)
        self.last_drive = time.time()
        self.drive_nonzero = any(abs(v) > 1e-6 for v in (vx, vy, wz))

    def deadman(self):
        """Called often. A phone that loses the WebSocket mid-drive must not
        leave the last command standing (twist_mux times out too, at 0.5 s)."""
        if self.drive_nonzero and time.time() - self.last_drive > 0.3:
            self.publish_twist(0.0, 0.0, 0.0)
            self.drive_nonzero = False

    def handle(self, msg):
        t = msg.get("type")
        if t == "drive":
            self.drive_from_stick(msg.get("x", 0), msg.get("y", 0), msg.get("r", 0))
        elif t == "estop":
            self.publish_twist(0.0, 0.0, 0.0)
            self.drive_nonzero = False
            self.mcu("<S>")
            self.cancel_goals()
            self.estop = True
            self.notify("warn", "E-STOP latched. CLEAR to drive again.")
        elif t == "estop_clear":
            self.mcu("<E1>")
            self.estop = False
            self.notify("info", "E-STOP cleared")
        elif t == "map_start":
            self.procs.start("mapping", "mapping.launch.py")
        elif t == "map_stop":
            if self.procs.running("nav"):
                self.procs.stop("nav")
            self.save_map()
            self.procs.stop("mapping")
        elif t == "map_save":
            self.save_map()
        elif t == "nav_start":
            if not self.procs.running("mapping"):
                self.notify("warn", "start MAP first: Nav2 needs a map and the map -> odom transform")
            else:
                self.procs.start("nav", "nav2.launch.py")
        elif t == "nav_stop":
            self.cancel_goals()
            self.procs.stop("nav")
        elif t == "goal":
            if not self.procs.running("nav"):
                self.notify("warn", "NAV is not running")
            else:
                self.send_goal(float(msg["x"]), float(msg["y"]), float(msg["yaw"]))
        elif t == "goal_cancel":
            self.cancel_goals()
        elif t == "rezero":
            if self.procs.running("mapping") or self.procs.running("nav"):
                self.notify("warn", "re-zero refused while MAP or NAV runs. Stop them, re-zero, "
                                    "then start MAP again.")
            else:
                self.rezero()
                self.notify("info", "odometry re-zeroed here")
        elif t == "rec_start":
            self.rec_start()
        elif t == "rec_stop":
            self.rec_stop()
        elif t == "mcu":
            cmd = str(msg.get("cmd", "")).strip()
            if cmd.startswith("<") and cmd.endswith(">") and len(cmd) < 120:
                self.mcu(cmd)
                self.notify("mcu", f"> {cmd}")
            else:
                self.notify("warn", "MCU commands look like <P> or <G,20,100,0>")

    def save_map(self):
        if not self.procs.running("mapping"):
            self.notify("warn", "no map to save: MAP is not running")
            return None
        base = os.path.join(os.path.expanduser(self.cfg["map_dir"]),
                            f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        ok = self.save_map_to(base)
        if not ok and self.grid:
            write_pgm(self.grid, base)
            ok = True
            self.notify("warn", "map_saver_cli failed; wrote the dashboard's own copy instead")
        if ok:
            self.notify("info", f"map saved: {base}.pgm / .yaml")
        else:
            self.notify("error", "map NOT saved: no map received yet")
        return base if ok else None

    def rec_start(self):
        from robot_base.telemetry_csv import TelemetryCsv
        if self.rec:
            return
        self.rec = TelemetryCsv(self.cfg["log_dir"], self.cfg["wheel_names"], tag="dash")
        self.notify("info", f"recording to {self.rec.path}")

    def rec_stop(self):
        if not self.rec:
            return
        r, self.rec = self.rec, None
        path = r.close()
        self.notify("info", f"recorded {r.rows} rows" + (f" -> {path}" if path else ""))

    def shutdown(self):
        self.publish_twist(0.0, 0.0, 0.0)
        self.rec_stop()
        if self.procs.running("nav"):
            self.procs.stop("nav")
        if self.procs.running("mapping"):
            self.notify("info", "shutting down: saving the map before stopping SLAM")
            self.save_map()
            self.procs.stop("mapping")

    # ── what the page sees ───────────────────────────────────────────
    def snapshot(self):
        with self.lock:
            return {
                "type": "state",
                "pose": self.pose, "odom": self.odom, "wheels": self.wheels,
                "estop": self.estop, "mcu_ok": time.time() - self.mcu_seen < 1.5,
                "mapping": self.procs.running("mapping"), "nav": self.procs.running("nav"),
                "nav_status": self.nav_status, "goal": self.goal,
                "rec": self.rec.rows if self.rec else None,
            }

    def scan_msg(self):
        with self.lock:
            pts = self.scan
        step = max(1, len(pts) // 360)
        return {"type": "scan", "points": [[round(x, 3), round(y, 3)] for x, y in pts[::step]]}

    def map_msg(self):
        with self.lock:
            g = self.grid
            v = self.map_version
        if not g:
            return None, v
        data = bytes(255 if c < 0 else min(100, c) for c in g["data"])
        return {"type": "map", "width": g["width"], "height": g["height"],
                "resolution": g["resolution"], "origin": g["origin"],
                "data": base64.b64encode(data).decode("ascii")}, v


# ══════════════════════════════════════════════════════════════════════
#  ROS 2
# ══════════════════════════════════════════════════════════════════════

class RosIO(BaseIO):

    def __init__(self, node, cfg):
        super().__init__(cfg)
        from action_msgs.msg import GoalStatusArray
        from action_msgs.srv import CancelGoal
        from geometry_msgs.msg import PoseStamped, Twist
        from nav_msgs.msg import OccupancyGrid, Odometry
        from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                               qos_profile_sensor_data)
        from sensor_msgs.msg import LaserScan
        from std_msgs.msg import Empty, Float64MultiArray, String
        import tf2_ros

        self.node = node
        self.Twist, self.PoseStamped, self.String, self.Empty = Twist, PoseStamped, String, Empty
        self.CancelGoal = CancelGoal
        self.pub_twist = node.create_publisher(Twist, "cmd_vel_manual", 10)
        self.pub_mcu = node.create_publisher(String, "mcu/command", 10)
        self.pub_reset = node.create_publisher(Empty, "odom/reset", 10)
        self.pub_goal = node.create_publisher(PoseStamped, "goal_pose", 10)
        self.cancel_cli = node.create_client(CancelGoal, "navigate_to_pose/_action/cancel_goal")
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(OccupancyGrid, "map", self._on_map, latched)
        node.create_subscription(LaserScan, "scan_filtered", self._on_scan, qos_profile_sensor_data)
        node.create_subscription(Float64MultiArray, "mcu/telemetry", self._on_tel, 20)
        node.create_subscription(String, "mcu/status", self._on_status, 20)
        node.create_subscription(Odometry, "odom", self._on_odom, 10)
        node.create_subscription(GoalStatusArray, "navigate_to_pose/_action/status", self._on_nav, 10)
        self.tf_buf = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buf, node)
        node.create_timer(0.1, self._update_pose)
        self.n = len(cfg["wheel_names"])

    def _tf2d(self, parent, child):
        import rclpy.time
        try:
            t = self.tf_buf.lookup_transform(parent, child, rclpy.time.Time())
        except Exception:  # noqa: BLE001  (frame does not exist yet)
            return None
        tr = t.transform
        return tr.translation.x, tr.translation.y, yaw_of(tr.rotation)

    def _update_pose(self):
        for frame in ("map", "odom"):
            p = self._tf2d(frame, "base_link")
            if p:
                with self.lock:
                    self.pose = [round(p[0], 4), round(p[1], 4), round(p[2], 4), frame]
                return

    def _on_map(self, msg):
        info = msg.info
        g = {"width": info.width, "height": info.height, "resolution": info.resolution,
             "origin": [info.origin.position.x, info.origin.position.y, yaw_of(info.origin.orientation)],
             "data": list(msg.data)}
        with self.lock:
            self.grid = g
            self.map_version += 1

    def _on_scan(self, msg):
        frame = "map" if self.pose and self.pose[3] == "map" else "odom"
        tf = self._tf2d(frame, msg.header.frame_id)
        if not tf:
            return
        tx, ty, tyaw = tf
        c, s = math.cos(tyaw), math.sin(tyaw)
        pts = []
        a = msg.angle_min
        for r in msg.ranges:
            if msg.range_min <= r <= msg.range_max:
                lx, ly = r * math.cos(a), r * math.sin(a)
                pts.append((tx + c * lx - s * ly, ty + s * lx + c * ly))
            a += msg.angle_increment
        with self.lock:
            self.scan = pts

    def _on_tel(self, msg):
        d = list(msg.data)
        n = self.n
        vals = d[1:]
        if len(vals) < 3 * n:
            return
        with self.lock:
            self.mcu_seen = time.time()
            self.wheels = {"target": [round(vals[3 * i], 3) for i in range(n)],
                           "actual": [round(vals[3 * i + 1], 3) for i in range(n)],
                           "pwm": [int(vals[3 * i + 2]) for i in range(n)]}
            rec = self.rec
        if rec:
            rec.add(time.time(), d)

    def _on_status(self, msg):
        line = msg.data
        if "ESTOP_LATCHED" in line or line.startswith("[TRIP"):
            self.estop = True
        elif line == "[OK,ENABLED]":
            self.estop = False
        if not line.startswith("[OK,LOG"):        # the bridge's keep-alive, every 5 s
            self.notify("mcu", line)

    def _on_odom(self, msg):
        p = msg.pose.pose
        with self.lock:
            self.odom = [round(p.position.x, 4), round(p.position.y, 4), round(yaw_of(p.orientation), 4)]

    def _on_nav(self, msg):
        names = {1: "accepted", 2: "driving", 3: "canceling", 4: "SUCCEEDED", 5: "CANCELED", 6: "ABORTED"}
        if msg.status_list:
            st = names.get(msg.status_list[-1].status, "")
            if st != self.nav_status:
                self.nav_status = st
                if st in ("SUCCEEDED", "CANCELED", "ABORTED"):
                    self.notify("info" if st == "SUCCEEDED" else "warn", f"goal {st}")

    # ── outputs ───────────────────────────────────────────────────────
    def publish_twist(self, vx, vy, wz):
        m = self.Twist()
        m.linear.x, m.linear.y, m.angular.z = float(vx), float(vy), float(wz)
        self.pub_twist.publish(m)

    def mcu(self, cmd):
        m = self.String()
        m.data = cmd
        self.pub_mcu.publish(m)

    def rezero(self):
        self.pub_reset.publish(self.Empty())

    def send_goal(self, x, y, yaw):
        m = self.PoseStamped()
        m.header.frame_id = "map"
        m.header.stamp = self.node.get_clock().now().to_msg()
        m.pose.position.x, m.pose.position.y = x, y
        m.pose.orientation.z, m.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        self.pub_goal.publish(m)
        self.goal = [round(x, 3), round(y, 3), round(yaw, 3)]
        self.notify("info", f"goal ({x:.2f}, {y:.2f}) heading {math.degrees(yaw):.0f} deg")

    def cancel_goals(self):
        self.goal = None
        if self.cancel_cli.service_is_ready():
            # A zero goal id and zero stamp means "cancel every goal".
            self.cancel_cli.call_async(self.CancelGoal.Request())

    def save_map_to(self, base):
        try:
            r = subprocess.run(["ros2", "run", "nav2_map_server", "map_saver_cli", "-f", base,
                                "--ros-args", "-p", "map_subscribe_transient_local:=true"],
                               capture_output=True, text=True, timeout=25)
            return r.returncode == 0 and os.path.exists(base + ".yaml")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


# ══════════════════════════════════════════════════════════════════════
#  Mock robot (no ROS): a 6 x 4 m room with a box, a differential or
#  holonomic base, a 180-beam scanner and a map that fills in as it looks.
# ══════════════════════════════════════════════════════════════════════

class MockIO(BaseIO):
    RES = 0.05

    def __init__(self, cfg):
        super().__init__(cfg)
        self.walls = [((-1, -2), (5, -2)), ((5, -2), (5, 2)), ((5, 2), (-1, 2)), ((-1, 2), (-1, -2)),
                      ((2, -0.5), (2.6, -0.5)), ((2.6, -0.5), (2.6, 0.3)), ((2.6, 0.3), (2, 0.3)),
                      ((2, 0.3), (2, -0.5))]
        self.x = self.y = self.th = 0.0
        self.cmd = (0.0, 0.0, 0.0)
        self.w, self.h = int(6.4 / self.RES), int(4.4 / self.RES)
        self.origin = [-1.2, -2.2, 0.0]
        self.cells = [-1] * (self.w * self.h)
        self.mcu_seen = time.time()
        threading.Thread(target=self._run, daemon=True).start()

    def publish_twist(self, vx, vy, wz):
        self.cmd = (vx, vy if self.cfg["holonomic"] else 0.0, wz)

    def mcu(self, cmd):
        if cmd == "<S>":
            self.estop = True
        elif cmd == "<E1>":
            self.estop = False
        self.notify("mcu", "[OK,MOCK]" if cmd not in ("<S>", "<E1>") else
                    ("[OK,ESTOP_LATCHED]" if cmd == "<S>" else "[OK,ENABLED]"))

    def rezero(self):
        self.x = self.y = self.th = 0.0

    def send_goal(self, x, y, yaw):
        self.goal = [round(x, 3), round(y, 3), round(yaw, 3)]
        self.nav_status = "driving"
        self.notify("info", f"goal ({x:.2f}, {y:.2f}) heading {math.degrees(yaw):.0f} deg")

    def cancel_goals(self):
        if self.goal:
            self.nav_status = "CANCELED"
        self.goal = None

    def save_map_to(self, base):
        with self.lock:
            g = dict(width=self.w, height=self.h, resolution=self.RES, origin=self.origin,
                     data=list(self.cells))
        write_pgm(g, base)
        return True

    def _ray(self, ox, oy, a, rmax=6.0):
        dx, dy = math.cos(a), math.sin(a)
        best = rmax
        for (x1, y1), (x2, y2) in self.walls:
            ex, ey = x2 - x1, y2 - y1
            den = dx * ey - dy * ex
            if abs(den) < 1e-9:
                continue
            t = ((x1 - ox) * ey - (y1 - oy) * ex) / den
            u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
            if 0 <= u <= 1 and 0 < t < best:
                best = t
        return best

    def _mark(self, x, y, v):
        i = int((x - self.origin[0]) / self.RES)
        j = int((y - self.origin[1]) / self.RES)
        if 0 <= i < self.w and 0 <= j < self.h:
            k = j * self.w + i
            if self.cells[k] != 100 or v == 100:
                self.cells[k] = v

    def _run(self):
        dt, k = 0.05, 0
        while True:
            time.sleep(dt)
            k += 1
            vx, vy, wz = (0.0, 0.0, 0.0) if self.estop else self.cmd
            if self.goal and self.procs.running("nav") and not self.estop:
                gx, gy, gyaw = self.goal
                d = math.hypot(gx - self.x, gy - self.y)
                if d > 0.05:
                    head = math.atan2(gy - self.y, gx - self.x)
                    err = math.atan2(math.sin(head - self.th), math.cos(head - self.th))
                    wz = max(-0.6, min(0.6, 2.0 * err))
                    vx = 0.15 if abs(err) < 0.3 else 0.0
                else:
                    err = math.atan2(math.sin(gyaw - self.th), math.cos(gyaw - self.th))
                    wz = max(-0.6, min(0.6, 2.0 * err))
                    if abs(err) < 0.05:
                        self.goal = None
                        self.nav_status = "SUCCEEDED"
                        self.notify("info", "goal SUCCEEDED")
            c, s = math.cos(self.th), math.sin(self.th)
            self.x += (vx * c - vy * s) * dt
            self.y += (vx * s + vy * c) * dt
            self.th = math.atan2(math.sin(self.th + wz * dt), math.cos(self.th + wz * dt))
            lx, ly = self.x + 0.10 * c, self.y + 0.10 * s
            pts = []
            for b in range(180):
                a = self.th - math.pi + b * 2 * math.pi / 180
                r = self._ray(lx, ly, a)
                if r < 6.0:
                    pts.append((lx + r * math.cos(a), ly + r * math.sin(a)))
                if self.procs.running("mapping") and k % 4 == 0:
                    for q in range(int(r / self.RES)):
                        self._mark(lx + q * self.RES * math.cos(a), ly + q * self.RES * math.sin(a), 0)
                    if r < 6.0:
                        self._mark(lx + r * math.cos(a), ly + r * math.sin(a), 100)
            n = len(self.cfg["wheel_names"])
            wl = (vx - wz * 0.15) / 0.05
            wr = (vx + wz * 0.15) / 0.05
            tg = [wl if i % 2 == 0 else wr for i in range(n)]
            with self.lock:
                frame = "map" if self.procs.running("mapping") else "odom"
                self.pose = [round(self.x, 4), round(self.y, 4), round(self.th, 4), frame]
                self.odom = list(self.pose[:3])
                self.scan = pts
                self.mcu_seen = time.time()
                self.wheels = {"target": [round(v, 3) for v in tg], "actual": [round(v * 0.98, 3) for v in tg],
                               "pwm": [int(v * 16) for v in tg]}
                if self.procs.running("mapping") and k % 20 == 0:
                    self.grid = dict(width=self.w, height=self.h, resolution=self.RES,
                                     origin=self.origin, data=list(self.cells))
                    self.map_version += 1
            if self.rec:
                vals = []
                for i in range(n):
                    vals += [tg[i], tg[i] * 0.98, tg[i] * 16]
                self.rec.add(time.time(), [k * 50.0] + vals)


# ══════════════════════════════════════════════════════════════════════
#  Web app
# ══════════════════════════════════════════════════════════════════════

def make_app(io):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI()
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC, "index.html"),
                            headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        s = io.snapshot()
        return {"ok": True, "mcu_ok": s["mcu_ok"], "mapping": s["mapping"], "nav": s["nav"]}

    @app.on_event("shutdown")
    def _shutdown():
        io.shutdown()

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        c = io.cfg
        await sock.send_text(json.dumps({"type": "hello", "config": {
            "name": c["name"], "wheel_names": c["wheel_names"], "holonomic": c["holonomic"],
            "max_linear": c["max_linear"], "max_angular": c["max_angular"],
            "footprint": list(zip(c["footprint_x"], c["footprint_y"])),
            "laser": [c["laser_x"], c["laser_y"]], "mock": isinstance(io, MockIO)}}))
        seen_map, seen_notice = -1, io.notice_seq - 10

        async def sender():
            nonlocal seen_map, seen_notice
            k = 0
            while True:
                io.deadman()
                await sock.send_text(json.dumps(io.snapshot()))
                if k % 2 == 0:
                    await sock.send_text(json.dumps(io.scan_msg()))
                if k % 10 == 0:
                    m, v = io.map_msg()
                    if m and v != seen_map:
                        seen_map = v
                        await sock.send_text(json.dumps(m))
                with io.lock:
                    new = [n for n in io.notices if n[0] > seen_notice]
                for seq, level, text in new:
                    seen_notice = seq
                    await sock.send_text(json.dumps({"type": "log", "level": level, "text": text}))
                k += 1
                await asyncio.sleep(0.1)

        task = asyncio.create_task(sender())
        try:
            while True:
                msg = json.loads(await sock.receive_text())
                await asyncio.get_running_loop().run_in_executor(None, io.handle, msg)
        except (WebSocketDisconnect, RuntimeError, json.JSONDecodeError):
            pass
        finally:
            task.cancel()
            io.publish_twist(0.0, 0.0, 0.0)      # page gone: stop

    return app


def config_from_args(args):
    return {"name": args.name, "wheel_names": args.wheels.split(","), "holonomic": args.holonomic,
            "max_linear": 0.2, "max_angular": 0.8, "footprint_x": [0.2, -0.2, -0.2, 0.2],
            "footprint_y": [0.17, 0.17, -0.17, -0.17], "laser_x": 0.1, "laser_y": 0.0,
            "log_dir": args.log_dir, "map_dir": args.log_dir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="no ROS: simulated robot")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--name", default="mock")
    ap.add_argument("--wheels", default="left,right")
    ap.add_argument("--holonomic", action="store_true")
    ap.add_argument("--log-dir", default="~/robot_logs")
    args, ros_args = ap.parse_known_args()
    import uvicorn

    if args.mock:
        io = MockIO(config_from_args(args))
        uvicorn.run(make_app(io), host="0.0.0.0", port=args.port, log_level="warning")
        return

    import rclpy
    from rclpy.node import Node
    rclpy.init(args=ros_args)
    node = Node("dashboard")
    for k, v in (("port", 8080), ("log_dir", "~/robot_logs"), ("map_dir", "~/maps"),
                 ("wheel_names", ["left", "right"]), ("holonomic", False), ("max_linear", 0.2),
                 ("max_angular", 0.8), ("footprint_x", [0.2, -0.2, -0.2, 0.2]),
                 ("footprint_y", [0.17, 0.17, -0.17, -0.17]), ("laser_x", 0.0), ("laser_y", 0.0)):
        node.declare_parameter(k, v)
    g = lambda k: node.get_parameter(k).value  # noqa: E731
    cfg = {k: g(k) for k in ("log_dir", "map_dir", "holonomic", "max_linear", "max_angular",
                             "laser_x", "laser_y")}
    cfg.update(name=os.uname().nodename, wheel_names=list(g("wheel_names")),
               footprint_x=list(g("footprint_x")), footprint_y=list(g("footprint_y")))
    io = RosIO(node, cfg)
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    node.get_logger().info(f"dashboard on http://0.0.0.0:{g('port')}")
    try:
        uvicorn.run(make_app(io), host="0.0.0.0", port=int(g("port")), log_level="warning")
    finally:
        io.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
