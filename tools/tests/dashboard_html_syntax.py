#!/usr/bin/env python3
"""dashboard_html_syntax.py — does the JavaScript Python actually SERVES
parse cleanly, as opposed to the JavaScript sitting in the source file?

WHY THIS EXISTS. 15 Sep 2026, discovered live on the robot: a line reading

    e.textContent = 'Over half of the sensor\'s returns are being dropped. '

inside the triple-quoted DASHBOARD_HTML assignment. That backslash-quote
is valid Python-source text, but Python's own string-literal parser EATS
the backslash while compiling the .py file -- so the value actually bound
to `DASHBOARD_HTML` at import time has a bare, unescaped apostrophe sitting
inside a JS single-quoted string. The page HTTP-served fine (curl 200, no
ROS error, no exception, nothing in the service log) because none of that
touches the string's content. The browser's JS parser hit the bare quote,
raised `Uncaught SyntaxError: unexpected token: identifier`, and because a
syntax error aborts an entire <script> block before any of it runs, EVERY
feature on the dashboard died at once -- the WebSocket never opened, the
joystick never bound, the whole page went inert. It looked like a network
or ROS problem. It was a one-character Python/JS escaping collision.

Every previous JS check this project ran (`node --check`, the Chromium
render tests) tested the RAW FILE TEXT — read via `pathlib.Path.read_text()`
or plain regex over the .py source — which still has the two-character
`\'` sequence intact and therefore still parses as valid JS. None of those
tests can ever catch this bug class, by construction: they check a string
Python never actually produces. This test is the one gap: it makes Python
itself evaluate the same string literal the running server evaluates
(via `ast.literal_eval` on the `DASHBOARD_HTML` assignment's own AST node,
which applies exactly the escape rules `python3` would apply on import,
without needing rclpy or any ROS dependency installed), then checks THAT
against `node --check`.

    python3 tools/tests/dashboard_html_syntax.py     # from the repo root

Needs `node` on PATH (checked; skips loudly rather than silently passing
if absent) and nothing else — no ROS, no browser, no server.
"""
import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not SRC.exists():
    sys.exit(f'run me from the repo root; {SRC} not found')

node = shutil.which('node')
if node is None:
    sys.exit('node not found on PATH -- this check needs it, cannot skip silently')

print('\ndashboard HTML/JS — the string Python actually serves, not the file text\n')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
html = None
for node_ in tree.body:
    if (isinstance(node_, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'DASHBOARD_HTML' for t in node_.targets)):
        # literal_eval, not .value directly: DASHBOARD_HTML is a plain string
        # constant today, but this stays correct if it ever becomes an
        # implicitly-concatenated multi-part literal.
        html = ast.literal_eval(node_.value)
        break

if html is None:
    sys.exit('DASHBOARD_HTML assignment not found at module level')
chk(isinstance(html, str) and len(html) > 1000, 'DASHBOARD_HTML evaluated to a real page')

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
chk(len(scripts) == 1, f'exactly one inline <script> block (found {len(scripts)})')
js = scripts[0] if scripts else ''

with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
    f.write(js)
    js_path = f.name

try:
    result = subprocess.run([node, '--check', js_path],
                            capture_output=True, text=True, timeout=30)
    chk(result.returncode == 0,
        'node --check passes on the TRUE runtime script (as Python actually serves it)')
    if result.returncode != 0:
        print('  --- node stderr ---')
        for line in result.stderr.strip().split('\n'):
            print(f'  {line}')
finally:
    Path(js_path).unlink(missing_ok=True)

# The specific bug class, checked directly so a future instance names
# itself rather than waiting to be re-discovered live on the robot: a
# backslash that survived Python's own parsing into the runtime string.
# Every legitimate use in this page (there are none as of this writing —
# see the docstring) would show up here too, so a hit is not automatically
# wrong, but it must be justified by hand, not assumed safe.
stray = [m.group() for m in re.finditer(r'.{0,24}\\.{0,24}', html)]
chk(len(stray) == 0,
    f'no stray backslashes survive into the served page ({len(stray)} found)')
for s in stray:
    print(f'    {s!r}')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all checks passed')
