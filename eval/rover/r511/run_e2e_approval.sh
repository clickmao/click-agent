#!/usr/bin/env bash
# R511 真机 E2E: delete_file + 人工审批通道闭环 (AOT + frontend-api + 真链真模型)。
# 两臂 (显式声明 = 单变量): approve=true ⇒ 文件必须真被删; approve=false ⇒ 文件必须原封不动。
# 臂间独立: 每臂全新 host 进程 + 全新工作区 + 独立 frontend session (R509 铁律)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
BIN=${BIN:-/tmp/pub_r511/agenthost}
D=${D:-/tmp/r511/e2e}
PORTA=${PORTA:-48681}
PORTB=${PORTB:-48682}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$D"
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
python3 "$R/r483/preflight_gate.py" --round R511 --out "$D/gate.json" >/dev/null 2>&1
v=$(python3 -c "import json;print(json.load(open('$D/gate.json'))['verdict'])" 2>/dev/null)
log "闸: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_FRONTEND_TOKEN="r511-approval-token"

run_arm(){ # $1=臂名 $2=端口 $3=approve(true|false)
  local arm=$1 port=$2 appr=$3 ws="$D/ws-$1"
  rm -rf "$ws"; mkdir -p "$ws"
  printf 'delete me\n' > "$ws/victim.txt"
  export AGENTFRAMEWORK_FRONTEND_SESSION="frontend-r511-$arm-$(date +%s)"
  export AGENTFRAMEWORK_WORKSPACE="$ws"
  export AGENTFRAMEWORK_PY_RUN=1
  export AGENTFRAMEWORK_ACTION_AUDIT="$D/audit-$arm"
  export ACTION_MAX_STEPS=${ACTION_MAX_STEPS:-8}
  export AGENTFRAMEWORK_ACTION_MAX_STEPS=${AGENTFRAMEWORK_ACTION_MAX_STEPS:-8}
  setsid nohup "$BIN" --frontend-api "$port" > "$D/host-$arm.log" 2>&1 & HPID=$!
  local ok=0
  for i in $(seq 1 60); do
    python3 - "$port" <<'PY' >/dev/null 2>&1 && { ok=1; break; }
import socket,sys
s=socket.create_connection(("127.0.0.1",int(sys.argv[1])),timeout=1); s.close()
PY
    sleep 1
  done
  [ "$ok" = 1 ] || { log "[致命] $arm frontend-api 未监听 :$port"; tail -5 "$D/host-$arm.log"; kill $HPID 2>/dev/null; return 3; }
  log "$arm host up pid=$HPID :$port ws=$ws approve=$appr"
  python3 "$R/r511/probe_frontend_approval.py" --port "$port" --out "$D/$arm.json" \
     --victim "$ws/victim.txt" --approve "$appr" 2>&1 | tail -2
  local prc=${PIPESTATUS[0]}
  kill $HPID 2>/dev/null; pkill -P $HPID 2>/dev/null; sleep 1
  log "$arm probe_rc=$prc"
  return $prc
}

run_arm approve "$PORTA" true;  RCA=$?
run_arm deny    "$PORTB" false; RCB=$?
python3 "$R/r511/assert_e2e_approval.py" --approve-json "$D/approve.json" --deny-json "$D/deny.json" \
  --json "$D/e2e-assert.json"; RC=$?
log "ARM_RC=$RCA/$RCB E2E_RC=$RC"
exit $RC
