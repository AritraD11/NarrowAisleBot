#!/usr/bin/env python3
"""
scan_relay.py — /scan (best-effort) -> /scan_reliable (reliable), with an
optional angular correction and a live-tunable quality gate applied on the
way through.

FOUR JOBS
---------

1. QoS BRIDGE (original purpose, Research_Journal.md 13.4).
   The ydlidar driver publishes /scan BEST_EFFORT; slam_toolbox and
   nav2_costmap_2d subscribe RELIABLE by default. Those endpoints never
   connect, and the symptom is a node that waits forever on a topic that
   `ros2 topic hz` says is perfectly alive.

2. ANGULAR CORRECTION (added 11 Aug 2026, section 17.9).
   Measured on hardware by placing a single block at known bearings *in
   base_link's own frame as this robot actually drives it* -- confirmed
   empirically (W -> +Y, D -> +X, both against Foxglove's Fixed/Display
   frame set to base_link), not assumed from the REP-103 textbook
   convention (which would put forward on +X). Whatever base_link's real
   axes are is what this scan has to line up with, so that is what was
   measured against:

       block truly RIGHT (base_link +X,   0 deg) -> reported  270 deg
       block truly FRONT (base_link +Y,  90 deg) -> reported  180 deg
       block truly LEFT  (base_link -X, 180 deg) -> reported   90 deg

   All three solve the same relationship: reported = 270 deg - true. That
   is a REFLECTION (a rotation would add the same signed delta at every
   heading; here the delta is 270, 90, 270 -- not constant -- while
   reported + true IS constant at every heading, which is what a mirror
   about a fixed line produces, not a turn).

   An earlier pass at this fix assumed base_link's forward was +X
   (REP-103) and derived yaw_offset=180 deg. That number is 90 deg off
   from every one of the three measurements above and was never deployed
   -- flagged here because it is the mistake to not repeat if this is ever
   re-derived: measure against how the robot actually drives, not against
   the textbook axis convention.

   This distinction decides where the fix can live: **a TF cannot express a
   reflection.** tf2 carries proper rigid motions (rotation + translation)
   only, so no base_link -> laser_frame transform, at any yaw, can undo
   this. The scan data itself has to be re-indexed -- which is why the fix
   is here, in the one node that already touches every scan.

   The correction is an involution (applying `reported = 180 - true` twice
   returns the original), so the same expression that describes the fault
   also repairs it.

3. SELF-OCCLUSION MASK (added 13 Aug 2026, section 17.15).
   The robot's own rear mast sits inside the LiDAR's field of view and
   BEYOND its 0.10 m minimum range, so it returns a valid, in-band hit on
   every single scan -- a phantom obstacle fixed in the robot's own frame
   rather than in the room. Navigation_Theory.md section 4 predicted this
   failure mode before Nav2 was ever run; these are the measurements that
   confirmed it.

   Measured with tools/scan_bearing.py at five headings around a full 360
   deg rotation (0/90/180/270/360). The discriminator is that real features
   sweep through the laser frame as the robot turns while self-occlusion
   does not, and the result is about as unambiguous as this kind of
   measurement gets -- nearest return per sector, across all five headings:

       sector        run1  run2  run3  run4  run5   spread
       -135..-120    0.13  0.12  0.13  0.12  0.13   0.01 m
       -120..-105    0.13  0.14  0.13  0.13  0.13   0.01 m
       -105.. -90    0.13  0.13  0.13  0.13  0.13   0.00 m
        -90.. -75    0.24  0.24  0.24  0.24  0.24   0.00 m
        -75.. -60    0.14  0.14  0.14  0.14  0.14   0.00 m
        -60.. -45    0.16  0.16  0.16  0.16  0.16   0.00 m

   A full revolution of the robot moved those distances by at most one
   centimetre. For scale, a genuinely room-dependent sector (+180..-165)
   ranged over 3.86 m across the same five headings. Second signature:
   in every masked sector hits% == close% exactly -- every beam that
   returns anything returns something under 1 m, i.e. nothing gets past.

   -90 deg is dead astern in this robot's frame (+X right, +Y forward, so
   -Y rear), which matches the physical rear stack exactly.

   THE SECTOR IS 90 DEG, NOT THE ~120 DEG ("about a third of the sweep")
   recorded in section 17.8. That earlier figure was measured in the
   pre-mirror-fix frame and was an estimate from block placement; this is a
   direct numeric measurement in the corrected frame. 90 deg -- a quarter --
   supersedes it.

   Masked beams are set to NaN, not to zero and not to inf, and the
   distinction matters:
     - a finite value would MARK a phantom obstacle (the bug)
     - inf reads as "nothing out to max range" and would CLEAR through
       whatever is really back there, which is worse than the bug
     - NaN is dropped by laser_geometry's projection, so the beam
       contributes nothing at all: it neither marks nor clears, which is
       the honest representation of "this sensor cannot see here."

   Nothing real is lost. Every valid return inside the arc was the mast
   itself (that is what hits% == close% means); beams that clear the mast
   simply never come back. The arc contained no room data to discard.

4. QUALITY GATE (added 14 Sep 2026, section 17.51). Three filters that
   decide whether a beam is published at all. All three default to OFF, so
   a freshly-deployed copy of this file behaves EXACTLY like the version
   before them.

   WHY THIS EXISTS. §17.45 measured the sensor, not the algorithm, as this
   project's binding constraint: with the robot STATIONARY, 47.4% of beams
   were valid at all and 74.8-78% of the beams that ever returned flipped
   valid/invalid across the capture. slam_toolbox is then being handed a
   materially different point cloud every sweep, which is a sufficient
   explanation for §17.44 (correction total invariant to 2% across three
   parameter sets — the matcher could not tell the parameter sets apart
   because the input noise dominated all three).

   The three filters, in the order they are applied:

   RANGE FLOOR / RANGE CAP. Blank anything outside [floor, cap]. This is
   the consumer-side range policy that system/ydlidar_params.yaml's RANGE
   block explicitly reserves ("Cap policy at the consumer. Never edit the
   spec sheet to record a decision."). The driver keeps telling the truth
   about what the X4 Pro can do; this decides what the robot is willing to
   believe. Set cap to 5.0 and slam_toolbox's max_laser_range never sees a
   return it would have thrown away.

   PERSISTENCE GATE. A beam is published only if it returned a valid range
   in at least K of the last N sweeps. This is aimed squarely at the
   flicker number and it is deliberately a VALIDITY gate, never a range
   filter: it decides whether to publish a beam, and if it publishes one it
   publishes that sweep's own instantaneous value, unaveraged and
   uncarried. So it CANNOT smear geometry the way a temporal median would,
   and the worst thing it can do to a moving robot is admit a genuinely new
   surface K sweeps late.

   Cost, stated so it can be argued with rather than assumed away: at the
   measured 11.35 Hz, K=2 costs one sweep of admission latency, ~88 ms. At
   the 0.08 m/s Nav2 cap that is 7 mm of travel, against a 50 mm costmap
   cell. At K=3 it is ~176 ms and 14 mm. Beyond about K=4 the latency stops
   being free and the gate should be argued for on measured map quality,
   not assumed.

   ⚠ A gate is not free in the other direction either. Every beam it drops
   is a beam that no longer CLEARS a cell, so an over-tight gate leaves
   stale obstacles standing in the costmap. Watch cut_persist in the stats
   topic: if it is cutting a large fraction of otherwise-valid beams, the
   gate is too tight, and the honest fix is a better mount or a better
   sensor rather than a tighter filter.

PARAMETERS
----------
   mirror         (bool,   default True)   negate the scan angle
   yaw_offset_deg (double, default 270.0)  rotation applied after the mirror
   mask_enabled   (bool,   default True)   blank the self-occluded arc
   mask_min_deg   (double, default -135.0) arc start, OUTPUT frame
   mask_max_deg   (double, default  -45.0) arc end, OUTPUT frame
   range_cap_m    (double, default 0.0)    blank returns beyond; 0 = off
   range_floor_m  (double, default 0.0)    blank returns below;  0 = off
   persist_n      (int,    default 1)      sweeps in the window; 1 = off
   persist_k      (int,    default 1)      valid sweeps required to publish
   stats_enabled  (bool,   default True)   publish /scan_relay_stats

   EVERY ONE of these is live-settable (`ros2 param set`, or the dashboard's
   LIDAR panel) and takes effect on the next sweep. That is new as of
   §17.51; before it, the values were read once at construction and a
   restart was the only way to change one. The dashboard tuner is the whole
   reason: tuning a filter you cannot see the effect of is guesswork, and
   tuning one that needs a node restart per trial is guesswork you only get
   to do a few times an hour.

   Physical angle recovered as:  true = mirror_sign * reported + yaw_offset

   Mask bounds are in the CORRECTED (published) frame -- the same frame
   tools/scan_bearing.py reports against when reading /scan_reliable, so a
   re-measurement can be typed straight in without re-deriving anything.
   The arc runs counter-clockwise from mask_min_deg to mask_max_deg and may
   wrap through +/-180.

   Set `mirror:=false yaw_offset_deg:=0.0 mask_enabled:=false` for a
   pass-through relay, which reproduces this file's original behaviour
   exactly.

   These are parameters rather than hard-coded constants because the values
   describe THIS mounting of THIS sensor on THIS chassis. Re-mount the
   LiDAR, or change what is bolted to the frame around it, and they must be
   re-measured (tools/scan_bearing.py), not assumed to carry over.

Run directly -- it is a plain script, no colcon build needed:

    python3 scan_relay.py
    python3 scan_relay.py --ros-args -p mirror:=false -p yaw_offset_deg:=0.0
"""

import math
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64MultiArray


class ScanRelay(Node):

    def __init__(self):
        super().__init__('scan_relay')

        self.declare_parameter('mirror', True)
        self.declare_parameter('yaw_offset_deg', 270.0)
        self.declare_parameter('mask_enabled', True)
        self.declare_parameter('mask_min_deg', -135.0)
        self.declare_parameter('mask_max_deg', -45.0)
        self.declare_parameter('range_cap_m', 0.0)
        self.declare_parameter('range_floor_m', 0.0)
        self.declare_parameter('persist_n', 1)
        self.declare_parameter('persist_k', 1)
        self.declare_parameter('stats_enabled', True)
        self.mirror = self.get_parameter('mirror').value
        self.yaw_offset = math.radians(
            self.get_parameter('yaw_offset_deg').value)
        self.mask_enabled = self.get_parameter('mask_enabled').value
        self.mask_min_deg = self.get_parameter('mask_min_deg').value
        self.mask_max_deg = self.get_parameter('mask_max_deg').value
        self.range_cap = float(self.get_parameter('range_cap_m').value)
        self.range_floor = float(self.get_parameter('range_floor_m').value)
        self.persist_n = int(self.get_parameter('persist_n').value)
        self.persist_k = int(self.get_parameter('persist_k').value)
        self.stats_enabled = bool(self.get_parameter('stats_enabled').value)

        self._recompute_modes()

        be = QoSProfile(depth=10,
                        reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10,
                         reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, '/scan_reliable', rel)
        self.sub = self.create_subscription(LaserScan, '/scan', self.cb, be)
        self.stats_pub = self.create_publisher(
            Float64MultiArray, '/scan_relay_stats', rel)

        # Index map and mask are rebuilt only when the scan's geometry
        # changes, so the per-message cost is a list comprehension, not
        # trigonometry.
        self._map = None
        self._mask = None
        self._map_key = None

        # Rolling validity history for the persistence gate: one bool list
        # per past sweep, newest last. Cleared whenever the beam count
        # changes, because index i stops meaning the same bearing.
        self._hist = deque(maxlen=max(1, self.persist_n))

        # Stats are throttled rather than sent per sweep. The dashboard
        # redraws at 5 Hz and the scan arrives at ~11.35 Hz, so publishing
        # every sweep would be two thirds waste.
        self._stats_every = 3
        self._stats_tick = 0

        # Parameters were read once, at construction, until §17.51. Now a
        # set from `ros2 param set` or the dashboard's LIDAR panel lands on
        # the next sweep. Registered AFTER the declares above so the
        # declares themselves do not fire it.
        self.add_on_set_parameters_callback(self._on_set_parameters)

        self.get_logger().info(
            'scan_relay up: /scan (best_effort) -> /scan_reliable (reliable); '
            f'mirror={self.mirror}, yaw_offset='
            f'{math.degrees(self.yaw_offset):.1f} deg')
        if self.mask_enabled:
            self.get_logger().info(
                f'  self-occlusion mask ON: {self.mask_min_deg:.1f} to '
                f'{self.mask_max_deg:.1f} deg blanked to NaN (rear mast, '
                'section 17.15)')
        else:
            self.get_logger().warn(
                '  self-occlusion mask OFF -- the rear mast will read as a '
                'phantom obstacle ~0.13 m behind the robot')
        if self._passthrough:
            self.get_logger().info('  (pass-through: no correction, no mask)')
        if self._gates_anything():
            self.get_logger().info(f'  quality gate ON: {self.gate_summary()}')

    # ── Configuration ─────────────────────────────────────────────────

    def _recompute_modes(self):
        """Derive the cached mode flags from the current parameter values.

        Called from __init__ and again after every accepted parameter set.
        Kept as one function rather than inlined twice so the live path and
        the startup path can never disagree about what 'pass-through'
        means — which they did, briefly, in the first draft of the live
        callback, with the result that setting a range cap on a
        pass-through relay was silently ignored.
        """
        self._corrects_angle = self.mirror or abs(self.yaw_offset) > 1e-9
        self._passthrough = (not self._corrects_angle
                             and not self.mask_enabled
                             and not self._gates_anything())

    def _gates_anything(self) -> bool:
        """True if any of the three quality filters would drop a beam."""
        return (self.range_cap > 0.0
                or self.range_floor > 0.0
                or (self.persist_n > 1 and self.persist_k > 1))

    def gate_summary(self) -> str:
        """One line describing the active filters, for logs and the UI."""
        bits = []
        if self.range_floor > 0.0:
            bits.append(f'floor {self.range_floor:.2f} m')
        if self.range_cap > 0.0:
            bits.append(f'cap {self.range_cap:.2f} m')
        if self.persist_n > 1 and self.persist_k > 1:
            bits.append(f'persist {self.persist_k}/{self.persist_n}')
        return ', '.join(bits) if bits else 'none'

    def _on_set_parameters(self, params):
        """Validate and apply a live parameter change.

        Rejecting is the point. rclpy applies every parameter in the batch
        if this returns successful=True, so a value that would make the
        node nonsense has to be refused HERE — there is no second chance
        further down, and a relay that silently accepted persist_k > n
        would gate every beam to NaN and look exactly like a dead LiDAR.

        Two-pass on purpose: validate the whole batch into a staging dict
        first, and only commit if every member passed. A half-applied batch
        (cap accepted, floor rejected) is a configuration nobody asked for.
        """
        staged = {}
        for p in params:
            name, v = p.name, p.value
            if name in ('range_cap_m', 'range_floor_m'):
                if v is None or float(v) < 0.0:
                    return SetParametersResult(
                        successful=False,
                        reason=f'{name} must be >= 0 (0 disables it)')
                staged[name] = float(v)
            elif name in ('persist_n', 'persist_k'):
                if v is None or int(v) < 1:
                    return SetParametersResult(
                        successful=False,
                        reason=f'{name} must be >= 1 (1 disables the gate)')
                staged[name] = int(v)
            elif name in ('mirror', 'mask_enabled', 'stats_enabled'):
                staged[name] = bool(v)
            elif name in ('yaw_offset_deg', 'mask_min_deg', 'mask_max_deg'):
                staged[name] = float(v)

        n = staged.get('persist_n', self.persist_n)
        k = staged.get('persist_k', self.persist_k)
        if k > n:
            return SetParametersResult(
                successful=False,
                reason=f'persist_k ({k}) cannot exceed persist_n ({n}) — '
                       'that gate can never pass a beam')

        floor = staged.get('range_floor_m', self.range_floor)
        cap = staged.get('range_cap_m', self.range_cap)
        if cap > 0.0 and floor > 0.0 and floor >= cap:
            return SetParametersResult(
                successful=False,
                reason=f'range_floor_m ({floor}) >= range_cap_m ({cap}) — '
                       'that window is empty')

        # Committed from here down; nothing below can fail.
        geometry_changed = False
        for name, v in staged.items():
            if name == 'mirror':
                self.mirror = v
                geometry_changed = True
            elif name == 'yaw_offset_deg':
                self.yaw_offset = math.radians(v)
                geometry_changed = True
            elif name == 'mask_enabled':
                self.mask_enabled = v
                geometry_changed = True
            elif name == 'mask_min_deg':
                self.mask_min_deg = v
                geometry_changed = True
            elif name == 'mask_max_deg':
                self.mask_max_deg = v
                geometry_changed = True
            elif name == 'range_cap_m':
                self.range_cap = v
            elif name == 'range_floor_m':
                self.range_floor = v
            elif name == 'persist_n':
                self.persist_n = v
            elif name == 'persist_k':
                self.persist_k = v
            elif name == 'stats_enabled':
                self.stats_enabled = v

        self._recompute_modes()

        if 'persist_n' in staged:
            # A shorter window must forget the sweeps it can no longer
            # hold, and a longer one must not inherit a stale run of
            # history from a different beam count. Rebuilding is cheaper
            # than reasoning about either.
            self._hist = deque(maxlen=max(1, self.persist_n))

        if geometry_changed:
            # Forces _build_map/_build_mask on the next sweep. Without
            # this, a live mirror or mask change would be accepted,
            # reported as applied, and then never actually take effect —
            # the cached map only rebuilds when the scan's own geometry
            # changes, and the scan's geometry did not change.
            self._map_key = None
            self._hist.clear()

        self.get_logger().info(
            'params updated: '
            + ', '.join(f'{k2}={v2}' for k2, v2 in sorted(staged.items()))
            + f'  | gate: {self.gate_summary()}')
        return SetParametersResult(successful=True)

    def _build_map(self, msg):
        """Output bin j takes its reading from input bin _map[j].

        Output bin j is meant to represent physical angle
            theta_out = angle_min + j * angle_increment
        The reading that actually corresponds to that direction sits at the
        reported angle theta_in satisfying
            theta_out = sign * theta_in + yaw_offset
        so
            theta_in = (theta_out - yaw_offset) / sign

        The modulo wrap below assumes the scan spans a full revolution, which
        holds for the X4 Pro (360 deg). On a partial-arc sensor the wrap would
        fold one end of the arc onto the other, so this would need bounds
        checks and an out-of-arc fill instead.
        """
        n = len(msg.ranges)
        if n == 0 or msg.angle_increment == 0.0:
            return None
        if not self._corrects_angle:
            return list(range(n))       # identity: mask-only configuration
        sign = -1.0 if self.mirror else 1.0
        idx = []
        for j in range(n):
            theta_out = msg.angle_min + j * msg.angle_increment
            theta_in = (theta_out - self.yaw_offset) / sign
            i = int(round((theta_in - msg.angle_min) / msg.angle_increment))
            idx.append(i % n)
        return idx

    def _build_mask(self, msg):
        """Which OUTPUT bins fall inside the self-occluded arc.

        Bounds are in the corrected/published frame, so this is applied
        after the index remap, against each output bin's own angle.

        The arc runs counter-clockwise from mask_min_deg to mask_max_deg.
        Testing `(a - lo) mod 360 <= (hi - lo) mod 360` rather than a plain
        `lo <= a <= hi` keeps that correct when the arc wraps through
        +/-180 -- not the case for the measured rear sector, but a
        re-measured mount could straddle the wrap and this should not
        silently invert if it does.
        """
        n = len(msg.ranges)
        if n == 0 or msg.angle_increment == 0.0:
            return None
        span = (self.mask_max_deg - self.mask_min_deg) % 360.0
        flags = []
        for j in range(n):
            deg = math.degrees(msg.angle_min + j * msg.angle_increment)
            flags.append(((deg - self.mask_min_deg) % 360.0) <= span)
        return flags

    def _apply_gate(self, ranges, msg):
        """Blank beams the quality filters reject. Returns (ranges, stats).

        Operates on the OUTPUT frame, after the index remap and the
        self-occlusion mask, so every bearing here means what the published
        scan says it means and a re-measurement can be typed straight in.

        Range values are never modified — only replaced wholesale with NaN.
        Nothing in here averages, interpolates, or carries a value forward
        from a previous sweep, which is what keeps the gate safe on a
        moving robot: the published geometry is always this sweep's own.
        """
        nan = float('nan')
        rmin, rmax = msg.range_min, msg.range_max
        n = len(ranges)

        # A beam is a candidate if the sensor returned something usable for
        # it at all. NaN here is the self-occlusion mask, which is
        # structural blindness rather than sensor performance and must stay
        # out of every denominator (§17.45 got this wrong once and every
        # percentage came out deflated).
        live = [r == r and rmin <= r <= rmax for r in ranges]
        n_live = sum(live)

        cut_range = 0
        if self.range_floor > 0.0 or self.range_cap > 0.0:
            floor = self.range_floor
            cap = self.range_cap if self.range_cap > 0.0 else float('inf')
            out = []
            for r, ok in zip(ranges, live):
                if ok and (r < floor or r > cap):
                    out.append(nan)
                    cut_range += 1
                else:
                    out.append(r)
            ranges = out
            live = [r == r and rmin <= r <= rmax for r in ranges]

        cut_persist = 0
        if self.persist_n > 1 and self.persist_k > 1:
            # History is per-beam-index, so a change in beam count
            # invalidates all of it: index 200 is a different bearing at
            # 430 beams than at 500.
            if self._hist and len(self._hist[0]) != n:
                self._hist.clear()
            self._hist.append(live)
            if len(self._hist) >= self.persist_k:
                counts = [0] * n
                for past in self._hist:
                    for i, ok in enumerate(past):
                        if ok:
                            counts[i] += 1
                out = []
                for i, r in enumerate(ranges):
                    if live[i] and counts[i] < self.persist_k:
                        out.append(nan)
                        cut_persist += 1
                    else:
                        out.append(r)
                ranges = out
            # Before the window has filled to K sweeps the gate cannot
            # have an opinion yet, so it passes everything rather than
            # blanking the first K sweeps after every restart — which
            # would look exactly like a LiDAR that takes a second to wake
            # up, and would be a lie.

        published = sum(1 for r in ranges if r == r and rmin <= r <= rmax)
        return ranges, (n, n_live, published, cut_range, cut_persist)

    def _publish_stats(self, stats):
        """Push the gate's own accounting out for the dashboard to read.

        The dashboard can already count valid beams on /scan_reliable, but
        it cannot tell WHY a beam is missing — sensor no-return, range
        policy, or persistence gate all look identical downstream. Only
        this node knows, so only this node can say, and a tuner that cannot
        show which knob did what is a tuner you tune by superstition.
        """
        n, n_live, published, cut_range, cut_persist = stats
        m = Float64MultiArray()
        m.data = [
            float(n),               # 0 beams in the sweep
            float(n_live),          # 1 beams the sensor returned usably
            float(published),       # 2 beams that survived the gate
            float(cut_range),       # 3 dropped by floor/cap
            float(cut_persist),     # 4 dropped by the persistence gate
            float(self.range_floor),
            float(self.range_cap),
            float(self.persist_k),
            float(self.persist_n),
            1.0 if self.mask_enabled else 0.0,
            float(self.mask_min_deg),
            float(self.mask_max_deg),
        ]
        self.stats_pub.publish(m)

    def cb(self, msg):
        if self._passthrough:
            self.pub.publish(msg)
            return

        key = (len(msg.ranges), msg.angle_min, msg.angle_increment)
        if key != self._map_key:
            self._map = self._build_map(msg)
            self._mask = self._build_mask(msg) if self.mask_enabled else None
            self._map_key = key
            self._hist.clear()
            if self._map is not None:
                blanked = sum(self._mask) if self._mask else 0
                self.get_logger().info(
                    f'angle correction map rebuilt for {len(msg.ranges)} '
                    f'beams; {blanked} masked as self-occluded')

        if self._map is None:
            self.pub.publish(msg)
            return

        ranges = [msg.ranges[i] for i in self._map]
        if self._mask is not None:
            nan = float('nan')
            ranges = [nan if m else r for r, m in zip(ranges, self._mask)]

        stats = None
        if self._gates_anything():
            ranges, stats = self._apply_gate(ranges, msg)
        elif self.stats_enabled:
            rmin, rmax = msg.range_min, msg.range_max
            live = sum(1 for r in ranges if r == r and rmin <= r <= rmax)
            stats = (len(ranges), live, live, 0, 0)

        if stats is not None and self.stats_enabled:
            self._stats_tick += 1
            if self._stats_tick >= self._stats_every:
                self._stats_tick = 0
                self._publish_stats(stats)

        out = LaserScan()
        out.header = msg.header
        out.angle_min = msg.angle_min
        out.angle_max = msg.angle_max
        out.angle_increment = msg.angle_increment
        out.time_increment = msg.time_increment
        out.scan_time = msg.scan_time
        out.range_min = msg.range_min
        out.range_max = msg.range_max
        out.ranges = ranges
        if msg.intensities:
            # Intensities are remapped but deliberately NOT masked: a NaN
            # range already invalidates the beam everywhere it matters, and
            # leaving intensity intact keeps the two arrays the same length
            # and the raw signal inspectable if the mask is ever re-examined.
            out.intensities = [msg.intensities[i] for i in self._map]
        self.pub.publish(out)


def main():
    rclpy.init()
    node = ScanRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
