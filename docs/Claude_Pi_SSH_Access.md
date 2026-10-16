# Letting Claude work on the Pi over SSH

Written 16 Oct 2026. Nothing in here is installed yet. It is a plan plus the
files to carry it out, one step at a time.

The idea is simple. Claude Code runs on the work PC (VS Code extension or the
CLI), with this repo cloned there. When it needs to look at the Pi, it runs
`ssh nab-pi-ro "<something>"`. On the Pi, that key is locked to one script,
`system/claude_ssh_gate.sh`, which runs the request only if it matches a short
list of safe verbs. Everything else is refused on the Pi itself. So the limit
holds even if the PC-side settings are wrong, and even if Claude reads
something hostile (a log line, a web page) that tries to talk it into more.

This does not work from the cloud session that wrote it. That session has no
route to the Pi. It is for Claude Code running on the PC.

## What each key can do

Two keys, because looking and changing are different risks.

| | `ro` key | `rw` key |
|---|---|---|
| read files under `~` and `/opt/ros` | yes | yes |
| `ros2 topic/node/param/service` introspection (list, echo, hz, get, info) | yes | yes |
| `journalctl -u X.service`, `systemctl status X.service`, `vcgencmd`, `lsusb`, `df`, `free` | yes | yes |
| replace a source file under `ros2_ws/src` or `ros2_ws/tools` | no | yes, with backup and hashes |
| shell, `sudo`, restart/stop a service, publish, service call, param set, launch, bag play, serial ports | never | never |
| `.ssh`, `.config`, shell history, anything named like a key, token or password | refused | refused |

Day to day you want the `ro` key only. Load the `rw` key when you have agreed a
specific change, then unload it.

## What this does not protect against

The `rw` key can change code that the robot runs as `aritra` the next time
someone restarts the service. That is real power, even though the gate cannot
start anything itself. The protection is the restart: it needs `sudo`, which
needs your password, so a change sits harmlessly until you have read the diff
and typed it. Do not skip that read.

`phone_dashboard.py` is refused by `install-src` on purpose. Per CLAUDE.md, a
dashboard edit is only proven by loading the page in a browser and watching its
console. That has to happen at your keyboard.

The gate has no verb that moves the robot. Driving stays manual with the
E-stop in reach. If you ever want one (say, a zero-velocity publish), that is a
separate decision with its own test, not a loosening of this one.

Remote-SSH in VS Code (Way 2 in our earlier discussion) is a different door. It
opens a full shell as `aritra` and the gate does not apply to it. Use one or
the other on purpose.

## Install, one step at a time

Paste the output of each step back before doing the next.

**Step 1, on the PC.** Make two keys. Give each a passphrase you will remember.
The passphrase is what keeps a stranger at your unlocked-but-idle PC from using
them.

```
ssh-keygen -t ed25519 -f ~/.ssh/nab_claude_ro -C claude-ro
ssh-keygen -t ed25519 -f ~/.ssh/nab_claude_rw -C claude-rw
```

On Windows PowerShell, `~` works for `ssh-keygen`; if it complains, use
`$env:USERPROFILE\.ssh\nab_claude_ro`.

**Step 2, on the PC.** Copy the gate into your scp folder and send it to the Pi,
the way you always do. Check the hash first (expected below), then on the Pi:

```
sha256sum /tmp/claude_ssh_gate.sh
```

Expected: `66ca48907b772c0c0e73f5ce4c028fd72162a8d2676cc49dbd9115a2acd422bd`
(if the file in the repo has changed since, trust the repo's `sha256sum`, not
this line).

**Step 3, on the Pi.** Install it owned by root, so nothing running as `aritra`
(including a compromised key) can edit it. This is the one `sudo`.

```
sudo install -o root -g root -m 755 /tmp/claude_ssh_gate.sh /usr/local/bin/claude_ssh_gate.sh
sha256sum /usr/local/bin/claude_ssh_gate.sh
```

**Step 4, on the Pi.** Add the two public keys to `~/.ssh/authorized_keys`. One
line each. Paste the contents of `nab_claude_ro.pub` and `nab_claude_rw.pub`
after the option text:

```
command="/usr/local/bin/claude_ssh_gate.sh ro",restrict ssh-ed25519 AAAA...ro-key... claude-ro
command="/usr/local/bin/claude_ssh_gate.sh rw",restrict ssh-ed25519 AAAA...rw-key... claude-rw
```

`restrict` turns off port forwarding, agent forwarding, X11 and a terminal.
`command=` makes the Pi ignore whatever the client asked for and run the gate
instead, with the request in `$SSH_ORIGINAL_COMMAND`. Keep your own normal key
line as it is.

**Step 5, on the PC.** Add to `~/.ssh/config`:

```
Host nab-pi-ro
    HostName 10.42.0.1
    User aritra
    IdentityFile ~/.ssh/nab_claude_ro
    IdentitiesOnly yes
    RequestTTY no
    ServerAliveInterval 15

Host nab-pi-rw
    HostName 10.42.0.1
    User aritra
    IdentityFile ~/.ssh/nab_claude_rw
    IdentitiesOnly yes
    RequestTTY no
```

**Step 6, on the PC, the acceptance test.** Load the read-only key and try
things that must work and things that must not:

```
ssh-add ~/.ssh/nab_claude_ro
ssh nab-pi-ro "help"
ssh nab-pi-ro "ros2 topic list"
ssh nab-pi-ro "ros2 topic echo --once /imu/data"
ssh nab-pi-ro "systemctl status aislebot.service"
```

All four should print something useful. Now the refusals. Every one of these
should print `[GATE,DENIED,...]` and nothing else:

```
ssh nab-pi-ro "sudo ls"
ssh nab-pi-ro "cat .ssh/id_ed25519"
ssh nab-pi-ro "ros2 topic pub /cmd_vel geometry_msgs/msg/Twist {}"
ssh nab-pi-ro "systemctl restart aislebot.service"
ssh nab-pi-ro "cat notes.txt; id"
ssh nab-pi-ro
scp nab-pi-ro:.ssh/id_ed25519 .
```

The last two (an interactive login, and scp) should also fail, since the
forced command only answers verbs it knows.

If any of those prints anything it should not, remove the key line from
`authorized_keys` first, then tell me what it printed.

## Using it day to day

Start of the working session: `ssh-add ~/.ssh/nab_claude_ro` and type the
passphrase. End of the session, or any time you step away: `ssh-add -D`.
That drops every key from the agent, and with no key loaded Claude cannot
reach the Pi at all, because the passphrase prompt has nobody to answer it.
Ctrl+C your Claude session, too; it should not run when you are not there.

On Windows the OpenSSH agent is a service that ships switched off. Turn it on
once (Services, "OpenSSH Authentication Agent", set to Manual, start it). I am
not sure that agent honours `ssh-add -t 4h` for an automatic timeout on every
Windows build, so do not rely on it; `ssh-add -D` is the kill switch.

Writing a file with the `rw` key:

```
ssh-add ~/.ssh/nab_claude_rw
ssh nab-pi-rw "install-src ros2_ws/src/mecanum_robot/mecanum_robot/esp32_bridge.py" < esp32_bridge.py
```

It prints `[GATE,INSTALLED,path=...,before=<sha256>,after=<sha256>,backup=...]`.
The old file is in `~/ros2_ws/backup_claude/<timestamp>/`. Compare `after`
with `sha256sum esp32_bridge.py` on the PC, as the discipline in CLAUDE.md
asks. Then `ssh-add -d ~/.ssh/nab_claude_rw`. The restart is yours, by hand,
with `sudo`.

Because the install is a symlink install, no rebuild is needed for Python
files under `ros2_ws/src`; the restart picks them up.

## The record

Every attempt, allowed or refused, is one line in
`~/aislebot_logs/claude_ssh.log` on the Pi: time, `ro` or `rw`, the decision,
and the request with anything odd turned into `?`. File contents never go in it.
Skim it now and then, especially after a session where Claude read logs from
somewhere you do not control.

```
tail -n 30 ~/aislebot_logs/claude_ssh.log
```

## Taking access away

Delete the two lines from `~/.ssh/authorized_keys` on the Pi. That is the whole
revocation; the keys on the PC become useless. Do the same if the PC is ever
lost or handed back to IT.

## The PC-side fence

`.claude/settings.json` in this repo tells Claude Code to ask before any `rw`
call, to refuse raw `ssh`, `scp`, `sftp` and `ssh-add`, and not to read `~/.ssh`.
Treat it as a seatbelt that catches honest mistakes. It is not the boundary. The
boundary is the gate on the Pi, which does not care what the PC says.

## Changing the gate

Add a verb to `system/claude_ssh_gate.sh`, add cases to
`tools/tests/claude_ssh_gate_check.py` for what it must allow and for the
nearest thing it must still refuse, run the test, then redo steps 2 and 3. The
test fakes a home directory and stub binaries; it cannot prove sshd hands the
script the request the way this page says, which is why step 6 exists.
