#!/usr/bin/env bash
# R413 臂执行器 — 一轮任务 token 预算测量 (判据 C1/C2)
#   臂 A = 本地通道关闭 (基线, 分母)  臂 B = 本地通道开启 (r1 真假判别, 分子)
# 用法: bash run_arm.sh A|B [桩端口] [api端口] [role.rbin]
set -u
# ── R424 形态口径缺陷封堵 (fail-closed)────────────────────────────────────────
# 本器具的被测路径 = IL apphost (78,256 B)，**不是** AOT 产物 ⇒ 其读数只能算 JIT 中间证据。
# 依据: docs/plans/v0.45.0-r424-aot-mainline-replication.md §1；AOT 版复现见 eval/rover/r424/。
if [ "${R413_ALLOW_IL_LEGACY:-0}" != "1" ]; then
  echo "[REFUSED] eval/rover/r413/run_arm.sh 的被测二进制是 IL apphost，非 AOT 发布形态 ⇒ 不得用于对外宣称 AOT 读数。" >&2
  echo "          改用 AOT 器具: bash eval/rover/r424/run_arm.sh A|B|BP [桩端口] [api端口] [role.rbin]" >&2
  echo "          确需复现历史 JIT 读数: R413_ALLOW_IL_LEGACY=1 bash $0 ..." >&2
  exit 2
fi
ARM=${1:?用法: run_arm.sh A|B [桩端口] [api端口] [role.rbin]}
STUB_PORT=${2:-47820}
API_PORT=${3:-47810}
ROLE=${4:-}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r413
HOST=$ROOT/src/agent.host/bin/Release/net10.0/agenthost
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
STUBLOG=$DIR/stub-$ARM.log

export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
# R358: frontend-api 首行鉴权必需 (否则静默断连 = "链跑不通"的假象)
export AGENTFRAMEWORK_FRONTEND_TOKEN=r413-budget-harness-fixed-token

# 磁盘前置闸 (失控日志铁律: 先看 df, 再重定向)
echo "[preflight] $(df -h / | tail -1)"
rm -f "$CALLS" "$TURNS"; : > "$CALLS"

# 1) 该臂配置目录 (整目录覆写 AGENTFRAMEWORK_CONFIG; 不污染产品 config/base)
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$ARM" "$MODEL" <<'PY'
import re, sys
path, port, arm, model = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
if arm == "B":
    src += f"""
# R413 臂B: 本地通道开启 (r1 长驻判别; AllowGeneral=false ⇒ 主回答仍远端)
local:
  model_path: {model}
  context_size: 4608
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: true
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] arm={arm} 改写了 {n} 处 request_address → 桩 :{port}; local 段={'有' if arm == 'B' else '无'}")
PY

# 2) 远端桩 (外部真值计数)
python3 -u "$DIR/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!

# 3) 宿主 (真链) — 隔离 cwd: 空 ./data ⇒ 无旧 sessions/计划续跑污染; 复制 master.key ⇒ 角色可解密
RUNDIR="$DIR/run-$ARM"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key"
cd "$RUNDIR"
ROLE_ARG=""
[ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" $ROLE_ARG > "$HOSTLOG" 2>&1 &
HOST_PID=$!

cleanup() {
  kill "$HOST_PID" 2>/dev/null || true
  kill "$STUB_PID" 2>/dev/null || true
  sleep 1
}
trap cleanup EXIT

# 4) 就绪门 (轮询, 不盲等)
for i in $(seq 1 60); do
  if ss -ltn 2>/dev/null | grep -q ":$API_PORT "; then echo "[ready] api :$API_PORT (${i}s)"; break; fi
  if ! kill -0 "$HOST_PID" 2>/dev/null; then echo "[致命] 宿主已退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; fi
  sleep 1
done
if ! ss -ltn 2>/dev/null | grep -q ":$API_PORT "; then echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; fi

# 5) 驱动固定任务脚本
python3 -u "$DIR/drive_task.py" "$API_PORT" "$DIR/task.json" "$TURNS" || echo "[warn] 驱动器非零退出"

# 6) 结算 (桩侧真值)
python3 - "$CALLS" "$ARM" "$DIR" <<'PY'
import json, sys, os
calls, arm, d = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
if os.path.exists(calls):
    for line in open(calls, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
pt = sum(r.get("prompt_tokens_est", 0) for r in rows)
ct = sum(r.get("completion_tokens_est", 0) for r in rows)
out = {"arm": arm, "remote_calls": len(rows), "prompt_tokens_est": pt,
       "completion_tokens_est": ct, "total_tokens_est": pt + ct}
with open(os.path.join(d, f"budget-{arm}.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("[budget]", json.dumps(out, ensure_ascii=False))
PY
