#!/usr/bin/env python3
"""dashboard_lidar.py — does the LIDAR panel control the thing it says it
controls, and does it agree with the node on the other end of the wire?

WHY THIS EXISTS. The tuner spans two files that are deployed separately:
the panel lives in phone_dashboard.py (a colcon package) and the knobs live
in src/scan_relay/scan_relay.py (a plain script run straight from disk).
Nothing forces those two to be the same version, and every way they can
disagree is silent:

  * a parameter the panel sends that the relay never declared -> rejected
    at the far end with a message the operator never sees
  * a double sent where the relay declared an integer -> rejected by rclpy
    with a type error that names no parameter
  * a default in DEFAULT_LIDAR_CFG that is not the relay's default ->
    RESET puts the sensor somewhere a fresh launch would never put it,
    which makes the reset button a trap rather than an escape
  * a preset that the relay's own validation refuses -> a labelled button
    that does nothing
  * an element id in the JS that no element has -> a dead button, and
    §17.32 is the whole project's standing lesson about those

Every check here is a cross-file one for that reason. A test that only read
phone_dashboard.py could pass with the relay broken.

    python3 tools/tests/dashboard_lidar.py      # from the repo root

No rclpy, no ROS, no browser: ast on both shipped sources plus a stub.
"""
import ast
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DASH = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')
RELAY = Path('src/scan_relay/scan_relay.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


for p in (DASH, RELAY):
    if not p.exists():
        sys.exit(f'run me from the repo root; {p} not found')

dash_src = DASH.read_text(encoding='utf-8')
relay_src = RELAY.read_text(encoding='utf-8')
dash_tree = ast.parse(dash_src)
relay_tree = ast.parse(relay_src)


def module_const(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    return None


LIDAR_PARAM_TYPES = module_const(dash_tree, 'LIDAR_PARAM_TYPES')
DEFAULT_LIDAR_CFG = module_const(dash_tree, 'DEFAULT_LIDAR_CFG')
LIDAR_PRESETS = module_const(dash_tree, 'LIDAR_PRESETS')
if not all((LIDAR_PARAM_TYPES, DEFAULT_LIDAR_CFG, LIDAR_PRESETS)):
    sys.exit('LIDAR_PARAM_TYPES / DEFAULT_LIDAR_CFG / LIDAR_PRESETS '
             'not found at module level in phone_dashboard.py')


def relay_declares():
    """{name: default} for every declare_parameter in ScanRelay.__init__."""
    out = {}
    for node in ast.walk(relay_tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'declare_parameter'
                and len(node.args) == 2):
            try:
                out[ast.literal_eval(node.args[0])] = ast.literal_eval(node.args[1])
            except ValueError:
                pass
    return out


DECLARED = relay_declares()

print('\nLiDAR tuner — dashboard panel against scan_relay\n')

# ── 1. THE TWO FILES AGREE ───────────────────────────────────────────
print('1. the panel and the relay declare the same parameters')
for name in LIDAR_PARAM_TYPES:
    chk(name in DECLARED, f'scan_relay declares "{name}"')

print('\n2. the declared types match what the panel sends')
PY_TO_ROS = {float: 'double', int: 'integer', bool: 'bool'}
for name, kind in LIDAR_PARAM_TYPES.items():
    if name not in DECLARED:
        continue
    default = DECLARED[name]
    # bool is a subclass of int in Python, so check it first or every bool
    # parameter reads as an integer and the mismatch this test exists to
    # catch would be reported backwards.
    actual = 'bool' if isinstance(default, bool) else PY_TO_ROS.get(type(default))
    chk(actual == kind,
        f'{name}: panel says {kind}, relay default is {actual}')

print('\n3. RESET puts the relay exactly where a fresh launch would')
for name, want in DEFAULT_LIDAR_CFG.items():
    got = DECLARED.get(name)
    chk(got == want and isinstance(got, type(want)),
        f'{name}: dashboard default {want!r} == relay default {got!r}')

# ── 4. THE NODE'S OWN LOGIC ──────────────────────────────────────────
cls = next((n for n in ast.walk(dash_tree)
            if isinstance(n, ast.ClassDef) and n.name == 'PhoneDashboard'), None)
if cls is None:
    sys.exit('class PhoneDashboard not found')

WANTED = ('lidar_validate', 'lidar_set', 'lidar_preset', 'lidar_save',
          'lidar_status', '_lidar_stats_callback', '_lidar_reap',
          '_lidar_param_msg')
methods = {n.name: n for n in cls.body
           if isinstance(n, ast.FunctionDef) and n.name in WANTED}
missing = [w for w in WANTED if w not in methods]
if missing:
    sys.exit(f'method(s) not found on PhoneDashboard: {", ".join(missing)}')


class Logger:
    def info(self, *a):
        pass

    def warn(self, *a):
        pass


ns = {
    'os': os, 'json': json, 'datetime': datetime, 'time': __import__('time'),
    'contextlib': __import__('contextlib'), 'Optional': None,
    'Float64MultiArray': object,
    'LIDAR_PARAM_TYPES': LIDAR_PARAM_TYPES,
    'DEFAULT_LIDAR_CFG': DEFAULT_LIDAR_CFG,
    'LIDAR_PRESETS': LIDAR_PRESETS,
    'Parameter': lambda: type('P', (), {})(),
    'ParameterValue': lambda: type('V', (), {})(),
    'ParameterType': type('T', (), {'PARAMETER_DOUBLE': 3,
                                    'PARAMETER_INTEGER': 2,
                                    'PARAMETER_BOOL': 1}),
    'SetParameters': type('S', (), {'Request': lambda: type('R', (), {'parameters': []})()}),
}
mod = ast.Module(body=[ast.ClassDef(name='Dash', bases=[], keywords=[],
                                    body=[methods[w] for w in WANTED],
                                    decorator_list=[])],
                 type_ignores=[])
exec(compile(ast.fix_missing_locations(mod), str(DASH), 'exec'), ns)
Dash = ns['Dash']


def dash(ready=True):
    d = Dash()
    d.lidar_cfg = dict(DEFAULT_LIDAR_CFG)
    d.lidar_live = None
    d.lidar_preset_path = ''
    d._lidar_pending = []
    d.notice = ''
    d.notice_seq = 0
    d.sent = []
    d.get_logger = lambda: Logger()

    class Cli:
        def service_is_ready(_s):
            return ready

        def call_async(_s, req):
            d.sent.append(req)
            return type('F', (), {'done': lambda _x: False})()

    d._lidar_cli = Cli()
    return d


print('\n4. validation refuses configurations that cannot work')
d = dash()
chk(d.lidar_validate(DEFAULT_LIDAR_CFG) == '', 'the defaults validate')
chk('never pass' in d.lidar_validate(
    {'persist_k': 4, 'persist_n': 2}), 'k > n is refused with a reason')
chk(d.lidar_validate({'range_cap_m': -1}) != '', 'a negative cap is refused')
chk(d.lidar_validate({'range_floor_m': 5.0, 'range_cap_m': 2.0}) != '',
    'floor above cap is refused')
chk('footprint' in d.lidar_validate({'range_cap_m': 0.1}),
    'a cap inside the robot\'s own footprint is refused')
chk(d.lidar_validate({'range_cap_m': 'five'}) != '',
    'a non-numeric value is refused rather than raising')

print('\n5. every preset is a configuration the relay would accept')
for name, cfg in LIDAR_PRESETS.items():
    reason = d.lidar_validate(cfg)
    chk(reason == '', f'preset "{name}" validates ({reason or "ok"})')
    chk(set(cfg) == set(LIDAR_PARAM_TYPES),
        f'preset "{name}" sets every parameter, leaving nothing stale')

print('\n6. presets reachable from the panel actually exist')
# The three preset buttons are hardcoded in the HTML. A renamed preset
# leaves a labelled button that silently does nothing.
for name in re.findall(r"data-preset=\"([a-z]+)\"", dash_src):
    chk(name in LIDAR_PRESETS, f'the "{name}" button maps to a real preset')

print('\n7. a set is refused cleanly when scan_relay is not running')
d = dash(ready=False)
reason = d.lidar_set({'range_cap_m': 5.0})
chk('not running' in reason, 'a missing relay is reported, not waited on')
chk(d.sent == [], 'nothing is queued against a service that is not there')
# Blocking here would freeze the executor thread that also feeds the drive
# joystick. A frozen joystick on a moving robot is a safety problem.
body = ast.dump(methods['lidar_set'])
chk('wait_for_service' not in body,
    'lidar_set never blocks on the service')

print('\n8. a valid set reaches the relay and is remembered as requested')
d = dash()
chk(d.lidar_set({'range_cap_m': 5.0, 'persist_n': 3, 'persist_k': 2}) == '',
    'a coherent set is accepted')
chk(len(d.sent) == 1 and len(d.sent[0].parameters) == 3,
    'three parameters are sent')
chk(d.lidar_cfg['range_cap_m'] == 5.0, 'the request is recorded')
d = dash()
chk(d.lidar_set({'nonsense': 1}) == 'nothing recognised in that request',
    'an unknown parameter is not silently forwarded')

print('\n9. typed parameter messages')
d = dash()
p = d._lidar_param_msg('range_cap_m', 5)
chk(p.value.type == 3 and p.value.double_value == 5.0,
    'an integer typed into a double field is coerced to double')
p = d._lidar_param_msg('persist_n', 3.0)
chk(p.value.type == 2 and p.value.integer_value == 3,
    'a double typed into an integer field is coerced to integer')
p = d._lidar_param_msg('mask_enabled', False)
chk(p.value.type == 1 and p.value.bool_value is False, 'bools carry as bools')

print('\n10. stats parsing')
d = dash()
d._lidar_stats_callback(type('M', (), {'data': [430.0, 200.0]})())
chk(d.lidar_live is None,
    'a short stats array is DROPPED, not zero-padded into a false reading')
d._lidar_stats_callback(type('M', (), {'data': [
    430.0, 200.0, 150.0, 30.0, 20.0, 0.0, 5.0, 2.0, 3.0, 1.0, -135.0, -45.0,
]})())
chk(d.lidar_live is not None, 'a full stats array parses')
chk(d.lidar_live['published'] == 150 and d.lidar_live['cut_range'] == 30,
    'counts land in the right fields')
chk(d.lidar_live['persist_k'] == 2 and d.lidar_live['persist_n'] == 3,
    'the relay\'s own gate configuration is read back')
chk(d.lidar_live['mask_enabled'] is True, 'the mask flag is a bool, not 1.0')

print('\n11. the panel shows the RELAY\'s state, not the request')
# The single most important behaviour here. Showing the request as though
# it were the state is how a refused set looks applied.
d = dash()
d.lidar_cfg['range_cap_m'] = 5.0          # requested
d.lidar_live = {'range_cap_m': 0.0, 'stamp': ns['time'].time()}
st = d.lidar_status()
chk(st['live']['range_cap_m'] == 0.0, 'live reports what the relay is running')
chk(st['requested']['range_cap_m'] == 5.0, 'the request is reported separately')

print('\n12. stale stats are dropped rather than left on screen')
# §17.25: a frozen scan sat on screen looking authoritative while the robot
# kept driving. Same failure, different widget.
d = dash()
d.lidar_live = {'range_cap_m': 5.0, 'stamp': ns['time'].time() - 30}
chk(d.lidar_status()['live'] is None,
    'stats older than the timeout read as absent, not as current')

print('\n13. SAVE writes only a confirmed configuration')
d = dash()
chk('nothing confirmed' in d.lidar_save(),
    'saving before any stats arrive is refused')
with tempfile.TemporaryDirectory() as tmpd:
    d = dash()
    d.lidar_preset_path = os.path.join(tmpd, 'lidar_tune.json')
    d.lidar_cfg['range_cap_m'] = 9.0        # requested but NOT confirmed
    d.lidar_live = {'range_cap_m': 5.0, 'range_floor_m': 0.0, 'persist_k': 2,
                    'persist_n': 3, 'mask_enabled': True, 'beams': 430,
                    'live': 200, 'published': 150, 'cut_range': 30,
                    'cut_persist': 20, 'stamp': ns['time'].time()}
    chk(d.lidar_save() == '', 'a confirmed configuration saves')
    saved = json.loads(Path(d.lidar_preset_path).read_text())
    chk(saved['config']['range_cap_m'] == 5.0,
        'the file holds the LIVE value, never the unconfirmed request')
    chk(saved['measured']['published'] == 150,
        'the numbers that configuration was producing are saved alongside it')
    chk(not [f for f in os.listdir(tmpd) if f.endswith('.tmp')],
        'no .tmp file survives the write')

# ── 14. THE UI IS WIRED ──────────────────────────────────────────────
print('\n14. every element the LiDAR JS reaches for exists in the HTML')
html_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', dash_src))
js_ids = set(re.findall(r"getElementById\('(ld[A-Za-z0-9_]*|btnLidar[A-Za-z]*)'\)",
                        dash_src))
chk(bool(js_ids), 'the test found LiDAR element lookups to check')
for i in sorted(js_ids):
    chk(i in html_ids, f'#{i} exists')

print('\n15. every LiDAR message the panel sends has a dispatch case')
sent_types = set(re.findall(r"send\(\{\s*type:\s*'(lidar_[a-z_]+)'", dash_src))
handled = set(re.findall(r"t == '(lidar_[a-z_]+)'", dash_src))
chk(bool(sent_types), 'the test found LiDAR messages to check')
for t in sorted(sent_types):
    chk(t in handled, f'"{t}" is handled in _dispatch')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all LiDAR tuner checks passed')
