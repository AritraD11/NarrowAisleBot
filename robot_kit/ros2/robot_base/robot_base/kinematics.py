"""
kinematics.py - wheel kinematics for any planar wheeled base.

Pure Python, no ROS, no numpy. The ROS nodes, the generator and the tests all
use this one file, so the robot's geometry is defined in exactly one place.

The model
---------
Every driven wheel i sits at (x_i, y_i) in base_link (REP-103: +x forward,
+y left). When the body moves with twist (vx, vy, wz), the contact point of
wheel i moves with velocity

    vcx = vx - wz * y_i
    vcy = vy + wz * x_i

A wheel only drives along one direction. Write that as a coupling vector
(ax_i, ay_i). The wheel's surface speed is the contact velocity projected on
it, and dividing by the radius gives the wheel's angular rate:

    w_i = (ax_i * vcx + ay_i * vcy) / r

That single line covers every drive type in this kit:

    differential, skid_steer   a = (1, 0)        rolls along x, cannot strafe
    mecanum                    a = (1, s_i)      s_i = +1 or -1 per wheel (45 deg rollers)
    omni                       a = (cos t, sin t) t = the wheel's drive direction

Check it against the textbook mecanum result: front_left at (lx, ly) with
s = -1 gives w = (vx - vy - (lx + ly) wz) / r. Same formula.

Forward kinematics (wheel rates -> body twist) is the least-squares inverse of
that map. For a holonomic base it solves for (vx, vy, wz); for a base that
cannot strafe it solves for (vx, wz) and reports vy = 0. With four mecanum
wheels the least-squares answer is the usual "sum the four wheels / 4" form.

Two measured corrections, both 1.0 until you have measured them:

    track_width_scale   multiplies every y_i (and x_i) lever arm in BOTH
                        directions. Skid-steer bases scrub when they turn and
                        behave as if the wheels were further apart. Same idea
                        as diff_drive_controller's wheel_separation_multiplier.
    lateral_scale       multiplies the vy that forward kinematics reports.
                        Mecanum rollers scrub sideways, so wheels over-report
                        strafe. Odometry only; commands are not changed.
                        NarrowAisleBot measured 0.80 on one floor and 0.92 on
                        another, same robot, same day.
"""

import math

HOLONOMIC_TYPES = ("mecanum", "omni")
DRIVE_TYPES = ("differential", "skid_steer", "mecanum", "omni")


class Wheel:
    __slots__ = ("name", "x", "y", "ax", "ay")

    def __init__(self, name, x, y, ax=1.0, ay=0.0):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.ax = float(ax)
        self.ay = float(ay)

    def __repr__(self):
        return (f"Wheel({self.name!r}, x={self.x:+.4f}, y={self.y:+.4f}, "
                f"a=({self.ax:+.3f}, {self.ay:+.3f}))")


def _solve(m, b):
    """Solve m x = b for a small square system by Gaussian elimination with
    partial pivoting. Raises ValueError if m is singular."""
    n = len(m)
    a = [list(map(float, row)) + [float(b[i])] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            raise ValueError("wheel layout cannot determine the body motion "
                             "(singular kinematics); check wheel positions")
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                for c in range(col, n + 1):
                    a[r][c] -= f * a[col][c]
    return [a[i][n] / a[i][i] for i in range(n)]


class DriveModel:
    """Inverse and forward kinematics for a list of Wheel objects."""

    def __init__(self, wheels, wheel_radius, holonomic,
                 track_width_scale=1.0, lateral_scale=1.0):
        if not wheels:
            raise ValueError("need at least one wheel")
        if wheel_radius <= 0:
            raise ValueError("wheel_radius must be positive")
        self.wheels = list(wheels)
        self.r = float(wheel_radius)
        self.holonomic = bool(holonomic)
        self.track_width_scale = float(track_width_scale)
        self.lateral_scale = float(lateral_scale)
        self._rows = self._build_rows()
        # Precompute the least-squares solver: (J^T J)^-1 J^T, as a matrix.
        self._pinv = self._pseudo_inverse()

    @property
    def names(self):
        return [w.name for w in self.wheels]

    def _build_rows(self):
        """Rows of J such that w = J * q, where q = (vx, vy, wz) for a
        holonomic base and (vx, wz) otherwise."""
        rows = []
        s = self.track_width_scale
        for w in self.wheels:
            x, y = w.x * s, w.y * s
            c_vx = w.ax / self.r
            c_vy = w.ay / self.r
            c_wz = (-w.ax * y + w.ay * x) / self.r
            rows.append((c_vx, c_vy, c_wz) if self.holonomic else (c_vx, c_wz))
        return rows

    def _pseudo_inverse(self):
        rows = self._rows
        k = len(rows[0])
        jtj = [[sum(r[i] * r[j] for r in rows) for j in range(k)] for i in range(k)]
        # Columns of (J^T J)^-1, one unit vector at a time.
        inv_cols = [_solve(jtj, [1.0 if i == c else 0.0 for i in range(k)])
                    for c in range(k)]
        inv = [[inv_cols[c][r] for c in range(k)] for r in range(k)]
        # pinv = inv * J^T, shape k x n
        return [[sum(inv[i][m] * rows[w][m] for m in range(k))
                 for w in range(len(rows))] for i in range(k)]

    # ── body twist -> wheel rates ───────────────────────────────────────
    def inverse(self, vx, vy, wz):
        """Wheel angular rates (rad/s), in wheel order. vy is ignored for a
        base that cannot strafe."""
        out = []
        for row in self._rows:
            if self.holonomic:
                out.append(row[0] * vx + row[1] * vy + row[2] * wz)
            else:
                out.append(row[0] * vx + row[1] * wz)
        return out

    # ── wheel rates (or angle increments) -> body twist ────────────────
    def forward(self, rates):
        """Least-squares body twist (vx, vy, wz) from wheel rates. Works the
        same on angle increments: pass d_phi and get (dx, dy, dtheta) in the
        body frame for that interval."""
        if len(rates) != len(self.wheels):
            raise ValueError(f"expected {len(self.wheels)} wheel values, got {len(rates)}")
        q = [sum(p * w for p, w in zip(row, rates)) for row in self._pinv]
        if self.holonomic:
            vx, vy, wz = q
            vy *= self.lateral_scale
        else:
            vx, wz = q
            vy = 0.0
        return vx, vy, wz

    @staticmethod
    def scale_to_limit(rates, max_rate):
        """If any wheel would exceed max_rate, scale ALL of them down by the
        same factor. Keeps the direction of motion and the curvature; a
        per-wheel clamp would turn a straight line into a curve."""
        peak = max((abs(v) for v in rates), default=0.0)
        if max_rate > 0 and peak > max_rate:
            k = max_rate / peak
            return [v * k for v in rates]
        return list(rates)

    def sign_pattern(self, vx, vy, wz):
        """Signs (+1/0/-1) of each wheel for a given motion. Used by the
        encoder logger to spin the robot in place for open-loop tests."""
        out = []
        for v in self.inverse(vx, vy, wz):
            out.append(0 if abs(v) < 1e-9 else (1 if v > 0 else -1))
        return out


class OdometryIntegrator:
    """Integrates body-frame increments into a pose in the odom frame.

    Uses the midpoint heading for each step (second order), which is what
    NarrowAisleBot's odometry_publisher does and what closed a 9.5 m,
    three-lap route to 1.9 mm on that robot.
    """

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

    def reset(self):
        self.x = self.y = self.theta = 0.0

    def step(self, dx, dy, dtheta):
        mid = self.theta + 0.5 * dtheta
        c, s = math.cos(mid), math.sin(mid)
        self.x += dx * c - dy * s
        self.y += dx * s + dy * c
        self.theta = math.atan2(math.sin(self.theta + dtheta),
                                math.cos(self.theta + dtheta))
        return self.x, self.y, self.theta


def model_from_params(names, xs, ys, axs, ays, wheel_radius, drive_type,
                      track_width_scale=1.0, lateral_scale=1.0):
    """Build a DriveModel from the flat parameter arrays the ROS nodes get
    (see config/robot.yaml, which generate.py writes)."""
    n = len(names)
    if not (len(xs) == len(ys) == len(axs) == len(ays) == n):
        raise ValueError("wheel parameter arrays must all have the same length")
    if drive_type not in DRIVE_TYPES:
        raise ValueError(f"drive_type must be one of {DRIVE_TYPES}, got {drive_type!r}")
    wheels = [Wheel(names[i], xs[i], ys[i], axs[i], ays[i]) for i in range(n)]
    return DriveModel(wheels, wheel_radius, drive_type in HOLONOMIC_TYPES,
                      track_width_scale, lateral_scale)
