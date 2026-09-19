#!/usr/bin/env bash
# R583 · 真机臂 (单变量: 形状库有无) —— 零产品源码改动; 前置闸 fail-closed。
# 臂: S0 负控(无库) / S1 治疗(预置库) / D 降级路径 / N 族外负控
# 预注册: eval/rover/r583/prereg-r583.json (先于任何臂落盘)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ROOT=eval/rover/r583
BIN=./src/agent.host/bin/Release/net10.0/agenthost
KEYS="$HOME/.agentframework/keys.env"

# ── 前置闸 1: key 面 (cron 会话环境缺该变量 ⇒ 作业环境需自备) ──
if [ -z "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" ] && [ -f "$KEYS" ]; then
  set -a; . "$KEYS"; set +a
fi
if [ -z "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" ]; then
  echo "VOID: AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置 (且 $KEYS 不可用) ⇒ 不起臂" | tee "$ROOT/gate-pre-r583.txt"
  exit 4
fi

# ── 前置闸 2: 远端预检 (http=200) ──
PRE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 \
  -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer ${AGENTFRAMEWORK_KEYS_DEEPSEEK}" \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-flash","messages":[{"role":"user","content":"ok"}],"max_tokens":1}' 2>/dev/null)
{
  echo "ts=$(date -Is)"
  echo "http_code=$PRE"
  echo "key_len=${#AGENTFRAMEWORK_KEYS_DEEPSEEK}"
  echo "mem_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
  echo "disk_avail=$(df -BG --output=avail / | tail -1 | tr -d ' G')GB"
} > "$ROOT/gate-pre-r583.txt"
if [ "$PRE" != "200" ]; then
  echo "VOID: 远端预检 http=$PRE ⇒ 学习前提不成立, 不起臂" >> "$ROOT/gate-pre-r583.txt"
  exit 4
fi

# ── 起臂前状态 ──
{
  echo "ts_start=$(date -Is)"
  echo "head=$(git rev-parse HEAD)"
  echo "tree_dirty=$(git status --porcelain | wc -l)"
  echo "bin_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "bin_mtime=$(stat -c %y $BIN)"
  echo "host_jsonl_bytes_before=$(wc -c < data/telemetry/host.jsonl)"
  echo "nlp_dir_before=$(test -d data/nlp && echo present || echo absent)"
} > "$ROOT/pre-arm-state.txt"

FIXTURE="$ROOT/fixture-shapes-line1.txt"
if [ ! -f "$FIXTURE" ]; then
  head -1 eval/rover/r581/shapes-r581.txt > "$FIXTURE"
fi
echo "fixture_sha256=$(sha256sum $FIXTURE | cut -d' ' -f1)" >> "$ROOT/pre-arm-state.txt"

: > "$ROOT/arm-meta.txt"

set_library() {  # $1 = absent | fixture
  if [ "$1" = "absent" ]; then
    rm -rf data/nlp
  else
    mkdir -p data/nlp
    cp "$FIXTURE" data/nlp/gate-shapes.txt
  fi
}

run_arm() {
  local arm="$1" sess="$2" turns="$3"
  local off start end rc
  off=$(wc -c < data/telemetry/host.jsonl)
  echo "$off" > "$ROOT/telemetry-offset-$arm.txt"
  start=$(date +%s)
  { cat "$turns"; printf '/exit\n'; } | timeout 240 "$BIN" --role ./skeptic.rbin --session-id "$sess" 2>&1 \
      | head -c 8388608 > "$ROOT/arm-$arm.out.txt"
  rc=${PIPESTATUS[1]}
  end=$(date +%s)
  {
    echo "arm=$arm session=$sess rc=$rc secs=$((end-start))"
    echo "mem_after=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB"
    echo "out_bytes=$(wc -c < "$ROOT/arm-$arm.out.txt")"
    echo "nlp_dir_after=$(test -d data/nlp && echo present || echo absent)"
    if [ -f data/nlp/gate-shapes.txt ]; then
      echo "shapes_lines=$(wc -l < data/nlp/gate-shapes.txt)"
      echo "shapes_sha256=$(sha256sum data/nlp/gate-shapes.txt | cut -d' ' -f1)"
    else
      echo "shapes_lines=none"
    fi
  } >> "$ROOT/arm-meta.txt"
  echo "ARM $arm done rc=$rc secs=$((end-start))"
}

# S0 = 负控: 同输入 + **无库** (单变量对照组)
set_library absent
run_arm S0 r583s0 "$ROOT/turns-S0.txt"
# S1/D/N = 预置库 (与 R581 产物同源, 逐字复用)
set_library fixture
echo "post_fixture_sha256=$(sha256sum data/nlp/gate-shapes.txt | cut -d' ' -f1)" >> "$ROOT/arm-meta.txt"
run_arm S1 r583s1 "$ROOT/turns-S1.txt"
run_arm D  r583d  "$ROOT/turns-D.txt"
run_arm N  r583n  "$ROOT/turns-N.txt"

# ── 收尾: 库复原为不存在 + 残留检查 ──
rm -rf data/nlp
{
  echo "ts_end=$(date -Is)"
  echo "nlp_dir_restored=$(test -d data/nlp && echo present || echo absent)"
  echo "host_jsonl_bytes_after=$(wc -c < data/telemetry/host.jsonl)"
  echo "leftover_proc=$(pgrep -af '[a]genthost' | wc -l)"
  echo "leftover_llama=$(pgrep -af '[l]lama-server' | wc -l)"
  echo "mem_end=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB"
} >> "$ROOT/arm-meta.txt"
echo "ALL_ARMS_DONE $(date -Is)"
