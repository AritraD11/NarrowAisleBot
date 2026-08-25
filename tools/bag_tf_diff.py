#!/usr/bin/env python3
"""
bag_tf_diff.py -- extract one TF pair's correction history out of a rosbag2,
printing every DISTINCT value change with its epoch timestamp.

WHY THIS EXISTS
    sec 17.28 needs to know not just THAT map->odom moves, but exactly WHEN
    and BY HOW MUCH, to line up against a captured slam_toolbox terminal
    log by wall-clock time -- the same correlation trajectory_viz.py's
    epoch_s column exists for, but read directly from a bag instead of a
    live recorder. transform_publish_period republishes the current value
    at 50 Hz regardless of whether it actually changed (slam_nodom.yaml),
    so consecutive identical samples are collapsed here -- only genuine
    corrections are printed, each one exactly once.

USAGE
    python3 bag_tf_diff.py ~/slam_tests/slam_test_01
    python3 bag_tf_diff.py ~/slam_tests/slam_test_01 --parent map --child odom
    python3 bag_tf_diff.py ~/slam_tests/slam_test_01 --parent zero_point --child base_link

Pure rosbag2_py + stdlib, matching the rest of the on-Pi tooling.
"""

import argparse
import math
import sys

import rosbag2_py
from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bag_path')
    ap.add_argument('--parent', default='map', help="TF parent frame (header.frame_id)")
    ap.add_argument('--child', default='odom', help="TF child frame (child_frame_id)")
    ap.add_argument('--topic', default='/tf')
    ap.add_argument('--jump-m', type=float, default=0.08,
                     help="flag threshold for position change, metres")
    ap.add_argument('--jump-deg', type=float, default=5.0,
                     help="flag threshold for heading change, degrees")
    args = ap.parse_args()

    storage_options = rosbag2_py.StorageOptions(uri=args.bag_path, storage_id='')
    converter_options = rosbag2_py.ConverterOptions('', '')
    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)
    reader.set_filter(rosbag2_py.StorageFilter(topics=[args.topic]))

    last = None
    events = []
    total_msgs = 0
    first_epoch = last_epoch = None

    while reader.has_next():
        _topic, data, _t = reader.read_next()
        msg = deserialize_message(data, TFMessage)
        for tf in msg.transforms:
            if tf.header.frame_id != args.parent or tf.child_frame_id != args.child:
                continue
            total_msgs += 1
            epoch = tf.header.stamp.sec + tf.header.stamp.nanosec * 1e-9
            first_epoch = epoch if first_epoch is None else first_epoch
            last_epoch = epoch
            x = tf.transform.translation.x
            y = tf.transform.translation.y
            yaw = yaw_from_quat(tf.transform.rotation)
            if last is None or (abs(x - last[0]) > 1e-6
                                 or abs(y - last[1]) > 1e-6
                                 or abs(yaw - last[2]) > 1e-6):
                events.append((epoch, x, y, yaw))
                last = (x, y, yaw)

    print('{} -> {}: {} messages on {}, {} distinct value changes'.format(
        args.parent, args.child, total_msgs, args.topic, len(events)))
    if first_epoch is not None:
        print('span: epoch {:.3f} -> {:.3f}  ({:.1f}s)'.format(
            first_epoch, last_epoch, last_epoch - first_epoch))
    else:
        print('No messages found for this frame pair on this topic in this bag.')
        return
    print()
    print('{:>18}  {:>7}  {:>9}  {:>9}  {:>9}   {:>8}  {:>9}'.format(
        'epoch', 'dt_s', 'x', 'y', 'yaw_deg', 'd_pos_m', 'd_yaw_deg'))

    prev = None
    for (epoch, x, y, yaw) in events:
        if prev is None:
            dpos = dyaw = dt = 0.0
        else:
            dpos = math.hypot(x - prev[1], y - prev[2])
            dyaw = math.degrees(yaw - prev[3])
            dt = epoch - prev[0]
        flag = '  <-- BIG' if dpos > args.jump_m or abs(dyaw) > args.jump_deg else ''
        print('{:18.3f}  {:7.2f}  {:9.4f}  {:9.4f}  {:9.2f}   {:8.4f}  {:9.2f}{}'.format(
            epoch, dt, x, y, math.degrees(yaw), dpos, dyaw, flag))
        prev = (epoch, x, y, yaw)


if __name__ == '__main__':
    sys.exit(main())
