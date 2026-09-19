#!/usr/bin/env bash
# R581 · RF0002 §3 验收面 ②③④ 真机首验 — 三臂串行执行器 (零产品改动; 只跑 + 落盘)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ROOT=eval/rover/r581
BIN=./src/agent.host/bin/Release/net10.0/agenthost
{
  echo "ts_start=$(date -Is)"
  echo "head=$(git rev-parse HEAD)"
  echo "tree_dirty=$(git status --porcelain | wc -l)"
  echo "bin_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "bin_mtime=$(stat -c %y $BIN)"
  echo "host_jsonl_bytes_before=$(wc -c < data/telemetry/host.jsonl)"
  echo "nlp_dir_before=$(test -d data/nlp && echo present || echo absent)"
} > $ROOT/pre-arm-state.txt

run_arm() {
  local arm="$1" sess="$2" turns="$3"
  local off start end rc
  off=$(wc -c < data/telemetry/host.jsonl)
  echo "$off" > $ROOT/telemetry-offset-$arm.txt
  start=$(date +%s)
  { cat "$turns"; printf '/exit\n'; } | timeout 1200 "$BIN" --role ./skeptic.rbin --session-id "$sess" 2>&1 \
      | head -c 8388608 > $ROOT/arm-$arm.log
  rc=${PIPESTATUS[1]}
  end=$(date +%s)
  {
    echo "arm=$arm session=$sess rc=$rc secs=$((end-start))"
    echo "mem_after=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB"
    echo "log_bytes=$(wc -c < $ROOT/arm-$arm.log)"
    echo "nlp_dir_after=$(test -d data/nlp && echo present || echo absent)"
    test -f data/nlp/gate-shapes.txt && echo "shapes_lines=$(wc -l < data/nlp/gate-shapes.txt)" || echo "shapes_lines=none"
  } >> $ROOT/arm-meta.txt
  echo "ARM $arm done rc=$rc secs=$((end-start))"
}

: > $ROOT/arm-meta.txt
run_arm A r581a $ROOT/turns-A.txt
run_arm B r581b $ROOT/turns-B.txt
run_arm N r581n $ROOT/turns-N.txt
echo "ALL_ARMS_DONE $(date -Is)"
