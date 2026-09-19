#!/usr/bin/env bash
# R581 v2 · 同预注册重跑 (v1 全臂 VOID: AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置 ⇒ 学习前提不成立)
# 与 v1 唯一差异 = 环境变量面 (key 面); 臂设计/轮次/命令面逐字沿用 v1。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ROOT=eval/rover/r581
BIN=./src/agent.host/bin/Release/net10.0/agenthost
KEYS="$HOME/.agentframework/keys.env"

# ── 前置闸 1: key 面 (fail-closed, 不起臂) ──
set -a; . "$KEYS"; set +a
if [ -z "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" ]; then
  echo "VOID: AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置 ⇒ 不起臂" > "$ROOT/void-r581v2.txt"
  exit 3
fi

# ── 前置闸 2: 远端预检 (1 次极小调用; 只落 http_code, 不落正文/key) ──
PRE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 \
  -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $AGENTFRAMEWORK_KEYS_DEEPSEEK" \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-flash","messages":[{"role":"user","content":"ok"}],"max_tokens":1}' 2>/dev/null)
{
  echo "ts=$(date -Is)"
  echo "http_code=$PRE"
  echo "key_len=${#AGENTFRAMEWORK_KEYS_DEEPSEEK}"
  echo "mem_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
} > "$ROOT/gate-pre-r581v2.json"
if [ "$PRE" != "200" ]; then
  echo "VOID: 远端预检 http=$PRE ⇒ 学习前提不成立, 不起臂" >> "$ROOT/gate-pre-r581v2.json"
  exit 4
fi

{
  echo "ts_start=$(date -Is)"
  echo "head=$(git rev-parse HEAD)"
  echo "tree_dirty=$(git status --porcelain | wc -l)"
  echo "bin_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "bin_mtime=$(stat -c %y $BIN)"
  echo "host_jsonl_bytes_before=$(wc -c < data/telemetry/host.jsonl)"
  echo "nlp_dir_before=$(test -d data/nlp && echo present || echo absent)"
} > "$ROOT/pre-arm-state.txt"

run_arm() {
  local arm="$1" sess="$2" turns="$3"
  local off start end rc
  off=$(wc -c < data/telemetry/host.jsonl)
  echo "$off" > "$ROOT/telemetry-offset-$arm.txt"
  start=$(date +%s)
  { cat "$turns"; printf '/exit\n'; } | timeout 1200 "$BIN" --role ./skeptic.rbin --session-id "$sess" 2>&1 \
      | head -c 8388608 > "$ROOT/arm-$arm.log"
  rc=${PIPESTATUS[1]}
  end=$(date +%s)
  {
    echo "arm=$arm session=$sess rc=$rc secs=$((end-start))"
    echo "mem_after=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB"
    echo "log_bytes=$(wc -c < "$ROOT/arm-$arm.log")"
    echo "nlp_dir_after=$(test -d data/nlp && echo present || echo absent)"
    test -f data/nlp/gate-shapes.txt && echo "shapes_lines=$(wc -l < data/nlp/gate-shapes.txt)" || echo "shapes_lines=none"
  } >> "$ROOT/arm-meta.txt"
  echo "ARM $arm done rc=$rc secs=$((end-start))"
}

: > "$ROOT/arm-meta.txt"
run_arm A r581a "$ROOT/turns-A.txt"
run_arm B r581b "$ROOT/turns-B.txt"
run_arm N r581n "$ROOT/turns-N.txt"
echo "ALL_ARMS_DONE $(date -Is)"
