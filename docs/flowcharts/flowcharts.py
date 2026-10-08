#!/usr/bin/env python3
"""NarrowAisleBot firmware flowcharts, drawn from the code.

Two families of figures share one drawing kit:

  handout  (h1..h3)  dense, 1160 to 1560 px wide, for the report appendix, a poster
                     or a printed A3 sheet. Text is about 10 px, so it is NOT readable
                     when pasted onto a slide.
  slide    (s1..s6)  1760 x 990 (16:9), text 20 px and up, one idea per figure, meant
                     to be pasted onto a slide full width.

Run:  python3 docs/flowcharts/flowcharts.py          writes svg/*.svg
Then: node docs/flowcharts/render_png.js             writes png/*.png and runs the layout check

Every number and topic name below was checked against the source on 2 Oct 2026,
see QA_2026-10-02.md for the row-by-row list.
"""
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return html.escape(s, quote=False)


CLASSES = ["manual", "auto", "merge", "fb", "scan", "ctl", "tf", "warn"]

PROFILES = {
    # padding, title baseline, first sub baseline, sub step, marker size
    "detail": dict(pad=9, t_dy=17, s_dy0=31, s_step=12.5, mk=7, h_min=40),
    "slide": dict(pad=16, t_dy=34, s_dy0=64, s_step=26, mk=13, h_min=60),
}


class Fig:
    def __init__(self, sid, w, h, claim, profile="detail"):
        self.sid, self.w, self.h, self.claim = sid, w, h, claim
        self.pf = PROFILES[profile]
        self.profile = profile
        self.bands, self.edges, self.nodes, self.labels = [], [], [], []
        self.rects = {}        # id -> (x, y, w, h)
        self.segments = []     # (edge index, (x1, y1), (x2, y2))
        self.nrect = []        # every node rect, for the crossing check

    # ------------------------------------------------------------- shapes
    def band(self, x, y, w, h, title, kind="pi", pos="top"):
        a, _, b = title.partition("  ")
        sub = f'<tspan class="bandsub" dx="10">{esc(b)}</tspan>' if b else ""
        dy = 15 if self.profile == "detail" else 27
        if pos == "bottom":
            dy = h - 12
        self.bands.append(
            f'<rect class="band band-{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
            f'<text class="bandlbl" x="{x + 14}" y="{y + dy}">{esc(a)}{sub}</text>')

    def node(self, x, y, w, h, title, lines=(), kind="ros", nid=None):
        pf = self.pf
        if h is None:
            n = len(lines)
            h = pf["h_min"] if n == 0 else int(pf["s_dy0"] + (n - 1) * pf["s_step"] + (14 if self.profile == "slide" else 12))
            h = max(h, pf["h_min"])
        t = [f'<g class="node node-{kind}">',
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/>',
             f'<text class="nt" x="{x + pf["pad"]}" y="{y + pf["t_dy"]}">{esc(title)}</text>']
        for i, ln in enumerate(lines):
            t.append(f'<text class="ns" x="{x + pf["pad"]}" y="{y + pf["s_dy0"] + i * pf["s_step"]}">{esc(ln)}</text>')
        t.append("</g>")
        self.nodes.append("".join(t))
        self.nrect.append((nid or title, x, y, w, h))
        if nid:
            self.rects[nid] = (x, y, w, h)
        return (x, y, w, h)

    def port(self, nid, side, f=0.5, off=0):
        x, y, w, h = self.rects[nid]
        if side == "l":
            return (x, y + h * f + off)
        if side == "r":
            return (x + w, y + h * f + off)
        if side == "t":
            return (x + w * f + off, y)
        return (x + w * f + off, y + h)

    def edge(self, cls, pts, both=False, dash=False, thick=False):
        d = "M" + " L".join(f"{round(x, 1)},{round(y, 1)}" for x, y in pts)
        mk = f"a-{self.sid}-{cls}"
        st = f' marker-start="url(#{mk})"' if both else ""
        k = f"e e-{cls}" + (" dash" if dash else "") + (" thick" if thick else "")
        self.edges.append(f'<path class="{k}" data-c="{cls}" d="{d}" marker-end="url(#{mk})"{st}/>')
        idx = len(self.edges) - 1
        for a, b in zip(pts, pts[1:]):
            self.segments.append((idx, a, b))

    def lbl(self, text, x, y, cls="ctl", anchor="middle"):
        self.labels.append(
            f'<text class="lb lb-{cls}" data-c="{cls}" x="{round(x, 1)}" y="{round(y, 1)}" text-anchor="{anchor}">{esc(text)}</text>')

    def note(self, text, x, y, anchor="start", cls="note"):
        self.labels.append(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(text)}</text>')

    def legend(self, x, y, items):
        """items: (cls, text, dash). Drawn in slide scale."""
        step = 38
        for i, (cls, text, dash) in enumerate(items):
            yy = y + i * step
            d = " dash" if dash else ""
            mk = f"a-{self.sid}-{cls}"
            self.edges.append(
                f'<path class="e e-{cls}{d} leg" data-c="{cls}" d="M{x},{yy} L{x + 70},{yy}" marker-end="url(#{mk})"/>')
            self.labels.append(f'<text class="legtxt leg" x="{x + 88}" y="{yy + 7}">{esc(text)}</text>')

    # ------------------------------------------------------------- output
    def markers(self):
        s = self.pf["mk"]
        out = ["<defs>"]
        for c in CLASSES:
            out.append(
                f'<marker id="a-{self.sid}-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{s}" markerHeight="{s}" '
                f'orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,1 L9,5 L0,9 z" class="mk mk-{c}"/></marker>')
        out.append("</defs>")
        return "".join(out)

    def inner(self):
        return (self.markers() + "".join(self.bands) + "".join(self.edges)
                + "".join(self.nodes) + "".join(self.labels))

    def svg_inline(self):
        cls = "fig " + ("big" if self.profile == "slide" else "small")
        return (f'<svg id="{self.sid}" class="{cls}" viewBox="0 0 {self.w} {self.h}" role="img" '
                f'aria-label="{esc(self.claim)}">{self.inner()}</svg>')

    def svg_standalone(self, css=None):
        css = css or STANDALONE_CSS
        cls = "fig " + ("big" if self.profile == "slide" else "small")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" id="{self.sid}" class="{cls}" '
                f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img" '
                f'aria-label="{esc(self.claim)}"><title>{esc(self.claim)}</title>'
                f'<style>{css}</style>'
                f'<rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>{self.inner()}</svg>')

    # ------------------------------------------------------------- checks
    def check_edges(self):
        """Flag any edge segment that passes through a node rectangle."""
        bad = []
        for idx, (x1, y1), (x2, y2) in self.segments:
            for name, rx, ry, rw, rh in self.nrect:
                if _seg_hits_rect(x1, y1, x2, y2, rx + 2, ry + 2, rx + rw - 2, ry + rh - 2):
                    bad.append(f"{self.sid}: edge #{idx} segment ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f}) crosses node '{name}'")
        return bad


def _seg_hits_rect(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    # axis-aligned segments only (every edge here is orthogonal)
    if abs(x1 - x2) < 0.01:
        x = x1
        lo, hi = sorted((y1, y2))
        return rx1 < x < rx2 and hi > ry1 and lo < ry2
    if abs(y1 - y2) < 0.01:
        y = y1
        lo, hi = sorted((x1, x2))
        return ry1 < y < ry2 and hi > rx1 and lo < rx2
    raise ValueError("non-orthogonal edge")


# Light-theme, self-contained CSS for the standalone SVG files and the PNGs.
STANDALONE_CSS = """
svg text{font-family:"IBM Plex Sans","Segoe UI",Arial,Helvetica,sans-serif;fill:#172126}
.band{stroke-width:1.4}
.band-op{fill:#E9EEF1;stroke:#9AA7AE}
.band-pi{fill:#F3F6F4;stroke:#52606A}
.band-od{fill:#FBFBF7;stroke:#52606A;stroke-dasharray:8 6}
.band-hw{fill:#EDEFE9;stroke:#52606A}
.band-pl{fill:#F7F9F8;stroke:#52606A}
.bandlbl{font-weight:600;font-size:10.5px;fill:#52606A;letter-spacing:.08em}
.bandsub{font-family:"IBM Plex Mono",Consolas,"Courier New",monospace;font-weight:500;font-size:11px;letter-spacing:0;fill:#52606A}
.node rect{fill:#FFFFFF;stroke:#172126;stroke-width:1.2}
.node-ext rect{fill:#E9EEF1;stroke:#52606A}
.node.dashed rect{stroke-dasharray:4 3}
.node-hwn rect{fill:#E3E8E2;stroke:#172126;stroke-width:1.6}
.node-warnbox rect{fill:#FFFFFF;stroke:#C62828;stroke-width:1.4}
.node-callout rect{fill:#F7F9F8;stroke:#9AA7AE;stroke-dasharray:6 4}
.nt{font-family:"IBM Plex Mono",Consolas,"Courier New",monospace;font-weight:600;font-size:11px}
.node-grp .nt,.node-callout .nt{font-family:"IBM Plex Sans","Segoe UI",Arial,sans-serif}
.ns{font-weight:400;font-size:10.5px;fill:#52606A}
.node-grp .ns{font-family:"IBM Plex Mono",Consolas,"Courier New",monospace;font-size:10px}
.note,.note-s{font-size:12px;fill:#52606A}.note-s{font-size:10.5px}
.e{fill:none;stroke-width:1.6;stroke-linejoin:round}
.e.thick{stroke-width:2.8}
.e.dash,.e-tf{stroke-dasharray:5 4}
.e-manual{stroke:#0072B2}.mk-manual{fill:#0072B2}
.e-auto{stroke:#C2410C}.mk-auto{fill:#C2410C}
.e-merge{stroke:#172126}.mk-merge{fill:#172126}
.e-fb{stroke:#00896A}.mk-fb{fill:#00896A}
.e-scan{stroke:#7C4DA8}.mk-scan{fill:#7C4DA8}
.e-ctl{stroke:#66737C}.mk-ctl{fill:#66737C}
.e-tf{stroke:#8A949B}.mk-tf{fill:#8A949B}
.e-warn{stroke:#C62828}.mk-warn{fill:#C62828}
.lb{font-family:"IBM Plex Mono",Consolas,"Courier New",monospace;font-weight:500;font-size:10px;paint-order:stroke;stroke:#FFFFFF;stroke-width:4px;stroke-linejoin:round}
.lb-manual{fill:#0072B2}.lb-auto{fill:#C2410C}.lb-merge{fill:#172126}.lb-fb{fill:#00896A}
.lb-scan{fill:#7C4DA8}.lb-ctl{fill:#66737C}.lb-tf{fill:#6A747B}.lb-warn{fill:#C62828}
/* slide scale */
.big .band{stroke-width:2}
.big .bandlbl{font-size:21px;letter-spacing:.05em}
.big .bandsub{font-size:21px}
.big .node rect{stroke-width:2.2}
.big .node-hwn rect{stroke-width:2.8}
.big .nt{font-size:24px}
.big .node-grp .nt,.big .node-callout .nt{font-size:26px}
.big .ns{font-size:21px}
.big .node-grp .ns{font-size:21px}
.big .note{font-size:21px}
.big .e{stroke-width:3.2}
.big .e.thick{stroke-width:5.5}
.big .lb{font-size:21px;stroke-width:6px}
.big .legtxt{font-size:21px}
.legtxt{font-size:12px}
"""


# Black-and-white variant for print and plain documents: every colour goes to a grey,
# the colour legend is hidden (it would mean nothing), labels carry the topic names.
_MONO_MAP = {
    "#0072B2": "#1A1A1A", "#C2410C": "#1A1A1A", "#00896A": "#1A1A1A", "#7C4DA8": "#1A1A1A",
    "#C62828": "#1A1A1A", "#172126": "#111111", "#66737C": "#4D4D4D", "#8A949B": "#6E6E6E",
    "#6A747B": "#555555", "#52606A": "#444444", "#9AA7AE": "#8C8C8C",
    "#E9EEF1": "#F2F2F2", "#F3F6F4": "#FFFFFF", "#FBFBF7": "#FFFFFF", "#EDEFE9": "#FFFFFF",
    "#F7F9F8": "#FFFFFF", "#E3E8E2": "#E6E6E6",
}
MONO_CSS = STANDALONE_CSS
for _a, _b in _MONO_MAP.items():
    MONO_CSS = MONO_CSS.replace(_a, _b)
MONO_CSS += ".leg{display:none}"


# =============================================================================
# HANDOUT FIGURES (dense)
# =============================================================================
def build_h1():
    f = Fig("h1", 1560, 1160,
            "Runtime data flow of the whole robot: operator inputs, Pi nodes, Nav2, sensors and the two microcontrollers")
    C1, C2, C3, C4 = 230, 500, 740, 980
    NW, NH = 150, 48
    f.band(16, 48, 172, 545, "OPERATOR", "op")
    f.band(204, 48, 952, 545, "ALWAYS ON  aislebot.service > aislebot_full.launch.py, 11 processes", "pi")
    f.band(204, 608, 952, 200, "ON DEMAND  mapping", "od")
    f.band(204, 845, 952, 290, "ON DEMAND  Nav2", "od")
    f.band(1176, 48, 368, 760, "HARDWARE", "hw")

    f.node(28, 90, 150, 48, "Gamepad", ["USB, not fitted"], "ext dashed")
    f.node(28, 250, 150, 48, "Phone browser", ["Wi-Fi AP, WebSocket :8080"], "ext")
    f.node(28, 500, 150, 48, "Foxglove Studio", ["laptop, WebSocket :8765"], "ext")

    f.node(C1, 90, NW, NH, "joy_node", ["/joy 25 Hz"])
    f.node(C2, 90, NW, NH, "joy_to_aislebot", ["0.15 m/s, 0.30 rad/s max"])
    f.node(C3, 90, NW, NH, "arm_bridge", ["50 Hz tx, 300 ms watchdog"])
    f.node(C1, 170, NW, 300, "phone_dashboard", [
        "FastAPI, WebSocket", "ROS node on own thread", "",
        "joystick, E-STOP", "arm and UV buttons", "map view, goal click",
        "named locations", "LiDAR filter tuner", "starts, stops mapping", "CSV logs, run report"])
    f.node(C2, 250, NW, NH, "twist_mux", ["manual 100, nav 10, 0.5 s"])
    f.node(C3, 250, NW, NH, "teleop_asym", ["inverse kinematics"])
    f.node(C4, 250, NW, NH, "esp32_bridge", ["serial, 0.5 s watchdog"])
    f.node(C3, 350, NW, NH, "odometry_publisher", ["forward kin, lateral 0.92"])
    f.node(C1, 500, NW, NH, "foxglove_bridge", ["viewer for every topic"])
    f.node(C4, 450, NW, NH, "robot_state_publisher", ["URDF fixed-joint TFs"])
    f.node(C4, 520, NW, NH, "lcd_display", ["IP and AP status, 2 s"])

    H1, H2, HW = 1230, 1400, 130
    f.node(H1, 90, HW, NH, "Arduino Mega", ["firmware v8"], "hwn")
    f.node(H2, 90, HW, NH, "Arms, lift, UV", ["2 arms, lift, 3 UV tubes"], "hwn")
    f.node(H1, 244, HW, 62, "ESP32 drive MCU", ["firmware v3.0", "100 Hz PID, E-STOP"], "hwn")
    f.node(H2, 244, HW, 62, "4 mecanum wheels", ["4 quadrature encoders", "read by PCNT"], "hwn")
    f.node(H1, 520, HW, NH, "16x2 I2C LCD", ["address 0x27"], "hwn")
    f.node(H1, 640, HW, NH, "YDLIDAR X4 Pro", ["/dev/ydlidar"], "hwn")

    f.node(C1, 640, NW, NH, "zero_point_tf", ["static TF map > zero_point"])
    f.node(C4, 640, NW, NH, "ydlidar driver", ["lifecycle, 11.4 Hz measured"])
    f.node(C4, 725, NW, NH, "scan_relay", ["mirror, rear mask, RELIABLE"])
    f.node(C3, 725, NW, NH, "slam_toolbox", ["async, scan matching off"])

    f.node(C1, 890, NW, NH, "goal_pose_adapter", ["yaw offset 0.0 deg"])
    f.node(C2, 890, NW, NH, "bt_navigator", ["replanning + recovery BT"])
    f.node(C3, 890, NW, NH, "planner_server", ["NavFn A*, global costmap"])
    f.node(C4, 890, NW, NH, "behavior_server", ["Spin, BackUp, Wait"])
    f.node(C3, 975, NW, NH, "controller_server", ["MPPI Omni, local costmap"])
    f.node(C3, 1060, NW, NH, "velocity_smoother", ["0.12 m/s, 0.30 rad/s caps"])
    f.node(C2, 1060, NW, NH, "collision_monitor", ["footprint approach, 1.2 s"])
    f.node(C1, 1060, NW, NH, "cmd_vel_axis_adapter", ["out.x = in.y, out.y = -in.x"])

    E, L = f.edge, f.lbl
    E("ctl", [(178, 274), (230, 274)], both=True)
    E("manual", [(178, 114), (230, 114)])
    E("ctl", [(230, 524), (178, 524)], both=True)

    E("manual", [(380, 114), (500, 114)]); L("/joy", 440, 108, "manual")
    E("manual", [(575, 138), (575, 250)]); L("/cmd_vel_manual", 583, 232, "manual", "start")
    E("manual", [(380, 274), (500, 274)]); L("/cmd_vel_manual", 440, 268, "manual")
    E("ctl", [(650, 114), (740, 114)]); L("/arm/cmd_vel", 695, 108, "ctl"); L("/arm/command", 695, 126, "ctl")
    E("ctl", [(380, 190), (460, 190), (460, 158), (815, 158), (815, 138)]); L("/arm/command", 700, 152, "ctl")
    E("ctl", [(890, 114), (1230, 114)], both=True); L("/dev/mega, 115200, <A,arm,lift>", 1060, 108, "ctl")
    E("ctl", [(1360, 114), (1400, 114)])
    E("ctl", [(380, 214), (1055, 214), (1055, 250)]); L("/esp32/command: <S> E-STOP, <E1> clear, <L1> <L0> log", 700, 208, "ctl")
    E("merge", [(650, 274), (740, 274)], thick=True); L("/cmd_vel", 695, 268, "merge")
    E("merge", [(890, 274), (980, 274)], thick=True); L("/wheel_speeds", 935, 268, "merge")
    E("merge", [(1130, 262), (1230, 262)], thick=True); L("<V,fr,fl,rr,rl>", 1180, 256, "merge")
    E("fb", [(1230, 292), (1130, 292)]); L("<L1> 20 Hz", 1180, 306, "fb")
    E("merge", [(1360, 268), (1400, 268)], both=True, thick=True)
    E("fb", [(1005, 298), (1005, 325), (380, 325)]); L("/motor_telemetry", 690, 319, "fb")
    E("fb", [(1055, 298), (1055, 374), (890, 374)]); L("/wheel_velocities_actual", 975, 368, "fb")
    E("ctl", [(380, 374), (740, 374)]); L("/odom/reset", 560, 368, "ctl")
    E("tf", [(775, 398), (775, 725)], dash=True)
    L("TF odom > base_link", 783, 530, "tf", "start"); L("also read by Nav2, dashboard", 783, 546, "tf", "start")
    E("fb", [(740, 392), (700, 392), (700, 845)]); L("/wheel_odom", 692, 690, "fb", "end")
    E("warn", [(305, 90), (305, 80), (925, 80), (925, 232), (860, 232), (860, 250)], dash=True)
    L("/joy also reaches teleop_asym, skipping twist_mux (latent, no gamepad fitted)", 1148, 74, "warn", "end")
    E("ctl", [(1130, 544), (1230, 544)]); L("I2C", 1180, 538, "ctl")

    E("scan", [(1230, 664), (1130, 664)]); L("128000 baud", 1180, 658, "scan")
    E("scan", [(1055, 688), (1055, 725)]); L("/scan BEST_EFFORT", 1047, 709, "scan", "end")
    E("scan", [(980, 749), (890, 749)]); L("/scan_reliable", 935, 743, "scan")
    E("scan", [(1055, 773), (1055, 826), (440, 826), (440, 392), (380, 392)])
    L("/scan_reliable, /scan_relay_stats", 760, 820, "scan")
    E("scan", [(1055, 826), (1055, 845)]); L("/scan_reliable", 1063, 838, "scan", "start")
    E("scan", [(740, 749), (425, 749), (425, 410), (380, 410)]); L("/map", 600, 743, "scan")
    E("scan", [(815, 773), (815, 845)]); L("/map", 823, 838, "scan", "start")
    E("ctl", [(380, 428), (410, 428), (410, 870), (305, 870), (305, 890)]); L("/goal_pose_click", 404, 800, "ctl", "end")
    E("ctl", [(380, 446), (395, 446), (395, 608)], dash=True)
    L("MAP button spawns", 387, 568, "ctl", "end"); L("mapping_full.launch", 387, 581, "ctl", "end")
    f.note("inputs: /wheel_odom, /map, /scan_reliable", 1140, 859, "end", "note-s")

    E("auto", [(380, 914), (500, 914)]); L("/goal_pose", 440, 908, "auto")
    E("auto", [(650, 914), (740, 914)]); L("plan", 695, 908, "auto")
    E("auto", [(600, 938), (600, 999), (740, 999)]); L("follow_path", 668, 993, "auto")
    E("auto", [(620, 890), (620, 878), (1055, 878), (1055, 890)], dash=True); L("recoveries", 850, 874, "auto")
    E("auto", [(815, 1023), (815, 1060)]); L("/cmd_vel_nav", 823, 1046, "auto", "start")
    E("auto", [(1055, 938), (1055, 1084), (890, 1084)]); L("/cmd_vel_nav", 1063, 1010, "auto", "start")
    E("auto", [(740, 1084), (650, 1084)]); L("/cmd_vel_", 695, 1075, "auto"); L("smoothed", 695, 1098, "auto")
    E("auto", [(500, 1084), (380, 1084)]); L("/cmd_vel_baselink", 440, 1078, "auto")
    E("auto", [(305, 1060), (305, 1040), (470, 1040), (470, 288), (500, 288)]); L("/cmd_vel_nav_out", 478, 1034, "auto", "start")
    return f


def build_h2():
    f = Fig("h2", 1320, 470,
            "Both drive paths merge at twist_mux and share one chain to the wheels, while encoder feedback returns through the bridge to odometry")
    E, L = f.edge, f.lbl
    f.node(20, 40, 170, 56, "Phone, gamepad, keys", ["REP-103 axes"], "ext")
    f.node(620, 40, 130, 56, "twist_mux", ["manual 100, nav 10", "0.5 s timeout each"])
    f.node(840, 40, 110, 56, "teleop_asym", ["clamp 6.28 rad/s"])
    f.node(1040, 40, 110, 56, "esp32_bridge", ["0.5 s no input,", "sends zero speed"])
    f.node(1190, 40, 100, 56, "ESP32", ["750 ms, ramps", "to stop"], "hwn")
    f.node(20, 150, 150, 56, "controller_server", ["MPPI, plus behavior", "server, same path"])
    f.node(260, 150, 130, 56, "velocity_smoother", ["accel 0.3, decel 0.5", "stops after 1 s"])
    f.node(470, 150, 130, 56, "collision_monitor", ["footprint polygon", "live scan only"])
    f.node(670, 150, 140, 56, "axis_adapter", ["base_link axes to", "wheel axes"])
    f.node(1190, 150, 100, 56, "Wheels", ["4 encoders"], "hwn")
    f.node(1190, 280, 100, 56, "ESP32", ["EMA alpha 0.4"], "hwn")
    f.node(1040, 280, 110, 56, "esp32_bridge", ["parses <L1>"])
    f.node(770, 280, 150, 56, "odometry_publisher", ["dt = Pi arrival time"])
    f.node(520, 280, 190, 56, "/wheel_odom + TF", ["odom > base_link", "rotated -90 deg, +Y fwd"])
    f.node(250, 280, 220, 56, "Nav2, slam_toolbox", ["pose is wheel odometry,", "scan matching is off"])
    E("manual", [(190, 68), (620, 68)]); L("/cmd_vel_manual", 405, 62, "manual")
    E("auto", [(170, 178), (260, 178)]); L("/cmd_vel_nav", 215, 172, "auto")
    E("auto", [(390, 178), (470, 178)]); L("smoothed", 430, 172, "auto")
    E("auto", [(600, 178), (670, 178)]); L("baselink", 635, 172, "auto")
    E("auto", [(700, 150), (700, 96)]); L("/cmd_vel_nav_out", 708, 126, "auto", "start")
    E("merge", [(750, 68), (840, 68)], thick=True); L("/cmd_vel", 795, 62, "merge")
    E("merge", [(950, 68), (1040, 68)], thick=True); L("/wheel_speeds", 995, 62, "merge")
    E("merge", [(1150, 68), (1190, 68)], thick=True)
    E("merge", [(1240, 96), (1240, 150)], thick=True); L("PWM", 1232, 128, "merge", "end")
    E("fb", [(1240, 206), (1240, 280)]); L("100 Hz PCNT", 1232, 248, "fb", "end")
    E("fb", [(1190, 308), (1150, 308)]); L("<L1>", 1170, 302, "fb")
    E("fb", [(1040, 308), (920, 308)]); L("/wheel_velocities_", 980, 298, "fb"); L("actual", 980, 324, "fb")
    E("fb", [(770, 308), (710, 308)])
    E("fb", [(520, 308), (470, 308)])
    E("tf", [(330, 280), (330, 206)], dash=True); L("pose", 338, 248, "tf", "start")
    f.note("Manual wins while it publishes and loses 0.5 s after the last message.", 20, 390)
    f.note("Four watchdogs stack: twist_mux 0.5 s, bridge 0.5 s, ESP32 750 ms, velocity_smoother 1 s.", 20, 410)
    f.note("Dashboard E-STOP: zero the drive, send <S> to the ESP32 (latched), ESTOP the arm, stop mapping.", 20, 430)
    return f


def build_h3():
    f = Fig("h3", 1160, 520,
            "Inside the ESP32 firmware: a comms task on core 0 feeds a 100 Hz PID task on core 1, which latches an E-STOP on any safety trip")
    E, L = f.edge, f.lbl
    f.band(20, 30, 330, 190, "COMMS TASK  core 0, prio 1, 1 ms poll", "od")
    f.band(380, 30, 760, 190, "PID TASK  core 1, prio 3, 100 Hz via vTaskDelayUntil", "pi")
    f.node(40, 66, 130, 56, "USB serial", ["921600, < > framed"], "hwn")
    f.node(200, 66, 130, 56, "Command parser", ["V B M T S E W Y", "G F K A X L ..."])
    f.node(40, 150, 130, 56, "Telemetry out", ["every 50 ms default", "L1 or L2 columns"])
    f.node(400, 66, 130, 56, "Read PCNT", ["4 encoders", "front CPR 186264"])
    f.node(560, 66, 130, 56, "Velocity", ["EMA alpha 0.4", "slew 12 rad/s^2"])
    f.node(720, 66, 130, 56, "FF + PID", ["Kff w + Kstat sgn(w)", "Kp 45 Ki 250 Kd 0.5"])
    f.node(880, 66, 100, 56, "PWM + DIR", ["8 bit, 5 kHz"])
    f.node(1000, 66, 120, 56, "Motor drivers", ["Cytron-style, 4x"], "hwn")
    f.node(400, 150, 300, 56, "Safety checks, every cycle", ["watchdog 750 ms, overspeed 1.3x 300 ms,", "runaway 500 ms, stall PWM >= 250 for 2 s"], "warnbox")
    f.node(830, 150, 290, 56, "Latching E-STOP", ["trip prints [TRIP,...], motors to zero,", "cleared only by <E1>"], "warnbox")
    f.node(640, 270, 300, 62, "Targets (shared)", ["V: closed loop rad/s, B: body twist", "M: open-loop PWM, T: one motor"])
    f.node(40, 380, 480, 62, "Runtime tuning, no reflash", ["<G kp,ki,kd> <F ff> <K stat> <A accel> <X vmax>", "<W0> <Y0> turn watchdog or trips off for bench work"])
    f.node(560, 380, 560, 62, "Wheel order everywhere", ["[FR, FL, RR, RL], MOTOR_DIR_SIGN and ENC_DIR_SIGN", "both {-1, +1, -1, +1}, front CPR is twice the rear"])
    E("ctl", [(170, 94), (200, 94)], both=True)
    E("fb", [(105, 150), (105, 122)])
    E("merge", [(265, 122), (265, 301), (640, 301)], thick=True); L("parsed targets", 272, 195, "merge", "start")
    E("merge", [(785, 270), (785, 122)], thick=True); L("setpoints", 793, 245, "merge", "start")
    E("fb", [(530, 94), (560, 94)])
    E("fb", [(690, 94), (720, 94)])
    E("merge", [(850, 94), (880, 94)], thick=True)
    E("merge", [(980, 94), (1000, 94)], thick=True)
    E("fb", [(465, 150), (465, 122)], dash=True)
    E("fb", [(625, 122), (625, 150)], dash=True)
    E("warn", [(700, 178), (830, 178)]); L("trip", 745, 172, "warn")
    E("warn", [(950, 150), (950, 122)]); L("zero PWM", 958, 140, "warn", "start")
    f.note("Telemetry carries the filtered wheel velocity from this loop, so that is what the Pi integrates.", 20, 478)
    f.note("position_rad (the exact count integral) ships only in <L2>. The bridge asks for <L1>, so the Pi never sees it.", 20, 498)
    return f


# =============================================================================
# SLIDE FIGURES (1760 x 990, large text, one idea each)
# =============================================================================
SW, SH = 1760, 990


def build_s1():
    """System at a glance."""
    f = Fig("s1", SW, SH, "System at a glance: operator interface, drive chain, odometry, arm, mapping and navigation on the Pi, and the ESP32 and Mega that drive the hardware", "slide")
    c0, c1, c2, c3, c4 = 35, 325, 625, 1025, 1425
    # bands first so they sit under everything
    f.band(c1 - 20, 190, (c3 + 330 + 20) - (c1 - 20), 250, "RASPBERRY PI 5  at boot", "pi", "bottom")
    f.band(c2 - 20, 478, (c3 + 330 + 20) - (c2 - 20), 255, "ON DEMAND", "od", "bottom")
    # row 1: operator
    f.node(c2, 35, 330, None, "Phone browser", ["Wi-Fi AP, WebSocket"], "ext", "phone")
    f.node(c1, 35, 230, None, "Foxglove", ["laptop, debug only"], "ext", "fox")
    # row 2: always-on groups and the two microcontrollers
    f.node(c2, 235, 330, 165, "Operator interface", ["phone_dashboard", "foxglove_bridge"], "grp", "ui")
    f.node(c3, 235, 330, 165, "Drive and odometry", ["twist_mux, teleop_asym", "esp32_bridge", "odometry_publisher"], "grp", "drive")
    f.node(c1, 235, 230, 120, "Arm", ["arm_bridge"], "grp", "arm")
    f.node(c0, 235, 220, 120, "Arduino Mega", ["arm, lift, 3 UV"], "hwn", "mega")
    f.node(c4, 235, 300, 165, "ESP32", ["100 Hz PID,", "latching E-STOP"], "hwn", "esp")
    # row 3: on demand
    f.node(c2, 520, 330, 165, "LiDAR and mapping", ["ydlidar driver", "scan_relay", "slam_toolbox"], "grp", "map")
    f.node(c3, 520, 330, 165, "Navigation (Nav2)", ["planner, MPPI controller", "velocity_smoother", "collision_monitor"], "grp", "nav")
    f.node(c4, 520, 300, 120, "4 wheels", ["mecanum, encoders"], "hwn", "whl")
    # row 4
    f.node(c2, 805, 330, None, "YDLIDAR X4 Pro", ["USB, 128000 baud"], "hwn", "lid")

    E = f.edge
    ph_h, fx_h = f.rects["phone"][3], f.rects["fox"][3]
    xp, xf = c2 + 230, c2 + 150
    E("ctl", [(xp, 35 + ph_h), (xp, 235)], both=True)
    E("ctl", [(c1 + 115, 35 + fx_h), (c1 + 115, 175), (xf, 175), (xf, 235)], both=True)
    ya = 235 + 60
    E("ctl", [(c2, ya), (c1 + 230, ya)])
    E("ctl", [(c1, ya), (c0 + 220, ya)], both=True)
    E("manual", [(c2 + 330, 290), (c3, 290)])
    E("merge", [(c3 + 330, 290), (c4, 290)], thick=True)
    E("fb", [(c4, 350), (c3 + 330, 350)])
    E("merge", [(c4 + 90, 400), (c4 + 90, 520)], thick=True)
    E("fb", [(c4 + 210, 520), (c4 + 210, 400)])
    E("auto", [(c3 + 120, 520), (c3 + 120, 400)])
    E("fb", [(c3 + 215, 400), (c3 + 215, 520)])
    E("tf", [(c3 + 40, 400), (c3 + 40, 459), (c2 + 290, 459), (c2 + 290, 520)], dash=True)
    E("scan", [(c2 + 60, 520), (c2 + 60, 400)])
    E("ctl", [(c2 + 130, 400), (c2 + 130, 520)])
    E("scan", [(c2 + 330, 640), (c3, 640)])
    E("scan", [(c2 + 165, 805), (c2 + 165, 685)])
    f.legend(c3 + 10, 810, [("manual", "Manual drive command", False), ("auto", "Autonomous drive command", False),
                              ("merge", "Command to the wheels", False), ("fb", "Feedback, odometry", False)])
    f.legend(c4 + 10, 810, [("scan", "LiDAR and map", False), ("ctl", "Operator, control", False),
                              ("tf", "TF", True)])
    return f


def build_s2():
    """Drive command path and the loop that closes it."""
    f = Fig("s2", SW, SH, "Manual and autonomous commands merge at twist_mux and share one chain to the wheels; encoder feedback returns through the bridge to odometry", "slide")
    A, B, Cc = 35, 640, 1290
    f.node(A, 35, 250, None, "Phone or gamepad", ["REP-103 axes"], "ext", "src")
    f.node(A, 235, 340, None, "controller_server", ["MPPI, plus behavior_server", "BackUp, Spin use it too"], "ros", "ctl")
    f.node(A, 410, 340, None, "velocity_smoother", ["accel 0.3, decel 0.5", "stops after 1 s idle"], "ros", "vs")
    f.node(A, 585, 340, None, "collision_monitor", ["footprint polygon,", "reads live scan only"], "ros", "cm")
    f.node(A, 760, 340, None, "cmd_vel_axis_adapter", ["base_link axes to wheel axes"], "ros", "ad")
    f.node(B, 35, 340, None, "twist_mux", ["manual 100, nav 10", "0.5 s timeout each"], "ros", "mux")
    f.node(B, 235, 340, None, "teleop_asym", ["inverse kinematics,", "clamp 6.28 rad/s"], "ros", "tel")
    f.node(B, 435, 340, None, "esp32_bridge", ["0.5 s silence sends", "zero speeds"], "ros", "br")
    f.node(B, 635, 340, None, "ESP32", ["100 Hz PID,", "750 ms watchdog"], "hwn", "esp")
    f.node(B, 835, 340, 100, "4 wheels", ["encoders"], "hwn", "whl")
    f.node(Cc, 435, 400, None, "odometry_publisher", ["forward kinematics,", "lateral scale 0.92"], "ros", "odo")
    f.node(Cc, 235, 400, None, "/wheel_odom + TF", ["read by Nav2, slam_toolbox"], "ros", "wo")
    H = lambda k: f.rects[k][3]
    yp = 35 + 38
    f.edge("manual", [(A + 250, yp), (B, yp)]); f.lbl("/cmd_vel_manual", 442, yp - 12, "manual")
    xc = A + 70
    f.edge("auto", [(xc, 235 + H("ctl")), (xc, 410)]); f.lbl("/cmd_vel_nav", xc + 14, 395, "auto", "start")
    f.edge("auto", [(xc, 410 + H("vs")), (xc, 585)]); f.lbl("/cmd_vel_smoothed", xc + 14, 570, "auto", "start")
    f.edge("auto", [(xc, 585 + H("cm")), (xc, 760)]); f.lbl("/cmd_vel_baselink", xc + 14, 745, "auto", "start")
    lane, ya2 = 400, 800
    f.edge("auto", [(A + 340, ya2), (lane, ya2), (lane, 35 + 82), (B, 35 + 82)])
    f.lbl("/cmd_vel_nav_out", lane + 16, ya2 - 14, "auto", "start")
    xf = B + 60
    f.edge("merge", [(xf, 35 + H("mux")), (xf, 235)], thick=True); f.lbl("/cmd_vel", xf + 16, 215, "merge", "start")
    f.edge("merge", [(xf, 235 + H("tel")), (xf, 435)], thick=True); f.lbl("/wheel_speeds", xf + 16, 415, "merge", "start")
    f.edge("merge", [(xf, 435 + H("br")), (xf, 635)], thick=True); f.lbl("<V,fr,fl,rr,rl>", xf + 16, 615, "merge", "start")
    f.edge("merge", [(xf, 635 + H("esp")), (xf, 835)], thick=True); f.lbl("PWM + DIR", xf + 16, 815, "merge", "start")
    xg = B + 285
    f.edge("fb", [(xg, 835), (xg, 635 + H("esp"))]); f.lbl("encoders", xg + 14, 815, "fb", "start")
    f.edge("fb", [(xg, 635), (xg, 435 + H("br"))]); f.lbl("<L1> 20 Hz", xg + 14, 615, "fb", "start")
    yb = 435 + 60
    f.edge("fb", [(B + 340, yb), (Cc, yb)]); f.lbl("/wheel_velocities_actual", (B + 340 + Cc) / 2, yb - 14, "fb")
    xo = Cc + 200
    f.edge("fb", [(xo, 435), (xo, 235 + H("wo"))]); f.lbl("publishes", xo + 14, 385, "fb", "start")
    f.node(Cc, 640, 430, None, "Four watchdogs, outermost first", [
        "twist_mux: 0.5 s per source", "esp32_bridge: 0.5 s, zero speeds",
        "ESP32: 750 ms, ramps to stop", "velocity_smoother: 1 s"], "callout", "wd")
    f.note("Manual wins while it publishes,", Cc, 905, "start", "note")
    f.note("and loses 0.5 s after the last message.", Cc, 932, "start", "note")
    return f


def build_s3():
    """Autonomous navigation chain."""
    f = Fig("s3", SW, SH, "Nav2 chain: goal click to goal_pose_adapter and bt_navigator, then planner, controller and behavior servers, then smoother, collision monitor, axis adapter and twist_mux", "slide")
    c1, c2, c3 = 35, 620, 1130
    f.node(c1, 35, 340, None, "Goal click", ["dashboard map, or Foxglove"], "ext", "goal")
    f.node(c1, 235, 340, None, "goal_pose_adapter", ["yaw offset 0.0 deg"], "ros", "gpa")
    f.node(c1, 435, 340, None, "bt_navigator", ["replanning and recovery", "behavior tree"], "ros", "bt")
    f.node(c2, 235, 380, None, "planner_server", ["NavFn, A*, global costmap", "reads /map"], "ros", "pl")
    f.node(c2, 435, 380, None, "controller_server", ["MPPI, Omni, local costmap", "reads /scan_reliable,", "/wheel_odom"], "ros", "ct")
    f.node(c2, 685, 380, None, "behavior_server", ["Spin, BackUp, Wait", "BackUp strafes left here"], "ros", "bh")
    f.node(c3, 35, 340, None, "velocity_smoother", ["0.12 m/s, 0.30 rad/s caps", "reads /wheel_odom"], "ros", "vs")
    f.node(c3, 235, 340, None, "collision_monitor", ["approach polygon, 1.2 s", "reads /scan_reliable"], "ros", "cm")
    f.node(c3, 435, 340, None, "cmd_vel_axis_adapter", ["out.x = in.y", "out.y = -in.x"], "ros", "ad")
    f.node(c3, 635, 340, None, "twist_mux", ["nav priority 10,", "manual 100 wins"], "ros", "mux")
    H = lambda k: f.rects[k][3]
    xg = c1 + 70
    f.edge("ctl", [(xg, 35 + H("goal")), (xg, 235)]); f.lbl("/goal_pose_click", xg + 14, 215, "ctl", "start")
    f.edge("auto", [(xg, 235 + H("gpa")), (xg, 435)]); f.lbl("/goal_pose", xg + 14, 415, "auto", "start")
    xr, ybt, lane1 = c1 + 340, 435 + 40, 445
    f.edge("auto", [(xr, ybt), (lane1, ybt), (lane1, 235 + 40), (c2, 235 + 40)]); f.lbl("plan", lane1 + 14, 255, "auto", "start")
    f.edge("auto", [(xr, ybt + 20), (c2, ybt + 20)]); f.lbl("follow_path", 540, ybt + 8, "auto")
    f.edge("auto", [(xr, ybt + 40), (lane1, ybt + 40), (lane1, 685 + 40), (c2, 685 + 40)], dash=True); f.lbl("recoveries", lane1 + 14, 705, "auto", "start")
    lane = 1050
    f.edge("auto", [(c2 + 380, 435 + 40), (lane, 435 + 40), (lane, 35 + 40), (c3, 35 + 40)])
    f.lbl("/cmd_vel_nav", lane - 14, 395, "auto", "end")
    f.edge("auto", [(c2 + 380, 685 + 40), (lane, 685 + 40), (lane, 435 + 40)])
    xd = c3 + 80
    f.edge("auto", [(xd, 35 + H("vs")), (xd, 235)]); f.lbl("/cmd_vel_smoothed", xd + 14, 215, "auto", "start")
    f.edge("auto", [(xd, 235 + H("cm")), (xd, 435)]); f.lbl("/cmd_vel_baselink", xd + 14, 415, "auto", "start")
    f.edge("auto", [(xd, 435 + H("ad")), (xd, 635)]); f.lbl("/cmd_vel_nav_out", xd + 14, 615, "auto", "start")
    f.node(c1, 770, 545, None, "Inputs from the rest of the robot", [
        "/map from slam_toolbox", "/scan_reliable from scan_relay", "/wheel_odom, TF from odometry_publisher"], "callout", "inp")
    f.node(c3, 770, 590, None, "Why the axis adapter is last", [
        "Everything before it works in base_link axes", "(+X right, +Y forward). The wheel kinematics",
        "use REP-103, so the adapter rotates the command."], "callout", "why")
    f.node(c2, 830, 380, None, "Not started on purpose", [
        "route_server, opennav_docking,", "robot_localization (no IMU)"], "callout", "nt")
    return f


def build_s4():
    """Perception and pose."""
    f = Fig("s4", SW, SH, "Perception and pose: LiDAR through the driver and scan_relay to slam_toolbox and the map, with odometry supplying the odom to base_link transform", "slide")
    c1, c2, c3 = 35, 640, 1170
    f.node(c1, 35, 340, None, "YDLIDAR X4 Pro", ["USB, 128000 baud"], "hwn", "lid")
    f.node(c1, 235, 340, None, "ydlidar driver", ["lifecycle node", "11.4 Hz measured"], "ros", "dr")
    f.node(c1, 435, 340, None, "scan_relay", ["mirror, rear mask,", "republish RELIABLE"], "ros", "rel")
    f.node(c1, 635, 340, None, "slam_toolbox", ["async mapping,", "scan matching off"], "ros", "slam")
    f.node(c1, 835, 340, None, "Map consumers", ["phone_dashboard,", "Nav2 global costmap"], "grp", "cons")
    H = lambda k: f.rects[k][3]
    xl = c1 + 80
    f.edge("scan", [(xl, 35 + H("lid")), (xl, 235)]); f.lbl("USB serial", xl + 14, 215, "scan", "start")
    f.edge("scan", [(xl, 235 + H("dr")), (xl, 435)]); f.lbl("/scan BEST_EFFORT", xl + 14, 415, "scan", "start")
    f.edge("scan", [(xl, 435 + H("rel")), (xl, 635)]); f.lbl("/scan_reliable", xl + 14, 615, "scan", "start")
    f.edge("scan", [(xl, 635 + H("slam")), (xl, 835)]); f.lbl("/map", xl + 14, 815, "scan", "start")
    f.node(c2, 400, 480, None, "What scan_relay does, in order", [
        "1  undo the mirrored bearing", "2  blank the rear mast arc, 107 beams",
        "3  optional range window", "4  optional K-of-N persistence gate"], "callout", "det")
    f.edge("ctl", [(c1 + 340, 490), (c2, 490)], dash=True)
    f.node(c2, 635, 400, None, "odometry_publisher", ["wheel velocities in,", "odom to base_link out"], "ros", "odo")
    f.edge("fb", [(c2, 690), (c1 + 340, 690)]); f.lbl("TF odom > base_link", (c2 + c1 + 340) / 2, 673, "fb")
    ct = 1280
    f.band(c3 - 20, 20, 590, 560, "TF TREE", "pl")
    f.node(ct - 90, 80, 230, 70, "map", [], "ros", "t1")
    f.node(ct - 90, 215, 230, 70, "odom", [], "ros", "t2")
    f.node(ct - 90, 350, 230, 70, "base_link", [], "ros", "t3")
    f.node(ct - 90, 485, 230, 70, "laser_frame", [], "ros", "t4")
    xt = ct + 25
    f.edge("tf", [(xt, 150), (xt, 215)]); f.lbl("slam_toolbox", xt + 16, 192, "tf", "start")
    f.edge("tf", [(xt, 285), (xt, 350)]); f.lbl("odometry_publisher", xt + 16, 327, "tf", "start")
    f.edge("tf", [(xt, 420), (xt, 485)]); f.lbl("robot_state_publisher", xt + 16, 462, "tf", "start")
    f.note("laser_frame sits at (0, 0.27, 0.275) from base_link.", c3 - 6, 640, "start", "note")
    f.note("Wheel frames are not published, nothing sends joint_states.", c3 - 6, 670, "start", "note")
    f.note("Pose is wheel odometry only: no IMU, scan matching off.", c3 - 6, 700, "start", "note")
    return f


def build_s5():
    """ESP32 drive firmware."""
    f = Fig("s5", SW, SH, "ESP32 drive firmware: a comms task on core 0 parses commands into shared targets, a 100 Hz PID task on core 1 drives the motors and latches an E-STOP on any safety trip", "slide")
    c1, c2, c3 = 35, 560, 1130
    f.band(c1 - 15, 20, 370, 560, "COMMS TASK  core 0, prio 1", "od")
    f.band(c2 - 15, 20, 450, 880, "PID TASK  core 1, prio 3, 100 Hz", "pi")
    f.node(c1, 80, 340, None, "USB serial", ["921600 baud, < > framed", "1 ms poll"], "hwn", "usb")
    f.node(c1, 280, 340, None, "Command parser", ["V B M T S E W Y", "G F K A X L"], "ros", "par")
    f.node(c1, 460, 340, None, "Targets (shared)", ["V: closed loop rad/s", "B: body twist, ESP32 does IK"], "ros", "tg")
    f.node(c2, 80, 380, None, "Read encoders", ["4 PCNT units, front CPR", "186264, rear 93132, EMA 0.4"], "ros", "enc")
    f.node(c2, 280, 380, None, "Slew, feedforward, PID", ["slew 12 rad/s^2", "Kp 45, Ki 250, Kd 0.5"], "ros", "pid")
    f.node(c2, 480, 380, None, "PWM and DIR", ["8 bit, 5 kHz"], "ros", "pwm")
    f.node(c2, 660, 380, None, "Motor drivers", ["4 wheels, Cytron-style"], "hwn", "mot")
    f.node(c3, 280, 590, None, "Safety checks, every cycle", ["watchdog 750 ms", "overspeed 1.3x for 300 ms", "runaway 500 ms, stall 2 s"], "warnbox", "sf")
    f.node(c3, 480, 590, None, "Latching E-STOP", ["prints [TRIP,...], motors to zero", "cleared only by <E1>"], "warnbox", "es")
    H = lambda k: f.rects[k][3]
    f.edge("ctl", [(c1 + 90, 80 + H("usb")), (c1 + 90, 280)], both=True)
    f.edge("merge", [(c1 + 90, 280 + H("par")), (c1 + 90, 460)], thick=True); f.lbl("writes", c1 + 104, 440, "merge", "start")
    f.edge("merge", [(c1 + 340, 500), (500, 500), (500, 340), (c2, 340)], thick=True)
    f.lbl("setpoints", c1 + 345, 488, "merge", "start")
    f.edge("fb", [(c2, 120), (c1 + 340, 120)]); f.lbl("<L1> 20 Hz", (c2 + c1 + 340) / 2 - 10, 104, "fb")
    f.edge("fb", [(c2 + 120, 80 + H("enc")), (c2 + 120, 280)]); f.lbl("velocity", c2 + 134, 260, "fb", "start")
    f.edge("merge", [(c2 + 120, 280 + H("pid")), (c2 + 120, 480)], thick=True); f.lbl("pwm", c2 + 134, 460, "merge", "start")
    f.edge("merge", [(c2 + 120, 480 + H("pwm")), (c2 + 120, 660)], thick=True); f.lbl("PWM, DIR", c2 + 134, 640, "merge", "start")
    f.edge("warn", [(c2 + 380, 340), (c3, 340)]); f.lbl("10 ms", 1006, 324, "warn", "start")
    f.edge("warn", [(c3 + 120, 280 + H("sf")), (c3 + 120, 480)]); f.lbl("trip", c3 + 134, 450, "warn", "start")
    f.edge("warn", [(c3, 525), (c2 + 380, 525)]); f.lbl("zero PWM", 1006, 509, "warn", "start")
    f.node(c1, 620, 480, None, "Control law, per wheel", [
        "pwm = Kff·ω + Kstat·sgn(ω) + PID(e)", "Kff 37.3 to 38.4 by wheel, Kstat 8",
        "D term on measurement, anti-windup", "against the real PWM headroom"], "callout", "law")
    f.node(c3, 80, 590, None, "Command source", [
        "The Pi is the only command source.", "WiFi and the web joystick left in v3.0."], "callout", "c1")
    f.node(c3, 700, 590, None, "Wheel order everywhere", [
        "[FR, FL, RR, RL]", "motor and encoder signs both {-1, +1, -1, +1}", "front CPR is twice the rear"], "callout", "c2")
    return f


def build_s6():
    """Boot chain and launch tree."""
    f = Fig("s6", SW, SH, "Boot chain: systemd runs the start script, which launches the eleven always-on processes; mapping and Nav2 start on demand", "slide")
    c1, c2, c3 = 35, 600, 1340
    f.band(c3 - 45, 20, 450, 940, "ON DEMAND", "od")
    f.node(c1, 35, 420, None, "aislebot.service", ["systemd, restarts on failure,", "10 s delay"], "ros", "svc")
    f.node(c1, 235, 420, None, "start_aislebot.sh", ["domain 42, Cyclone on loopback", "waits 30 s for /dev/esp32, aborts", "waits 15 s for /dev/mega, warns"], "ros", "sh")
    f.node(c1, 485, 420, None, "aislebot_full.launch.py", ["11 processes, all always on"], "ros", "ln")
    H = lambda k: f.rects[k][3]
    x = c1 + 80
    f.edge("merge", [(x, 35 + H("svc")), (x, 235)], thick=True)
    f.edge("merge", [(x, 235 + H("sh")), (x, 485)], thick=True)
    groups = [
        ("Operator interface", ["joy_node, joy_to_aislebot", "phone_dashboard"], "ui"),
        ("Drive", ["twist_mux, teleop_asym", "esp32_bridge"], "dr"),
        ("Pose", ["odometry_publisher"], "po"),
        ("Arm and status", ["arm_bridge, lcd_display"], "ar"),
        ("Viewer and model", ["foxglove_bridge", "robot_state_publisher"], "vw"),
    ]
    y, ys = 35, {}
    for t, ls, k in groups:
        h = f.node(c2, y, 520, None, t, ls, "grp", k)[3]
        ys[k] = y + h / 2
        y += h + 30
    xr, yl, lane = c1 + 420, 485 + 38, 540
    f.edge("merge", [(xr, yl), (lane, yl), (lane, ys["ui"]), (c2, ys["ui"])])
    f.edge("merge", [(xr, yl), (lane, yl), (lane, ys["vw"]), (c2, ys["vw"])])
    for k in ["dr", "po", "ar"]:
        f.edge("merge", [(lane, ys[k]), (c2, ys[k])])
    f.node(c3, 60, 380, None, "mapping_full.launch.py", ["started by the MAP button", "runs sensors.launch.py"], "ros", "mp")
    f.node(c3, 290, 380, None, "sensors.launch.py", ["ydlidar driver, scan_relay,", "zero_point_tf"], "ros", "se")
    f.node(c3, 480, 380, None, "slam_toolbox", ["online_async"], "ros", "sl")
    f.node(c3, 640, 380, None, "nav2_slam.launch.py", ["by hand, after mapping", "Nav2 servers and adapters"], "ros", "n2")
    ymp = 60 + H("mp") / 2
    f.edge("ctl", [(c2 + 520, ymp), (c3, ymp)], dash=True)
    f.lbl("MAP button", c2 + 520 + 18, ymp - 14, "ctl", "start")
    xm = c3 + 80
    f.edge("ctl", [(xm, 60 + H("mp")), (xm, 290)])
    f.edge("ctl", [(c3, 60 + 82), (c3 - 24, 60 + 82), (c3 - 24, 519), (c3, 519)])
    f.note("Run exactly one of mapping_full", c3 - 6, 850, "start", "note")
    f.note("and navigation. Two LiDAR drivers on", c3 - 6, 878, "start", "note")
    f.note("one serial port is a hard failure.", c3 - 6, 906, "start", "note")
    return f


HANDOUTS = [build_h1, build_h2, build_h3]
SLIDES = [build_s1, build_s2, build_s3, build_s4, build_s5, build_s6]
NAMES = {
    "h1": "h1_whole_system_handout",
    "h2": "h2_drive_paths_handout",
    "h3": "h3_esp32_firmware_handout",
    "s1": "s1_system_overview_slide",
    "s2": "s2_drive_command_path_slide",
    "s3": "s3_navigation_chain_slide",
    "s4": "s4_perception_and_pose_slide",
    "s5": "s5_esp32_firmware_slide",
    "s6": "s6_boot_and_launch_slide",
}


def build_all():
    return [b() for b in HANDOUTS + SLIDES]


def main():
    figs = build_all()
    bad = []
    os.makedirs(os.path.join(HERE, "svg"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "mono", "svg"), exist_ok=True)
    for f in figs:
        bad += f.check_edges()
        path = os.path.join(HERE, "svg", NAMES[f.sid] + ".svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f.svg_standalone())
        with open(os.path.join(HERE, "mono", "svg", NAMES[f.sid] + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(f.svg_standalone(MONO_CSS))
        print("wrote", os.path.relpath(path, os.path.dirname(HERE)), "and its mono copy")
    if bad:
        print("\nEDGE CHECK FAILED:")
        print("\n".join(bad))
        sys.exit(1)
    print("edge check: no edge passes through a node")


if __name__ == "__main__":
    main()
