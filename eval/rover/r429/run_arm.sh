#!/usr/bin/env bash
# R429 臂执行器 — 「决策路径缓存态钉死」可复现性测量 (判据 P5a/P5b/P6 + 判别力负控)
#   臂 C = 门开 + relation_judge=true (R426 臂 C 口径: 门判与判官共用同一 llama-server slot ⇒ 顺序交错)
#   PRE  = /tmp/pub_r428/agenthost (改动前: 一切本地生成 Session 口径 = 前缀缓存复用)
#   POST = /tmp/pub_r429/agenthost (改动后: 决策路径 CacheReuse=false ⇒ Reconciliation)
# 用法: AGENTFRAMEWORK_HOST_BIN=<bin> bash run_arm.sh C <k8r|k8p> [桩端口] [api端口] [role.rbin]
set -u
ARM=${1:?用法: run_arm.sh C <k8r|k8p> [stub] [api] [role]}
GRID=${2:?缺 grid (k8r 同文重复 / k8p 判别力)}
STUB_PORT=${3:-47910}
API_PORT=${4:-47911}
ROLE=${5:-}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r429
SFX=${R429_NS:-}
TASK=$DIR/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r429/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
CFG=$DIR/config-$ARM-$GRID$SFX
CALLS=$DIR/calls-$ARM-$GRID$SFX.jsonl
TURNS=$DIR/turns-$ARM-$GRID$SFX.jsonl
HOSTLOG=$DIR/host-$ARM-$GRID$SFX.log
STUBLOG=$DIR/stub-$ARM-$GRID$SFX.log
[ -f "$DIR/verdict-$ARM-$GRID$SFX.json" ] && { echo "[致命] REFUSE_NS_COLLISION: verdict-$ARM-$GRID$SFX.json 已存在 ⇒ 换 NS"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r429-harness-fixed-token
echo "[preflight] grid=$GRID arm=$ARM bin=$HOST $(df -h / | tail -1)"
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在/不可执行: $HOST"; exit 5; }
python3 "$DIR/prov_check.py" --json "$DIR/prov-$ARM-$GRID$SFX.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MODEL" <<'PY'
import re, sys
path, port, model = sys.argv[1:4]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src += f"""
# R429 臂 C: 本地通道开启 (AllowGeneral=false ⇒ 主回答仍远端); turn_gate=true; relation_judge=true
local:
  model_path: {model}
  context_size: 4608
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: true
  relation_judge: true
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] 改写 {n} 处 request_address → 桩 :{port}; local: turn_gate=true relation_judge=true")
PY
python3 -u "$DIR/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!
RUNDIR="$DIR/run-$ARM-$GRID$SFX"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key" 2>/dev/null || true
cd "$RUNDIR"
ROLE_ARG=""; [ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
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
python3 -u "$DIR/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
sleep 25
python3 -u "$DIR/settle_r429.py" "$CALLS" "$ARM" "$DIR" "$HOST" "$BIN_SHA" "$GRID" "$SFX" "$RUNDIR"
