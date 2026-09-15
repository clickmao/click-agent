#!/usr/bin/env bash
# R466 臂执行器 —— 复述回放 vs 承接反问优先级 (修 R465 C3 FAIL)
#   承重对照 (同网格 p12 / 同桩 / 同 role / **同一 AOT 二进制**):
#     Arole = 门关 + role on                        ← 诚实分母 (R464/R465 口径)
#     R     = 门开 + role on + PRIORITY=on(默认)     ← 主判据面 (生产行为)
#     NC    = 门开 + role on + PRIORITY=0           ← 负控: 复原 R465 覆盖行为 (同二进制/单变量)
#     R2    = R 复跑                                 ← 预注册 C6 (逐位)
# 用法: bash run_arm.sh <Arole|R|NC|R2> [stub_port] [api_port]
set -u
ARM=${1:?用法: run_arm.sh <Arole|R|NC|R2>}
STUB_PORT=${2:-47994}
API_PORT=${3:-47996}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r466
TOOLS=$ROOT/eval/rover/r430
GRID=p12
TASK=$ROOT/eval/rover/r438/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r466/agenthost}
M3B=/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
STUBLOG=$DIR/stub-$ARM.log
RUNDIR=$DIR/run-$ARM
SERVLOG=$DIR/server-$ARM.txt
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数 ⇒ 拒绝覆盖"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r466-harness-fixed-token
echo "[preflight] arm=$ARM bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  Arole) MP=$M3B; GATE=false; RJ=true; ROLE="$ROLE_GROWTH"; RS=off; PRIO=1 ;;
  R|R2)  MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  PRIO=1 ;;
  NC)    MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  PRIO=0 ;;
  *)   echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
export AGENTFRAMEWORK_GATE_REPEAT_SKIP=$RS
# R466 消融开关: 只有 NC 置 0 (默认即生产行为 ⇒ R 面必须是未设-默认等价)
if [ "$PRIO" = "0" ]; then export AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY=0; else unset AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY; fi
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ role=on repeat_skip=$RS repeat_priority=$PRIO"
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MP" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src = re.sub(r"(?m)^(  (model_path|context_size|parallel|gpu_layers|max_tokens|max_prompt_tokens|allowed_kinds|allow_general|turn_gate|relation_judge):.*)$", "", src)
src += f"""
# R466 臂 (单变量 = 承接反问/复述回放优先级; 其余与生产 config/base/models.yaml 逐字同)
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
: > "$SERVLOG"
( while :; do
    for p in $(pgrep -f '[l]lama-server' 2>/dev/null); do
      echo "$(date +%s) pid=$p etimes=$(awk '{print int($22/100)}' /proc/$p/stat 2>/dev/null)" >> "$SERVLOG"
    done
    sleep 2
  done ) &
MON_PID=$!
cd "$RUNDIR"
ROLE_ARG=""; [ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" $ROLE_ARG > "$HOSTLOG" 2>&1 &
HOST_PID=$!
cleanup() { kill "$MON_PID" 2>/dev/null || true; pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主已退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }
echo "[warnscan] $(grep -c 'config_' "$HOSTLOG" 2>/dev/null) 条配置告警标记"
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
echo "[quiesce] drive=$((T1-T0))s wait=${waited}s judge/calls=$last bin_sha=$BIN_SHA"
echo "[server] $(sort -u -t= -k2 "$SERVLOG" 2>/dev/null | wc -l) 个不同 pid 采样; 行数=$(wc -l < "$SERVLOG")"
python3 -u "$DIR/settle_r466.py" "$DIR" "$ARM"
