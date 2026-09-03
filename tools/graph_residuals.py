#!/usr/bin/env python3
"""graph_residuals.py — watch slam_toolbox's pose graph correct itself.

MATLAB_Navigation_Reference.md Tier 1 #2. §17.29 proved this slam_toolbox
build has zero observable per-closure signal — no console line, no topic, no
service — so "was that a good closure?" cannot be answered by watching for
the event. MATLAB's `trimLoopClosures` does not watch either: it computes
`edgeResidualErrors` across the *solved* graph and flags statistical
outliers. That sidesteps the missing signal, and the graph is already on the
wire.

    ./tools/graph_residuals.py --watch               # during the drive
    ./tools/graph_residuals.py --watch --log g.jsonl # ... and record it
    ./tools/graph_residuals.py                       # one snapshot
    ./tools/graph_residuals.py --save g.json         # capture for later
    ./tools/graph_residuals.py --load g.json         # analyse, no ROS
    ./tools/graph_residuals.py --selftest

═══════════════════════════════════════════════════════════════════════════
  WHAT THE TOPIC CARRIES — read this before believing a number
═══════════════════════════════════════════════════════════════════════════

Verified against slam_toolbox's own source (`loop_closure_assistant.cpp`,
`publishGraph()`), not assumed:

  PUBLISHED   node id -> solved (x, y), SPHERE markers in ns "slam_toolbox",
              one per vertex, at GetCorrectedPose()
              edges, as two LINE_LIST markers in ns "slam_toolbox_edges",
              whose `points` are pairs of solved endpoint COORDINATES
              republished every `map_update_interval` (1.0 s here)

  NOT PUBLISHED
              node ORIENTATION — toMarker() hardcodes orientation.w = 1
              edge node IDs — the line list carries geometry, not topology
              the edge MEASUREMENT — the relative transform the scan matcher
              computed, which is what a true residual is measured against
              the information matrix

A true SE(2) chi-squared residual is therefore **not computable from this
topic**. Anyone claiming otherwise has not read the publisher.

═══════════════════════════════════════════════════════════════════════════
  WHAT IS COMPUTABLE, AND WHY IT IS BETTER THAN A SNAPSHOT RESIDUAL
═══════════════════════════════════════════════════════════════════════════

The graph is republished every second, so successive messages can be
differenced. **A node that moves between two publications was moved by the
optimiser.** That is a correction, observed directly.

This is Stage A's method — §17.32 caught a 39.57 cm map->odom jump by
differencing TF — but at per-node resolution instead of one aggregate
transform, and with the cause attached: comparing edge sets across the same
two messages says **which edge appeared in the update that moved things**.
A closure that arrives in the same update as a 40 cm shift is that shift's
cause. That is the per-closure signal §17.29 concluded did not exist. It
does not exist as an *event*; it exists as a *difference*.

And the difference can be judged, which a raw jump size cannot:

    implied drift rate = how far the graph moved
                         -------------------------------------
                         metres driven since the closed-on node

A legitimate closure cancels drift accumulated since the robot was last at
that spot, so its implied rate should sit near this robot's measured
odometry error — 1.5% over the 3.4 m box drive (§17.32), 2.4% on 0.5 m
forward/back, 3.3% lateral (§17.30). A closure implying 20% either corrected
drift that never accumulated or the robot slipped badly, and the first is a
false match. The default ceiling is 10%: three to four times the worst
measured rate, so it fires on the pathological case and not on a bad day.

That threshold is the one judgement call in here and it is a parameter
(`--max-drift-rate`). Everything else is measured.

A single snapshot cannot do any of this — it has nothing to difference
against — so snapshot mode reports structure only and says so.
"""
import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

# Defaults mirror system/slam_nodom_stageB.yaml.
MIN_TRAVEL_M = 0.2
LOOP_SEARCH_MAX_M = 2.0
CHAIN_SIZE = 8
Z_OUTLIER = 3.5             # Iglewicz-Hoaglin modified z-score cut
MOVE_THRESH_M = 0.02        # below this a node "moved" only numerically
MAX_DRIFT_RATE = 0.10       # see header; 3-4x this robot's measured worst
TOPIC = '/slam_toolbox/graph_visualization'

NODE_NS = 'slam_toolbox'
EDGE_NS = 'slam_toolbox_edges'
DELETEALL = 3
LINE_LIST = 5


# ═════════════════════════════════════════════════════════════════════════
#  MarkerArray -> graph
# ═════════════════════════════════════════════════════════════════════════
def graph_from_markers(markers):
    """markers: dicts with ns, id, type, action, pose, points.

    Dict-shaped rather than taking the ROS message directly, so the same code
    runs on a saved capture and in --selftest with no ROS installed.
    """
    nodes, seg = {}, []
    for m in markers:
        if m.get('action') == DELETEALL:
            continue
        ns = m.get('ns', '')
        if ns == NODE_NS:
            nodes[int(m['id'])] = (m['pose'][0], m['pose'][1])
        elif ns == EDGE_NS and m.get('type') == LINE_LIST:
            pts = m.get('points') or []
            for k in range(0, len(pts) - 1, 2):
                seg.append((tuple(pts[k]), tuple(pts[k + 1])))
    return nodes, seg


def resolve_edges(nodes, segments, tol=1e-3):
    """Turn endpoint coordinates back into node-id pairs.

    Exact first, because both sides are the same doubles from the same
    message. The tolerant pass exists only so a float that took a different
    route does not silently drop an edge, and anything it cannot place is
    counted and reported rather than quietly discarded — a mis-matched
    endpoint would invent an edge that was never in the graph.
    """
    exact = {}
    for i, (x, y) in nodes.items():
        exact.setdefault((round(x, 9), round(y, 9)), []).append(i)
    dupes = sum(len(v) - 1 for v in exact.values())

    cell = max(tol * 10, 1e-2)
    buckets = {}
    for i, (x, y) in nodes.items():
        buckets.setdefault((int(x // cell), int(y // cell)), []).append(i)

    def find(p):
        hit = exact.get((round(p[0], 9), round(p[1], 9)))
        if hit:
            return hit[0]
        bx, by = int(p[0] // cell), int(p[1] // cell)
        best, bd = None, tol
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in buckets.get((bx + dx, by + dy), ()):
                    d = math.dist(nodes[i], p)
                    if d <= bd:
                        best, bd = i, d
        return best

    edges, unresolved = set(), 0
    for p0, p1 in segments:
        a, b = find(p0), find(p1)
        if a is None or b is None or a == b:
            unresolved += 1
            continue
        edges.add((min(a, b), max(a, b)))
    return sorted(edges), unresolved, dupes


def robust_z(values):
    """Modified z-score: (x - median) / (1.4826 * MAD).

    Median/MAD rather than mean/sd for the same reason trimLoopClosures uses
    a truncated loss — the outliers being hunted would otherwise inflate the
    spread they are measured against and hide inside it.
    """
    if len(values) < 3:
        return [0.0] * len(values)
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    if mad > 0:
        return [(v - med) / (1.4826 * mad) for v in values]
    sd = statistics.pstdev(values)
    return [(v - med) / sd for v in values] if sd > 0 else [0.0] * len(values)


# ═════════════════════════════════════════════════════════════════════════
#  Structure of one snapshot
# ═════════════════════════════════════════════════════════════════════════
def structural(nodes, edges, unresolved=0, dupes=0, p=None):
    p = p or {}
    min_travel = p.get('min_travel', MIN_TRAVEL_M)
    local_span = p.get('local_span', CHAIN_SIZE)
    zcut = p.get('z_cut', Z_OUTLIER)

    def L(e):
        return math.dist(nodes[e[0]], nodes[e[1]])

    seq = [e for e in edges if e[1] - e[0] == 1]
    local = [e for e in edges if 1 < e[1] - e[0] <= local_span]
    loops = [e for e in edges if e[1] - e[0] > local_span]

    out = {'nodes': len(nodes), 'edges': len(edges), 'sequential': len(seq),
           'local': len(local), 'loops': len(loops),
           'unresolved_endpoints': unresolved, 'coincident_nodes': dupes}
    if not seq:
        out['chain'] = None
        return out

    slen = [L(e) for e in seq]
    sz = robust_z(slen)
    # A chain edge is a ~20 cm step by construction (minimum_travel_distance),
    # so one that solved much longer is a link the optimiser stretched.
    # Requiring BOTH the statistical outlier and the physical implausibility
    # matters: on a slow uniform drive the MAD collapses and z alone fires on
    # millimetres.
    strained = sorted(
        ({'edge': list(e), 'len_m': round(l, 3), 'z': round(z, 1),
          'map_x': round((nodes[e[0]][0] + nodes[e[1]][0]) / 2, 2),
          'map_y': round((nodes[e[0]][1] + nodes[e[1]][1]) / 2, 2)}
         for e, l, z in zip(seq, slen, sz)
         if z > zcut and l > 2.0 * min_travel),
        key=lambda d: -d['len_m'])

    out['chain'] = {
        'median_m': round(statistics.median(slen), 3),
        'p95_m': round(sorted(slen)[min(len(slen) - 1, int(0.95 * len(slen)))], 3),
        'max_m': round(max(slen), 3),
        'total_m': round(sum(slen), 2),
        'strained': strained,
    }
    out['loop_edges'] = sorted(
        ({'edge': list(e), 'span': e[1] - e[0], 'direct_m': round(L(e), 3),
          'map_x': round((nodes[e[0]][0] + nodes[e[1]][0]) / 2, 2),
          'map_y': round((nodes[e[0]][1] + nodes[e[1]][1]) / 2, 2)}
         for e in loops), key=lambda r: -r['span'])
    return out


def chain_lengths(nodes, edges):
    """Metres per consecutive-node hop, for measuring distance driven."""
    return {a: math.dist(nodes[a], nodes[b])
            for a, b in edges if b - a == 1 and a in nodes and b in nodes}


# ═════════════════════════════════════════════════════════════════════════
#  The difference between two snapshots — where the real signal is
# ═════════════════════════════════════════════════════════════════════════
class Tracker:
    """Holds the previous graph and reports what the optimiser did to it."""

    def __init__(self, p=None):
        self.p = p or {}
        self.prev_nodes = None
        self.prev_edges = None
        self.t0 = time.time()

    def update(self, nodes, edges, unresolved=0, dupes=0):
        move_thresh = self.p.get('move_thresh', MOVE_THRESH_M)
        max_rate = self.p.get('max_drift_rate', MAX_DRIFT_RATE)
        local_span = self.p.get('local_span', CHAIN_SIZE)

        ev = structural(nodes, edges, unresolved, dupes, self.p)
        ev['t'] = round(time.time() - self.t0, 2)
        ev['first'] = self.prev_nodes is None

        if self.prev_nodes is None:
            ev.update({'new_nodes': len(nodes), 'moved': 0, 'max_shift_m': 0.0,
                       'new_loops': [], 'verdict': 'BASELINE', 'notes': []})
            self.prev_nodes, self.prev_edges = dict(nodes), set(edges)
            return ev

        shared = [i for i in nodes if i in self.prev_nodes]
        shifts = {i: math.dist(nodes[i], self.prev_nodes[i]) for i in shared}
        moved = {i: d for i, d in shifts.items() if d >= move_thresh}
        max_shift = max(shifts.values()) if shifts else 0.0

        new_edges = set(edges) - self.prev_edges
        new_loops = sorted(e for e in new_edges if e[1] - e[0] > local_span)
        clen = chain_lengths(nodes, edges)

        rows = []
        for a, b in new_loops:
            # Metres driven between the two nodes this closure links: the
            # distance over which drift had the chance to accumulate.
            driven = sum(clen.get(k, MIN_TRAVEL_M) for k in range(a, b))
            span_shift = max([shifts[i] for i in range(a, b + 1) if i in shifts],
                             default=0.0)
            rate = span_shift / driven if driven > 0 else None
            rows.append({
                'edge': [a, b], 'span': b - a,
                'driven_m': round(driven, 2),
                'shift_m': round(span_shift, 3),
                'implied_drift_rate': round(rate, 4) if rate is not None else None,
                'map_x': round((nodes[a][0] + nodes[b][0]) / 2, 2),
                'map_y': round((nodes[a][1] + nodes[b][1]) / 2, 2),
                'suspect': bool(rate is not None and rate > max_rate
                                and span_shift >= move_thresh),
            })

        ev.update({
            'new_nodes': len([i for i in nodes if i not in self.prev_nodes]),
            'moved': len(moved), 'max_shift_m': round(max_shift, 3),
            'shifted_nodes': sorted(
                ({'node': i, 'shift_m': round(d, 3),
                  'map_x': round(nodes[i][0], 2), 'map_y': round(nodes[i][1], 2)}
                 for i, d in moved.items()), key=lambda r: -r['shift_m'])[:10],
            'new_loops': rows,
        })

        notes = []
        suspect = [r for r in rows if r['suspect']]
        for r in suspect:
            notes.append(
                f"closure {r['edge'][0]}->{r['edge'][1]} moved the graph "
                f"{r['shift_m']} m over {r['driven_m']} m driven = "
                f"{r['implied_drift_rate']:.0%} implied drift, above the "
                f"{max_rate:.0%} ceiling")
        if moved and not rows:
            notes.append(f"{len(moved)} node(s) moved (max {max_shift:.3f} m) with no "
                         f"new loop edge — a local link or continued optimisation, "
                         f"not a closure")
        if unresolved:
            notes.append(f"{unresolved} edge endpoint(s) unmatched — topology is a "
                         f"lower bound this update")

        if suspect:
            ev['verdict'] = 'SUSPECT'
        elif rows and moved:
            ev['verdict'] = 'CLOSURE'
        elif moved:
            ev['verdict'] = 'SHIFT'
        else:
            ev['verdict'] = 'QUIET'
        ev['notes'] = notes

        self.prev_nodes, self.prev_edges = dict(nodes), set(edges)
        return ev


# ═════════════════════════════════════════════════════════════════════════
#  Reporting
# ═════════════════════════════════════════════════════════════════════════
def watch_line(ev):
    c = ev.get('chain') or {}
    tag = {'BASELINE': '.', 'QUIET': ' ', 'SHIFT': '~',
           'CLOSURE': '+', 'SUSPECT': '!'}.get(ev['verdict'], '?')
    s = (f"{tag} t={ev['t']:7.1f}s {ev['verdict']:<8} "
         f"n={ev['nodes']:<4} e={ev['edges']:<4} "
         f"driven={c.get('total_m', 0):6.2f}m "
         f"moved={ev.get('moved', 0):<3} max_shift={ev.get('max_shift_m', 0):.3f}m "
         f"loops={ev.get('loops', 0)}")
    for r in ev.get('new_loops', []):
        s += (f"\n    -> closure {r['edge'][0]}->{r['edge'][1]}  "
              f"shift {r['shift_m']} m over {r['driven_m']} m driven  "
              f"= {r['implied_drift_rate']:.1%} implied drift"
              f"{'   SUSPECT' if r['suspect'] else ''}"
              f"   at map ({r['map_x']}, {r['map_y']})")
    return s


def print_report(a, snapshot_only):
    print(f"\n{'=' * 70}\n  pose graph\n{'=' * 70}")
    print(f"  {a['nodes']} nodes, {a['edges']} edges "
          f"({a['sequential']} chain, {a['local']} local, {a['loops']} loop)")
    c = a.get('chain')
    if not c:
        print('\n  No sequential edges — the graph is empty or too young to read.')
        return
    print(f"  chain edges   median {c['median_m']} m, p95 {c['p95_m']} m, "
          f"max {c['max_m']} m, {c['total_m']} m driven")
    if c['strained']:
        print('\n  STRAINED CHAIN EDGES — a step that solved much longer than the')
        print('  20 cm it was created at, i.e. a link the optimiser pulled:')
        for s in c['strained'][:8]:
            print(f"    node {s['edge'][0]:>4}->{s['edge'][1]:<4} {s['len_m']:>6.3f} m  "
                  f"z={s['z']:>5.1f}   at map ({s['map_x']}, {s['map_y']})")
    if a.get('loop_edges'):
        print(f"\n  LOOP EDGES, longest span first:")
        for r in a['loop_edges'][:10]:
            print(f"    {r['edge'][0]:>5}->{r['edge'][1]:<5} span {r['span']:>4}  "
                  f"endpoints {r['direct_m']:>6.2f} m apart   "
                  f"at map ({r['map_x']}, {r['map_y']})")
    if a.get('unresolved_endpoints'):
        print(f"\n  note: {a['unresolved_endpoints']} edge endpoint(s) unmatched")
    if snapshot_only:
        print('\n  This is one snapshot, so it can only describe the graph as it')
        print('  stands. Whether a correction was legitimate needs two snapshots')
        print('  to difference — run --watch during the drive. Cross-check the')
        print('  strained locations against map_integrity.py: a false closure')
        print('  puts a doubled wall where it strained the chain.')


# ═════════════════════════════════════════════════════════════════════════
#  Live
# ═════════════════════════════════════════════════════════════════════════
def marker_to_dict(m):
    return {'ns': m.ns, 'id': m.id, 'type': m.type, 'action': m.action,
            'pose': [m.pose.position.x, m.pose.position.y],
            'points': [[p.x, p.y] for p in m.points]}


def run_live(args):
    try:
        import rclpy
        from rclpy.node import Node
        from visualization_msgs.msg import MarkerArray
    except ImportError as exc:
        sys.exit(f'{exc}\n\nLive mode needs a sourced ROS 2 environment:\n'
                 '  source /opt/ros/jazzy/setup.bash\n'
                 'To analyse without ROS, use --load on a file made by --save.')

    state = {'markers': None}
    tracker = Tracker(vars(args))
    log = open(args.log, 'a') if args.log else None

    class Sub(Node):
        def __init__(self):
            super().__init__('graph_residuals')
            self.create_subscription(MarkerArray, args.topic, self.cb, 1)

        def cb(self, msg):
            ms = [marker_to_dict(m) for m in msg.markers]
            state['markers'] = ms
            if not args.watch:
                return
            nodes, seg = graph_from_markers(ms)
            if not nodes:
                print('no node markers — is enable_interactive_mode true?',
                      flush=True)
                return
            edges, unres, dup = resolve_edges(nodes, seg)
            ev = tracker.update(nodes, edges, unres, dup)
            if not (args.only_events and ev['verdict'] in ('QUIET', 'BASELINE')):
                print(watch_line(ev), flush=True)
            if log:
                log.write(json.dumps(ev) + '\n')
                log.flush()

    rclpy.init()
    node = Sub()
    print(f'subscribed to {args.topic}')
    print('slam_toolbox republishes the graph every map_update_interval '
          '(1.0 s in slam_nodom_stageB.yaml)')
    if args.watch:
        print('legend:  . baseline   (blank) quiet   ~ shift   '
              '+ closure   ! suspect closure')
        print('Ctrl-C to stop\n')
    try:
        deadline = time.time() + args.timeout
        while rclpy.ok() and (args.watch or state['markers'] is None):
            rclpy.spin_once(node, timeout_sec=0.5)
            if not args.watch and time.time() > deadline:
                break
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        node.destroy_node()
        # Close the log BEFORE touching rclpy. On Ctrl-C rclpy's own signal
        # handler has already shut the context down, so rclpy.shutdown()
        # raises RCLError('rcl_shutdown already called') — and with the close
        # sequenced after it, that exception skipped log.close() entirely.
        # Every record survived only because the writer flushes per line.
        # Found on the tool's first live run against the node, 27 Aug 2026.
        if log:
            log.close()
        try:
            rclpy.shutdown()
        except Exception:
            pass

    if state['markers'] is None:
        sys.exit(f'\nno message on {args.topic} in {args.timeout} s.\n'
                 'Is slam_toolbox running, and has mapping actually started?')
    return state['markers']


# ═════════════════════════════════════════════════════════════════════════
#  Self-test
# ═════════════════════════════════════════════════════════════════════════
def _markers(nodes, edges):
    """The message shape slam_toolbox actually publishes — including the part
    that makes this hard: edges carry coordinates, not node ids."""
    ms = [{'ns': '', 'id': 0, 'type': 2, 'action': DELETEALL,
           'pose': [0, 0], 'points': []}]
    for i, (x, y) in nodes.items():
        ms.append({'ns': NODE_NS, 'id': i, 'type': 2, 'action': 0,
                   'pose': [x, y], 'points': []})
    pts = []
    for a, b in edges:
        pts += [list(nodes[a]), list(nodes[b])]
    ms.append({'ns': EDGE_NS, 'id': 0, 'type': LINE_LIST, 'action': 0,
               'pose': [0, 0], 'points': pts})
    return ms


def _square(n, step):
    """n nodes walked round a square at `step` metres per node."""
    nodes, per, x, y = {}, max(n // 4, 1), 0.0, 0.0
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for i in range(n):
        nodes[i] = (x, y)
        dx, dy = dirs[(i // per) % 4]
        x, y = x + dx * step, y + dy * step
    return nodes


def _feed(tracker, nodes, edges):
    ms = _markers(nodes, edges)
    rn, seg = graph_from_markers(ms)
    re_, unres, dup = resolve_edges(rn, seg)
    assert set(re_) == {(min(a, b), max(a, b)) for a, b in edges}, \
        'topology not recovered from coordinates alone'
    return tracker.update(rn, re_, unres, dup), re_


def selftest(args):
    ok = True

    # ── 1. a legitimate closure: 8 m loop, 15 cm of accumulated drift
    #        cancelled. 0.15 / 8.0 = 1.9%, right at this robot's measured
    #        rate, so it must NOT be called suspect.
    # ── 2. a false closure: 3 m driven, the graph yanked 60 cm.
    #        0.60 / 3.0 = 20%, well past any drift this robot accumulates.
    for label, n, step, drift, want in (
            ('good closure', 40, 0.20, 0.15, 'CLOSURE'),
            ('false closure', 16, 0.20, 0.60, 'SUSPECT')):
        tr = Tracker(vars(args))
        nodes = _square(n, step)
        chain = [(i, i + 1) for i in range(n - 1)]
        ev, _ = _feed(tr, nodes, chain)
        if ev['verdict'] != 'BASELINE':
            print(f'  {label}: FAIL — first update should be BASELINE')
            ok = False

        # the optimiser closes the loop: the tail of the chain slides back by
        # `drift`, tapering to nothing at the start, and a closure edge appears
        after = dict(nodes)
        for i in range(n):
            f = i / (n - 1)
            after[i] = (nodes[i][0] - drift * f, nodes[i][1])
        ev, _ = _feed(tr, after, chain + [(0, n - 1)])

        driven = (n - 1) * step
        print(f"  {label:<14} {n} nodes, {driven:.1f} m driven, graph moved "
              f"{ev['max_shift_m']} m -> {ev['verdict']}")
        for r in ev['new_loops']:
            print(f"  {'':<14}   closure {r['edge']} shift {r['shift_m']} m over "
                  f"{r['driven_m']} m = {r['implied_drift_rate']:.1%} implied"
                  f"{'  SUSPECT' if r['suspect'] else ''}")
        if ev['verdict'] != want:
            print(f"  {'':<14}   FAIL: expected {want}")
            ok = False
        if len(ev['new_loops']) != 1:
            print(f"  {'':<14}   FAIL: the new closure edge was not identified")
            ok = False

    # ── 3. a quiet update must stay quiet: same graph twice running.
    tr = Tracker(vars(args))
    nodes = _square(20, 0.2)
    chain = [(i, i + 1) for i in range(19)]
    _feed(tr, nodes, chain)
    ev, _ = _feed(tr, nodes, chain)
    print(f"  {'quiet':<14} unchanged graph -> {ev['verdict']} "
          f"(moved {ev['moved']})")
    if ev['verdict'] != 'QUIET' or ev['moved']:
        print(f"  {'':<14}   FAIL: an unchanged graph must not report movement")
        ok = False

    # ── 4. structural: a stretched chain edge is found on a lone snapshot.
    nodes = _square(20, 0.2)
    for i in range(12, 20):
        nodes[i] = (nodes[i][0] + 0.6, nodes[i][1])
    chain = [(i, i + 1) for i in range(19)]
    ms = _markers(nodes, chain)
    rn, seg = graph_from_markers(ms)
    re_, unres, dup = resolve_edges(rn, seg)
    st = structural(rn, re_, unres, dup, vars(args))
    n_strained = len(st['chain']['strained'])
    print(f"  {'structural':<14} planted one stretched link -> "
          f"{n_strained} strained, chain median {st['chain']['median_m']} m")
    if n_strained != 1:
        print(f"  {'':<14}   FAIL: expected exactly one strained chain edge")
        ok = False

    print('\nselftest:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--topic', default=TOPIC)
    ap.add_argument('--watch', action='store_true',
                    help='difference every update — where the real signal is')
    ap.add_argument('--only-events', action='store_true',
                    help='with --watch, print only updates where something moved')
    ap.add_argument('--timeout', type=float, default=15.0)
    ap.add_argument('--save', help='write the captured MarkerArray as JSON')
    ap.add_argument('--load', help='analyse a saved capture, no ROS needed')
    ap.add_argument('--log', help='append per-update analyses as JSONL (--watch)')
    ap.add_argument('--json', help='write the analysis as JSON')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--min-travel', type=float, default=MIN_TRAVEL_M, dest='min_travel')
    ap.add_argument('--loop-search-max', type=float, default=LOOP_SEARCH_MAX_M,
                    dest='loop_search_max')
    ap.add_argument('--local-span', type=int, default=CHAIN_SIZE, dest='local_span')
    ap.add_argument('--z-cut', type=float, default=Z_OUTLIER, dest='z_cut')
    ap.add_argument('--move-thresh', type=float, default=MOVE_THRESH_M,
                    dest='move_thresh')
    ap.add_argument('--max-drift-rate', type=float, default=MAX_DRIFT_RATE,
                    dest='max_drift_rate',
                    help='implied-drift ceiling for a legitimate closure '
                         f'(default {MAX_DRIFT_RATE:.2f})')
    args = ap.parse_args()

    if args.selftest:
        return selftest(args)

    if args.load:
        markers = json.loads(Path(args.load).read_text())
    else:
        markers = run_live(args)
        if args.save:
            Path(args.save).write_text(json.dumps(markers))
            print(f'wrote {args.save}')
        if args.watch:
            return 0

    nodes, seg = graph_from_markers(markers)
    if not nodes:
        print('No node markers in this message. If edges are present but nodes')
        print('are not, enable_interactive_mode is true and slam_toolbox is')
        print('sending the nodes to an interactive-marker server instead.')
        return 1
    edges, unres, dup = resolve_edges(nodes, seg)
    a = structural(nodes, edges, unres, dup, vars(args))
    print_report(a, snapshot_only=True)
    if args.json:
        Path(args.json).write_text(json.dumps(a, indent=2))
        print(f'  wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
