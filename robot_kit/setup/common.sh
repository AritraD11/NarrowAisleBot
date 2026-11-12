# shellcheck shell=bash
# common.sh - sourced by every setup script. Not run on its own.
set -eo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/robot_kit_install.log"
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'
ok()   { echo -e "${G}  ok    $*${N}"; echo "ok    $*" >> "$LOG"; }
warn() { echo -e "${Y}  WARN  $*${N}"; echo "WARN  $*" >> "$LOG"; }
die()  { echo -e "${R}  FAIL  $*${N}"; echo "FAIL  $*" >> "$LOG"; exit 1; }
step() { echo -e "\n${C}${B}== $*${N}"; echo "== $* ($(date))" >> "$LOG"; }
run()  { echo "+ $*" >> "$LOG"; "$@" >> "$LOG" 2>&1 || die "command failed: $*  (see $LOG)"; }

[ "$(id -u)" != "0" ] || die "run as your normal user, not root (the scripts call sudo themselves)"

load_env() {
    [ -f "$KIT/setup/generated/robot.env" ] || die "no setup/generated/robot.env: run  python3 $KIT/generate.py  first"
    # shellcheck disable=SC1091
    source "$KIT/setup/generated/robot.env"
}
