#!/usr/bin/env bash
# R509 真机 E2E: AOT 二进制 + frontend-api + 真链真模型 ⇒ 任务事件域 (task.started/completed) + state.snapshot.tasks 可实际观测。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
BIN=${BIN:-/tmp/pub_r509/agenthost}
D=${D:-/tmp/r509/e2e}
PORT=${PORT:-48677}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$D"
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
# 起手闸 (单次 PASS; 真机探针不吃 token 区间, 只要求内存可用)
python3 "$R/r483/preflight_gate.py" --round R509 --out "$D/gate.json" >/dev/null 2>&1
v=$(python3 -c "import json;print(json.load(open('$D/gate.json'))['verdict'])" 2>/dev/null)
log "闸: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_FRONTEND_TOKEN="r509-probe-token"
export AGENTFRAMEWORK_FRONTEND_SESSION="frontend-r509-e2e-$(date +%s)"
export AGENTFRAMEWORK_WORKSPACE="$D/ws"; mkdir -p "$D/ws"
setsid nohup "$BIN" --frontend-api "$PORT" > "$D/host.log" 2>&1 & HPID=$!
ok=0; for i in $(seq 1 60); do
  python3 - "$PORT" <<'PY' >/dev/null 2>&1 && { ok=1; break; }
import socket,sys
s=socket.create_connection(("127.0.0.1",int(sys.argv[1])),timeout=1); s.close()
PY
  sleep 1; done
[ "$ok" = 1 ] || { log "[致命] frontend-api 未监听 :$PORT"; tail -5 "$D/host.log"; kill $HPID 2>/dev/null; exit 3; }
log "frontend-api up pid=$HPID :$PORT"
python3 "$R/r509/probe_frontend_tasks.py" --port "$PORT" --out "$D/e2e.json" 2>&1 | tail -2
python3 "$R/r509/assert_e2e_tasks.py" "$D/e2e.json" --json "$D/e2e-assert.json"; rc=$?
kill $HPID 2>/dev/null; pkill -P $HPID 2>/dev/null; sleep 1
log "E2E_RC=$rc"
exit $rc
