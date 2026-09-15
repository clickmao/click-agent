#!/usr/bin/env bash
# R463 臂执行器 — 3B 判别通道采用验证（承重: 用户一轮 total API token 降幅 / 质量不退化）
#   单变量对照（模型档位）: B3B(3B,采用) vs B15(1.5B,旧) —— 同 cfg / 同网格 / 同桩 / 同 role
#   通道对照: A(本地通道关,分母) / BP(3B 路径不存在,负控 ⇒ 增益须归零)
# 用法: bash run_arm.sh <A|B15|B3B|BP>
set -u
ARM=${1:?用法: run_arm.sh <A|B15|B3B|BP>}
STUB_PORT=${2:-47980}
API_PORT=${3:-47982}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r463
TOOLS=$ROOT/eval/rover/r430
GRID=p12
TASK=$ROOT/eval/rover/r438/grid/task-$GRID.json     # 同网格同输入 (R442 口径: A 分母必须同网格)
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r463/agenthost}
M15=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
M3B=/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
STUBLOG=$DIR/stub-$ARM.log
VERDICT=$DIR/verdict-$ARM.json
RUNDIR=$DIR/run-$ARM
[ -f "$VERDICT" ] && { echo "[致命] REFUSE_NS_COLLISION: $VERDICT 已存在"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r463-harness-fixed-token
echo "[preflight] arm=$ARM bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  A)     MP=$M3B; GATE=false; RJ=false; ROLE="" ;;
  B15)   MP=$M15; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH" ;;
  B3B)   MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH" ;;
  BP)    MP=/nonexistent/r463-nomodel.gguf; GATE=true; RJ=true; ROLE="$ROLE_GROWTH" ;;
  B15pf0) MP=$M15; GATE=true; RJ=false; ROLE="$ROLE_GROWTH"; export AGENTFRAMEWORK_GATE_PREFILTER=0 ;;
  # BP 负控修 (R463 实测): 配置 model_path 缺失时, 端口回退 baseOpts.ModelPath (env/默认) — 而 R463 默认已改成 3B
  #   ⇒ 首跑 BP 静默跑了 3B, 负控 VOID。真负控必须 env 也指不存在 (ServiceCollectionExtensions.cs:300 行锚)。
  BP2)   MP=/nonexistent/r463-nomodel.gguf; GATE=true; RJ=true; ROLE="$ROLE_GROWTH"; export AGENTFRAMEWORK_LLM_MODEL=/nonexistent/r463-nomodel-env.gguf ;;
  B3Bpf0) MP=$M3B; GATE=true; RJ=false; ROLE="$ROLE_GROWTH"; export AGENTFRAMEWORK_GATE_PREFILTER=0 ;;
  *)   echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MP" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
# 纪律: 整份 base 复用后 ① 端点全部改指桩 ② 已存在的 local 块剥离后再追加 (禁双块)
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
# 剥离可能残留的 local 块内的键 (顶层 local 块被删后其子键会悬挂 ⇒ 一并清理)
src = re.sub(r"(?m)^(  (model_path|context_size|parallel|gpu_layers|max_tokens|max_prompt_tokens|allowed_kinds|allow_general|turn_gate|relation_judge):.*)$", "", src)
src += f"""
# R463 臂 (单变量 = 模型档位; 其余与生产 config/base/models.yaml 逐字同)
local:
  model_path: {model}
  context_size: 4608
  parallel: 1
  gpu_layers: 0
  max_tokens: 512
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: {gate}
  relation_judge: {rj}
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] 端点改写 {n} 处 → 桩 :{port}; gate={gate} rj={rj} model={model}")
PY
python3 -u "$TOOLS/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!
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
T0=$(date +%s)
python3 -u "$TOOLS/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
T1=$(date +%s)
last=""; stable=0; waited=0
while [ "$waited" -lt 900 ]; do
  n=$(grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" 2>/dev/null); n=${n:-0}
  c=$(wc -l < "$CALLS" 2>/dev/null); c=${c:-0}
  key="$n/$c"
  [ "$key" = "$last" ] && stable=$((stable+1)) || stable=0
  last="$key"
  [ "$stable" -ge 14 ] && break
  sleep 5; waited=$((waited+5))
done
echo "[quiesce] drive=$((T1-T0))s wait=${waited}s judge/calls=$last"
python3 -u "$DIR/settle_r463.py" "$DIR" "" "$ARM"
