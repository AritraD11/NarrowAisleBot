#!/usr/bin/env python3
"""Generator checks:  python3 tests/test_generate.py

Runs generate.py on every config in the kit (robot_config.yaml and
examples/*.yaml) into a temp directory and checks what it wrote:

  - every YAML file parses
  - every parameter a ROS node declares as a double is written as a double
    (an integer there makes the node refuse to start)
  - no empty lists in ROS parameter files (ROS cannot type them)
  - the URDF is well-formed and has a laser joint and one link per wheel
  - the firmware header has one entry per wheel in every per-motor array
  - Nav2: footprint matches the config, controller block matches the drive
  - bad configs are rejected with a readable message
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
import xml.dom.minidom

import yaml

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(KIT, "ros2", "robot_base"))
from robot_base.robot_model import resolve, ConfigError  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def walk(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    else:
        yield path, d


# Parameters the kit's nodes declare as double / double[] (see the nodes).
DOUBLE_KEYS = {"max_wheel_speed", "telemetry_hz", "cmd_timeout", "wheel_radius",
               "wheel_x", "wheel_y", "wheel_ax", "wheel_ay", "track_width_scale",
               "lateral_scale", "max_linear", "max_angular", "mask_deg", "range_min",
               "range_max", "footprint_x", "footprint_y", "laser_x", "laser_y"}

configs = [os.path.join(KIT, "robot_config.yaml")] + sorted(glob.glob(os.path.join(KIT, "examples", "*.yaml")))
for cfg_path in configs:
    name = os.path.relpath(cfg_path, KIT)
    print(f"\n{name}")
    cfg = yaml.safe_load(open(cfg_path))
    n = len(cfg["wheels"])
    with tempfile.TemporaryDirectory() as out:
        r = subprocess.run([sys.executable, os.path.join(KIT, "generate.py"),
                            "--config", cfg_path, "--out", out], capture_output=True, text=True)
        check(r.returncode == 0, f"generate.py exits 0 ({r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr})")
        cdir = os.path.join(out, "ros2", "robot_base", "config")
        for f in ("robot", "nav2_params", "slam_toolbox", "lidar", "twist_mux"):
            try:
                yaml.safe_load(open(os.path.join(cdir, f + ".yaml")))
                ok = True
            except Exception as e:  # noqa: BLE001
                ok = False
                print("      ", e)
            check(ok, f"{f}.yaml parses")

        params = yaml.safe_load(open(os.path.join(cdir, "robot.yaml")))
        bad, empty = [], []
        for node, body in params.items():
            for key, val in body["ros__parameters"].items():
                if isinstance(val, list) and not val:
                    empty.append(f"{node}.{key}")
                if key in DOUBLE_KEYS:
                    vals = val if isinstance(val, list) else [val]
                    if any(not isinstance(v, float) for v in vals):
                        bad.append(f"{node}.{key}={val}")
        check(not bad, "every double parameter is written as a double " + (str(bad) if bad else ""))
        check(not empty, "no empty lists in robot.yaml " + (str(empty) if empty else ""))
        names = params["base_controller"]["ros__parameters"]["wheel_names"]
        check(len(names) == n and all(len(params["base_controller"]["ros__parameters"][k]) == n
                                      for k in ("wheel_x", "wheel_y", "wheel_ax", "wheel_ay")),
              "wheel arrays all have one entry per wheel")

        nav = yaml.safe_load(open(os.path.join(cdir, "nav2_params.yaml")))
        ctrl = nav["controller_server"]["ros__parameters"]
        check(isinstance(ctrl["controller_frequency"], float), "controller_frequency is a double")
        plug = ctrl["FollowPath"]["plugin"]
        holo = cfg["robot"]["drive_type"] in ("mecanum", "omni")
        want = cfg["nav"].get("controller", "auto")
        if want == "auto":
            want = "mppi" if holo else "rpp"
        check(("MPPI" in plug) == (want == "mppi"), f"controller plugin {plug.split('::')[-1]} matches {want}")
        if "MPPI" in plug:
            check(ctrl["FollowPath"]["motion_model"] == ("Omni" if holo else "DiffDrive"), "MPPI motion model fits the drive")
        vs = nav["velocity_smoother"]["ros__parameters"]
        check((vs["max_velocity"][1] == 0.0) == (not holo), "vy limit is zero exactly when the base cannot strafe")
        fp = yaml.safe_load(nav["local_costmap"]["local_costmap"]["ros__parameters"]["footprint"])
        body = cfg["robot"]["body"]
        hx = body["length"] / 2 + body["footprint_margin"]
        check(abs(max(p[0] for p in fp) - (body.get("center_x", 0) + hx)) < 1e-3, "footprint front edge = half length + margin")
        check(nav["collision_monitor"]["ros__parameters"]["cmd_vel_out_topic"] == "cmd_vel_nav_out",
              "collision monitor feeds twist_mux")

        dom = xml.dom.minidom.parse(os.path.join(out, "ros2", "robot_base", "urdf", "robot.urdf"))
        joints = [j.getAttribute("name") for j in dom.getElementsByTagName("joint")]
        check("laser_joint" in joints, "URDF has laser_joint")
        check(sum(1 for j in joints if j.startswith("wheel_")) == n, "URDF has one joint per wheel")
        check(all(j.getAttribute("type") == "fixed" for j in dom.getElementsByTagName("joint")),
              "all URDF joints fixed (no missing wheel TF)")

        hdr = open(os.path.join(out, "firmware", "robot_mcu", "robot_config.h")).read()
        check(f"#define NUM_MOTORS {n}" in hdr, f"header NUM_MOTORS = {n}")
        arrays = re.findall(r"\[NUM_MOTORS\]\s*=\s*\{([^}]*)\}", hdr)
        check(arrays and all(len(a.split(",")) == n for a in arrays),
              f"all {len(arrays)} per-motor arrays have {n} entries")

        rules = open(os.path.join(out, "setup", "generated", "99-robot.rules")).read()
        check(f'SYMLINK+="{cfg["mcu"]["device_name"]}"' in rules, "udev rule names the MCU device")

print("\nbad configs are rejected")
good = yaml.safe_load(open(os.path.join(KIT, "robot_config.yaml")))


def rejects(mutate, what):
    import copy
    c = copy.deepcopy(good)
    mutate(c)
    try:
        resolve(c)
    except ConfigError as e:
        check(True, f"{what}: {e}")
        return
    check(False, f"{what}: was accepted")


rejects(lambda c: c["robot"].update(drive_type="tank"), "unknown drive type")
rejects(lambda c: c["wheels"].pop(), "differential with one wheel")
rejects(lambda c: c["wheels"][0]["pins"].pop("dir"), "missing dir pin for pwm_dir")
rejects(lambda c: c["mcu"].update(kff=[1.0]), "kff with the wrong length")
rejects(lambda c: c["mcu"].update(board="avr"), "pcnt backend on an AVR")
rejects(lambda c: c["wheels"][0].update(name="wheel_a"), "auto position for an unplaceable name")
rejects(lambda c: c["wheels"][1].update(name="left"), "duplicate wheel names")
rejects(lambda c: c["wheels"][0].update(motor_dir=2), "motor_dir not +1/-1")
rejects(lambda c: c["robot"].update(wheel_radius=5), "absurd wheel radius")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all generator checks passed")
