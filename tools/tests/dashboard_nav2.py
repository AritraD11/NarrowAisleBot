#!/usr/bin/env python3
"""dashboard_nav2.py — does the NAV2 button start, stop and report Nav2 the
way it claims to, and does the pose box show it without breaking?

Replaces dashboard_lidar.py (5 Oct 2026). The LIDAR tuner it tested was
removed when the LiDAR settings were fixed in scan_relay.py's defaults
(those are pinned by scan_relay_gate.py section 13 now).

THREE PARTS, because the feature spans three places that fail differently:

  A. Static, on the page Python actually SERVES (ast.literal_eval of
     DASHBOARD_HTML, per CLAUDE.md), and on the server source: the button
     exists, no tuner remnant survives, every id the script reaches for is
     in the HTML, both messages have a dispatch case, and Nav2 is stopped
     BEFORE the map on MAP-stop, E-STOP and shutdown.

  B. The server's Nav2 state machine, run for real: the shipped methods are
     pulled out with ast and driven against a stub node, a fake process and
     a fake lifecycle service. Preflight refusals, start, 'starting' -> 'up'
     only on the lifecycle manager's word, stop (cancel + SIGINT, SIGKILL
     after the grace), a crash while up, a terminal launch, and the goal
     status and distance logic.

  C. The browser, headless Chromium: button labels per state, the pose
     box's Nav2 rows, the fold button, the folded summary, taps sending the
     right message (and nothing behind an E-STOP), and no page errors.

    python3 tools/tests/dashboard_nav2.py        # from the repo root

Part C needs Playwright for Python and the pre-installed Chromium; A and B
are stdlib only.
"""
import ast
import os
import re
import signal
import sys
import tempfile
import types
from pathlib import Path

DASH = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')
LAUNCH = Path('src/mecanum_navigation/launch/nav2_slam.launch.py')
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


for p in (DASH, LAUNCH):
    if not p.exists():
        sys.exit(f'run me from the repo root; {p} not found')

src = DASH.read_text(encoding='utf-8')
tree = ast.parse(src)


def module_assign(name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return node
    return None


def module_const(name):
    node = module_assign(name)
    return ast.literal_eval(node.value) if node else None


# The page exactly as Python serves it, not as the file reads.
HTML = module_const('DASHBOARD_HTML')
script = re.search(r'<script>(.*)</script>', HTML, re.S).group(1)

# ═══════════════════════════════════════════════════════════════════
print('\nA. static: the served page and the server source\n')

chk('id="btnNav2"' in HTML, 'the NAV2 button is on the served page')
for gone in ('btnLidar', 'lidarPanel', 'lidar_set', 'lidar_preset',
             'lidar_reset', 'lidar_save', 'ldApply', 'ldRenderStats'):
    chk(gone not in HTML, f'no tuner remnant on the page: {gone}')
for gone in ('LIDAR_PARAM_TYPES', 'DEFAULT_LIDAR_CFG', 'LIDAR_PRESETS'):
    chk(module_assign(gone) is None, f'no tuner remnant in the server: {gone}')
chk('SetParameters' not in src and '/scan_relay_stats' not in src,
    'the server no longer talks to scan_relay at all')

# Every id the script reaches for must exist, or that control is dead.
html_ids = set(re.findall(r'\bid="([^"]+)"', HTML))
used_ids = set(re.findall(r"getElementById\('([^']+)'\)", script))
missing = sorted(used_ids - html_ids)
chk(not missing, f'every getElementById id exists in the HTML (missing: {missing})')

chk("type: 'nav2_start'" in script and "type: 'nav2_stop'" in script,
    'the page sends nav2_start and nav2_stop')
chk("m.type === 'nav'" in script, "the page handles the server's 'nav' payload")


def func_src(name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return ''


dispatch = func_src('_dispatch')
for t in ('nav2_start', 'nav2_stop'):
    chk(f"t == '{t}'" in dispatch, f'"{t}" is handled in _dispatch')


def branch(body, key):
    """Source of one `elif t == 'key':` branch in _dispatch."""
    a = body.find(f"t == '{key}'")
    b = body.find('elif t ==', a + 1)
    return body[a:b if b > 0 else len(body)]


for key in ('map_stop', 'estop'):
    br = branch(dispatch, key)
    i, j = br.find('stop_nav2()'), br.find('stop_mapping()')
    chk(0 <= i < j, f'{key}: Nav2 is stopped before the map it plans on')
shut = func_src('_shutdown_cleanly')
chk(0 <= shut.find('_node.stop_nav2()') < shut.find('_node.stop_mapping()'),
    'shutdown: Nav2 is stopped before the map')

svc = module_const('NAV2_ACTIVE_SERVICE')
mgr = re.search(r"executable='lifecycle_manager',\s*name='([^']+)'", LAUNCH.read_text())
chk(mgr is not None and svc == f'/{mgr.group(1)}/is_active',
    f'NAV2_ACTIVE_SERVICE ({svc}) names the manager nav2_slam.launch.py starts')
chk(module_const('NAV2_MAP_SETTLE_S') == 30.0,
    'Nav2 waits 30 s after MAP (the handoff clean-start order)')

# ═══════════════════════════════════════════════════════════════════
print('\nB. the server state machine, shipped methods on a stub node\n')

ns = {}
for name in ('NAV2_MAP_SETTLE_S', 'NAV2_STOP_GRACE_S', 'NAV2_GRAPH_SETTLE_S', 'NAV2_ACTIVE_SERVICE',
             'NAV_GOAL_STATUS', 'NAV_GOAL_TERMINAL'):
    ns[name] = module_const(name)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                              and n.name == 'pick_latest_goal'], type_ignores=[]),
             str(DASH), 'exec'), ns)
pick = ns['pick_latest_goal']

chk(pick([]) is None, 'pick_latest_goal: no goals -> None')
g = pick([(b'a' * 16, 100, 0, 4), (b'b' * 16, 200, 5, 2), (b'c' * 16, 150, 0, 6)])
chk(g is not None and g[0] == b'b' * 16 and g[2] == 2,
    'pick_latest_goal: the most recently ACCEPTED goal, not the last element')

cls = next(n for n in ast.walk(tree)
           if isinstance(n, ast.ClassDef) and n.name == 'PhoneDashboard')
WANTED = {'_nav2_set', 'nav2_preflight', 'start_nav2', 'stop_nav2',
          '_close_nav2_log', '_nav2_watchdog', '_nav_status_cb', '_plan_cb',
          'nav_status'}
meths = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in WANTED]
chk({m.name for m in meths} == WANTED, f'all {len(WANTED)} Nav2 methods found in PhoneDashboard')
for m in meths:                       # drop annotations that name ROS types
    m.returns = None
    for a in m.args.args:
        a.annotation = None
stub_cls = ast.ClassDef(name='Stub', bases=[], keywords=[], body=meths, decorator_list=[])

calls = []                            # every signal sent, in order
clock = {'t': 1000.0}


class FakeProc:
    def __init__(self, *a, **k):
        self.pid, self.code = 4242, None
        calls.append(('popen', a[0] if a else None))

    def poll(self):
        return self.code


class Fut:
    def __init__(self, ok):
        self.ok = ok

    def done(self):
        return True

    def result(self):
        return types.SimpleNamespace(success=self.ok)


class Cli:
    def __init__(self):
        self.ready, self.answer = True, False

    def service_is_ready(self):
        return self.ready

    def call_async(self, _req):
        return Fut(self.answer)


fake_os = types.SimpleNamespace(
    path=os.path, makedirs=os.makedirs, getpgid=lambda pid: pid, setsid=os.setsid,
    killpg=lambda pg, sig: calls.append(('kill', sig)))
ns.update({
    'os': fake_os, 'signal': signal, 'math': __import__('math'),
    'time': types.SimpleNamespace(monotonic=lambda: clock['t'],
                                  time=lambda: clock['t']),
    'datetime': __import__('datetime').datetime,
    'subprocess': types.SimpleNamespace(Popen=FakeProc, STDOUT=-2),
    'Trigger': types.SimpleNamespace(Request=lambda: None),
    'GoalStatusArray': object, 'Path': object, 'Optional': None,
})
exec(compile(ast.fix_missing_locations(ast.Module(body=[stub_cls], type_ignores=[])),
             str(DASH), 'exec'), ns)
Stub = ns['Stub']


class Log:
    def info(self, *a): pass
    def warn(self, *a): pass
    def error(self, *a): pass


def node(mapping=True, since=60.0, graph=()):
    n = Stub()
    n.log_dir = tempfile.mkdtemp()
    n.mapping_active = mapping
    n._mapping_started = (clock['t'] - since) if mapping else None
    n._graph = list(graph)
    n.get_node_names = lambda: n._graph
    n.get_logger = lambda: Log()
    n.notice, n.notice_seq = '', 0
    n.nav2_state, n.nav2_note, n.nav2_log_path = 'off', '', ''
    n._nav2_proc = n._nav2_log_file = n._nav2_active_fut = None
    n._nav2_started, n._nav2_kill_after = 0.0, None
    n._nav2_quiet_until = 0.0
    n._nav2_active_cli = Cli()
    n._nav_goal = n._plan_end = None
    n.latest_pose = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
    n.cancelled = 0
    n.cancel_nav_goals = lambda: setattr(n, 'cancelled', n.cancelled + 1)
    return n


n = node(mapping=False)
chk('press MAP first' in n.nav2_preflight(), 'refuses without MAP')
n = node(since=10.0)
r = n.nav2_preflight()
chk('wait 20 s more' in r, f'refuses until the map is 30 s old ({r!r})')
n = node(graph=['bt_navigator'])
chk('terminal' in n.nav2_preflight(), 'refuses when Nav2 already runs from a terminal')

n = node()
calls.clear()
chk(n.start_nav2() == '' and n.nav2_state == 'starting',
    'start: launches and reports STARTING, not UP')
chk(calls and calls[0][1] == ['ros2', 'launch', 'mecanum_navigation', 'nav2_slam.launch.py'],
    'start: runs nav2_slam.launch.py')
chk(n.nav2_log_path.startswith(n.log_dir) and os.path.isfile(n.nav2_log_path),
    'start: output goes to a nav2_*.log in the log dir')
chk('already running' in n.nav2_preflight(), 'a second start is refused while it runs')

n._nav2_watchdog()                   # asks the lifecycle manager
n._nav2_watchdog()                   # answer: not active yet
chk(n.nav2_state == 'starting', 'stays STARTING while the lifecycle manager says not active')
n._nav2_active_cli.answer = True
n._nav2_watchdog()
n._nav2_watchdog()
chk(n.nav2_state == 'up', 'UP only once the lifecycle manager reports every node ACTIVE')

calls.clear()
n.stop_nav2()
chk(n.cancelled == 1, 'stop: cancels goals first')
chk(calls == [('kill', signal.SIGINT)] and n.nav2_state == 'stopping',
    'stop: SIGINT to the launch group, state STOPPING')
clock['t'] += 25.0
n._nav2_watchdog()
chk(calls[-1] == ('kill', signal.SIGKILL), 'SIGKILL once the grace period passes')
n._nav2_proc.code = -9
n._nav2_watchdog()
chk(n.nav2_state == 'off' and n._nav2_proc is None, 'reaped after exit, state OFF')
n._graph = ['bt_navigator']          # our own nodes still on the graph
n._nav2_watchdog()
chk(n.nav2_state == 'off', 'a lingering bt_navigator after our own stop is not read as a terminal launch')
chk('still leaving the ROS graph' in n.nav2_preflight(), 'and a restart in that window says why it waits')
clock['t'] += 31.0
n._nav2_watchdog()
chk(n.nav2_state == 'external', 'after the settle window, a bt_navigator on the graph IS reported')

n = node()
n.start_nav2()
n._nav2_active_cli.answer = True
n._nav2_watchdog(); n._nav2_watchdog()
n._nav2_proc.code = 1
n._nav2_watchdog()
chk(n.nav2_state == 'failed' and 'code 1' in n.nav2_note and n.notice_seq == 1,
    'a crash while UP reads FAILED, with the exit code, pushed to the phone')

n = node(graph=['bt_navigator'])
n._nav2_watchdog()
chk(n.nav2_state == 'external', 'a terminal launch is reported, not shown as OFF')
calls.clear()
n.stop_nav2()
chk(n.cancelled == 1 and calls == [],
    "stop with a terminal launch: its goal is cancelled, nothing is killed")
m = node()
m.stop_nav2()
chk(m.cancelled == 0, 'stop with no Nav2 at all sends no cancel (that call would hang)')
n._graph = []
n._nav2_watchdog()
chk(n.nav2_state == 'off', 'and back to OFF when it goes away')

# goal status + distance
n = node()
SN = types.SimpleNamespace


def status_msg(gid, sec, code):
    return SN(status_list=[SN(goal_info=SN(goal_id=SN(uuid=list(gid)),
                                           stamp=SN(sec=sec, nanosec=0)),
                              status=code)])


def plan_msg(x, y, sec, frame='map'):
    return SN(poses=[SN(pose=SN(position=SN(x=x, y=y)))],
              header=SN(frame_id=frame, stamp=SN(sec=sec, nanosec=0)))


chk(n.nav_status()['goal'] is None, 'no goal yet -> no goal block')
clock['t'] = 2000.0
n._plan_cb(plan_msg(5.0, 5.0, 1990))          # an older plan, previous goal
n._nav_status_cb(status_msg(b'g' * 16, 1995, 2))
s = n.nav_status()['goal']
chk(s['status'] == 'EXECUTING' and s['dist'] is None,
    'a plan older than the goal is never shown as its distance')
n._plan_cb(plan_msg(0.0, 0.6, 1996))
n.latest_pose = {'x': 0.0, 'y': 0.2, 'yaw': 0.0}
s = n.nav_status()['goal']
chk(s['dist'] == 0.4 and s['elapsed'] == 5.0,
    f"distance to the plan end and time since accept ({s['dist']}, {s['elapsed']})")
clock['t'] = 2030.0
n._nav_status_cb(status_msg(b'g' * 16, 1995, 4))
clock['t'] = 2100.0
s = n.nav_status()['goal']
chk(s['status'] == 'SUCCEEDED' and s['elapsed'] == 35.0 and not s['active'],
    'time stops at the result instead of running on')
n._plan_cb(plan_msg(1.0, 1.0, 2101, frame='odom'))
chk(n.nav_status()['goal']['dist'] is None, 'a plan not in the map frame is not measured against the map pose')

# ═══════════════════════════════════════════════════════════════════
print('\nC. the browser: button, pose box, fold, taps\n')

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
    chk(False, 'Playwright for Python is installed (pip install playwright)')

if sync_playwright is not None:
    stub = """
<script>
window.__sent = [];
class WebSocket {
  static get OPEN(){ return 1; }
  constructor(u){ this.url=u; this.readyState=1; setTimeout(()=>this.onopen&&this.onopen(),0); }
  send(s){ try { window.__sent.push(JSON.parse(s)); } catch(e){ window.__sent.push(s); } }
  close(){ this.readyState = 3; }
}
window.WebSocket = WebSocket;
</script>
"""
    page_html = HTML.replace('<script>', stub + '<script>', 1)
    page_file = Path(tempfile.mkdtemp()) / 'dash_nav2.html'
    page_file.write_text(page_html, encoding='utf-8')
    UP = {'type': 'nav', 'state': 'up', 'note': '', 'log': '/x/nav2_1.log', 'for_s': 40,
          'goal': {'status': 'EXECUTING', 'active': True, 'elapsed': 12.4, 'dist': 0.42}}

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        for label, vw, vh, dsf in (('phone', 390, 844, 3.0), ('desktop', 1600, 900, 1.0)):
            pg = b.new_page(viewport={'width': vw, 'height': vh}, device_scale_factor=dsf)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto(page_file.as_uri())
            pg.wait_for_timeout(300)
            pg.evaluate("setMapView(true)")
            pg.evaluate("() => { try { localStorage.removeItem('hudMin'); } catch (e) {} hudMin = false;"
                        " robotPose = {x: 0.043, y: 0.58, yaw: 0}; updateHud(); }")
            hud = lambda: pg.evaluate("document.getElementById('mapHud').innerText")
            btn = lambda: pg.evaluate("[document.getElementById('btnNav2').textContent,"
                                      " document.getElementById('btnNav2').className]")

            def nav(m):
                pg.evaluate("m => ws.onmessage({data: JSON.stringify(m)})", m)

            nav({'type': 'nav', 'state': 'off', 'note': '', 'log': '', 'for_s': None, 'goal': None})
            chk('NAV2' not in hud() and btn()[0] == 'NAV2',
                f'{label}: OFF and no goal adds nothing to the pose box')
            nav({'type': 'nav', 'state': 'starting', 'note': '', 'log': '', 'for_s': 12, 'goal': None})
            chk('STARTING 12 s' in hud() and 'armed' in btn()[1],
                f'{label}: STARTING shows its seconds, button amber')
            nav(UP)
            t = hud()
            chk(all(w in t for w in ('UP', 'EXECUTING', '0.42 m', '12 s', 'NOSE'))
                and 'nav-up' in btn()[1] and btn()[0] == 'NAV2 ●',
                f'{label}: UP + goal rows (status, distance, time), button green')

            pg.click('#mapHud .hud-toggle')
            t = hud()
            chk('NAV2 UP · EXECUTING 0.42 m · 12 s' in t and 'NOSE' not in t
                and pg.evaluate("localStorage.getItem('hudMin')") == '1',
                f'{label}: fold -> two-line summary, remembered')
            pg.click('#mapHud .hud-toggle')
            chk('NOSE' in hud() and pg.evaluate("localStorage.getItem('hudMin')") == '0',
                f'{label}: unfold restores the full box')
            chk(pg.evaluate("getComputedStyle(document.getElementById('mapHud')).pointerEvents") == 'none',
                f'{label}: the box still lets map pans through (only the button takes taps)')

            nav({'type': 'nav', 'state': 'failed', 'note': 'x', 'log': '/x/nav2_2.log',
                 'for_s': None, 'goal': None})
            chk('FAILED' in hud() and '/x/nav2_2.log' in hud() and 'nav-bad' in btn()[1],
                f'{label}: FAILED names the log to read')

            pg.evaluate("window.__sent = []")
            nav({'type': 'nav', 'state': 'off', 'note': '', 'log': '', 'for_s': None, 'goal': None})
            pg.click('#btnNav2')
            nav(UP)
            pg.click('#btnNav2')
            sent = pg.evaluate("window.__sent.map(m => m.type)")
            chk(sent == ['nav2_start', 'nav2_stop'], f'{label}: tap sends start when OFF, stop when UP ({sent})')
            pg.evaluate("window.__sent = []; estopped = true")
            pg.click('#btnNav2')
            chk(pg.evaluate("window.__sent.length") == 0, f'{label}: nothing is sent behind an E-STOP')
            pg.evaluate("estopped = false")

            chk(not errs, f'{label}: no page errors ({errs})')
            pg.close()
        b.close()

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all NAV2 checks passed')
