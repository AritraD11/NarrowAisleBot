#!/usr/bin/env python3
"""IMU health numbers from a `ros2 topic echo --no-arr /imu/data` capture (stationary robot).
Usage: imu_health.py capture.txt
Pure stdlib. Prints the numbers and the check each one is compared against."""
import math
import re
import statistics as st
import sys

txt = open(sys.argv[1], encoding='utf-8', errors='replace').read()
msgs = [m for m in txt.split('---') if 'orientation:' in m]


def num(block, key):
    m = re.search(r'^\s*' + key + r':\s*(-?[0-9.eE+-]+)\s*$', block, re.M)
    return float(m.group(1)) if m else None


rows = []
for m in msgs:
    sec = re.search(r'sec:\s*(\d+)', m)
    nsec = re.search(r'nanosec:\s*(\d+)', m)
    o = m.split('orientation:')[1].split('orientation_covariance')[0]
    g = m.split('angular_velocity:')[1].split('angular_velocity_covariance')[0]
    a = m.split('linear_acceleration:')[1].split('linear_acceleration_covariance')[0]
    try:
        rows.append(dict(
            t=int(sec.group(1)) + int(nsec.group(1)) * 1e-9,
            q=[num(o, k) for k in ('x', 'y', 'z', 'w')],
            g=[num(g, k) for k in ('x', 'y', 'z')],
            a=[num(a, k) for k in ('x', 'y', 'z')]))
    except Exception:
        pass
rows = [r for r in rows if None not in r['q'] + r['g'] + r['a']]
n = len(rows)
print(f'messages parsed: {n}')
if n < 50:
    sys.exit('too few messages')

T = [r['t'] for r in rows]
dt = [b - a for a, b in zip(T, T[1:])]
span = T[-1] - T[0]
print(f'\nTIMING  span {span:.2f} s, mean rate {n/span:.2f} Hz  (stamps; the echo itself can drop messages)')
print(f'  dt mean {st.mean(dt)*1e3:.2f} ms, stdev {st.pstdev(dt)*1e3:.2f} ms, min {min(dt)*1e3:.2f}, max {max(dt)*1e3:.2f}')
gaps = [d for d in dt if d > 0.030]
print(f'  gaps > 30 ms (>1.5 periods at 50 Hz): {len(gaps)}' + (f', largest {max(gaps)*1e3:.1f} ms' if gaps else ''))
print(f'  non-monotonic stamps: {sum(1 for d in dt if d <= 0)}')


def euler(q):
    x, y, z, w = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    s = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    pitch = math.asin(s)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return [math.degrees(v) for v in (roll, pitch, yaw)]


norms = [math.sqrt(sum(c * c for c in r['q'])) for r in rows]
print(f'\nQUATERNION  |q| mean {st.mean(norms):.5f}, worst deviation from 1: {max(abs(v-1) for v in norms):.5f}  (check: < 0.005)')
E = [euler(r['q']) for r in rows]
for i, nm in enumerate(('roll', 'pitch', 'yaw')):
    col = [e[i] for e in E]
    print(f'  {nm:5s} mean {st.mean(col):8.3f} deg  stdev {st.pstdev(col):.4f}  range {max(col)-min(col):.4f}')
yaw_drift = E[-1][2] - E[0][2]
yaw_drift = (yaw_drift + 180) % 360 - 180
print(f'  yaw first->last: {yaw_drift:+.4f} deg over {span:.1f} s = {yaw_drift/span*60:+.3f} deg/min')

print('\nGYRO  rad/s (robot should be still)')
bias = []
for i, nm in enumerate('xyz'):
    col = [r['g'][i] for r in rows]
    bias.append(st.mean(col))
    print(f'  {nm}: mean {st.mean(col)*1e3:+8.3f} mrad/s ({math.degrees(st.mean(col)):+.4f} deg/s)  stdev {st.pstdev(col)*1e3:.3f} mrad/s  min/max {min(col):+.4f}/{max(col):+.4f}')
print(f'  z bias as heading drift if left uncorrected: {math.degrees(bias[2])*60:+.3f} deg/min')
quant = sorted({round(abs(r['g'][i]), 6) for r in rows for i in range(3) if r['g'][i] != 0})[:4]
print(f'  smallest non-zero |gyro| values seen: {quant}  (resolution/quantisation of the published rate)')

print('\nACCELEROMETER  m/s^2')
for i, nm in enumerate('xyz'):
    col = [r['a'][i] for r in rows]
    print(f'  {nm}: mean {st.mean(col):+8.4f}  stdev {st.pstdev(col):.4f}  min/max {min(col):+.3f}/{max(col):+.3f}')
mag = [math.sqrt(sum(c * c for c in r['a'])) for r in rows]
print(f'  |a| mean {st.mean(mag):.4f}  stdev {st.pstdev(mag):.4f}  vs g = 9.8067: error {st.mean(mag)-9.80665:+.4f} ({(st.mean(mag)/9.80665-1)*100:+.2f} %)')
ax, ay, az = (st.mean([r['a'][i] for r in rows]) for i in range(3))
print(f'  tilt from accelerometer alone: roll {math.degrees(math.atan2(ay, az)):+.2f} deg, pitch {math.degrees(math.atan2(-ax, math.hypot(ay, az))):+.2f} deg')
print('  tilt from fused quaternion:    roll {:+.2f} deg, pitch {:+.2f} deg'.format(st.mean([e[0] for e in E]), st.mean([e[1] for e in E])))

# repeated identical samples (stuck/duplicated data)
dup = sum(1 for a, b in zip(rows, rows[1:]) if a['q'] == b['q'] and a['g'] == b['g'] and a['a'] == b['a'])
print(f'\nSTUCK DATA  consecutive identical samples: {dup} of {n-1}')
