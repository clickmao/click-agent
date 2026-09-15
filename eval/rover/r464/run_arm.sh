#!/usr/bin/env bash
# R464 臂执行器 — 本地判别通道「配置错配 fail-closed」（消灭静默回退默认权重）
#   承重对照（同网格 p12 / 同桩 / 同 role / 仅换二进制）:
#     Arole = 门关 + role on  ← 诚实分母（修 R463 口径: 旧 A 臂未带 --role, 把 role 块成本记到门上）
#     B3B   = 门开 + role on（已采用档, 3B）      ← 主判据: 对 Arole 的远端 token 降幅
#     BP    = cfg.model_path 不存在, env 默认**存在** ⇒ 旧代码静默跑默认 3B(R463 VOID); 新代码须告警+不可用
#     BP2   = cfg + env 双缺 ⇒ 真缺模型 fail-open 负控
# 用法: bash run_arm.sh <Arole|B3B|BP|BP2>
set -u
ARM=${1:?用法: run_arm.sh <Arole|B3B|BP|BP2>}
STUB_PORT=${2:-47990}
API_PORT=${3:-47992}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r464
TOOLS=$ROOT/eval/rover/r430
GRID=p12
TASK=$ROOT/eval/rover/r438/grid/task-$GRID.json     # 同网格同输入 (R442 口径: 分母必须同网格)
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r464/agenthost}
M3B=/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
STUBLOG=$DIR/stub-$ARM.log
VERDICT=$DIR/verdict-r464.json
RUNDIR=$DIR/run-$ARM
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数 ⇒ 拒绝覆盖"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r464-harness-fixed-token
echo "[preflight] arm=$ARM bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  Arole) MP=$M3B; GATE=false; RJ=false; ROLE="$ROLE_GROWTH" ;;
  B3B)   MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH" ;;
  # 配置错配: cfg 指不存在; **不动 env** ⇒ env 默认 = ~/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf (真实存在)
  #   旧代码 ⇒ lc.IsReady=false ⇒ 静默替换成默认 3B, 读数与 B3B 逐位相同 (R463 实测);
  #   新代码 ⇒ R464 config_mismatch 告警 + 通道不可用, 读数必须 ≠ B3B。
  BP)    MP=/nonexistent/r464-cfg-nomodel.gguf; GATE=true; RJ=true; ROLE="$ROLE_GROWTH" ;;
  BP2)   MP=/nonexistent/r464-cfg-nomodel.gguf; GATE=true; RJ=true; ROLE="$ROLE_GROWTH"
         export AGENTFRAMEWORK_LLM_MODEL=/nonexistent/r464-env-nomodel.gguf ;;
  *)   echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ role=$([ -n "$ROLE" ] && echo on || echo off) env_model=${AGENTFRAMEWORK_LLM_MODEL:-<default>}"
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MP" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
# 纪律: 整份 base 复用后 ① 端点全部改指桩 ② 已存在的 local 块剥离后再追加 (禁双块)
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src = re.sub(r"(?m)^(  (model_path|context_size|parallel|gpu_layers|max_tokens|max_prompt_tokens|allowed_kinds|allow_general|turn_gate|relation_judge):.*)$", "", src)
src += f"""
# R464 臂 (单变量 = 配置错配/通道开关; 其余与生产 config/base/models.yaml 逐字同)
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
# 告警面取证: 宿主起好后立即抓一次 stderr 告警标记 (错配臂必须在跑测前就可见)
echo "[warnscan] $(grep -c 'R464 config_' "$HOSTLOG" 2>/dev/null) 条 R464 告警标记"
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
echo "[warnscan-final] $(grep -c 'R464 config_' "$HOSTLOG" 2>/dev/null) 条; llama-server 启动次数=$(grep -c 'llama-server\|本地生成' "$HOSTLOG" 2>/dev/null)"
python3 -u "$DIR/settle_r464.py" "$DIR" "$ARM"
