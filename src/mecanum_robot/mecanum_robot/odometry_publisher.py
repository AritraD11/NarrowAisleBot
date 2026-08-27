#!/usr/bin/env python3
"""
AisleBot Odometry Publisher v1.0
================================
Computes robot odometry from wheel encoder feedback using
AisleBot's asymmetric mecanum forward kinematics.

FORWARD KINEMATICS (wheel speeds → body velocity):
  vx = (r/4) * (w_fr + w_fl + w_rr + w_rl)
  vy = (r/4) * (w_fr - w_fl - w_rr + w_rl)
  wz = (r/4) * (w_fr/K_out - w_fl/K_in + w_rr/K_in - w_rl/K_out)

  (Simplified using pseudoinverse of asymmetric kinematics matrix)

TOPICS:
  Subscribes: /wheel_velocities_actual (Float64MultiArray) [FR,FL,RR,RL] rad/s
  Publishes:  /wheel_odom (Odometry) raw wheel odometry
  Publishes:  /tf (odom → base_link transform)

PUBLISHED-FRAME ROTATION (added 11 Aug 2026 §17.10; COMPLETED 27 Aug 2026
§17.38 -- read the second half before changing anything here).
  The kinematics above compute vx/vy/theta in the standard REP-103 sense
  (vx=forward, vy=left). That internal computation is correct and is left
  untouched. What gets PUBLISHED is rotated by a constant -90 deg from it,
  so that base_link's own +X reads as "right" and +Y reads as "forward" --
  matching the already-validated LiDAR scan calibration (scan_relay.py,
  mirror=True, yaw_offset=270 deg) rather than requiring it to be redone.

  THE BUG THAT LIVED HERE UNTIL 27 AUG 2026, and why it was invisible.
  That relabel was applied to the published ORIENTATION and the published
  TWIST, but NOT to the published TRANSLATION, which went out as the raw
  internal (self.x, self.y). The old docstring argued translation "is
  unaffected by how the frame's local axes are labelled", and for the pose
  of base_link *relative to odom* that is true -- the algebra is
  self-consistent and §17.37 re-derived it correctly.

  What it misses is that publishing raw internal translation DEFINES the
  odom frame's own axes to be the internal REP-103 ones. So odom +X ended
  up pointing along whatever direction the robot faced when odometry was
  zeroed, while base_link carried +Y=forward. The constant -90 deg yaw was
  not a free choice -- it was the seam between those two definitions, and
  map inherited it wholesale (slam_toolbox starts map->odom at identity, so
  map axes == odom axes). Measured on hardware 27 Aug: driving forward from
  the ZERO mark increased map X and left map Y at 0.000; strafing right
  decreased map Y. Two frames, two conventions, one constant offset papering
  over the join -- and a chain of downstream -90 deg compensations
  (dashboard canvas rotation, dashboard print-site relabel, goal_pose_adapter
  yaw offset, ZERO_POINT_YAW) each undoing it again for one consumer.

  THE FIX: apply the relabel to all three published quantities, not two.
  Translation is now rotated the same way orientation and twist already
  were (pub_x = -self.y, pub_y = +self.x), and pub_theta is therefore just
  self.theta -- the -90 deg constant disappears because there is no longer
  a seam for it to bridge. odom, map and base_link now all share
  +X=right, +Y=forward. Consequences, all verified by tools/verify_axis_chain.py:

      drive forward -> map +Y     strafe right -> map +X
      drive back    -> map -Y     strafe left  -> map -X

  This REMOVES a conversion point rather than adding one: every downstream
  -90 deg compensation listed above was deleted in the same commit, because
  each existed only to undo this. Do not reintroduce one in isolation.

  NOT affected, and deliberately not touched: the internal REP-103
  integration above; mecanum_teleop_asymmetric.py; cmd_vel_axis_adapter.py
  (base_link <-> wheel-kinematics axes, a different conversion that is still
  needed); scan_relay.py's mirror (a sensor-bearing reflection calibrated in
  base_link, which this does not move); the URDF; nav2's footprint and MPPI
  velocity limits (all base_link-frame).

  If the LiDAR is ever remounted and scan_relay.py's yaw_offset is
  re-derived, that affects base_link's relationship to the sensor, not
  odom's axes -- the two are no longer coupled through this file.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty, Float64MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster
import math
import time


class OdometryPublisher(Node):

    def __init__(self):
        super().__init__('odometry_publisher')

        # Robot geometry
        self.declare_parameter('wheel_radius', 0.0762)
        self.declare_parameter('l1', 0.403)
        self.declare_parameter('l2', 0.333)
        self.declare_parameter('d', 0.15769)
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        # ── LATERAL SLIP CORRECTION (measured on hardware 15 Aug 2026) ──
        # Mecanum rollers scrub sideways across the floor during a strafe, so
        # the wheels turn further than the chassis actually travels. The ideal
        # kinematics below cannot know this and over-report lateral distance.
        #
        # Measured directly, tape measure vs this node's own output, robot
        # driven manually with no rotation:
        #     forward 1.00 m -> reported 1.009 m   (+0.9%,  no correction needed)
        #     strafe  1.00 m -> reported 1.248 m   (+24.8%)
        #     strafe  1.00 m -> reported 1.245 m   (+24.5%)   repeat run
        # -> true lateral distance = 0.80 x reported.
        #
        # Longitudinal is left at 1.0 deliberately: it measured accurate, and
        # scaling an axis that isn't wrong only adds a second thing to doubt.
        #
        # Why this matters beyond tidiness: slam_toolbox takes odom as its
        # motion prior and then scan-matches against it. A 25% lie on every
        # sideways move forces a correction each time, which is what produced
        # the 6.7-18.2 cm pose jumps seen during zero_point_scan.py's first
        # working run, and why its nudges never landed where it aimed them.
        #
        # A PARAMETER, not a constant, and READ LIVE rather than cached at
        # startup. Surface dependence is not a footnote here, it is the main
        # result -- two floors in the same building measured, same procedure,
        # same robot, same session:
        #     floor A:  raw 1.248 / 1.245 per 1.00 m tape  -> scale 0.80
        #     floor B:  raw 1.080 / 1.089 per 1.00 m tape  -> scale 0.92
        # A single compiled-in constant is therefore wrong somewhere by
        # construction. Reading the parameter inside the callback makes
        #     ros2 param set /odometry_publisher lateral_scale 0.92
        # take effect immediately, so recalibrating for a new floor is a
        # strafe, a tape measure and one command -- no edit, no rebuild, no
        # service restart that would throw away the zero point.
        #
        # Repeatability on a single surface is excellent (an out-and-back of
        # ~1.74 m closed to 2.6 cm, 1.5%), so this is a scale factor worth
        # measuring, not noise to be averaged away.
        # DEFAULT IS FLOOR B, the surface the zero mark sits on and therefore
        # the one every mapping and navigation run actually starts from.
        # Confirmed twice by independent routes: an uncorrected strafe read
        # 1.080 m per 1.00 m tape, and a 0.80-corrected strafe read 0.868 m
        # per 1.00 m tape (raw 1.085). Both give 0.92.
        # On floor A use 0.80 — see the surface table above.
        self.declare_parameter('lateral_scale', 0.92)

        self.r = self.get_parameter('wheel_radius').value
        self.l1 = self.get_parameter('l1').value
        self.l2 = self.get_parameter('l2').value
        self.d = self.get_parameter('d').value
        self.publish_tf = self.get_parameter('publish_tf').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value

        self.K_outer = self.l1 + self.d
        self.K_inner = self.l2 + self.d

        # State
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()

        # ROS2
        self.sub = self.create_subscription(
            Float64MultiArray, 'wheel_velocities_actual',
            self.velocity_cb, 10)

        self.odom_pub = self.create_publisher(Odometry, 'wheel_odom', 50)

        # ── Re-zero without a service restart (§17.32) ────────────────────
        # Setting the zero point used to mean `systemctl restart
        # aislebot.service`, because x/y/theta are only ever zeroed in
        # __init__. That works from a terminal, but it also tears down
        # phone_dashboard -- which is the thing that would be asking for the
        # re-zero in the first place -- so the dashboard could never own the
        # §8 procedure. This topic zeroes the same three numbers in place.
        #
        # ORDERING STILL MATTERS, and is enforced by the caller, not here:
        # slam_toolbox pins map->odom to identity at its first scan, so a
        # re-zero must happen BEFORE mapping starts or map (0,0) lands on
        # the old origin. phone_dashboard refuses the request while mapping
        # is active for exactly this reason (Important_Commands.md §8).
        self.create_subscription(Empty, 'odom/reset', self._reset_cb, 10)

        if self.publish_tf:
            self.tf_broadcaster = TransformBroadcaster(self)

        self.get_logger().info(
            f'Odometry publisher started | '
            f'K_out={self.K_outer:.4f} K_in={self.K_inner:.4f}')

    def _reset_cb(self, _msg):
        """Zero the integrated pose in place — the robot's current physical
        spot becomes odom's origin, exactly as a fresh node start would."""
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        # Integration is dt-based off the previous callback; without this the
        # first post-reset sample would integrate the whole idle gap since the
        # last wheel message and immediately walk the new origin off zero.
        self.last_time = self.get_clock().now()
        self.get_logger().info('Odometry re-zeroed: this spot is now odom (0, 0, 0)')

    def velocity_cb(self, msg):
        if len(msg.data) < 4:
            return

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        self.last_time = now

        if dt <= 0.0 or dt > 1.0:
            return

        w_fr, w_fl, w_rr, w_rl = msg.data[0], msg.data[1], msg.data[2], msg.data[3]

        # Forward kinematics (asymmetric)
        vx = (self.r / 4.0) * (w_fr + w_fl + w_rr + w_rl)
        # lateral_scale corrects roller scrub — see the parameter's comment in
        # __init__ for the tape-measured derivation. Applied here, at the one
        # place vy is produced, so the integrated position, the published
        # twist, and anything downstream all inherit the same correction.
        lateral_scale = self.get_parameter('lateral_scale').value
        vy = (self.r / 4.0) * (w_fr - w_fl - w_rr + w_rl) * lateral_scale

        # For rotation, use weighted formula accounting for asymmetry
        wz = (self.r / 4.0) * (
            w_fr / self.K_outer
            - w_fl / self.K_inner
            + w_rr / self.K_inner
            - w_rl / self.K_outer
        )

        # Integrate position (2nd order midpoint for better accuracy)
        half_dtheta = wz * dt * 0.5
        cos_mid = math.cos(self.theta + half_dtheta)
        sin_mid = math.sin(self.theta + half_dtheta)

        self.x += (vx * cos_mid - vy * sin_mid) * dt
        self.y += (vx * sin_mid + vy * cos_mid) * dt
        self.theta += wz * dt

        # Normalize theta to [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # ── Published-frame rotation (see module docstring, §17.10/§17.38) ─
        # Internal self.x/self.y/self.theta above are standard REP-103
        # (vx=forward, vy=left) and stay that way. The PUBLISHED frame is
        # that frame rotated -90 deg, so its +X reads "right" and +Y reads
        # "forward", matching the LiDAR's validated calibration.
        #
        # All THREE published quantities carry that rotation. Until 27 Aug
        # 2026 translation did not, which silently defined odom's own axes
        # to be the internal REP-103 ones and left a constant -90 deg seam
        # between odom and base_link that map then inherited. Rotating
        # position here is what makes odom, map and base_link agree, and is
        # why pub_theta is now plain self.theta with no constant.
        pub_x = -self.y   # published +X = "right"
        pub_y = self.x    # published +Y = "forward"
        pub_theta = self.theta
        pub_vx = -vy   # published +X = "right"
        pub_vy = vx    # published +Y = "forward"

        # Create quaternion from published yaw
        qz = math.sin(pub_theta / 2.0)
        qw = math.cos(pub_theta / 2.0)

        # Publish odometry
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        odom.pose.pose.position.x = pub_x
        odom.pose.pose.position.y = pub_y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw

        # Covariance (diagonal, tuned for mecanum)
        odom.pose.covariance[0] = 0.01   # x
        odom.pose.covariance[7] = 0.01   # y
        odom.pose.covariance[35] = 0.03  # yaw

        odom.twist.twist.linear.x = pub_vx
        odom.twist.twist.linear.y = pub_vy
        odom.twist.twist.angular.z = wz

        odom.twist.covariance[0] = 0.01
        odom.twist.covariance[7] = 0.01
        odom.twist.covariance[35] = 0.03

        self.odom_pub.publish(odom)

        # Publish TF
        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = now.to_msg()
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = pub_x
            t.transform.translation.y = pub_y
            t.transform.translation.z = 0.0
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = OdometryPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
