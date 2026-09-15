#!/usr/bin/env bash
# R452 臂执行器 — **产品原生**跑真实语料（零重建路线, 承 R449/R451 两次 VOID）
#   臂 RP  = 生产行为（门开 + 前置门开）      → 期望 0 r1 调用 / 0 Skip（真实流量可跳面）
#   臂 RJ  = 判官强制面（前置门关=0）          → 让门判吃到**真实 (msg, prev) 对**, 读判官真读数
# 用法: R452_GRID=REAL R452_NS=-p1 R452_PREFILTER=1 bash run_arm_r452.sh [RP|RJ] [桩端口] [api端口]
set -u
ARM=${1:-RP}
STUB_PORT=${2:-48400}
API_PORT=${3:-48402}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r452
TOOLS=$ROOT/eval/rover/r430
SFX=${R452_NS:--p1}
GRID=${R452_GRID:-REAL}
PREF=${R452_PREFILTER:-1}
TASK=$DIR/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r450/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM-$GRID$SFX
CALLS=$DIR/calls-$ARM-$GRID$SFX.jsonl
TURNS=$DIR/turns-$ARM-$GRID$SFX.jsonl
HOSTLOG=$DIR/host-$ARM-$GRID$SFX.log
STUBLOG=$DIR/stub-$ARM-$GRID$SFX.log
VERDICT=$DIR/verdict-$ARM-$GRID$SFX.json
DUMP=$DIR/dump-$ARM-$GRID$SFX.jsonl
RUNDIR=$DIR/run-$ARM-$GRID$SFX
[ -f "$VERDICT" ] && { echo "[致命] REFUSE_NS_COLLISION: $VERDICT 已存在 ⇒ 换 NS"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在/不可执行: $HOST"; exit 5; }
[ -f "$MODEL" ] || { echo "[致命] 模型缺失: $MODEL"; exit 9; }
SEQ=${R452_SEQ:-$DIR/grid/reply-seq.json}
[ -f "$SEQ" ] || { echo "[致命] reply-seq 缺失: $SEQ"; exit 10; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r452-harness-fixed-token
echo "[preflight] arm=$ARM grid=$GRID ns=$SFX prefilter=$PREF mem=$(free -m | awk '/Mem:/{print $7}')MB $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM-$GRID$SFX.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS" "$DUMP"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MODEL" <<'PY'
import re, sys
path, port, model = sys.argv[1:4]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src += f"""
# R452 臂: 主回答恒远端 (allow_general=false)
local:
  model_path: {model}
  context_size: 3584
  parallel: 1
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: true
  relation_judge: true
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] 改写 {n} 处 request_address → 桩 :{port}; ctx=3584 (内存闸下修, 记偏差)")
PY
TURNS_ARG="$TASK"
if [ "${R452_MATCH:-1}" = "0" ]; then TURNS_ARG="$DIR/grid/task-EMPTY.json"; fi
python3 -u "$DIR/stub_seq.py" "$STUB_PORT" "$CALLS" "$SEQ" "$TURNS_ARG" > "$STUBLOG" 2>&1 &
STUB_PID=$!
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key" 2>/dev/null || true
cd "$RUNDIR"
export AGENTFRAMEWORK_GATE_PROMPT_DUMP="$DUMP"
export AGENTFRAMEWORK_GATE_PREFILTER="$PREF"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" --role "$ROLE_GROWTH" > "$HOSTLOG" 2>&1 &
HOST_PID=$!
cleanup() { pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主已退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }
T0=$(date +%s)
python3 -u "$TOOLS/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
T1=$(date +%s)
last=""; stable=0; waited=0
while [ "$waited" -lt 1500 ]; do
  n=$(grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" 2>/dev/null); n=${n:-0}
  c=$(wc -l < "$CALLS" 2>/dev/null); c=${c:-0}
  key="$n/$c"
  [ "$key" = "$last" ] && stable=$((stable+1)) || stable=0
  last=$key
  [ "$stable" -ge 10 ] && break
  sleep 5; waited=$((waited+5))
done
echo "[quiesce] arm=$ARM grid=$GRID prefilter=$PREF drive=$((T1-T0))s wait=${waited}s judge_events/stub_calls=$last dump_lines=$( [ -f "$DUMP" ] && wc -l < "$DUMP" || echo 0 )"
python3 -u "$ROOT/eval/rover/r444/settle_r444.py" "$CALLS" "$ARM" "$DIR" "$HOST" "$BIN_SHA" "$GRID" "$SFX" "$RUNDIR"
