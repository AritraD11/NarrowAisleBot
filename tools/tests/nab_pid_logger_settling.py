#!/usr/bin/env python3
"""nab_pid_logger_settling.py — does settle(s) report "none" for every row
regardless of how good the gains are?

WHY THIS EXISTS. Live sweep, 14 Sep 2026: three gain sets (Kp=45, 22, 26),
four setpoints each, 48 rows total, every single one printed "settle: none".
Root cause: settling_time()'s pass criterion is "the signal never leaves the
band again, all the way to the end of the series I was handed" -- and
test_steps() handed it the WHOLE multi-setpoint run rather than a window
ending at this step's own t_end. The next setpoint (or the final return to
zero) always pulls the signal back out of band later in the run, so the
check was structurally guaranteed to fail no matter what the gains did.
Overshoot and steady-state error were unaffected and were what the gain
comparison actually had to run on that day.

This is the exact failure mode session-health.md warns about: a metric
that always reads the same regardless of the input is not measuring
anything, and it read as "nothing ever settles" rather than erroring, which
is worse than a crash.

    python3 tools/tests/nab_pid_logger_settling.py     # from the repo root

Extracts settling_time() with ast and drives it directly (no serial, no
ROS), plus a scripted reproduction of the exact call-site bug using a
synthetic multi-setpoint trace shaped like a real --test sweep run.
"""
import ast
import sys
from pathlib import Path

SRC = Path('tools/nab_pid_logger.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not SRC.exists():
    sys.exit(f'run me from the repo root; {SRC} not found')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
fn = next((n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == 'settling_time'), None)
if fn is None:
    sys.exit('settling_time() not found in nab_pid_logger.py')

ns = {}
mod = ast.Module(body=[fn], type_ignores=[])
exec(compile(ast.fix_missing_locations(mod), str(SRC), 'exec'), ns)
settling_time = ns['settling_time']

print('\nsettling_time() and its call-site window (14 Sep sweep)\n')

# A clean step: jumps near target immediately and stays there.
clean = [(0.0, 0.0), (0.05, 0.0)] + [(0.05 + 0.05 * i, 1.0) for i in range(1, 20)]
st = settling_time(clean, t_step=0.0, target=1.0)
chk(st is not None and 0.0 < st < 1.5,
    f'a clean step that stays in band settles within the window (got {st})')

# Never gets within band at all.
never = [(0.0, 0.0)] + [(0.1 * i, 0.5) for i in range(1, 20)]   # stuck at 0.5, target 1.0
st = settling_time(never, t_step=0.0, target=1.0)
chk(st is None, f'a step that never reaches the band returns None (got {st})')

# Reaches band, leaves again, never comes back -- must not settle.
leaves = ([(0.0, 0.0)]
          + [(0.1 * i, 1.0) for i in range(1, 6)]      # in band
          + [(0.5 + 0.1 * i, 1.5) for i in range(1, 6)])  # kicked out, stays out
st = settling_time(leaves, t_step=0.0, target=1.0)
chk(st is None, f'a step that settles then leaves for good returns None (got {st})')

# Targets under 0.1 rad/s are deliberately exempt (near-zero steps).
st = settling_time([(0.0, 0.0), (0.1, 0.05)], t_step=0.0, target=0.05)
chk(st is None, 'a near-zero target is exempted rather than scored')

print()
print('The call-site bug: settling_time on a whole multi-setpoint run\n')

# Build a synthetic trace shaped like a real 2-setpoint sweep: step to 1.0,
# settle cleanly, THEN the run moves on to a second setpoint (2.0) the way
# test_steps() actually drives one continuous collection across all of
# args.setpoints. Step 1's own window is clean; the full run is not.
t_end_1 = 1.0
step1 = [(0.0 + 0.05 * i, 1.0) for i in range(int(t_end_1 / 0.05) + 1)]
step2 = [(t_end_1 + 0.05 * i, 2.0) for i in range(1, 20)]     # next setpoint
full_run = step1 + step2

st_unwindowed = settling_time(full_run, t_step=0.0, target=1.0)
chk(st_unwindowed is None,
    f'reproduces the bug: unwindowed, step 1 never "settles" because step 2 '
    f'moves the signal away later (got {st_unwindowed})')

windowed = [(t, v) for t, v in full_run if t <= t_end_1]
st_windowed = settling_time(windowed, t_step=0.0, target=1.0)
chk(st_windowed is not None and st_windowed < t_end_1,
    f'the fix: windowed to this step\'s own t_end, step 1 settles correctly '
    f'(got {st_windowed})')

# The fix must actually be present at the call site, not just prove the
# function works in isolation -- otherwise this test would stay green after
# someone reverted the one-line change in test_steps().
call_site = SRC.read_text(encoding='utf-8')
chk('act_window' in call_site and 'settling_time(act_window' in call_site,
    'test_steps() actually calls settling_time() on the windowed slice, not the raw column')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all settling-time checks passed')
