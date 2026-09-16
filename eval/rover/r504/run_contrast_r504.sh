#!/usr/bin/env bash
# R504 主线对照 runner: 外部真值(codex-cli) × 本侧(AOT agenthost) —— 同冻结题集 / 同 adapter / 同机械判分
#
# 铁律: 预注册先于首跑; 两侧工作目录初始逐字节同; 缺任一侧面 ⇒ rc=3; 收口按 /proc 扫 + 端口断言。
# 用法: bash eval/rover/r504/run_contrast_r504.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${R504_ENV:-/tmp/r504_env}
PORT=${R504_ADAPTER_PORT:-48626}
CODEX_BIN=${R504_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
AGENT_BIN=${PROBE_AGENT_BIN:-/tmp/pub_r504/agenthost/agenthost}
TASKS=$REPO/eval/rover/r504/taskset-r504.json
log() { echo "[R504] $*"; }
cd "$REPO" || exit 3

# --- 0 预注册（先于首跑）------------------------------------------------------
if ! python3 eval/rover/r504/make_prereg_r504.py --check; then
  log "[致命] 预注册非 UNIFORM ⇒ 弃权 (rc=3)"; exit 3
fi
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex: $CODEX_BIN"; exit 3; }
[ -f "$AGENT_BIN" ] && [ -x "$AGENT_BIN" ] || { log "[致命] 缺 agenthost(必须是可执行文件): $AGENT_BIN"; exit 3; }
[ -f "$TASKS" ]    || { log "[致命] 缺冻结题集: $TASKS"; exit 3; }

# --- 1 夹具（两侧同环境）------------------------------------------------------
rm -rf "$D"; mkdir -p "$D"/{codex/work,agent/work,logs,adapter}
man() { (cd "$1" && find . -type f -printf '%P %s\n' | LC_ALL=C sort | md5sum | cut -d' ' -f1); }
mc=$(man "$D/codex/work"); ma=$(man "$D/agent/work")
[ "$mc" = "$ma" ] || { log "[致命] 初始夹具不同 ($mc vs $ma)"; exit 3; }
log "夹具同形 mc=$mc ma=$ma"
log "本侧 agenthost sha256=$(sha256sum "$AGENT_BIN" | cut -d' ' -f1) bytes=$(stat -c%s "$AGENT_BIN")"

# --- 2 adapter（同一真实模型网关）---------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT=$D/adapter setsid nohup python3 eval/rover/r455/adapter_tools.py "$PORT" \
  >"$D/logs/adapter.log" 2>&1 &
APID=$!
ready=0
for _ in $(seq 1 40); do
  if curl -s -m 3 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then ready=1; break; fi
  kill -0 "$APID" 2>/dev/null || { log "[致命] adapter 进程退出"; tail -5 "$D/logs/adapter.log"; exit 3; }
  sleep 0.5
done
[ "$ready" = "1" ] || { log "[致命] adapter 健康检查超时"; exit 3; }
log "adapter up port=$PORT pid=$APID"

cleanup() {
  kill -TERM "$APID" 2>/dev/null
  for _ in $(seq 1 16); do kill -0 "$APID" 2>/dev/null || break; sleep 0.5; done
  kill -KILL "$APID" 2>/dev/null
  pgrep -af "adapter_tools.py $PORT" >/dev/null && log "[告警] adapter 残留"
}
trap cleanup EXIT

# --- 3 agent 侧 cfg（同上游, 只换端口）----------------------------------------
CFGSRC=${R504_CFG_SEED:-/tmp/r455_env/agent/cfg}
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC（先跑 R455 环境）"; exit 3; }
cp -r "$CFGSRC" "$D/agent/cfg"
grep -rl 48615 "$D/agent/cfg" 2>/dev/null | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }

# --- 4 外部真值侧（codex）----------------------------------------------------
R504_WORK="$D/codex/work" R504_RAW="$D/logs/codex-raw" R504_AUDIT="$D/logs/codex-audit.jsonl" \
R504_ADAPTER_PORT="$PORT" R504_CODEX_BIN="$CODEX_BIN" \
  python3 eval/probe/run_probe.py --tasks "$TASKS" \
  --solver "command:python3 $REPO/eval/rover/r504/codex_solver_r504.py" --tag codex-r504 \
  2>&1 | tee "$D/logs/probe-codex.log"; rc1=${PIPESTATUS[0]}
log "codex 侧 rc=$rc1"

# --- 5 本侧（AOT agenthost）---------------------------------------------------
AGENTFRAMEWORK_CONFIG="$D/agent/cfg" PROBE_AGENT_BIN="$AGENT_BIN" \
  python3 eval/probe/run_probe.py --tasks "$TASKS" --solver agent --tag agent-r504 \
  2>&1 | tee "$D/logs/probe-agent.log"; rc2=${PIPESTATUS[0]}
log "agent 侧 rc=$rc2"

# --- 6 收口 + 端口断言 --------------------------------------------------------
cleanup; trap - EXIT
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 未释放"; exit 3; fi
log "收口 clean"

# --- 7 判分（只读落盘, 不重跑）--------------------------------------------------
CJ=$(ls -t data/probe/probe-*codex-r504*.json 2>/dev/null | head -1)
AJ=$(ls -t data/probe/probe-*agent-r504*.json 2>/dev/null | head -1)
[ -n "$CJ" ] && [ -n "$AJ" ] || { log "[致命] 缺侧面产物 (codex=$CJ agent=$AJ) ⇒ rc=3"; exit 3; }
python3 eval/rover/r504/judge_contrast_r504.py --codex "$CJ" --agent "$AJ" \
  --prereg eval/rover/r504/prereg_r504.json --adapter-log "$D/adapter" \
  --out "$D/verdict-r504.json"; jrc=$?
log "judge rc=$jrc"
bash eval/rover/r504/make_evidence_r504.sh || true
exit $jrc
