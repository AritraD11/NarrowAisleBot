#!/bin/bash
# run_tests.sh - every automated check in the kit. Needs python3 (pyyaml,
# pyserial), g++ and make. The browser test also needs fastapi, uvicorn and
# Node with playwright; it is skipped if they are missing.
#
#   ./run_tests.sh          (about two minutes; the logger test runs in real time)
cd "$(dirname "$0")" || exit 1
export NODE_PATH="${NODE_PATH:-$(npm root -g 2>/dev/null)}"
set -o pipefail
fail=0
t() { echo; echo "######## $*"; "$@" || fail=$((fail+1)); }
t python3 tests/test_kinematics.py
t python3 tests/test_generate.py
t python3 tests/test_scan_and_tools.py
t python3 tests/test_firmware_sim.py
t python3 tests/test_logger_sim.py
if node -e "require('playwright')" 2>/dev/null && python3 -c "import fastapi, uvicorn" 2>/dev/null; then
  t node tests/test_dashboard_browser.js
else
  echo; echo "######## dashboard browser test SKIPPED (needs node + playwright, fastapi, uvicorn)"
fi
python3 generate.py > /dev/null      # leave the generated files matching robot_config.yaml
echo
[ "$fail" -eq 0 ] && echo "ALL TEST FILES PASSED" || echo "$fail TEST FILE(S) FAILED"
exit "$fail"
