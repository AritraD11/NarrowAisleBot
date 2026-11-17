#!/bin/bash
# ================================================================
#  claude_ssh_gate.sh  ro|rw
#
#  Server-side gate for the SSH keys Claude uses to reach the Pi.
#  Installed as the FORCED COMMAND of a restricted key in
#  ~/.ssh/authorized_keys on the Pi (see docs/Claude_Pi_SSH_Access.md):
#
#     command="/usr/local/bin/claude_ssh_gate.sh ro",restrict ssh-ed25519 AAAA... claude-ro
#
#  Whatever the client asks for arrives in $SSH_ORIGINAL_COMMAND. This
#  script runs it only if it matches a short allowlist; everything else
#  is refused HERE, on the Pi, so the limit does not depend on what
#  Claude, the PC's settings or a prompt-injected page tries to do.
#
#  ro  read files under ~ and /opt/ros, logs, service status, ROS 2
#      introspection (topic/node/param/service list, echo, hz, get).
#  rw  everything in ro, plus  install-src REL_PATH  (new file contents
#      on stdin) into ~/ros2_ws/src or ~/ros2_ws/tools, with a backup,
#      before/after hashes and a syntax check for .py;
#      build PKG       colcon build of one of three named packages;
#      restart-aislebot   restart of aislebot.service, nothing else. It
#      calls  sudo -n  (never prompts), so it only works once the
#      operator has added the single sudoers line in
#      docs/Claude_Pi_SSH_Access.md. Without that line it fails.
#
#  Never allowed, in either mode: a shell, sudo as a general verb,
#  anything that publishes, calls a service, sets a parameter, launches or
#  plays a bag, writes to a serial port, stops or starts a service by any
#  other route, or reads keys. Nothing here can move the robot: there is
#  no verb that publishes a velocity or sends a goal.
#
#  Every decision is appended to ~/aislebot_logs/claude_ssh.log.
# ================================================================
set -u
umask 077

MODE="${1:-}"
if [ "$MODE" != ro ] && [ "$MODE" != rw ]; then
    echo "[GATE,DENIED,bad_mode]" >&2
    exit 2
fi

# GATE_PATH exists only so the test can put stub binaries first. sshd does
# not pass client environment variables to a forced command by default.
PATH="${GATE_PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
export PATH

HOME_DIR="${HOME:-}"
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
    echo "[GATE,DENIED,no_home]" >&2
    exit 2
fi
HOME_DIR="$(cd "$HOME_DIR" && pwd -P)"
LOGDIR="$HOME_DIR/aislebot_logs"
CMD="${SSH_ORIGINAL_COMMAND:-}"

log() {
    local safe
    safe="$(printf '%s' "$CMD" | tr -c 'A-Za-z0-9 _./:=@%+,-' '?' | head -c 200)"
    mkdir -p "$LOGDIR" 2>/dev/null
    printf '%s %s %s | %s\n' "$(date -Is)" "$MODE" "$1" "$safe" >> "$LOGDIR/claude_ssh.log" 2>/dev/null
    return 0
}

deny() {
    log "DENY($1)"
    printf '[GATE,DENIED,%s]  (send "help" to list what this key may run)\n' "$1" >&2
    exit 126
}

# ── 1. Characters. No quotes, no globs, no redirects, no separators, no
#       substitutions, no newlines: nothing a shell could act on.
CHARS_RE='^[A-Za-z0-9 _./:=@%+,-]+$'
[ -n "$CMD" ] || deny empty
[ "${#CMD}" -le 300 ] || deny too_long
[[ "$CMD" =~ $CHARS_RE ]] || deny characters

IFS=' ' read -r -a A <<< "$CMD"
[ "${#A[@]}" -ge 1 ] || deny empty
[ "${#A[@]}" -le 12 ] || deny too_many_words

# ── 2. Paths.
secret_path() {      # $1 = resolved absolute path; 0 = looks like a secret
    local lc="${1,,}"
    case "$lc" in
        */.ssh|*/.ssh/*|*/.gnupg|*/.gnupg/*|*/.config|*/.config/*|*/.aws|*/.aws/*|\
        */.netrc*|*/.bash_history*|*/.claude|*/.claude/*|*/.git-credentials*|*/.docker/*|\
        *password*|*passwd*|*secret*|*token*|*credential*|*id_rsa*|*id_ed25519*|*id_ecdsa*|\
        *authorized_keys*|*known_hosts*|*.pem|*.key) return 0 ;;
    esac
    return 1
}

path_ok() {          # $1 = path, $2 = 1 if /dev listings are acceptable (ls only)
    local raw="$1" devok="${2:-0}" abs res
    [ -n "$raw" ] || return 1
    case "$raw" in -*) return 1 ;; esac
    [[ "$raw" == *..* ]] && return 1
    if [ "$devok" = 1 ]; then
        case "$raw" in
            /dev|/dev/serial/by-id|/dev/esp32|/dev/mega|/dev/ttyUSB[0-9]|/dev/ttyUSB[0-9][0-9]|/dev/ttyACM[0-9]) return 0 ;;
        esac
    fi
    if [[ "$raw" == /* ]]; then abs="$raw"; else abs="$HOME_DIR/$raw"; fi
    res="$(realpath -m -- "$abs" 2>/dev/null)" || return 1     # follows symlinks
    case "$res" in
        "$HOME_DIR"|"$HOME_DIR"/*|/opt/ros|/opt/ros/*) ;;
        *) return 1 ;;
    esac
    secret_path "$res" && return 1
    return 0
}

rec_ok() {           # recursive search only inside source, tools and logs
    local res
    res="$(realpath -m -- "$HOME_DIR/$1" 2>/dev/null)" || return 1
    [[ "$1" == /* ]] && res="$(realpath -m -- "$1" 2>/dev/null)"
    case "$res" in
        "$HOME_DIR/ros2_ws/src"|"$HOME_DIR/ros2_ws/src"/*|\
        "$HOME_DIR/ros2_ws/tools"|"$HOME_DIR/ros2_ws/tools"/*|\
        "$HOME_DIR/aislebot_logs"|"$HOME_DIR/aislebot_logs"/*) return 0 ;;
    esac
    return 1
}

num_ok() {           # $1 digits, 1 <= value <= $2
    [[ "$1" =~ ^[0-9]{1,5}$ ]] || return 1
    [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le "$2" ]
}

# ── 3. Run something that passed every check. Output capped at 1 MB,
#       wall-clock capped, no stdin.
limited() {          # $1 = timeout seconds, rest = command
    local t="$1"; shift
    log ALLOW
    cd "$HOME_DIR" || exit 1
    timeout -k 2 "$t" "$@" 2>&1 </dev/null | head -c 1000000
    exit "${PIPESTATUS[0]}"
}

ros_env() {
    # The same environment start_aislebot.sh gives the service, or the CLI
    # looks at a different DDS domain and sees nothing.
    set +u
    [ -f /opt/ros/jazzy/setup.bash ] && . /opt/ros/jazzy/setup.bash
    [ -f "$HOME_DIR/ros2_ws/install/setup.bash" ] && . "$HOME_DIR/ros2_ws/install/setup.bash"
    set -u
    export PYTHONUNBUFFERED=1        # so a timeout kill does not lose buffered hz/echo output
    export ROS_DOMAIN_ID=42
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" priority="default" multicast="false"/></Interfaces></General></Domain></CycloneDDS>'
}

TOPIC_RE='^/[A-Za-z0-9_/]+$'
FIELD_RE='^[A-Za-z0-9_.]+$'
PARAM_RE='^[A-Za-z0-9_.]+$'
UNIT_RE='^[A-Za-z0-9_.@-]+\.service$'
TYPE_RE='^[A-Za-z0-9_/]+$'

run_help() {
    log ALLOW
    cat <<'HELP'
[GATE,HELP] words only: letters, digits and  _ . / : = @ % + , -   (no quotes, globs, pipes, redirects)
  cat PATH..           head|tail [-n N] PATH..         ls [-lahtR1] PATH..
  wc -l PATH           stat PATH                       sha256sum PATH..
  grep [-nicrlwFH] PATTERN PATH..   (-r only under ros2_ws/src, ros2_ws/tools, aislebot_logs)
  journalctl -u UNIT.service [-n N] [-b]      systemctl status|is-active|is-enabled UNIT.service
  uptime date whoami hostname lsusb  uname -a  df -h  free -h  vcgencmd get_throttled|measure_temp
  ros2 topic list|type T|info T|hz T|bw T|echo [--once] [--no-arr] [--field F] T
  ros2 node list|info N   ros2 param list [N]|get N P|dump N|describe N P
  ros2 service list|type S    ros2 interface show TYPE    ros2 bag info PATH
  paths: under ~ and /opt/ros only; keys, history, .config and secret-looking names refused
HELP
    if [ "$MODE" = rw ]; then
        cat <<'HELP'
  install-src REL_PATH   (rw key) new contents on stdin -> ~/REL_PATH, which must be under
                         ros2_ws/src or ros2_ws/tools. Backup + before/after sha256 are printed.
                         .py .yaml .yml .md .txt .cfg .xml .json .launch.py only; <= 1 MB;
                         .py is syntax-checked; phone_dashboard.py is refused (browser check needed).
  build PKG              (rw key) colcon build --symlink-install of mecanum_robot | mecanum_navigation | scan_relay
  restart-aislebot       (rw key) restart aislebot.service; needs the one sudoers line, else it fails
HELP
    fi
    exit 0
}

install_src() {
    [ "$MODE" = rw ] || deny rw_only
    [ "${#A[@]}" -eq 2 ] || deny usage
    local rel="${A[1]}" target dir base ext tmp bak ts before after stamp
    [[ "$rel" == /* ]] && deny absolute_path
    [[ "$rel" == *..* ]] && deny parent_ref
    case "$rel" in
        ros2_ws/src/*|ros2_ws/tools/*) ;;
        *) deny outside_src ;;
    esac
    base="$(basename -- "$rel")"
    [ "$base" = phone_dashboard.py ] && deny dashboard_needs_browser_check
    case "$base" in
        *.py|*.yaml|*.yml|*.md|*.txt|*.cfg|*.xml|*.json) ;;
        *) deny extension ;;
    esac
    target="$(realpath -m -- "$HOME_DIR/$rel" 2>/dev/null)" || deny path
    case "$target" in
        "$HOME_DIR/ros2_ws/src"/*|"$HOME_DIR/ros2_ws/tools"/*) ;;
        *) deny outside_src_resolved ;;
    esac
    secret_path "$target" && deny secret_path
    dir="$(dirname -- "$target")"
    [ -d "$dir" ] || deny no_such_directory
    [ -L "$dir" ] && deny symlinked_directory
    { [ -e "$target" ] && [ ! -f "$target" ]; } && deny not_a_regular_file

    tmp="$(mktemp "$dir/.claude_tmp.XXXXXX")" || deny cannot_create
    trap 'rm -f "$tmp"' EXIT
    head -c 1048577 > "$tmp"
    local size
    size="$(stat -c %s "$tmp")"
    [ "$size" -gt 0 ] || deny empty_input
    [ "$size" -le 1048576 ] || deny too_large
    case "$base" in
        *.py)
            python3 -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1])' "$tmp" \
                2>/dev/null || deny python_syntax ;;
    esac

    before=none; bak=none
    if [ -f "$target" ]; then
        before="$(sha256sum -- "$target" | cut -d' ' -f1)"
        stamp="$(date +%Y%m%d_%H%M%S)"
        bak="$HOME_DIR/ros2_ws/backup_claude/$stamp/${rel//\//__}"
        mkdir -p -- "$(dirname -- "$bak")" && cp -p -- "$target" "$bak" || deny backup_failed
        chmod --reference="$target" "$tmp" 2>/dev/null
    else
        chmod 644 "$tmp"
    fi
    mv -f -- "$tmp" "$target" || deny write_failed
    trap - EXIT
    after="$(sha256sum -- "$target" | cut -d' ' -f1)"
    log "ALLOW(install-src $rel bytes=$size)"
    printf '[GATE,INSTALLED,path=%s,bytes=%s,before=%s,after=%s,backup=%s]\n' \
        "$rel" "$size" "$before" "$after" "${bak#"$HOME_DIR"/}"
    exit 0
}

BUILD_PKGS=(mecanum_robot mecanum_navigation scan_relay)

build_pkg() {
    [ "$MODE" = rw ] || deny rw_only
    [ "${#A[@]}" -eq 2 ] || deny usage
    local pkg="${A[1]}" ok=0 p
    for p in "${BUILD_PKGS[@]}"; do [ "$pkg" = "$p" ] && ok=1; done
    [ "$ok" = 1 ] || deny package
    [ -d "$HOME_DIR/ros2_ws/src/$pkg" ] || deny no_such_package
    ros_env
    log "ALLOW(build $pkg)"
    cd "$HOME_DIR/ros2_ws" || exit 1
    # tail, not head: with a build log the end is the part that says whether it worked.
    timeout -k 5 900 colcon build --symlink-install --packages-select "$pkg" 2>&1 </dev/null | tail -c 30000
    exit "${PIPESTATUS[0]}"
}

restart_aislebot() {
    [ "$MODE" = rw ] || deny rw_only
    [ "${#A[@]}" -eq 1 ] || deny usage
    log "ALLOW(restart-aislebot)"
    cd "$HOME_DIR" || exit 1
    local rc
    # sudo -n: never asks for a password, so without the sudoers line this fails
    # instead of hanging. The unit name is fixed here, not taken from the client.
    timeout -k 2 60 sudo -n systemctl restart aislebot.service 2>&1 </dev/null | head -c 2000
    rc="${PIPESTATUS[0]}"
    if [ "$rc" -ne 0 ]; then
        printf '[GATE,RESTART_FAILED,rc=%s]  (is the sudoers line installed?)\n' "$rc" >&2
        exit 1
    fi
    # GATE_RESTART_WAIT exists only so the test does not sleep; sshd does not pass it.
    sleep "${GATE_RESTART_WAIT:-3}"
    printf '[GATE,RESTARTED,state=%s]\n' "$(systemctl is-active aislebot.service 2>&1 | head -c 40)"
    exit 0
}

# ── 4. Dispatch. Anything not listed falls through to a refusal.
cmd="${A[0]}"
case "$cmd" in

help) run_help ;;

install-src) install_src ;;

build) build_pkg ;;

restart-aislebot) restart_aislebot ;;

cat)
    [ "${#A[@]}" -ge 2 ] && [ "${#A[@]}" -le 6 ] || deny usage
    for p in "${A[@]:1}"; do path_ok "$p" || deny path; done
    limited 10 cat -- "${A[@]:1}" ;;

head|tail)
    n=; idx=1
    if [ "${A[1]:-}" = -n ]; then
        num_ok "${A[2]:-x}" 5000 || deny count
        n="${A[2]}"; idx=3
    fi
    [ "${#A[@]}" -gt "$idx" ] && [ "${#A[@]}" -le $((idx + 3)) ] || deny usage
    for p in "${A[@]:$idx}"; do path_ok "$p" || deny path; done
    if [ -n "$n" ]; then limited 10 "$cmd" -n "$n" -- "${A[@]:$idx}"
    else                  limited 10 "$cmd" -- "${A[@]:$idx}"; fi ;;

ls)
    flags=(); paths=()
    for w in "${A[@]:1}"; do
        if [[ "$w" == -* ]]; then
            [[ "$w" =~ ^-[lahtR1]+$ ]] || deny flag
            flags+=("$w")
        else
            path_ok "$w" 1 || deny path
            paths+=("$w")
        fi
    done
    [ "${#paths[@]}" -le 5 ] || deny usage
    [ "${#paths[@]}" -ge 1 ] || paths=(.)
    limited 10 ls "${flags[@]}" -- "${paths[@]}" ;;

wc)
    [ "${#A[@]}" -eq 3 ] && [ "${A[1]}" = -l ] || deny usage
    path_ok "${A[2]}" || deny path
    limited 10 wc -l -- "${A[2]}" ;;

stat)
    [ "${#A[@]}" -eq 2 ] || deny usage
    path_ok "${A[1]}" || deny path
    limited 10 stat -- "${A[1]}" ;;

sha256sum)
    [ "${#A[@]}" -ge 2 ] && [ "${#A[@]}" -le 9 ] || deny usage
    for p in "${A[@]:1}"; do path_ok "$p" || deny path; done
    limited 10 sha256sum -- "${A[@]:1}" ;;

grep)
    flags=(); pat=; paths=(); recursive=0
    for w in "${A[@]:1}"; do
        if [ -z "$pat" ] && [[ "$w" == -* ]]; then
            [[ "$w" =~ ^-[nicrlwFH]+$ ]] || deny flag
            [[ "$w" == *r* ]] && recursive=1
            flags+=("$w")
        elif [ -z "$pat" ]; then
            pat="$w"
        else
            path_ok "$w" || deny path
            paths+=("$w")
        fi
    done
    [ -n "$pat" ] && [ "${#paths[@]}" -ge 1 ] && [ "${#paths[@]}" -le 5 ] || deny usage
    if [ "$recursive" = 1 ]; then
        for p in "${paths[@]}"; do rec_ok "$p" || deny recursive_scope; done
    fi
    limited 15 grep "${flags[@]}" -e "$pat" -- "${paths[@]}" ;;

journalctl)
    unit=; n=100; i=1
    while [ "$i" -lt "${#A[@]}" ]; do
        case "${A[$i]}" in
            -u)  i=$((i + 1)); [[ "${A[$i]:-}" =~ $UNIT_RE ]] || deny unit; unit="${A[$i]}" ;;
            -n)  i=$((i + 1)); num_ok "${A[$i]:-x}" 1000 || deny count; n="${A[$i]}" ;;
            -b)  : ;;
            --no-pager) : ;;
            *)   deny flag ;;
        esac
        i=$((i + 1))
    done
    [ -n "$unit" ] || deny unit
    bflag=(); [[ " ${A[*]} " == *" -b "* ]] && bflag=(-b)
    limited 20 journalctl --no-pager "${bflag[@]}" -u "$unit" -n "$n" ;;

systemctl)
    [ "${#A[@]}" -ge 3 ] && [ "${#A[@]}" -le 4 ] || deny usage
    case "${A[1]}" in status|is-active|is-enabled) ;; *) deny verb ;; esac
    [[ "${A[2]}" =~ $UNIT_RE ]] || deny unit
    [ "${#A[@]}" -eq 3 ] || [ "${A[3]}" = --no-pager ] || deny flag
    limited 10 systemctl --no-pager "${A[1]}" "${A[2]}" ;;

uptime|date|whoami|hostname|lsusb)
    [ "${#A[@]}" -eq 1 ] || deny usage
    limited 10 "$cmd" ;;

uname)
    [ "$CMD" = "uname -a" ] || deny usage
    limited 10 uname -a ;;

df)
    [ "$CMD" = "df -h" ] || deny usage
    limited 10 df -h ;;

free)
    [ "$CMD" = "free -h" ] || deny usage
    limited 10 free -h ;;

vcgencmd)
    [ "${#A[@]}" -eq 2 ] || deny usage
    case "${A[1]}" in get_throttled|measure_temp|pmic_read_adc) ;; *) deny verb ;; esac
    limited 10 vcgencmd "${A[1]}" ;;

ros2)
    [ "${#A[@]}" -ge 3 ] || deny usage
    key="${A[1]}:${A[2]}:${#A[@]}"
    args=()
    case "$key" in
        topic:list:3)  args=(topic list) ;;
        topic:list:4)  [ "${A[3]}" = -t ] || deny flag; args=(topic list -t) ;;
        topic:type:4|topic:info:4|topic:hz:4|topic:bw:4)
            [[ "${A[3]}" =~ $TOPIC_RE ]] || deny topic; args=(topic "${A[2]}" "${A[3]}") ;;
        topic:echo:*)
            args=(topic echo); i=3; topic=
            while [ "$i" -lt "${#A[@]}" ]; do
                case "${A[$i]}" in
                    --once|--no-arr|--no-str) args+=("${A[$i]}") ;;
                    --field) i=$((i + 1)); [[ "${A[$i]:-}" =~ $FIELD_RE ]] || deny field
                             args+=(--field "${A[$i]}") ;;
                    *)  [ -z "$topic" ] && [[ "${A[$i]}" =~ $TOPIC_RE ]] || deny topic
                        topic="${A[$i]}" ;;
                esac
                i=$((i + 1))
            done
            [ -n "$topic" ] || deny topic
            args+=("$topic") ;;
        node:list:3)   args=(node list) ;;
        node:info:4)   [[ "${A[3]}" =~ $TOPIC_RE ]] || deny node; args=(node info "${A[3]}") ;;
        param:list:3)  args=(param list) ;;
        param:list:4)  [[ "${A[3]}" =~ $TOPIC_RE ]] || deny node; args=(param list "${A[3]}") ;;
        param:dump:4)  [[ "${A[3]}" =~ $TOPIC_RE ]] || deny node; args=(param dump "${A[3]}") ;;
        param:get:5|param:describe:5)
            [[ "${A[3]}" =~ $TOPIC_RE ]] && [[ "${A[4]}" =~ $PARAM_RE ]] || deny param
            args=(param "${A[2]}" "${A[3]}" "${A[4]}") ;;
        service:list:3) args=(service list) ;;
        service:type:4) [[ "${A[3]}" =~ $TOPIC_RE ]] || deny service; args=(service type "${A[3]}") ;;
        interface:show:4) [[ "${A[3]}" =~ $TYPE_RE ]] || deny type; args=(interface show "${A[3]}") ;;
        bag:info:4)    path_ok "${A[3]}" || deny path; args=(bag info "${A[3]}") ;;
        *) deny ros2_verb ;;
    esac
    ros_env
    limited 20 ros2 "${args[@]}" ;;

*)
    deny command ;;
esac
