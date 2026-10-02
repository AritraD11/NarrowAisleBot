#!/usr/bin/env python3
"""bag_cmd_chain.py - which stage of the Nav2 command chain squashed the speed?

Reads a rosbag2 .mcap and prints, per time bin, the mean and peak speed seen
at each stage of the chain between MPPI and the wheels, plus every
collision_monitor state change. If one stage already shows tiny numbers, that
stage (not the ones after it) is where the speed was lost.

    /cmd_vel_nav  ->  /cmd_vel_smoothed  ->  /cmd_vel_baselink  ->  /cmd_vel
    (controller)      (velocity_smoother)    (collision_monitor)    (after the
                                                                     axis adapter
                                                                     and twist_mux)

First used 1 Oct 2026: every stage read the same 4.4 mm/s, which put the fault
inside MPPI itself (docs/Session_Handoff_2026-10-01.md, Part 2).

Needs, on the machine that runs it (the Pi does not need ROS sourced):
    pip install mcap mcap-ros2-support

Usage
    python3 tools/bag_cmd_chain.py fwd06_small_0.mcap
    python3 tools/bag_cmd_chain.py fwd06_small_0.mcap --bin 5 --from 0 --to 60

--from / --to are seconds after the first /cmd_vel_nav message (the moment the
goal started). Speeds are hypot(linear.x, linear.y) in m/s, so the result does
not depend on which of the two base_link axes was forward.

Record the bag with, at least:
    ros2 bag record /cmd_vel_nav /cmd_vel_smoothed /cmd_vel_baselink /cmd_vel \\
        /collision_monitor_state
"""

import argparse
import math
import statistics
import sys

STAGES = ["/cmd_vel_nav", "/cmd_vel_smoothed", "/cmd_vel_baselink", "/cmd_vel"]
ACTIONS = {0: "DO_NOTHING", 1: "STOP", 2: "SLOWDOWN", 3: "APPROACH", 4: "LIMIT"}


def load(path):
    try:
        from mcap.reader import make_reader
        from mcap_ros2.decoder import DecoderFactory
    except ImportError:
        sys.exit("needs: pip install mcap mcap-ros2-support")
    twists = {s: [] for s in STAGES}
    states = []
    with open(path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for _schema, channel, message, msg in reader.iter_decoded_messages():
            t = message.log_time / 1e9
            topic = channel.topic
            if topic in twists:
                twists[topic].append((t, msg.linear.x, msg.linear.y, msg.angular.z))
            elif topic == "/collision_monitor_state":
                states.append((t, msg.action_type, msg.polygon_name))
    return twists, states


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mcap")
    ap.add_argument("--bin", type=float, default=10.0, help="bin width, seconds")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=60.0)
    args = ap.parse_args()

    twists, states = load(args.mcap)
    nav = twists["/cmd_vel_nav"]
    if not nav:
        sys.exit("no /cmd_vel_nav messages in this bag")
    t0 = nav[0][0]

    print("t = 0 is the first /cmd_vel_nav message. Speeds in m/s: mean | peak.")
    print(f"{'bin (s)':>9}  " + "  ".join(f"{s:>21}" for s in STAGES))
    a = args.t_from
    while a < args.t_to:
        b = a + args.bin
        cells = []
        for stage in STAGES:
            sp = [math.hypot(x, y) for t, x, y, _w in twists[stage] if a <= t - t0 < b]
            cells.append("-" if not sp else f"{statistics.mean(sp):8.4f} | {max(sp):8.4f}")
        print(f"{a:4.0f}-{b:<4.0f}  " + "  ".join(f"{c:>21}" for c in cells))
        a = b

    print()
    if states:
        print("collision_monitor state changes (seconds after t = 0):")
        for t, action, polygon in states:
            name = ACTIONS.get(action, str(action))
            print(f"  {t - t0:8.1f}  {name:<10} {polygon or ''}")
    else:
        print("no /collision_monitor_state messages in this bag")


if __name__ == "__main__":
    main()
