#!/usr/bin/env python3
"""nab_pid_logger_autodetect.py — does the serial port picker still pick
the LiDAR by mistake?

WHY THIS EXISTS. On 14 Sep 2026, `--test plant` autodetected `/dev/ttyUSB2`
and talked to it for 13.6 seconds before erroring: "device reports readiness
to read but returned no data". ttyUSB2 is the YDLIDAR X4 Pro, not the ESP32
(docs/LiDAR_SLAM_Bringup.md, docs/Research_Journal.md Part V). The old
`_autodetect()` matched on description string ("CP210", "CH340", "Silicon
Labs", "FTDI"), and the ESP32 and the LiDAR both report a CP2102 chip WITH
THE SAME FACTORY SERIAL -- the exact ambiguity `system/99-aislebot.rules`
was written to resolve, by pinning each device to its physical USB port
rather than its chip identity. The udev rule already existed. The
autodetect function just never used it.

This is the failure mode session-health.md calls out by name: "an
instrument that cannot fail its own check is not an instrument." A port
picker that can silently hand you the wrong serial device is exactly that,
and it stayed latent because nobody had forced the collision until a live
run did.

    python3 tools/tests/nab_pid_logger_autodetect.py     # from the repo root

Extracts the real `_autodetect` method out of nab_pid_logger.py with `ast`
and runs it against a faked os/serial layer, so this tests the source that
ships. No pyserial or hardware needed.
"""
import ast
import sys
import types
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
cls = next((n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == 'ESP32Link'), None)
if cls is None:
    sys.exit('ESP32Link class not found in nab_pid_logger.py')
fn = next((n for n in cls.body
           if isinstance(n, ast.FunctionDef) and n.name == '_autodetect'), None)
if fn is None:
    sys.exit('_autodetect() not found on ESP32Link')


class FakePort:
    def __init__(self, device, description='', manufacturer=''):
        self.device = device
        self.description = description
        self.manufacturer = manufacturer


class FakeListPorts:
    def __init__(self, ports):
        self._ports = ports

    def comports(self):
        return self._ports


def make_autodetect(exists_fn, realpath_fn, ports):
    ns = {
        'os': types.SimpleNamespace(
            path=types.SimpleNamespace(exists=exists_fn, realpath=realpath_fn)),
        'sys': sys,
        'serial': types.SimpleNamespace(
            tools=types.SimpleNamespace(list_ports=FakeListPorts(ports))),
    }
    mod = ast.Module(body=[fn], type_ignores=[])
    exec(compile(ast.fix_missing_locations(mod), str(SRC), 'exec'), ns)
    return ns['_autodetect'].__func__


print('\nnab_pid_logger.py serial-port autodetect\n')

# The symlink exists: use it, full stop, no scanning even attempted.
detect = make_autodetect(
    exists_fn=lambda p: p == '/dev/esp32',
    realpath_fn=lambda p: p,
    ports=[FakePort('/dev/ttyUSB2', 'CP2102 device')],   # the LiDAR, must be ignored
)
got = detect()
chk(got == '/dev/esp32', f'/dev/esp32 present is used directly (got {got})')

# The exact collision that happened live: no symlink yet, the only CP210x
# port visible IS the LiDAR (ttyUSB2), reached by its /dev/ydlidar symlink.
detect = make_autodetect(
    exists_fn=lambda p: p == '/dev/ydlidar',
    realpath_fn=lambda p: {'/dev/ydlidar': '/dev/ttyUSB2',
                            '/dev/ttyUSB2': '/dev/ttyUSB2'}.get(p, p),
    ports=[FakePort('/dev/ttyUSB2', 'CP2102 device')],
)
got = detect()
chk(got != '/dev/ttyUSB2',
    f'the LiDAR is never returned even as a last-resort guess (got {got})')

# Same collision, but the real ESP32 is ALSO visible on the bus (bare
# ttyUSB1, no symlink yet). The picker must find it rather than giving up.
detect = make_autodetect(
    exists_fn=lambda p: p == '/dev/ydlidar',
    realpath_fn=lambda p: {'/dev/ydlidar': '/dev/ttyUSB2',
                            '/dev/ttyUSB2': '/dev/ttyUSB2',
                            '/dev/ttyUSB1': '/dev/ttyUSB1'}.get(p, p),
    ports=[FakePort('/dev/ttyUSB2', 'CP2102 device'),    # the lidar
           FakePort('/dev/ttyUSB1', 'CP2102 device')],   # the ESP32
)
got = detect()
chk(got == '/dev/ttyUSB1',
    f'with the LiDAR excluded, the real ESP32 is still found (got {got})')

# No symlinks at all (fresh Pi, udev rule not yet installed), one plausible
# port: falls back to the chip-identity guess rather than refusing to run.
detect = make_autodetect(
    exists_fn=lambda p: False,
    realpath_fn=lambda p: p,
    ports=[FakePort('/dev/ttyUSB0', 'CP2102 device')],
)
got = detect()
chk(got == '/dev/ttyUSB0', f'with no udev rule installed, falls back to a guess (got {got})')

# Nothing plausible connected at all: must return None, not crash.
detect = make_autodetect(
    exists_fn=lambda p: False,
    realpath_fn=lambda p: p,
    ports=[],
)
got = detect()
chk(got is None, f'no ports at all returns None cleanly (got {got})')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print(f'  - {f}')
    sys.exit(1)
print('all autodetect checks passed')
