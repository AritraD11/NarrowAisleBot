#!/usr/bin/env python3
"""
mcu_bridge - the only ROS node that talks to the microcontroller.

  subscribes  /wheel_cmd      Float64MultiArray  wheel targets, rad/s, wheel order
              /mcu/command    String             raw protocol command, e.g. "<S>"
  publishes   /wheel_states   JointState         name, position (rad), velocity (rad/s),
                                                 effort (PWM), stamped at sample time
              /mcu/telemetry  Float64MultiArray  [mcu_ms, then every telemetry value]
              /mcu/status     String             every [..] line the firmware prints

Behaviour worth knowing before you debug it:

  * On connect it sends <E1> (enable) and <L2,hz> (extended telemetry), and
    re-sends <L2> every 5 s. NarrowAisleBot lost telemetry silently after a
    brownout reset the ESP32 without the port closing; odometry stopped,
    slam_toolbox sat at "Activating" with no error. Re-sending heals it.
  * It asks the firmware for [MOTORS,N,names] and REFUSES to drive if the
    names differ from wheel_names. A wheel order mismatch sends the right
    command to the wrong wheel; that should be impossible, not just unlikely.
  * No /wheel_cmd for cmd_timeout seconds: it sends zeros once. The
    firmware's own watchdog (750 ms) is the layer below that.
  * On shutdown it sends <S> then <E0>.
  * Only this process may open the port. The encoder logger and this
    bridge cannot run at the same time.
"""

import threading
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String
from builtin_interfaces.msg import Time

from robot_base import protocol as P


class McuBridge(Node):

    def __init__(self):
        super().__init__("mcu_bridge")
        self.declare_parameter("port", "/dev/robot_mcu")
        self.declare_parameter("baud", 921600)
        self.declare_parameter("wheel_names", ["left", "right"])
        self.declare_parameter("max_wheel_speed", 10.0)
        self.declare_parameter("telemetry_mode", 2)
        self.declare_parameter("telemetry_hz", 20.0)
        self.declare_parameter("cmd_timeout", 0.5)
        self.declare_parameter("open_delay", 2.0)

        self.port = self.get_parameter("port").value
        self.baud = int(self.get_parameter("baud").value)
        self.names = list(self.get_parameter("wheel_names").value)
        self.n = len(self.names)
        self.vmax = float(self.get_parameter("max_wheel_speed").value)
        self.tmode = int(self.get_parameter("telemetry_mode").value)
        self.thz = float(self.get_parameter("telemetry_hz").value)
        self.cmd_timeout = float(self.get_parameter("cmd_timeout").value)
        self.open_delay = float(self.get_parameter("open_delay").value)

        self.link = None
        self.ready = False              # connected AND identity checked
        self.last_cmd = 0.0
        self.last_sent_nonzero = False
        self.offset = None              # arrival - mcu time, see _stamp()
        self.last_mcu_ms = None
        self.rx_rows = 0

        self.pub_states = self.create_publisher(JointState, "wheel_states", 20)
        self.pub_tel = self.create_publisher(Float64MultiArray, "mcu/telemetry", 20)
        self.pub_status = self.create_publisher(String, "mcu/status", 20)
        self.create_subscription(Float64MultiArray, "wheel_cmd", self._on_cmd, 10)
        self.create_subscription(String, "mcu/command", self._on_raw, 10)
        self.create_timer(0.05, self._watchdog)
        self.create_timer(5.0, self._keepalive)
        self.create_timer(10.0, self._report)

        self._stop = False
        threading.Thread(target=self._connection_loop, daemon=True).start()
        self.get_logger().info(f"mcu_bridge: {self.port} @ {self.baud}, wheels {self.names}")

    # ── connection management (own thread: opening a port can take seconds)
    def _connection_loop(self):
        while not self._stop:
            if self.link is None or not self.link.running:
                self.ready = False
                if self.link is not None:
                    self.get_logger().warn(f"serial link lost: {self.link.error}")
                    self.link = None
                try:
                    link = P.SerialLink(self.port, self.baud, n_motors=self.n,
                                        on_line=self._on_line, open_delay=self.open_delay)
                except Exception as e:  # noqa: BLE001
                    self.get_logger().warn(f"cannot open {self.port}: {e}",
                                           throttle_duration_sec=10.0)
                    time.sleep(2.0)
                    continue
                self.link = link
                self.offset = None
                ident = P.read_identity(link)
                if ident["names"] is not None and ident["names"] != self.names:
                    self.get_logger().error(
                        f"firmware motors {ident['names']} != wheel_names {self.names}. "
                        "NOT driving. Regenerate robot_config.h and reflash, or fix "
                        "robot_config.yaml.")
                    time.sleep(5.0)
                    link.close(stop=True)
                    continue
                if ident["names"] is None:
                    self.get_logger().warn("firmware did not report [MOTORS,...]; "
                                           "trusting wheel_names")
                link.send("<E1>", 0.05)
                link.send(f"<L{self.tmode},{self.thz:g}>", 0.05)
                self.ready = True
                self.get_logger().info(f"connected: {ident['info'] or 'unknown firmware'}")
            time.sleep(1.0)

    def _send(self, cmd):
        if self.link is None or not self.link.running:
            return False
        try:
            self.link.send(cmd, 0)
            return True
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f"write failed: {e}", throttle_duration_sec=5.0)
            self.link.running = False
            return False

    # ── commands in ─────────────────────────────────────────────────────
    def _on_cmd(self, msg):
        if not self.ready:
            return
        if len(msg.data) != self.n:
            self.get_logger().warn(f"/wheel_cmd has {len(msg.data)} values, expected {self.n}",
                                   throttle_duration_sec=5.0)
            return
        w = [max(-self.vmax, min(self.vmax, float(v))) for v in msg.data]
        if self._send(P.cmd_velocity(w)):
            self.last_cmd = time.time()
            self.last_sent_nonzero = any(abs(v) > 1e-6 for v in w)

    def _on_raw(self, msg):
        cmd = msg.data.strip()
        if not (cmd.startswith("<") and cmd.endswith(">")):
            self.get_logger().warn(f"ignoring /mcu/command without <...> framing: {cmd!r}")
            return
        self.get_logger().info(f"raw command: {cmd}")
        self._send(cmd)

    def _watchdog(self):
        if self.last_sent_nonzero and time.time() - self.last_cmd > self.cmd_timeout:
            if self._send(P.cmd_velocity([0.0] * self.n)):
                self.last_sent_nonzero = False

    def _keepalive(self):
        if self.ready:
            self._send(f"<L{self.tmode},{self.thz:g}>")

    def _report(self):
        if self.ready and self.rx_rows == 0:
            self.get_logger().warn("connected but no telemetry for 10 s: is the firmware "
                                   "the kit's (send <I>), and the baud right?")
        self.rx_rows = 0

    # ── telemetry out ───────────────────────────────────────────────────
    def _stamp(self, arrival, mcu_ms):
        """Sample time on the ROS clock. USB delivery adds a variable delay;
        the smallest (arrival - mcu time) seen is the true clock offset, so
        delay = (arrival - mcu) - offset. The offset relaxes slowly upward so
        a later USB hiccup or crystal drift cannot pin it forever, and it
        resets if the MCU reboots (millis goes backwards)."""
        mcu = mcu_ms / 1000.0
        if self.last_mcu_ms is not None and mcu_ms < self.last_mcu_ms:
            self.offset = None
        self.last_mcu_ms = mcu_ms
        d = arrival - mcu
        if self.offset is None or d < self.offset:
            self.offset = d
        else:
            self.offset += 1e-5
        delay = max(0.0, d - self.offset)
        now = self.get_clock().now().nanoseconds * 1e-9 - delay
        return Time(sec=int(now), nanosec=int((now % 1.0) * 1e9))

    def _on_line(self, arrival, line):
        if line.startswith("["):
            m = String()
            m.data = line
            self.pub_status.publish(m)
            if line.startswith(("[TRIP", "[ERR", "[WARN")):
                self.get_logger().warn(f"firmware: {line}")
            return
        tel = P.parse_telemetry(line, self.n)
        if tel is None:
            return
        self.rx_rows += 1
        raw = Float64MultiArray()
        raw.data = [float(tel.mcu_ms)] + [float(v) for v in tel.values]
        self.pub_tel.publish(raw)
        js = JointState()
        js.header.stamp = self._stamp(arrival, tel.mcu_ms)
        js.name = self.names
        js.velocity = [float(v) for v in tel.actual]
        js.effort = [float(v) for v in tel.pwm]
        js.position = [float(v) for v in tel.pos_rad] if tel.extended else []
        self.pub_states.publish(js)

    def shutdown(self):
        self._stop = True
        if self.link is not None:
            self.link.close(stop=True)


def main(args=None):
    rclpy.init(args=args)
    node = McuBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
