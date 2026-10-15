#!/usr/bin/env python3
"""
AisleBot ESP32 Bridge v3.2
==========================
Bidirectional serial bridge between ROS2 (Raspberry Pi 5) and ESP32.

PROTOCOL (matches aislebot_esp32.ino v3.1; v3.0 still works, it just
answers <N...> with [ERR,UNKNOWN:N] and never sends [IMU] lines):
  Pi → ESP32:  <V,fr,fl,rr,rl>   velocity setpoints in rad/s
  Pi → ESP32:  <M,fr,fl,rr,rl>   direct PWM (-255 to 255)
  Pi → ESP32:  <S>               emergency stop (LATCHES — clear with <E1>)
  Pi → ESP32:  <P>               ping (expects [PONG])
  Pi → ESP32:  <E1> / <E0>       enable (+ clear E-STOP) / disable motors
  Pi → ESP32:  <N1,hz> / <N0>    IMU stream on at hz / off (v3.1)
  ESP32 → Pi:  CSV telemetry lines (when <L1> enabled)
  ESP32 → Pi:  [IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az,t_us   (rad/s, m/s^2;
               only published when the enable_imu parameter is true.
               t_us is the ESP32's micros(), not used yet)
  ESP32 → Pi:  [IMUS,...] / [IMUC,...] IMU status, 8 fields or fewer

v3.0 keeps <V> and the 13-column telemetry line byte-identical to v2.0,
so nothing in this bridge needed changing for it. <L2> appends further
columns after those 13; the fixed-index parse below is unaffected either
way. The ESP32-hosted WiFi joystick is gone in v3.0 — this bridge is now
the only command source, so there is no arbitration to lose against.

TOPICS:
  Subscribes: /wheel_speeds  (Float64MultiArray) [FR, FL, RR, RL] rad/s
  Subscribes: /esp32/command (String) raw command strings for ESP32
  Publishes:  /motor_telemetry_raw (String) raw string from ESP32
  Publishes:  /motor_telemetry (Float64MultiArray) structured CSV data
  Publishes:  /wheel_velocities_actual (Float64MultiArray) measured speeds
  Publishes:  /imu/data (Imu, frame imu_link) if enable_imu. REP-145 calls
              a message with orientation imu/data; imu/data_raw is for
              messages without it. ekf_params.yaml already reads imu/data.

IIT Bombay — Aritra Das (25D0074) — Prof. Ambarish Kunwar
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, String
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion
import serial
import serial.tools.list_ports
import threading
import time
import math


class ESP32Bridge(Node):

    def __init__(self):
        super().__init__('esp32_bridge')

        # === Parameters ===
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 921600)
        # Match the firmware's max_wheel_speed. 5.2 rad/s is the v3.0 AIR
        # value; the ESP32 clamps to its own limit regardless, but keeping
        # them equal means the Pi's idea of what it commanded is the truth.
        # Lower BOTH to ~4.2 after ground calibration — see
        # docs/PID_Calibration.md §7.
        self.declare_parameter('max_wheel_speed', 5.20)       # rad/s
        self.declare_parameter('reconnect_interval', 3.0)     # seconds
        self.declare_parameter('watchdog_timeout', 0.5)       # seconds
        self.declare_parameter('enable_imu', False)
        self.declare_parameter('telemetry_enabled', False)
        self.declare_parameter('imu_topic', 'imu/data')
        # 50 Hz is plenty for yaw-rate fusion at 0.30 rad/s and costs the Pi
        # half the parsing of 100 Hz. The firmware caps it at 100.
        self.declare_parameter('imu_rate_hz', 50.0)
        # Variances on the diagonal of each sensor_msgs/Imu covariance.
        # All-zero covariances read as "unknown" to some consumers and as
        # "perfect" to robot_localization (it floors them near 1e-9).
        # gyro: 3e-5 (rad/s)^2 is the top of the range implied by the
        #   BNO055's ~0.1-0.3 deg/s rms output noise (datasheet value seen
        #   second-hand; replace with the 15-minute static log's figure).
        # accel and orientation: placeholders until measured. IMUPLUS yaw
        #   is relative to power-on, so the orientation is not an absolute
        #   heading whatever this says.
        self.declare_parameter('imu_gyro_variance', 3e-5)
        self.declare_parameter('imu_accel_variance', 1e-2)
        self.declare_parameter('imu_orientation_variance', 1e-3)

        self.port = self.get_parameter('serial_port').value
        self.baud = self.get_parameter('baud_rate').value
        self.max_speed = self.get_parameter('max_wheel_speed').value
        self.reconnect_sec = self.get_parameter('reconnect_interval').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value
        self.enable_imu = self.get_parameter('enable_imu').value
        self.telemetry_enabled = self.get_parameter('telemetry_enabled').value
        self.imu_topic = self.get_parameter('imu_topic').value
        self.imu_rate_hz = float(self.get_parameter('imu_rate_hz').value)
        self.imu_gyro_var = float(self.get_parameter('imu_gyro_variance').value)
        self.imu_accel_var = float(self.get_parameter('imu_accel_variance').value)
        self.imu_orient_var = float(self.get_parameter('imu_orientation_variance').value)

        # === State ===
        self.serial_conn = None
        self.connected = False
        self.serial_lock = threading.Lock()
        self.last_cmd_time = time.time()
        self.last_speeds = [0.0, 0.0, 0.0, 0.0]
        self.actual_speeds = [0.0, 0.0, 0.0, 0.0]
        self.msg_count = 0
        self.error_count = 0

        # === ROS2 Subscribers ===
        self.sub_wheel = self.create_subscription(
            Float64MultiArray, 'wheel_speeds', self.wheel_speed_cb, 10)
            
        # Subscriber for raw commands from phone_dashboard
        self.sub_raw_cmd = self.create_subscription(
            String, '/esp32/command', self._raw_command_callback, 10)

        # === ROS2 Publishers ===
        # Renamed original string publisher to avoid clash with the new array publisher
        self.pub_telemetry_raw = self.create_publisher(String, 'motor_telemetry_raw', 10)
        
        # New Publisher: parsed telemetry for phone_dashboard to log as CSV.
        self.telemetry_pub = self.create_publisher(
            Float64MultiArray, '/motor_telemetry', 10)
            
        self.pub_actual = self.create_publisher(
            Float64MultiArray, 'wheel_velocities_actual', 10)
        if self.enable_imu:
            self.pub_imu = self.create_publisher(Imu, self.imu_topic, 10)

        # === Timers ===
        self.create_timer(self.reconnect_sec, self.check_connection)
        self.create_timer(1.0 / 20.0, self.watchdog_check)  # 20Hz watchdog
        if self.telemetry_enabled or self.enable_imu:
            # <L1> and <N1> are otherwise only sent once, in connect_serial().
            # If the ESP32 resets on its own (e.g. brownout) fast enough that
            # this bridge's serial layer never sees a disconnect, both streams
            # go silent with no error anywhere while drive commands keep
            # working (Research_Journal.md §16.10). Re-sending periodically
            # means they self-heal. Neither feeds the ESP32's command watchdog
            # from v3.1 on, so this can't keep a stale <V> alive.
            self.create_timer(5.0, self.resend_telemetry_enable)

        # === Serial reader thread ===
        self.reader_thread = threading.Thread(target=self.serial_reader, daemon=True)
        self.reader_running = True

        # === Connect ===
        self.connect_serial()
        self.reader_thread.start()

        self.get_logger().info(
            f'ESP32 Bridge started | port={self.port} baud={self.baud} '
            f'imu={"ON" if self.enable_imu else "OFF"}')

    # ─── Serial Connection ───────────────────────────────────────

    def connect_serial(self):
        if self.connected:
            return True
        try:
            self.serial_conn = serial.Serial(
                self.port, self.baud, timeout=0.1,
                write_timeout=0.1)
            time.sleep(0.5)  # ESP32 boot time
            self.serial_conn.reset_input_buffer()
            self.connected = True
            self.error_count = 0

            # Enable motors and optionally telemetry
            self.send_raw('<E1>')
            if self.telemetry_enabled:
                time.sleep(0.05)
                self.send_raw('<L1>')
            # Ask for the IMU stream, or make sure it's off. A firmware
            # session that turned it on survives a bridge restart.
            time.sleep(0.05)
            self.send_raw(self._imu_stream_cmd())

            self.get_logger().info(f'Connected to ESP32 on {self.port}')
            return True
        except Exception as e:
            self.connected = False
            self.get_logger().warn(f'Serial connect failed: {e}', throttle_duration_sec=5.0)
            return False

    def check_connection(self):
        if not self.connected:
            # Try auto-detect
            ports = serial.tools.list_ports.comports()
            for p in ports:
                if 'CP2102' in (p.description or '') or 'USB' in (p.device or ''):
                    if p.device != self.port:
                        self.get_logger().info(f'Auto-detected ESP32 on {p.device}')
                        self.port = p.device
                    break
            self.connect_serial()

    def _imu_stream_cmd(self):
        if self.enable_imu:
            return f'<N1,{self.imu_rate_hz:g}>'
        return '<N0>'

    def resend_telemetry_enable(self):
        if self.connected:
            if self.telemetry_enabled:
                self.send_raw('<L1>')
            if self.enable_imu:
                self.send_raw(self._imu_stream_cmd())

    def send_raw(self, cmd):
        with self.serial_lock:
            if not self.connected or not self.serial_conn:
                return False
            try:
                self.serial_conn.write(cmd.encode('ascii'))
                return True
            except Exception as e:
                self.get_logger().error(f'Serial write error: {e}')
                self.connected = False
                return False

    # ─── Command Callbacks ───────────────────────────────────────

    def wheel_speed_cb(self, msg):
        if len(msg.data) < 4:
            return
        self.last_cmd_time = time.time()

        fr = max(-self.max_speed, min(self.max_speed, msg.data[0]))
        fl = max(-self.max_speed, min(self.max_speed, msg.data[1]))
        rr = max(-self.max_speed, min(self.max_speed, msg.data[2]))
        rl = max(-self.max_speed, min(self.max_speed, msg.data[3]))

        cmd = f'<V,{fr:.3f},{fl:.3f},{rr:.3f},{rl:.3f}>'
        if self.send_raw(cmd):
            self.last_speeds = [fr, fl, rr, rl]
            self.msg_count += 1
            if self.msg_count % 100 == 0:
                self.get_logger().debug(
                    f'Sent #{self.msg_count}: FR={fr:.2f} FL={fl:.2f} '
                    f'RR={rr:.2f} RL={rl:.2f}')

    def _raw_command_callback(self, msg: String):
        """Forward a raw command string (e.g. '<L1>') directly to ESP32 serial."""
        cmd = msg.data.strip()
        if cmd and self.connected:
            try:
                # Use send_raw to maintain lock safety and error handling
                self.send_raw(cmd)
                self.get_logger().debug(f'Forwarded to ESP32: {cmd}')
            except Exception as e:
                self.get_logger().warn(f'Failed to forward command: {e}')

    # ─── Watchdog ────────────────────────────────────────────────

    def watchdog_check(self):
        if time.time() - self.last_cmd_time > self.watchdog_timeout:
            if any(s != 0.0 for s in self.last_speeds):
                self.send_raw('<V,0.000,0.000,0.000,0.000>')
                self.last_speeds = [0.0, 0.0, 0.0, 0.0]

    # ─── Serial Reader Thread ────────────────────────────────────

    def serial_reader(self):
        """Background thread: reads ESP32 serial output, parses telemetry."""
        while self.reader_running:
            if not self.connected or not self.serial_conn:
                time.sleep(0.1)
                continue
            try:
                line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                if not line:
                    continue
                self.parse_esp32_line(line)
            except Exception as e:
                self.error_count += 1
                if self.error_count > 10:
                    self.get_logger().error(f'Serial read errors ({self.error_count}), reconnecting')
                    self.connected = False
                time.sleep(0.01)

    def _publish_telemetry(self, line: str):
        """
        Parse an ESP32 telemetry CSV line and publish on /motor_telemetry.

        ESP32 format (from outputSerialTelemetry in firmware):
            timestamp_ms,FR_tgt,FR_act,FR_pwm,FL_tgt,FL_act,FL_pwm,
                         RR_tgt,RR_act,RR_pwm,RL_tgt,RL_act,RL_pwm
        That is 13 comma-separated values.
        We publish the 12 motor values (drop the ESP32 timestamp).
        """
        try:
            parts = line.strip().split(',')
            if len(parts) < 13:
                return
            # parts[0] = timestamp_ms, parts[1..12] = motor data
            values = [float(p) for p in parts[1:13]]   # 12 values
            msg = Float64MultiArray()
            msg.data = values
            self.telemetry_pub.publish(msg)
        except (ValueError, IndexError):
            pass   # Ignore malformed lines silently

    def parse_esp32_line(self, line):
        """Parse telemetry/encoder lines from ESP32."""
        # IMU lines are comma separated too, and the wheel-speed fallback
        # below accepts any line with a comma, nine or more fields and a
        # non-digit first field. An IMU line used to fall into it and went
        # out on /wheel_velocities_actual as four "wheel speeds" (gyro and
        # quaternion values), which odometry_publisher integrates. Handle
        # the line here and return so it can never reach that branch,
        # whether or not enable_imu is set. It's also handled before the
        # raw republish, which would otherwise add 50-100 String messages
        # a second to a topic nothing subscribes to.
        if line.startswith('[IMU]'):
            if self.enable_imu:
                self._publish_imu(line)
            return

        # Publish raw telemetry
        tel_msg = String()
        tel_msg.data = line
        self.pub_telemetry_raw.publish(tel_msg)

        # Detect CSV telemetry line (starts with digit and has commas)
        if line and line[0].isdigit() and ',' in line:
            self._publish_telemetry(line)

        # Parse CSV telemetry: t,tgt_fr,act_fr,tgt_fl,act_fl,tgt_rr,act_rr,tgt_rl,act_rl,...
        # (Legacy parsing block kept for publishing to /wheel_velocities_actual)
        if line.startswith('[TEL]') or ',' in line:
            try:
                parts = line.replace('[TEL]', '').strip().split(',')
                # If it's the 13-part telemetry string, extract actual speeds
                if len(parts) >= 13 and parts[0].isdigit():
                     # Format: time, FR_tgt, FR_act, FR_pwm, FL_tgt, FL_act, FL_pwm...
                     act_fr = float(parts[2])
                     act_fl = float(parts[5])
                     act_rr = float(parts[8])
                     act_rl = float(parts[11])
                     self.actual_speeds = [act_fr, act_fl, act_rr, act_rl]
                     
                     msg = Float64MultiArray()
                     msg.data = self.actual_speeds
                     self.pub_actual.publish(msg)
                # Keep original logic as a fallback if the line is not the new format
                elif len(parts) >= 9 and not parts[0].isdigit():
                    # Extract actual speeds [FR, FL, RR, RL]
                    act_fr = float(parts[2])
                    act_fl = float(parts[4])
                    act_rr = float(parts[6])
                    act_rl = float(parts[8])
                    self.actual_speeds = [act_fr, act_fl, act_rr, act_rl]

                    msg = Float64MultiArray()
                    msg.data = self.actual_speeds
                    self.pub_actual.publish(msg)
            except (ValueError, IndexError):
                pass

    def _publish_imu(self, line: str):
        """
        Parse '[IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az[,t_us]' and publish it
        on imu_topic (imu/data by default).

        Units are sensor_msgs/Imu's: gyro in rad/s, acceleration in m/s^2,
        quaternion unitless. The firmware must print them in these units.
        The stamp is the Pi's arrival time, not the ESP32's; an 11th field
        (the ESP32's micros()) is accepted and ignored for now.
        """
        try:
            parts = line[5:].split(',')
            if len(parts) >= 10:
                imu_msg = Imu()
                imu_msg.header.stamp = self.get_clock().now().to_msg()
                imu_msg.header.frame_id = 'imu_link'
                for i in (0, 4, 8):
                    imu_msg.orientation_covariance[i] = self.imu_orient_var
                    imu_msg.angular_velocity_covariance[i] = self.imu_gyro_var
                    imu_msg.linear_acceleration_covariance[i] = self.imu_accel_var
                imu_msg.orientation.w = float(parts[0])
                imu_msg.orientation.x = float(parts[1])
                imu_msg.orientation.y = float(parts[2])
                imu_msg.orientation.z = float(parts[3])
                imu_msg.angular_velocity.x = float(parts[4])
                imu_msg.angular_velocity.y = float(parts[5])
                imu_msg.angular_velocity.z = float(parts[6])
                imu_msg.linear_acceleration.x = float(parts[7])
                imu_msg.linear_acceleration.y = float(parts[8])
                imu_msg.linear_acceleration.z = float(parts[9])
                self.pub_imu.publish(imu_msg)
        except (ValueError, IndexError):
            pass

    # ─── Cleanup ─────────────────────────────────────────────────

    def destroy_node(self):
        self.reader_running = False
        self.send_raw('<S>')  # Emergency stop on shutdown
        time.sleep(0.05)
        self.send_raw('<E0>')
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ESP32Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()