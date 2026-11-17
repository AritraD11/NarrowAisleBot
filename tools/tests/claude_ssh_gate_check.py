#!/usr/bin/env python3
"""claude_ssh_gate_check.py - try to break system/claude_ssh_gate.sh.

The gate is the forced command behind Claude's SSH keys on the Pi. Its whole
job is to say no. So this test spends most of its effort on things that must
be refused: shell metacharacters, command substitution, path traversal,
symlinks that point out of the home directory, key files, and every verb that
would move the robot (publish, service call, param set, launch, bag play,
sudo, systemctl restart, serial ports).

It runs the real script with a fake HOME and a directory of stub binaries
for the Pi-only tools (ros2, systemctl, journalctl, vcgencmd, lsusb, sudo).
The stubs print what they were asked; the `sudo` stub also drops a marker
file, so "sudo was never reached" is a checked fact, not a hope.

What it can't do: prove sshd hands the script SSH_ORIGINAL_COMMAND the way
the docs say, or that `restrict` is honoured. After installing on the Pi,
run the "acceptance" block in docs/Claude_Pi_SSH_Access.md.

    python3 tools/tests/claude_ssh_gate_check.py      # repo root, needs bash
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path('system/claude_ssh_gate.sh').resolve()
_fails = []
_calls = 0


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not GATE.exists() or not shutil.which('bash'):
    sys.exit('run me from the repo root (needs bash)')

root = Path(tempfile.mkdtemp(prefix='gatetest_'))
home = root / 'home'
outside = root / 'outside'
stubs = root / 'stubs'
marker = root / 'SUDO_WAS_CALLED'
pwned = root / 'PWNED'
for d in (home, outside, stubs):
    d.mkdir()

# ── fake Pi home
(home / 'ros2_ws/src/mecanum_robot/mecanum_robot').mkdir(parents=True)
(home / 'ros2_ws/tools').mkdir(parents=True)
(home / 'aislebot_logs').mkdir()
(home / '.ssh').mkdir()
(home / '.config').mkdir()
(home / 'notes.txt').write_text('line one\nline two foo\nline three\n')
(home / 'aislebot_logs/run.log').write_text('imu ok\nfoo happened\n')
(home / 'ros2_ws/src/mecanum_robot/mecanum_robot/esp32_bridge.py').write_text('x = 1  # foo\n')
(home / 'ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py').write_text('DASHBOARD_HTML = "x"\n')
(home / '.ssh/id_ed25519').write_text('PRIVATE KEY MATERIAL\n')
(home / '.ssh/authorized_keys').write_text('ssh-ed25519 AAAA claude\n')
(home / '.bash_history').write_text('sudo something\n')
(home / '.config/x').write_text('cfg\n')
(outside / 'secret.txt').write_text('OUTSIDE SECRET\n')
(outside / 'other').mkdir()
os.symlink(outside / 'secret.txt', home / 'shortcut_a')
os.symlink('/etc/passwd', home / 'shortcut_b')
os.symlink(outside / 'other', home / 'ros2_ws/src/linkdir')
os.symlink(outside / 'secret.txt', home / 'ros2_ws/src/evil.py')
os.symlink(home / '.ssh', home / 'sshlink')

# ── stub binaries for the Pi-only tools
for name in ('ros2', 'systemctl', 'journalctl', 'vcgencmd', 'lsusb'):
    f = stubs / name
    f.write_text(f'#!/bin/bash\necho "STUB {name} $* DOMAIN=${{ROS_DOMAIN_ID:-unset}}"\n')
    f.chmod(0o755)
sudo_fail = root / 'SUDO_FAILS'   # while this file exists the sudo stub behaves like "no sudoers line"
f = stubs / 'sudo'
f.write_text(f'#!/bin/bash\ntouch {marker}\n'
             f'if [ -e {sudo_fail} ]; then echo "sudo: a password is required" >&2; exit 1; fi\n'
             f'echo "STUB sudo $*"\n')
f.chmod(0o755)
f = stubs / 'colcon'
f.write_text('#!/bin/bash\necho "STUB colcon $* CWD=$(pwd)"\n')
f.chmod(0o755)

# The script keeps its PATH, but tests need stubs first; GATE_PATH is the hook.
BASEPATH = f'{stubs}:/usr/local/bin:/usr/bin:/bin'


def run(mode, cmd, stdin=b'', counted=True):
    """Run the gate the way sshd would: HOME set, command in SSH_ORIGINAL_COMMAND."""
    global _calls
    env = {'HOME': str(home), 'GATE_PATH': BASEPATH, 'PATH': '/usr/bin:/bin',
           'GATE_RESTART_WAIT': '0'}
    if cmd is not None:
        env['SSH_ORIGINAL_COMMAND'] = cmd
    r = subprocess.run(['bash', str(GATE), mode], env=env, input=stdin,
                       capture_output=True, timeout=30)
    if counted and mode in ('ro', 'rw'):
        _calls += 1
    return r.returncode, r.stdout.decode(errors='replace'), r.stderr.decode(errors='replace')


def allowed(mode, cmd, want=None, label=None):
    rc, out, err = run(mode, cmd)
    ok = 'GATE,DENIED' not in err and rc == 0 and (want is None or want in out)
    chk(ok, label or f'{mode}: allowed  {cmd!r}')
    if not ok:
        print('      rc', rc, 'out', out[:200], 'err', err[:200])
    return out


def denied(mode, cmd, why=None, label=None):
    rc, out, err = run(mode, cmd)
    ok = rc == 126 and 'GATE,DENIED' in err and (why is None or f'DENIED,{why}]' in err)
    leaked = 'OUTSIDE SECRET' in out or 'PRIVATE KEY' in out or 'root:' in out
    chk(ok and not leaked, label or f'{mode}: refused  {cmd!r}' + (f'  [{why}]' if why else ''))
    if not (ok and not leaked):
        print('      rc', rc, 'out', out[:200], 'err', err[:200])


print('modes and an empty command')
rc, _, err = run('xx', 'cat notes.txt', counted=False)
chk(rc == 2 and 'bad_mode' in err, 'unknown mode is refused with exit 2')
rc, _, err = run('', 'cat notes.txt', counted=False)
chk(rc == 2, 'missing mode is refused')
denied('ro', None, 'empty', 'interactive login (no command at all) is refused')
denied('rw', '', 'empty', 'empty command is refused')
denied('ro', '   ', None, 'blank command is refused')

print('read-only verbs that must work')
allowed('ro', 'help', 'GATE,HELP')
allowed('ro', 'cat notes.txt', 'line two foo')
allowed('ro', 'cat notes.txt aislebot_logs/run.log', 'imu ok')
allowed('ro', 'head -n 1 notes.txt', 'line one')
allowed('ro', 'tail -n 1 notes.txt', 'line three')
allowed('ro', 'ls', 'notes.txt')
allowed('ro', 'ls -la ros2_ws/src', 'mecanum_robot')
allowed('ro', 'wc -l notes.txt', '3')
allowed('ro', 'stat notes.txt', 'notes.txt')
want = hashlib.sha256((home / 'notes.txt').read_bytes()).hexdigest()
allowed('ro', 'sha256sum notes.txt', want)
allowed('ro', 'grep -n foo notes.txt', 'line two foo')
allowed('ro', 'grep -rn foo ros2_ws/src', 'esp32_bridge.py')
allowed('ro', 'grep -rn foo aislebot_logs', 'foo happened')
allowed('ro', 'journalctl -u aislebot.service -n 50', 'STUB journalctl')
allowed('ro', 'journalctl -u aislebot.service -b -n 5', 'STUB journalctl')
allowed('ro', 'systemctl status aislebot.service', 'STUB systemctl')
allowed('ro', 'systemctl is-active aislebot.service', 'STUB systemctl')
allowed('ro', 'whoami')
allowed('ro', 'date')
allowed('ro', 'uptime')
allowed('ro', 'uname -a')
allowed('ro', 'df -h')
allowed('ro', 'free -h')
allowed('ro', 'lsusb', 'STUB lsusb')
allowed('ro', 'vcgencmd get_throttled', 'STUB vcgencmd')
rc, out, err = run('ro', 'ls /dev/ttyUSB0')
chk('GATE,DENIED' not in err, 'ro: "ls /dev/ttyUSB0" passes the gate (existence check only)')

print('ros2 introspection uses the robot\'s DDS domain')
out = allowed('ro', 'ros2 topic list', 'STUB ros2 topic list')
chk('DOMAIN=42' in out, 'ros2 runs with ROS_DOMAIN_ID=42')
allowed('ro', 'ros2 topic echo --once /imu/data', 'topic echo --once /imu/data')
allowed('ro', 'ros2 topic echo --field angular_velocity.z /imu/data', '--field angular_velocity.z')
allowed('ro', 'ros2 topic hz /imu/data', 'topic hz')
allowed('ro', 'ros2 topic info /imu/data', 'topic info')
allowed('ro', 'ros2 node list', 'node list')
allowed('ro', 'ros2 node info /esp32_bridge', 'node info')
allowed('ro', 'ros2 param list /esp32_bridge', 'param list')
allowed('ro', 'ros2 param get /esp32_bridge imu_rate_hz', 'param get')
allowed('ro', 'ros2 param dump /esp32_bridge', 'param dump')
allowed('ro', 'ros2 service list', 'service list')
allowed('ro', 'ros2 interface show sensor_msgs/msg/Imu', 'interface show')

print('anything that moves the robot or changes the system is refused')
for cmd in ('ros2 topic pub /cmd_vel geometry_msgs/msg/Twist {}',
            'ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist',
            'ros2 service call /x std_srvs/srv/Empty',
            'ros2 param set /esp32_bridge imu_rate_hz 5',
            'ros2 param delete /esp32_bridge x',
            'ros2 param load /esp32_bridge f.yaml',
            'ros2 launch mecanum_robot aislebot_full.launch.py',
            'ros2 run mecanum_robot esp32_bridge',
            'ros2 bag play x',
            'ros2 bag record -a',
            'ros2 node kill x',
            'ros2 lifecycle set /x shutdown',
            'ros2 action send_goal /x y z',
            'ros2 daemon stop'):
    denied('ro', cmd, 'ros2_verb' if cmd.split()[1] != 'topic' or 'pub' not in cmd else None)
denied('rw', 'ros2 topic pub /cmd_vel geometry_msgs/msg/Twist', None, 'rw: topic pub is refused too')
denied('rw', 'ros2 service call /x std_srvs/srv/Empty', 'ros2_verb', 'rw: service call is refused too')
for cmd in ('sudo ls', 'sudo systemctl restart aislebot.service', 'su -', 'bash', 'sh -c id',
            'python3 -c print(1)', 'perl -e 1', 'rm notes.txt', 'mv notes.txt x', 'cp notes.txt x',
            'chmod 777 notes.txt', 'touch x', 'tee x', 'dd if=/dev/zero of=x', 'kill 1', 'reboot',
            'shutdown now', 'curl http://example.com', 'wget http://example.com', 'scp x y',
            'ssh localhost', 'nc -l 9', 'env', 'printenv', 'set', 'export X=1', 'id', 'crontab -l',
            'find . -name x', 'sed s/a/b/ notes.txt', 'awk 1 notes.txt', 'nano notes.txt',
            'systemctl restart aislebot.service', 'systemctl stop aislebot.service',
            'systemctl start aislebot.service', 'systemctl disable aislebot.service',
            'systemctl daemon-reload', 'systemctl edit aislebot.service',
            'journalctl -u aislebot.service --vacuum-size=1M', 'journalctl --rotate',
            'journalctl -n 10', 'vcgencmd otp_dump', 'uname -r', 'df', 'free'):
    denied('ro', cmd)
chk(not marker.exists(), 'the sudo stub was never reached')

print('shell tricks never reach a shell')
for cmd in ('cat notes.txt; touch %s' % pwned,
            'cat notes.txt && touch %s' % pwned,
            'cat notes.txt || touch %s' % pwned,
            'cat notes.txt | sh',
            'cat notes.txt > %s' % pwned,
            'cat notes.txt >> x',
            'cat < notes.txt',
            'cat $(touch %s)' % pwned,
            'cat `touch %s`' % pwned,
            'cat ${HOME}/notes.txt',
            'cat $HOME/notes.txt',
            'cat "notes.txt"',
            "cat 'notes.txt'",
            'cat notes.txt\ntouch %s' % pwned,
            'cat notes.txt\rtouch %s' % pwned,
            'cat notes.*',
            'cat n?tes.txt',
            'cat [n]otes.txt',
            'cat ~/notes.txt',
            'cat notes.txt &',
            'cat notes.txt # comment',
            'cat notes.txt\\ x',
            'cat {notes.txt,x}',
            'cat !!',
            'cat \tnotes.txt'.replace('\t', '\x09'),
            'cat notes.txt\x1b[2J'):
    denied('ro', cmd, 'characters' if '\n' in cmd or any(c in cmd for c in '&|;<>$`"\'*?[]{}~!#\\\r\t\x1b') else None)
chk(not pwned.exists(), 'no injected command ever ran (PWNED file absent)')
denied('ro', 'cat ' + 'a' * 400, 'too_long')
denied('ro', 'cat ' + ' '.join(['notes.txt'] * 14), 'too_many_words')

print('paths: traversal, symlinks, secrets, outside the home')
denied('ro', 'cat ../outside/secret.txt', 'path')
denied('ro', 'cat ros2_ws/../.ssh/id_ed25519', 'path')
denied('ro', 'cat shortcut_a', 'path', 'symlink to a file outside home is refused')
denied('ro', 'cat shortcut_b', 'path', 'symlink to /etc/passwd is refused')
denied('ro', 'cat sshlink/id_ed25519', 'path', 'symlink to ~/.ssh is refused (resolved before checking)')
denied('ro', 'ls sshlink', 'path')
denied('ro', 'cat /etc/passwd', 'path')
denied('ro', 'cat /etc/shadow', 'path')
denied('ro', 'cat /proc/self/environ', 'path')
denied('ro', 'cat /dev/ttyUSB0', 'path', 'serial port cannot be read')
denied('ro', 'cat /dev/esp32', 'path')
denied('ro', 'head -n 1 /dev/ttyUSB0', 'path')
denied('ro', 'ls /etc', 'path')
denied('ro', 'ls /', 'path')
denied('ro', 'ls /dev/mem', 'path')
denied('ro', 'cat .ssh/id_ed25519', 'path')
denied('ro', 'cat .ssh/authorized_keys', 'path')
denied('ro', 'cat .bash_history', 'path')
denied('ro', 'cat .config/x', 'path')
denied('ro', 'ls .ssh', 'path')
denied('ro', 'ls -la .ssh', 'path')
denied('ro', 'stat .ssh/id_ed25519', 'path')
denied('ro', 'sha256sum .ssh/id_ed25519', 'path')
denied('ro', 'grep PRIVATE .ssh/id_ed25519', 'path')
denied('ro', 'grep -rn PRIVATE .', 'recursive_scope', 'recursive grep from ~ is refused')
denied('ro', 'grep -r PRIVATE .ssh', None)
denied('ro', 'grep -r foo /opt/ros', 'recursive_scope')
denied('ro', 'grep -rn foo ros2_ws', 'recursive_scope', 'recursive grep of ros2_ws (install/, build/) is refused')
denied('ro', 'cat -n notes.txt', 'path', 'option-looking path is refused')
denied('ro', 'cat --help', 'path')
denied('ro', 'ls -z', 'flag')
denied('ro', 'ls --color=always', 'flag')
denied('ro', 'grep -P x notes.txt', 'flag')
denied('ro', 'grep --include=x foo notes.txt', 'flag')
denied('ro', 'head -n 99999 notes.txt', 'count')
denied('ro', 'head -n abc notes.txt', 'count')
denied('ro', 'journalctl -u ssh.service -n 1000000', 'count')
denied('ro', 'journalctl -u notaunit -n 5', 'unit')
denied('ro', 'journalctl -u aislebot.service --follow', 'flag')
denied('ro', 'systemctl status aislebot', 'unit')
denied('ro', 'systemctl status aislebot.service --user', 'flag')

print('ro key cannot write; rw key can write only under ros2_ws/src and ros2_ws/tools')
denied('ro', 'install-src ros2_ws/src/mecanum_robot/mecanum_robot/esp32_bridge.py', 'rw_only')

bridge_rel = 'ros2_ws/src/mecanum_robot/mecanum_robot/esp32_bridge.py'
bridge = home / bridge_rel
old_text = bridge.read_text()
old_hash = hashlib.sha256(old_text.encode()).hexdigest()
new_text = b'x = 2  # new\n'
new_hash = hashlib.sha256(new_text).hexdigest()
rc, out, err = run('rw', 'install-src ' + bridge_rel, new_text)
chk(rc == 0 and 'GATE,INSTALLED' in out, 'rw: install-src replaces an existing source file')
chk(bridge.read_bytes() == new_text, 'file now holds the new contents')
chk(f'before={old_hash}' in out and f'after={new_hash}' in out,
    'printed before/after sha256 match what is on disk')
backups = list((home / 'ros2_ws/backup_claude').rglob('*esp32_bridge.py'))
chk(len(backups) == 1 and backups[0].read_text() == old_text, 'old contents were backed up first')

rc, out, err = run('rw', 'install-src ros2_ws/tools/new_tool.py', b'print(1)\n')
chk(rc == 0 and 'before=none' in out and (home / 'ros2_ws/tools/new_tool.py').exists(),
    'rw: a brand-new file under ros2_ws/tools is created (before=none)')

before = bridge.read_bytes()
rc, out, err = run('rw', 'install-src ' + bridge_rel, b'def broken(:\n')
chk(rc == 126 and 'python_syntax' in err and bridge.read_bytes() == before,
    'rw: a .py with a syntax error is refused and the file is untouched')
rc, out, err = run('rw', 'install-src ' + bridge_rel, b'')
chk(rc == 126 and 'empty_input' in err and bridge.read_bytes() == before, 'rw: empty input is refused')
rc, out, err = run('rw', 'install-src ' + bridge_rel, b'#' * (1048576 + 10) + b'\n')
chk(rc == 126 and 'too_large' in err and bridge.read_bytes() == before, 'rw: >1 MB input is refused')

dash_rel = 'ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py'
rc, out, err = run('rw', 'install-src ' + dash_rel, b'DASHBOARD_HTML = "y"\n')
chk(rc == 126 and 'dashboard_needs_browser_check' in err
    and (home / dash_rel).read_text() == 'DASHBOARD_HTML = "x"\n',
    'rw: phone_dashboard.py is refused (needs the browser-console check)')

for rel, why in (
        ('.ssh/authorized_keys', 'outside_src'),
        ('.bashrc', 'outside_src'),
        ('notes.txt', 'outside_src'),
        ('ros2_ws/install/setup.bash', 'outside_src'),
        ('ros2_ws/srcx/y.py', 'outside_src'),
        ('ros2_ws/src/../../.ssh/authorized_keys', 'parent_ref'),
        ('ros2_ws/src/a/../b.py', 'parent_ref'),
        ('/etc/passwd', 'absolute_path'),
        (str(home / bridge_rel), 'absolute_path'),
        ('ros2_ws/src/linkdir/a.py', 'outside_src_resolved'),
        ('ros2_ws/src/evil.py', 'outside_src_resolved'),
        ('ros2_ws/src/mecanum_robot/run.sh', 'extension'),
        ('ros2_ws/src/mecanum_robot/run', 'extension'),
        ('ros2_ws/src/mecanum_robot/x.so', 'extension'),
        ('ros2_ws/src/mecanum_robot/id_rsa.txt', 'secret_path'),
        ('ros2_ws/src/nodir/x.py', 'no_such_directory')):
    rc, out, err = run('rw', 'install-src ' + rel, b'x = 1\n')
    chk(rc == 126 and f'DENIED,{why}]' in err, f'rw: install-src {rel!r} refused [{why}]')
chk(not (outside / 'secret.txt').read_text() != 'OUTSIDE SECRET\n', 'the file outside home was not modified')
chk((outside / 'other').exists() and not list((outside / 'other').iterdir()),
    'nothing was written through the symlinked directory')
chk((home / '.ssh/authorized_keys').read_text() == 'ssh-ed25519 AAAA claude\n', 'authorized_keys untouched')
chk(not list(home.rglob('.claude_tmp.*')), 'no temporary files left behind after refusals')
rc, out, err = run('rw', 'install-src')
chk(rc == 126 and 'usage' in err, 'rw: install-src with no path is refused')
rc, out, err = run('rw', 'install-src a b')
chk(rc == 126 and 'usage' in err, 'rw: install-src with two paths is refused')
for cmd in ('sudo ls', 'bash', 'rm notes.txt', 'systemctl restart aislebot.service',
            'cat notes.txt; id', 'cat .ssh/id_ed25519'):
    denied('rw', cmd)
allowed('rw', 'cat notes.txt', 'line one', 'rw: read verbs still work')
out = allowed('rw', 'help', 'install-src')
chk('install-src' not in run('ro', 'help')[1], 'ro help does not advertise install-src')
chk(not marker.exists(), 'sudo still never reached after all the rw refusals above')

print('rw only: build and restart-aislebot (and nothing next to them)')
help_rw, help_ro = run('rw', 'help')[1], run('ro', 'help')[1]
chk('build PKG' in help_rw and 'restart-aislebot' in help_rw, 'rw help lists build and restart-aislebot')
chk('build PKG' not in help_ro and 'restart-aislebot' not in help_ro, 'ro help lists neither')
denied('ro', 'build mecanum_robot', 'rw_only', 'ro key cannot build')
denied('ro', 'restart-aislebot', 'rw_only', 'ro key cannot restart')
chk(not marker.exists(), 'ro: sudo was not reached')

out = allowed('rw', 'build mecanum_robot', 'STUB colcon build --symlink-install --packages-select mecanum_robot')
chk(f'CWD={home / "ros2_ws"}' in out, 'build runs inside ~/ros2_ws')
for cmd, why in (('build', 'usage'),
                 ('build other_pkg', 'package'),
                 ('build ../mecanum_robot', 'package'),
                 ('build mecanum_robot extra', 'usage'),
                 ('build mecanum_robot --cmake-args', 'usage'),
                 ('build mecanum_robot;id', 'characters'),
                 ('build $(id)', 'characters'),
                 ('build scan_relay', 'no_such_package'),   # on the allowlist but absent in this fake home
                 ('colcon build', 'command'),
                 ('colcon build --packages-select mecanum_robot', 'command')):
    denied('rw', cmd, why)

allowed('rw', 'restart-aislebot', 'STUB sudo -n systemctl restart aislebot.service')
chk(marker.exists(), 'restart-aislebot is the one verb that reaches sudo')
out = allowed('rw', 'restart-aislebot', 'GATE,RESTARTED,state=STUB systemctl')
marker.unlink()
for cmd, why in (('restart-aislebot now', 'usage'),
                 ('restart-aislebot aislebot.service', 'usage'),
                 ('restart-aislebot other.service', 'usage'),
                 ('restart-aislebot;id', 'characters'),
                 ('systemctl restart aislebot.service', 'verb'),
                 ('systemctl stop aislebot.service', 'verb'),
                 ('systemctl start aislebot.service', 'verb'),
                 ('sudo systemctl restart aislebot.service', 'command'),
                 ('sudo -n systemctl restart ssh.service', 'command'),
                 ('sudo ls', 'command'),
                 ('ros2 topic pub /cmd_vel geometry_msgs/msg/Twist', None),
                 ('ros2 launch mecanum_robot aislebot_full.launch.py', 'ros2_verb')):
    denied('rw', cmd, why)
chk(not marker.exists(), 'after the near-misses, sudo was still not reached')

sudo_fail.write_text('x')                       # simulate: sudoers line not installed
rc, out, err = run('rw', 'restart-aislebot')
chk(rc == 1 and 'RESTART_FAILED' in err and 'GATE,RESTARTED' not in out,
    'restart-aislebot fails cleanly (no hang, no success message) when sudo -n is refused')
sudo_fail.unlink()
marker.unlink(missing_ok=True)

print('audit log')
logf = home / 'aislebot_logs/claude_ssh.log'
lines = logf.read_text().splitlines() if logf.exists() else []
chk(len(lines) == _calls, f'one log line per attempt ({len(lines)} lines, {_calls} attempts)')
chk(any(' ALLOW' in ln for ln in lines) and any(' DENY(' in ln for ln in lines),
    'both allowed and refused attempts are logged')
chk(all(ln.split(' ')[1] in ('ro', 'rw') for ln in lines), 'every line names the key (ro or rw)')
chk(not any('PRIVATE KEY' in ln for ln in lines), 'file contents never reach the log')

shutil.rmtree(root, ignore_errors=True)
print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
