#!/usr/bin/env python3
"""scan_relay_gate.py — does the LiDAR quality gate drop the beams it claims
to drop, and only those?

WHY THIS EXISTS. The gate decides what SLAM and the costmaps are allowed to
see. Every class of bug it can have is silent downstream:

  * too permissive -> nothing changes, and the tuner reads as a dead knob
    (§17.32's failure: a parameter that looks like a working control and is
    not one)
  * too aggressive -> beams that should CLEAR a cell are dropped, stale
    obstacles stand in the costmap, and the robot refuses a clear aisle
  * off-by-one in the persistence window -> the first K sweeps after every
    restart come back blank, which looks exactly like a LiDAR that takes a
    moment to wake up
  * a mask beam counted in a denominator -> every percentage the dashboard
    shows is deflated, which is the §17.45 mistake repeated in a new place

None of those raise. All of them would be discovered on the floor, mid-run,
by a robot behaving oddly.

    python3 tools/tests/scan_relay_gate.py      # from the repo root

Extracts _apply_gate, _gates_anything, gate_summary and _on_set_parameters
from the SHIPPED src/scan_relay/scan_relay.py with ast and drives them
against a stub, so there is no rclpy import, no ROS, no serial port, and no
second copy of the logic to drift out of step with the real one.
"""
import ast
import math
import sys
from collections import deque
from pathlib import Path

SRC = Path('src/scan_relay/scan_relay.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not SRC.exists():
    sys.exit(f'run me from the repo root; {SRC} not found')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
cls = next((n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == 'ScanRelay'), None)
if cls is None:
    sys.exit('class ScanRelay not found in scan_relay.py')

WANTED = ('_apply_gate', '_publish_stats', '_gates_anything', 'gate_summary',
          '_recompute_modes', '_on_set_parameters')
methods = {n.name: n for n in cls.body
           if isinstance(n, ast.FunctionDef) and n.name in WANTED}
missing = [w for w in WANTED if w not in methods]
if missing:
    sys.exit(f'method(s) not found in ScanRelay: {", ".join(missing)}')


class Result:
    """Stands in for rcl_interfaces.msg.SetParametersResult."""

    def __init__(self, successful=True, reason=''):
        self.successful = successful
        self.reason = reason


class Param:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Logger:
    def info(self, *a):
        pass

    def warn(self, *a):
        pass


class Msg:
    """The two LaserScan fields the gate reads."""

    def __init__(self, range_min=0.1, range_max=10.0):
        self.range_min = range_min
        self.range_max = range_max


ns = {'math': math, 'deque': deque, 'SetParametersResult': Result,
      'Float64MultiArray': lambda: type('M', (), {'data': []})()}
mod = ast.Module(body=[ast.ClassDef(
    name='Relay', bases=[], keywords=[],
    body=[methods[w] for w in WANTED], decorator_list=[])],
    type_ignores=[])
exec(compile(ast.fix_missing_locations(mod), str(SRC), 'exec'), ns)
Relay = ns['Relay']


def relay(cap=0.0, floor=0.0, k=1, n=1, mask=True, mirror=True, yaw=270.0):
    r = Relay()
    r.range_cap = cap
    r.range_floor = floor
    r.persist_k = k
    r.persist_n = n
    r.mask_enabled = mask
    r.mask_min_deg = -135.0
    r.mask_max_deg = -45.0
    r.mirror = mirror
    r.yaw_offset = math.radians(yaw)
    r.stats_enabled = True
    r._hist = deque(maxlen=max(1, n))
    r._map_key = 'unchanged'
    r.get_logger = lambda: Logger()
    r._recompute_modes()
    return r


NAN = float('nan')
MSG = Msg()

print('\nLiDAR quality gate — src/scan_relay/scan_relay.py\n')

# ── 1. OFF BY DEFAULT ────────────────────────────────────────────────
# The whole deployment argument for this change is that a fresh copy
# behaves identically to the version before it. If that is not true, the
# file cannot be dropped onto a working robot nine days before a seminar.
print('1. default configuration is a no-op')
r = relay()
chk(r._gates_anything() is False, 'no gate active with default parameters')
chk(r.gate_summary() == 'none', 'gate_summary() reads "none" when idle')
scan = [1.0, 2.0, NAN, 9.5, 0.05]
out, st = r._apply_gate(list(scan), MSG)
chk(all((a != a and b != b) or a == b for a, b in zip(scan, out)),
    'ranges pass through byte-identical when nothing is enabled')
chk(st[3] == 0 and st[4] == 0, 'nothing reported as cut')

# ── 2. RANGE CAP ─────────────────────────────────────────────────────
print('\n2. range cap — the 5 m policy, applied at the consumer')
r = relay(cap=5.0)
chk(r._gates_anything() is True, 'a cap counts as an active gate')
# 0.05 is below the sensor's own range_min, so it was never a live beam and
# the cap must not take credit for it.
out, st = r._apply_gate([1.0, 4.99, 5.01, 9.5, NAN, 0.05], MSG)
chk(out[0] == 1.0 and out[1] == 4.99, 'returns inside the cap survive')
chk(out[2] != out[2] and out[3] != out[3], 'returns beyond the cap go NaN')
chk(out[4] != out[4], 'the self-occlusion mask is left alone')
chk(st[3] == 2, 'exactly the two beyond-cap beams counted as cut')
chk(st[1] == 4, 'n_live counts only beams the SENSOR returned usably')
chk(st[2] == 2, 'published count reflects the cut')

print('\n3. range floor')
r = relay(floor=0.3)
out, st = r._apply_gate([0.15, 0.29, 0.30, 1.0], MSG)
chk(out[0] != out[0] and out[1] != out[1], 'returns below the floor go NaN')
chk(out[2] == 0.30 and out[3] == 1.0, 'the floor itself is inclusive')
chk(st[3] == 2, 'two beams counted as cut by range policy')

# ── 4. PERSISTENCE GATE ──────────────────────────────────────────────
print('\n4. persistence gate — 2 of 3')
r = relay(k=2, n=3)
chk(r._gates_anything() is True, 'a real persistence window is an active gate')
chk('persist 2/3' in r.gate_summary(), 'gate_summary() names the window')

# Sweep 1: window holds one sweep, below K, so the gate has no opinion yet
# and must not blank anything. Blanking here is the bug that would look
# like a LiDAR taking a second to wake up after every restart.
out, st = r._apply_gate([1.0, 2.0, 3.0], MSG)
chk(st[4] == 0 and all(v == v for v in out),
    'first sweep passes untouched — window not yet filled to K')

# Beam 0 steady, beam 1 flickering, beam 2 steady.
r = relay(k=2, n=3)
r._apply_gate([1.0, 2.0, 3.0], MSG)          # sweep 1: all valid
out, st = r._apply_gate([1.0, NAN, 3.0], MSG)  # sweep 2: beam 1 drops
chk(out[0] == 1.0 and out[2] == 3.0, 'steady beams survive the gate')
chk(st[4] == 0, 'a beam that is already absent is not "cut" by the gate')
out, st = r._apply_gate([1.0, 2.0, 3.0], MSG)  # sweep 3: beam 1 returns
# Beam 1 has now been valid in 2 of the last 3 (sweeps 1 and 3), so 2-of-3
# admits it. This is the gate working as specified, not a miss: 2/3 is a
# loose setting by construction.
chk(out[1] == 2.0, 'a beam valid in 2 of the last 3 is admitted at K=2')

print('\n5. persistence gate — 3 of 3, the strict setting')
r = relay(k=3, n=3)
r._apply_gate([1.0, 2.0], MSG)
r._apply_gate([1.0, NAN], MSG)
out, st = r._apply_gate([1.0, 2.0], MSG)
chk(out[0] == 1.0, 'a beam valid in all three sweeps survives')
chk(out[1] != out[1], 'a beam that missed one sweep is rejected at K=3')
chk(st[4] == 1, 'exactly one beam attributed to the persistence gate')

print('\n6. the gate never invents or alters a range')
r = relay(k=2, n=3)
r._apply_gate([4.0, 4.0], MSG)
r._apply_gate([4.0, 4.0], MSG)
out, _ = r._apply_gate([4.2, 4.2], MSG)
chk(out == [4.2, 4.2],
    'published values are THIS sweep\'s own — no averaging, no carry-over')

print('\n7. beam count change clears the history')
# Index 200 is a different bearing at 430 beams than at 500. Carrying the
# history across would gate beams against a bearing they never occupied.
r = relay(k=2, n=3)
r._apply_gate([1.0, 2.0, 3.0], MSG)
r._apply_gate([1.0, 2.0, 3.0], MSG)
out, st = r._apply_gate([1.0, 2.0], MSG)
chk(st[4] == 0 and out == [1.0, 2.0],
    'a changed beam count resets the window rather than gating on stale bins')

# ── 8. PARAMETER VALIDATION ──────────────────────────────────────────
# Every one of these, accepted, produces a robot that looks broken in a way
# that does not point back at the parameter that caused it.
print('\n8. live parameter validation rejects nonsense')
r = relay()
res = r._on_set_parameters([Param('persist_k', 5), Param('persist_n', 3)])
chk(res.successful is False, 'persist_k > persist_n is refused')
chk('never pass' in res.reason, 'the refusal says why')
chk(r.persist_k == 1 and r.persist_n == 1,
    'a refused batch changes NOTHING — not even its valid members')

r = relay()
res = r._on_set_parameters([Param('range_cap_m', -1.0)])
chk(res.successful is False, 'a negative range cap is refused')

r = relay()
res = r._on_set_parameters([Param('range_floor_m', 6.0),
                            Param('range_cap_m', 5.0)])
chk(res.successful is False, 'floor above cap is refused as an empty window')

r = relay()
res = r._on_set_parameters([Param('persist_n', 0)])
chk(res.successful is False, 'persist_n below 1 is refused')

print('\n9. live parameter application')
r = relay()
res = r._on_set_parameters([Param('range_cap_m', 5.0),
                            Param('persist_n', 3), Param('persist_k', 2)])
chk(res.successful is True, 'a coherent batch is accepted')
chk(r.range_cap == 5.0 and r.persist_k == 2 and r.persist_n == 3,
    'the accepted values land on the node')
chk(r._hist.maxlen == 3, 'the history window is resized to the new persist_n')
chk(r._gates_anything() is True, 'mode flags are recomputed after the set')
out, _ = r._apply_gate([1.0, 9.0], MSG)
chk(out[1] != out[1], 'the new cap takes effect on the very next sweep')

print('\n10. a geometry change forces the cached map to rebuild')
# This is the one that bit the first draft. mirror/mask/yaw only rebuild
# when the SCAN's geometry changes, and a live parameter set does not
# change the scan's geometry. Without clearing _map_key, the set would be
# accepted, logged as applied, and never actually do anything.
r = relay()
r._map_key = (430, -3.14, 0.0146)
res = r._on_set_parameters([Param('mask_min_deg', -120.0)])
chk(res.successful is True, 'a mask bound change is accepted')
chk(r._map_key is None, 'the cached index map is invalidated so it rebuilds')

r = relay()
r._map_key = (430, -3.14, 0.0146)
r._on_set_parameters([Param('range_cap_m', 5.0)])
chk(r._map_key is not None,
    'a range-only change does NOT needlessly rebuild the index map')

print('\n11. a gate-only configuration is not pass-through')
# The first draft's actual bug: _passthrough asked only about the angle
# correction and the mask, so setting a range cap on a relay with both of
# those off was accepted, reported, and then skipped entirely by cb().
r = relay(mask=False, mirror=False, yaw=0.0)
chk(r._passthrough is True, 'no correction, no mask, no gate = pass-through')
r._on_set_parameters([Param('range_cap_m', 5.0)])
chk(r._passthrough is False,
    'adding a range cap takes the relay OUT of pass-through')

print('\n12. stats vector is self-describing and consistent')
r = relay(cap=5.0, k=2, n=3)
r._apply_gate([1.0, 2.0, 3.0, 9.0], MSG)
out, st = r._apply_gate([1.0, NAN, 3.0, 9.0], MSG)
n, n_live, published, cut_range, cut_persist = st
chk(n == 4, 'beam count reported')
chk(n_live == 3, 'n_live counts sensor returns before any policy is applied')
chk(published == n_live - cut_range - cut_persist,
    'published == live - range cuts - persistence cuts, exactly')

sent = []
r.stats_pub = type('P', (), {'publish': lambda _s, m: sent.append(m)})()
r._publish_stats(st)
chk(len(sent) == 1 and len(sent[0].data) == 12,
    'the stats message carries all 12 fields the dashboard reads')
chk(sent[0].data[6] == 5.0, 'the cap the gate is actually running is echoed')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all checks passed')
