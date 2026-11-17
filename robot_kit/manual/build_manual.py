#!/usr/bin/env python3
"""
build_manual.py - manual.md (+ every kit source file as Appendix C) -> PDF.

    python3 manual/build_manual.py

Needs pandoc and Node with playwright (Chromium). Writes
manual/build/manual.html and manual/Robot_Setup_Manual.pdf.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "build")

LISTINGS = [
    ("Your robot", ["robot_config.yaml", "examples/nab_mecanum_reference.yaml"]),
    ("Generator", ["generate.py"]),
    ("Setup scripts", ["setup/install_all.sh", "setup/common.sh", "setup/01_base_system.sh",
                       "setup/02_ros_jazzy.sh", "setup/03_lidar_driver.sh", "setup/04_workspace.sh",
                       "setup/05_system.sh", "setup/06_wifi_ap.sh", "setup/start_robot.sh",
                       "setup/check_robot.sh", "setup/list_usb_serial.py"]),
    ("Microcontroller firmware", ["firmware/robot_mcu/robot_mcu.ino",
                                  "firmware/robot_mcu/robot_config.h"]),
    ("ROS 2 package robot_base", ["ros2/robot_base/package.xml", "ros2/robot_base/setup.py",
                                  "ros2/robot_base/robot_base/kinematics.py",
                                  "ros2/robot_base/robot_base/robot_model.py",
                                  "ros2/robot_base/robot_base/protocol.py",
                                  "ros2/robot_base/robot_base/scan_math.py",
                                  "ros2/robot_base/robot_base/telemetry_csv.py",
                                  "ros2/robot_base/robot_base/mcu_bridge.py",
                                  "ros2/robot_base/robot_base/base_controller.py",
                                  "ros2/robot_base/robot_base/wheel_odometry.py",
                                  "ros2/robot_base/robot_base/scan_filter.py",
                                  "ros2/robot_base/robot_base/telemetry_logger.py",
                                  "ros2/robot_base/launch/base.launch.py",
                                  "ros2/robot_base/launch/lidar.launch.py",
                                  "ros2/robot_base/launch/mapping.launch.py",
                                  "ros2/robot_base/launch/nav2.launch.py"]),
    ("Dashboard", ["ros2/robot_base/robot_base/dashboard/server.py",
                   "ros2/robot_base/robot_base/dashboard/static/index.html",
                   "ros2/robot_base/robot_base/dashboard/static/app.js",
                   "ros2/robot_base/robot_base/dashboard/static/style.css"]),
    ("Tools", ["tools/encoder_logger.py", "tools/analyze_log.py",
               "tools/firmware_sim/sim.cpp", "tools/firmware_sim/Arduino.h",
               "tools/firmware_sim/Makefile"]),
]
LANG = {".py": "python", ".sh": "bash", ".ino": "cpp", ".h": "cpp", ".cpp": "cpp",
        ".js": "javascript", ".html": "html", ".css": "css", ".yaml": "yaml", ".xml": "xml"}


def appendix_c():
    out = ["# Appendix C. Source listings {#appendix-c .unnumbered}", "",
           "Every file you need to run the robot, as shipped. The tests (`tests/`) and the files "
           "`generate.py` writes are in the kit folder but not printed here; `robot_config.h` is "
           "printed as generated from the example `robot_config.yaml`, so you can see what the "
           "generator produces. If you are copying from this PDF rather than the folder, check the "
           "line counts against the headings.", ""]
    for group, files in LISTINGS:
        out += [f"::: listing", "", f"## {group} {{-}}", ""]
        for rel in files:
            path = os.path.join(KIT, rel)
            text = open(path, encoding="utf-8").read().rstrip("\n")
            n = text.count("\n") + 1
            ext = os.path.splitext(rel)[1] or ("makefile" if rel.endswith("Makefile") else "")
            lang = LANG.get(ext, "makefile" if rel.endswith("Makefile") else "")
            fence = "~~~~~~"
            out += [f"### `{rel}` ({n} lines) {{-}}", "", f"{fence} {{.{lang}}}" if lang else fence,
                    text, fence, ""]
        out += [":::", ""]
    return "\n".join(out)


def main():
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(KIT, "generate.py")], check=True,
                   capture_output=True)
    src = os.path.join(BUILD, "full.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(open(os.path.join(HERE, "manual.md"), encoding="utf-8").read())
        fh.write("\n\n" + appendix_c())
    html = os.path.join(BUILD, "manual.html")
    subprocess.run(["pandoc", src, "-f", "markdown", "-t", "html5", "-s",
                    "--template", os.path.join(HERE, "template.html"),
                    "--toc", "--toc-depth=2", "--mathml", "--highlight-style=tango",
                    "--resource-path", HERE, "-o", html], check=True)
    for asset in ("manual.css",):
        subprocess.run(["cp", os.path.join(HERE, asset), BUILD], check=True)
    subprocess.run(["rm", "-rf", os.path.join(BUILD, "img")], check=True)
    subprocess.run(["cp", "-r", os.path.join(HERE, "img"), BUILD], check=True)
    pdf = os.path.join(HERE, "Robot_Setup_Manual.pdf")
    env = dict(os.environ)
    if "NODE_PATH" not in env:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True,
                                          text=True).stdout.strip()
    subprocess.run(["node", os.path.join(HERE, "print_pdf.js"), html, pdf], check=True, env=env)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
