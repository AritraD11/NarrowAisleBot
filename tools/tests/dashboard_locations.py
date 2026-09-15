#!/usr/bin/env python3
"""dashboard_locations.py — does the named-location library survive the one
test G7 actually applies to it, which is a power cut?

WHY THIS EXISTS. G7's pass criterion is "3 taught locations recalled after a
full power cycle". That makes the JSON file on disk the whole subsystem: if
it is half-written when the power goes, or if a corrupt file takes the
dashboard down on the next boot instead of reading as empty, the gate fails
for a reason that has nothing to do with navigation. §17.34 is the precedent
in this repo — a 24-minute mapping run was lost because a save path was
never reached under systemd, and nobody knew until the file was not there.

This does not mock the location library. It extracts the real method bodies
out of phone_dashboard.py with `ast` and runs them against a stub node, so
what is tested is the source that ships, not a copy of it that can drift.

    python3 tools/tests/dashboard_locations.py     # from the repo root

No rclpy needed, which is the point: this runs on a laptop before the file
is ever deployed.
"""
import ast
import contextlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')
WANTED = ['_locations_load', '_locations_write',
          'save_location', 'goto_location', 'list_locations']

_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


# ── pull the real methods out of the shipped source ──────────────────
if not SRC.exists():
    sys.exit(f'run me from the repo root; {SRC} not found')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
found = {}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in WANTED:
        found[node.name] = node

missing = [n for n in WANTED if n not in found]
if missing:
    sys.exit(f'these methods are not in {SRC}: {", ".join(missing)}')

ns = {'json': json, 'os': os, 'math': math, 'contextlib': contextlib}
mod = ast.Module(body=[found[n] for n in WANTED], type_ignores=[])
exec(compile(ast.fix_missing_locations(mod), str(SRC), 'exec'), ns)


class _Log:
    def __init__(self):
        self.lines = []

    def info(self, m):
        self.lines.append(('info', m))

    def warn(self, m):
        self.lines.append(('warn', m))


class StubNode:
    """Everything the location methods touch on `self`, and nothing else."""

    def __init__(self, path, map_name='', pose=(1.0, 2.0, 0.5)):
        self.locations_path = path
        self.map_name = map_name
        self._pose = pose
        self._log = _Log()
        self.goals = []

    def _lookup(self, parent, child):
        return self._pose

    def get_logger(self):
        return self._log

    def publish_goal(self, x, y, yaw):
        self.goals.append((x, y, yaw))


for name in WANTED:
    setattr(StubNode, name, ns[name])


# ── the tests ─────────────────────────────────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix='nab_loc_'))
lib = str(tmp / 'locations.json')

print('\nNamed-location library (G7)\n')

n = StubNode(lib, map_name='lab_commission_v1', pose=(1.25, -0.5, 0.7854))
err = n.save_location('Aisle A')
chk(err == '', f'teaching a location succeeds (got {err!r})')
chk(Path(lib).exists(), 'the library file is created on first teach')

on_disk = json.loads(Path(lib).read_text())
chk(on_disk['map'] == 'lab_commission_v1', 'the map name is stored alongside the row')
chk(len(on_disk['locations']) == 1, 'exactly one row after one teach')
chk(abs(on_disk['locations'][0]['x'] - 1.25) < 1e-6,
    'the stored x is the pose the localiser reported, not a rounded guess')

# a power cycle is a fresh process reading the same file
n2 = StubNode(lib, map_name='lab_commission_v1', pose=(9.9, 9.9, 0.0))
err = n2.goto_location('Aisle A')
chk(err == '', f'recall after a restart succeeds (got {err!r})')
chk(n2.goals and abs(n2.goals[0][0] - 1.25) < 1e-6 and abs(n2.goals[0][1] + 0.5) < 1e-6,
    'the recalled goal is the taught coordinate, not the current pose')

# re-teaching a moved spot replaces it rather than shadowing it
n2._pose = (3.0, 4.0, 0.0)
n2.save_location('Aisle A')
rows = json.loads(Path(lib).read_text())['locations']
chk(len(rows) == 1, 're-teaching the same name overwrites instead of duplicating')
chk(abs(rows[0]['x'] - 3.0) < 1e-6, 're-teaching stores the new pose')

# three locations, which is what the gate asks for
n2._pose = (5.0, 1.0, 0.0)
n2.save_location('Staging')
n2._pose = (0.0, 0.0, 0.0)
n2.save_location('Home')
chk(len(n2.list_locations()['locations']) == 3, 'three taught locations coexist')

# refusing is better than storing a number from the wrong frame
n3 = StubNode(lib, map_name='lab_commission_v1')
n3._lookup = lambda parent, child: None
before = Path(lib).read_text()
err = n3.save_location('Nowhere')
chk(err != '', 'teaching is refused when map->base_link is absent')
chk(Path(lib).read_text() == before, 'a refused teach writes nothing at all')

err = n3.save_location('')
chk(err != '', 'an empty name is refused')

# the map guard
n4 = StubNode(lib, map_name='a_different_map')
err = n4.goto_location('Aisle A')
chk(err != '', 'recall is refused when a different map is loaded')
chk(not n4.goals, 'a refused recall sends no goal')
chk(n4.list_locations()['stale'] is True, 'the library reports itself stale to the UI')

err = n4.goto_location('Does Not Exist')
chk(err != '', 'recalling an unknown name is refused')

# a corrupt file must degrade, not explode
bad = str(tmp / 'corrupt.json')
Path(bad).write_text('{ this is not json')
n5 = StubNode(bad, map_name='lab_commission_v1')
try:
    listing = n5.list_locations()
    chk(listing['locations'] == [], 'a corrupt library reads as empty rather than raising')
except Exception as exc:                                   # noqa: BLE001
    chk(False, f'a corrupt library reads as empty rather than raising (raised {exc!r})')

# and a truncated-but-valid-JSON file of the wrong shape
odd = str(tmp / 'odd.json')
Path(odd).write_text('[1, 2, 3]')
n6 = StubNode(odd, map_name='m')
chk(n6.list_locations()['locations'] == [], 'a library of the wrong shape reads as empty')

# no temporary file is left behind for the next boot to trip over
leftovers = [p.name for p in tmp.iterdir() if p.name.endswith('.tmp')]
chk(not leftovers, f'no .tmp files survive a write (found {leftovers})')

shutil.rmtree(tmp, ignore_errors=True)

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all location-library checks passed')
