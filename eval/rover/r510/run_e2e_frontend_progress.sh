#!/usr/bin/env bash
# R510 真机 E2E: AOT 二进制 + frontend-api + **动作环开** + 真模型
#   ⇒ task.progress 真发 (步进事实来自真实工具执行) + 审批回程负控。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
BIN=${BIN:-/tmp/pub_r510/agenthost}
D=${D:-/tmp/r510/e2e}
PORT=${PORT:-48678}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$D" "$D/ws"
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
python3 "$R/r483/preflight_gate.py" --round R510 --out "$D/gate.json" >/dev/null 2>&1
v=$(python3 -c "import json;print(json.load(open('$D/gate.json'))['verdict'])" 2>/dev/null)
log "闸: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_FRONTEND_TOKEN="r510-probe-token"
export AGENTFRAMEWORK_FRONTEND_SESSION="frontend-r510-e2e-$(date +%s)"
export AGENTFRAMEWORK_WORKSPACE="$D/ws"
# 配置根显式钉死 (cwd=$D 时向上 8 级找不到 config ⇒ 空配置 ⇒ 无模型可调, R509 靠 cwd=REPO 隐式命中)
export AGENTFRAMEWORK_CONFIG="$REPO/config"
# 动作环必须开: 无工具声明 ⇒ 无工具调用 ⇒ task.progress 无从产生 (R509 的 E2E 实测踩点)
export AGENTFRAMEWORK_ACTION_MAX_STEPS="${AGENTFRAMEWORK_ACTION_MAX_STEPS:-6}"
cd "$D"
setsid nohup "$BIN" --frontend-api "$PORT" > "$D/host.log" 2>&1 & HPID=$!
ok=0; for i in $(seq 1 60); do
  python3 - "$PORT" <<'PY' >/dev/null 2>&1 && { ok=1; break; }
import socket,sys
s=socket.create_connection(("127.0.0.1",int(sys.argv[1])),timeout=1); s.close()
PY
  sleep 1; done
[ "$ok" = 1 ] || { log "[致命] frontend-api 未监听 :$PORT"; tail -5 "$D/host.log"; kill $HPID 2>/dev/null; exit 3; }
log "frontend-api up pid=$HPID :$PORT 动作环上限=$AGENTFRAMEWORK_ACTION_MAX_STEPS"
rm -f "$D/e2e.json"
python3 "$R/r510/probe_frontend_progress.py" --port "$PORT" --out "$D/e2e.json" 2>&1 | tail -3
python3 "$R/r510/assert_e2e_progress.py" "$D/e2e.json" --json "$D/e2e-assert.json"; rc=$?
kill $HPID 2>/dev/null; pkill -P $HPID 2>/dev/null; sleep 1
log "E2E_RC=$rc"
exit $rc
