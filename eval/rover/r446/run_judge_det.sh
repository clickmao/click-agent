#!/usr/bin/env bash
# R446 判官确定性探针执行器 (真机, 产品路径)
#   12 轮同一消息 ⇒ 第 2 轮起判官输入逐字相同 ⇒ 字母若不恒定 = H1 (路径非确定)
# 用法: R446_NS=-s1 bash run_judge_det.sh [stub端口] [api端口]
set -u
STUB_PORT=${1:-48300}
API_PORT=${2:-48302}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r446
TOOLS=$ROOT/eval/rover/r430
SFX=${R446_NS:--s1}
GRID=${R446_GRID:-JDET}
TASK=$DIR/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r444b/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$GRID$SFX
CALLS=$DIR/calls-$GRID$SFX.jsonl
TURNS=$DIR/turns-$GRID$SFX.jsonl
HOSTLOG=$DIR/host-$GRID$SFX.log
STUBLOG=$DIR/stub-$GRID$SFX.log
RUNDIR=$DIR/run-$GRID$SFX
[ -f "$DIR/verdict-$GRID$SFX.json" ] && { echo "[致命] REFUSE_NS_COLLISION"; exit 7; }
[ -x "$HOST" ] || { echo "[致命] 二进制不可执行: $HOST"; exit 5; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r446-probe-fixed-token
echo "[preflight] grid=$GRID bin=$HOST ns=$SFX $(df -h / | tail -1)"
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
echo "[bin] $BIN_SHA"
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MODEL" <<'PY'
import re, sys
path, port, model = sys.argv[1:4]
src = open(path, encoding="utf-8").read()
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src += f"""
# R446 探针: 主回答恒远端(桩); 门关, 判官本地开 (唯一被测 = 判官路径)
local:
  model_path: {model}
  context_size: 4608
  parallel: 1
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: false
  relation_judge: true
"""
open(path, "w", encoding="utf-8").write(src)
print("[config] 桩地址改写 + relation_judge=true turn_gate=false")
PY
python3 -u "$TOOLS/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key" 2>/dev/null || true
cd "$RUNDIR"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" --role "$ROLE_GROWTH" > "$HOSTLOG" 2>&1 &
HOST_PID=$!
cleanup() { pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }
T0=$(date +%s)
python3 -u "$TOOLS/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
T1=$(date +%s)
last=""; stable=0; waited=0
while [ "$waited" -lt 900 ]; do
  n=$(grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" 2>/dev/null); n=${n:-0}
  FORM=$DIR/form-$GRID$SFX.txt
  if [ "$n" -gt 0 ] && [ ! -s "$FORM" ]; then
    for p in $(pgrep -f "llama-server.*r1-distill" 2>/dev/null); do
      { echo "# 形态自证: 实际被启动的 r1 llama-server argv (pid $p, $(date +%H:%M:%S))"; tr '\0' ' ' < /proc/$p/cmdline; echo; } > "$FORM"
    done
  fi
  c=$(wc -l < "$CALLS" 2>/dev/null); c=${c:-0}
  key="$n/$c"
  [ "$key" = "$last" ] && stable=$((stable+1)) || stable=0
  last=$key
  [ "$stable" -ge 14 ] && break
  sleep 5; waited=$((waited+5))
done
echo "[quiesce] drive=$((T1-T0))s wait=${waited}s judge_events/stub_calls=$last"
python3 -u "$DIR/analyze_judge_det.py" "$RUNDIR/data/telemetry/host.jsonl" "$DIR" "$SFX" "$BIN_SHA" "${FORM:-$HOSTLOG}" "$GRID"
echo "[done] rc=$?"
