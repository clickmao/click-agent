#!/usr/bin/env bash
# R444 臂执行器 — 廉价必要条件前置 (¬Ack ⇒ Pass) 的可证等价优化 + 短档真值补测
#   臂 A    = 分母: turn_gate=false (无门/无判官) ⇒ 全远端
#   臂 BRJ  = 门开 + J 本地优先 + **前置门默认开** (R444 生产行为)
#   臂 BRJL = BRJ + AGENTFRAMEWORK_GATE_PREFILTER=0 ⇒ 复原 R443 的「后置否决」行为
#             ⇒ 与 BRJ 构成**同网格单变量**对照 (唯一变量 = Ack 前置 vs 后置)
# 用法: R444_GRID=M20 R444_NS=-s4 bash run_arm_r444.sh <A|BRJ|BRJL> [桩端口] [api端口]
set -u
ARM=${1:?用法: run_arm_r444.sh <A|BRJ|BRJL> [stub] [api]}
STUB_PORT=${2:-48200}
API_PORT=${3:-48202}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r444
TOOLS=$ROOT/eval/rover/r430
SFX=${R444_NS:--s4}
GRID=${R444_GRID:-M20}
TASK=$DIR/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r444/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM-$GRID$SFX
CALLS=$DIR/calls-$ARM-$GRID$SFX.jsonl
TURNS=$DIR/turns-$ARM-$GRID$SFX.jsonl
HOSTLOG=$DIR/host-$ARM-$GRID$SFX.log
STUBLOG=$DIR/stub-$ARM-$GRID$SFX.log
VERDICT=$DIR/verdict-$ARM-$GRID$SFX.json
RUNDIR=$DIR/run-$ARM-$GRID$SFX
[ -f "$VERDICT" ] && { echo "[致命] REFUSE_NS_COLLISION: $VERDICT 已存在 ⇒ 换 NS"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在/不可执行: $HOST"; exit 5; }
[ -f "$MODEL" ] || { echo "[致命] 模型缺失: $MODEL"; exit 9; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r444-harness-fixed-token
echo "[preflight] arm=$ARM grid=$GRID bin=$HOST ns=$SFX $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM-$GRID$SFX.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  A)    GATE=false; RJ=false; ROLE="";            PREFILTER="";;
  BRJ)  GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; PREFILTER="";;
  BRJL) GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; PREFILTER="0";;
  *)    echo "[致命] 未知臂: $ARM (R444 只跑 A/BRJ/BRJL)"; exit 2;;
esac
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MODEL" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src += f"""
# R444 臂: 主回答恒远端 (allow_general=false); 单变量 = turn_gate 与 relation_judge
local:
  model_path: {model}
  context_size: 4608
  parallel: 1
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: {gate}
  relation_judge: {rj}
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] 改写 {n} 处 request_address → 桩 :{port}; turn_gate={gate} relation_judge={rj}")
PY
python3 -u "$TOOLS/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key" 2>/dev/null || true
cd "$RUNDIR"
ROLE_ARG=""; [ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
# R444: 消融臂显式关前置门 (默认开 = 生产行为)
if [ -n "$PREFILTER" ]; then export AGENTFRAMEWORK_GATE_PREFILTER="$PREFILTER"; else unset AGENTFRAMEWORK_GATE_PREFILTER; fi
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" $ROLE_ARG > "$HOSTLOG" 2>&1 &
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
while [ "$waited" -lt 700 ]; do
  n=$(grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" 2>/dev/null); n=${n:-0}
  c=$(wc -l < "$CALLS" 2>/dev/null); c=${c:-0}
  key="$n/$c"
  [ "$key" = "$last" ] && stable=$((stable+1)) || stable=0
  last=$key
  [ "$stable" -ge 14 ] && break
  sleep 5; waited=$((waited+5))
done
echo "[quiesce] arm=$ARM grid=$GRID drive=$((T1-T0))s wait=${waited}s judge_events/stub_calls=$last"
python3 -u "$DIR/settle_r444.py" "$CALLS" "$ARM" "$DIR" "$HOST" "$BIN_SHA" "$GRID" "$SFX" "$RUNDIR"
