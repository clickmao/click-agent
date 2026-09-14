#!/usr/bin/env bash
# R415 臂执行器 — 链级钉死「前置门入参 = 用户本轮原文」(真链 + 真端口 + 假本地后端)
#   pin = 本地通道开 + 假后端 (判定确定性: 原文含「谢谢」⇒ S, 否则 P)
#   off = 本地通道关 (负控: 同一脚本该轮本来就该走远端)
# 用法: bash run_arm.sh pin|off [stub端口] [api端口] [role.rbin] [jit|aot]
set -u
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r415
ARM=${1:?用法: run_arm.sh pin|off [stub端口] [api端口] [role.rbin] [jit|aot]}
STUB_PORT=${2:-47840}
API_PORT=${3:-47841}
ROLE=${4:-$ROOT/skeptic.rbin}
FORM=${5:-jit}
SUF=""
HOST=$ROOT/src/agent.host/bin/Release/net10.0/agenthost
if [ "$FORM" = "aot" ]; then SUF="-aot"; HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r414/agenthost}; fi
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM$SUF.jsonl
TURNS=$DIR/turns-$ARM$SUF.jsonl
HOSTLOG=$DIR/host-$ARM$SUF.log
STUBLOG=$DIR/stub-$ARM$SUF.log
LLAMALOG=$DIR/llamareq-$ARM$SUF.jsonl

export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
# ★ 关键: 本地后端替换为确定性假实现 (真链只认「二进制 + --port N」)
export AGENTFRAMEWORK_LLAMA_BIN=$DIR/fake_llama_bin.sh
export R415_LOG="$LLAMALOG"
# 本轮只测「门入参」: 关掉向量召回, 让假后端日志只承载判别器流量 (降噪)
export AGENTFRAMEWORK_BGE_MODEL=/tmp/r415-no-bge.gguf
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r415-gate-pin-fixed-token

# 磁盘前置闸 (失控日志铁律: 先看 df/空间, 再重定向)
echo "[preflight] $(df -h / | tail -1) host=$HOST form=$FORM"
rm -f "$CALLS" "$TURNS" "$LLAMALOG"; : > "$CALLS"; : > "$LLAMALOG"

# 1) 该臂配置目录 (整目录覆写 AGENTFRAMEWORK_CONFIG; 不污染产品 config/base)
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$ARM" "$MODEL" <<'PY'
import re, sys
path, port, arm, model = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
if arm == "pin":
    src += f"""
# R415 pin: 本地通道开启 (turn_gate=true) —— 后端是假实现, 判定确定性
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
print(f"[config] arm={arm} 改写了 {n} 处 request_address -> 桩 :{port}; local 段={'有' if arm == 'pin' else '无'}")
PY

# 2) 远端桩 (外部真值计数)
python3 -u "$DIR/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!

# 3) 宿主 (真链) — 隔离 cwd; 复制 master.key (角色可解密) + 判别力探针 skill (相对 cwd/skills)
RUNDIR="$DIR/run-$ARM$SUF"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key" 2>/dev/null || true
cp -r "$DIR/skills" "$RUNDIR/skills"
cd "$RUNDIR"
ROLE_ARG=""
[ -n "$ROLE" ] && [ -f "$ROLE" ] && ROLE_ARG="--role $ROLE"
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

# 6) 结算 (桩侧 + 假后端侧 真值)
python3 - "$CALLS" "$LLAMALOG" "$ARM" "$DIR" "$SUF" <<'PY'
import json, os, sys
calls, llama, arm, d, suf = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
def rows(p):
    out = []
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
cr, lr = rows(calls), rows(llama)
pt = sum(r.get("prompt_tokens_est", 0) for r in cr)
ct = sum(r.get("completion_tokens_est", 0) for r in cr)
out = {"arm": arm, "form": suf or "jit", "remote_calls": len(cr), "local_requests": len(lr),
       "local_apply_template": sum(1 for r in lr if r.get("t") == "apply-template"),
       "prompt_tokens_est": pt, "completion_tokens_est": ct, "total_tokens_est": pt + ct}
with open(os.path.join(d, f"budget-{arm}{suf}.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("[budget]", json.dumps(out, ensure_ascii=False))
PY
