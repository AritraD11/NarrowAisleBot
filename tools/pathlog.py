import math, time, rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros import Buffer, TransformListener, TransformException
from nav_msgs.msg import OccupancyGrid

rclpy.init()
n = Node('pathlog')
buf = Buffer()
TransformListener(buf, n)
m = {'msg': None}
q = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
               reliability=QoSReliabilityPolicy.RELIABLE)
n.create_subscription(OccupancyGrid, '/map', lambda x: m.__setitem__('msg', x), q)
print('t,cells,dcells,x,y,yaw')
t0 = time.monotonic()
prev = None
try:
    while rclpy.ok():
        d = time.monotonic() + 1.0
        while time.monotonic() < d:
            rclpy.spin_once(n, timeout_sec=0.05)
        c = None if m['msg'] is None else sum(1 for v in m['msg'].data if v != -1)
        dc = '' if (c is None or prev is None) else c - prev
        if c is not None:
            prev = c
        t = time.monotonic() - t0
        try:
            tf = buf.lookup_transform('map', 'base_link', Time())
            p = tf.transform.translation
            r = tf.transform.rotation
            yaw = math.degrees(math.atan2(2 * (r.w * r.z), 1 - 2 * r.z * r.z))
            print('%.1f,%s,%s,%.3f,%.3f,%.1f' % (t, c, dc, p.x, p.y, yaw), flush=True)
        except TransformException:
            print('%.1f,%s,%s,,,' % (t, c, dc), flush=True)
except KeyboardInterrupt:
    pass
