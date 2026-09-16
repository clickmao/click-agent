#!/usr/bin/env bash
# R505 主线对照 runner（批量版）: 外部真值(codex-cli) × 本侧(AOT agenthost) —— 同冻结题集 / 同 adapter / 同机械判分
#
# 相对 R504 runner 的三处**器具修复**（R504 实测缺陷: 判分后证据被覆盖 ⇒ 读数不可重放）:
#   ① 命名空间守卫: $D 与 $EV 必须为空（否则 rc=4 拒跑）—— 杜绝两个作业共用 DEMO_OUT;
#   ② 阶段快照: 每个阶段结束**立即**把 side-*.json 拷进仓内 $EV/adapter-<side>/ （/tmp 之外, 不可变）;
#   ③ 逐文件 sha256 清单 + 冻结清单: 判分只读仓内快照; H9 可重放/H10 不可变由 check_usage_replay 机检。
#
# 用法: bash eval/rover/r505/run_contrast_r505.sh <a|b|c>
set -uo pipefail
REPO=/home/agentuser/AgentFramework
BATCH=${1:-}
if [ -z "$BATCH" ]; then echo "用法: bash $0 <a|b|c>"; exit 4; fi
D=${R505_ENV:-/tmp/r505_$BATCH}
PORT=${R505_ADAPTER_PORT:-48636}
EV=$REPO/eval/rover/r505/evidence/$BATCH
CODEX_BIN=${R505_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
AGENT_BIN=${PROBE_AGENT_BIN:-/tmp/pub_r504/agenthost/agenthost}   # 与 R504 同一 AOT 二进制（本轮不改链码 ⇒ 保同环境可比）
TASKS=$REPO/eval/rover/r505/taskset-r505.json
SOLVER=$REPO/eval/rover/r504/codex_solver_r504.py      # 同一外部解法器（跨轮可对照）
log() { echo "[R505-$BATCH] $*"; }
cd "$REPO" || exit 4

# --- 0 守卫（R505 新增）-------------------------------------------------------
forced=${R505_FORCE:-0}
if [ "$forced" != "1" ]; then
  if [ -d "$D" ] && [ -n "$(ls -A "$D" 2>/dev/null)" ]; then
    log "[致命] 命名空间已被占用: $D ⇒ rc=4（R505_FORCE=1 显式覆盖）"; exit 4
  fi
  if [ -d "$EV" ] && [ -n "$(ls -A "$EV" 2>/dev/null)" ]; then
    log "[致命] 本批证据目录已有产物: $EV ⇒ rc=4（禁覆盖已判分证据）"; exit 4
  fi
fi
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 已被占用 ⇒ rc=4（不抢别人的进程）"; exit 4; fi

if ! python3 eval/rover/r505/make_prereg_r505.py --check; then
  log "[致命] 预注册非 UNIFORM ⇒ 弃权 (rc=3)"; exit 3
fi
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex: $CODEX_BIN"; exit 3; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺 agenthost(须可执行): $AGENT_BIN"; exit 3; }
[ -f "$TASKS" ]     || { log "[致命] 缺冻结题集: $TASKS"; exit 3; }
[ -f "$SOLVER" ]    || { log "[致命] 缺外部解法器: $SOLVER"; exit 3; }

# --- 1 夹具（两侧同环境）------------------------------------------------------
rm -rf "$D"; mkdir -p "$D"/{codex/work,agent/work,logs,adapter,snap} "$EV"
echo "batch=$BATCH port=$PORT pid=$$ ts=$(date -Is)" > "$D/adapter/.owner-r505"
n0=$(ls "$D"/adapter/side-*.json 2>/dev/null | wc -l)
[ "$n0" = "0" ] || { log "[致命] adapter 目录非空 ($n0) ⇒ rc=4"; exit 4; }
man() { (cd "$1" && find . -type f -printf '%P %s\n' | LC_ALL=C sort | md5sum | cut -d' ' -f1); }
mc=$(man "$D/codex/work"); ma=$(man "$D/agent/work")
[ "$mc" = "$ma" ] || { log "[致命] 初始夹具不同 ($mc vs $ma)"; exit 3; }
log "夹具同形 mc=$mc ma=$ma | agenthost sha256=$(sha256sum "$AGENT_BIN" | cut -d' ' -f1) bytes=$(stat -c%s "$AGENT_BIN")"

# --- 2 adapter（同一真实模型网关）---------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT=$D/adapter setsid nohup python3 eval/rover/r455/adapter_tools.py "$PORT" \
  >"$D/logs/adapter.log" 2>&1 &
APID=$!
ready=0
for _ in $(seq 1 40); do
  if curl -s -m 3 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then ready=1; break; fi
  kill -0 "$APID" 2>/dev/null || { log "[致命] adapter 退出"; tail -5 "$D/logs/adapter.log"; exit 3; }
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
CFGSRC=${R505_CFG_SEED:-/tmp/r455_env/agent/cfg}
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
cp -r "$CFGSRC" "$D/agent/cfg"
grep -rl 48615 "$D/agent/cfg" 2>/dev/null | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }

snap_side() {  # $1=side  $2=dest
  local side=$1 dest=$2
  rm -rf "$dest"; mkdir -p "$dest"
  cp -a "$D"/adapter/side-$side-*.json "$dest"/ 2>/dev/null || true
  python3 eval/rover/r505/manifest_r505.py --dir "$dest" --side "$side" \
    --usage-out "$D/usage-$side.txt" --manifest-out "$D/manifest-$side.json" --batch "$BATCH" || return 2
  cp "$D/usage-$side.txt" "$D/manifest-$side.json" "$dest"/
  return 0
}

# --- 4 外部真值侧（codex）-----------------------------------------------------
R504_WORK="$D/codex/work" R504_RAW="$D/logs/codex-raw" R504_AUDIT="$D/logs/codex-audit.jsonl" \
R504_ADAPTER_PORT="$PORT" R504_CODEX_BIN="$CODEX_BIN" \
  python3 eval/probe/run_probe.py --tasks "$TASKS" \
  --solver "command:python3 $SOLVER" --tag "codex-r505$BATCH" \
  2>&1 | tee "$D/logs/probe-codex.log"; rc1=${PIPESTATUS[0]}
log "codex 侧 rc=$rc1"
snap_side codex "$EV/adapter-codex" || { log "[致命] codex 快照失败"; exit 3; }
log "codex 快照 -> $EV/adapter-codex"

# --- 5 本侧（AOT agenthost）---------------------------------------------------
AGENTFRAMEWORK_CONFIG="$D/agent/cfg" PROBE_AGENT_BIN="$AGENT_BIN" \
  python3 eval/probe/run_probe.py --tasks "$TASKS" --solver agent --tag "agent-r505$BATCH" \
  2>&1 | tee "$D/logs/probe-agent.log"; rc2=${PIPESTATUS[0]}
log "agent 侧 rc=$rc2"
snap_side agent "$EV/adapter-agent" || { log "[致命] agent 快照失败"; exit 3; }
log "agent 快照 -> $EV/adapter-agent"

# --- 6 收口 + 端口断言 --------------------------------------------------------
cleanup; trap - EXIT
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 未释放"; exit 3; fi
log "收口 clean"

# --- 7 判分（只读**仓内快照**, 不重跑）----------------------------------------
CJ=$(ls -t data/probe/probe-*"codex-r505$BATCH"*.json 2>/dev/null | head -1)
AJ=$(ls -t data/probe/probe-*"agent-r505$BATCH"*.json 2>/dev/null | head -1)
[ -n "$CJ" ] && [ -n "$AJ" ] || { log "[致命] 缺侧面产物 (codex=$CJ agent=$AJ) ⇒ rc=3"; exit 3; }
# 侧面摘要也搬进仓内（判分输入全部落在 $EV, /tmp 被清不影响重放）
cp "$CJ" "$EV/probe-codex.json"; cp "$AJ" "$EV/probe-agent.json"
mkdir -p "$EV/codex"; cp -a "$D/logs/codex-raw" "$EV/codex/raw" 2>/dev/null
cp "$D/logs/codex-audit.jsonl" "$EV/codex/audit.jsonl" 2>/dev/null
python3 eval/rover/r505/judge_contrast_r505.py \
  --codex "$EV/probe-codex.json" --agent "$EV/probe-agent.json" \
  --prereg eval/rover/r505/prereg_r505.json \
  --adapter-codex-dir "$EV/adapter-codex" --adapter-agent-dir "$EV/adapter-agent" \
  --manifest-codex "$EV/adapter-codex/manifest-codex.json" \
  --manifest-agent "$EV/adapter-agent/manifest-agent.json" \
  --codex-raw-dir "$EV/codex/raw" --codex-audit "$EV/codex/audit.jsonl" \
  --batch "$BATCH" --out "$EV/verdict-r505$BATCH.json"; jrc=$?
log "judge rc=$jrc"

# --- 8 H9 立即复核（同一次运行内第二次读, 读**仓内快照**）----------------------
python3 eval/rover/r505/check_usage_replay.py --usage "$EV/adapter-codex/usage-codex.txt" \
  --dir "$EV/adapter-codex" --out "$EV/replay-codex-$BATCH.json"; r9a=$?
python3 eval/rover/r505/check_usage_replay.py --usage "$EV/adapter-agent/usage-agent.txt" \
  --dir "$EV/adapter-agent" --out "$EV/replay-agent-$BATCH.json"; r9b=$?
log "H9 复核 codex=$r9a agent=$r9b"
cp "$D/logs/probe-codex.log" "$D/logs/probe-agent.log" "$D/logs/adapter.log" "$EV/" 2>/dev/null
exit $(( jrc != 0 ? jrc : (rc1 != 0 || rc2 != 0 ? 3 : (r9a != 0 || r9b != 0 ? 1 : 0)) ))
