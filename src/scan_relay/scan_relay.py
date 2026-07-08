import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan

class ScanRelay(Node):
    def __init__(self):
        super().__init__('scan_relay')
        be = QoSProfile(depth=10,
                        reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10,
                         reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, '/scan_reliable', rel)
        self.sub = self.create_subscription(LaserScan, '/scan', self.cb, be)
        self.get_logger().info('scan_relay up: /scan (best_effort) -> /scan_reliable (reliable)')

    def cb(self, msg):
        self.pub.publish(msg)

def main():
    rclpy.init()
    rclpy.spin(ScanRelay())

if __name__ == '__main__':
    main()
