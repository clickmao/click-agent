#!/usr/bin/env bash
# R423 臂执行器 — 主线 KPI 在 AOT 发布形态上复现 (判据 C1/C2/C5; 形态闸 V0)
#   臂 A = 本地通道关闭（分母） · 臂 B = 前置门开 + 模型在（治疗） · 臂 B' = 前置门开 + 模型缺（无设备负控 / r1 归因臂）
# 用法: bash run_arm.sh A|B|BP [桩端口] [api端口] [role.rbin]
# 与 R413 的差别: ①被测二进制 = AOT 发布产物 且 跑前过 V0 形态闸（fail-closed）
#                 ②每臂记录二进制 sha256/bytes 入 budget json（读数绑定身份）
#                 ③新增臂 BP（无设备零回归）
set -u
ARM=${1:?用法: run_arm.sh A|B|BP [桩端口] [api端口] [role.rbin]}
STUB_PORT=${2:-47830}
API_PORT=${3:-47840}
ROLE=${4:-}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r423
# ★ 被测二进制: 必须是 AOT 发布产物（R413 的 bin/Release/net10.0/agenthost = IL apphost, 已证）
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r423/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
BADMODEL=/tmp/models/__r423_missing_model.gguf
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
STUBLOG=$DIR/stub-$ARM.log

export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r423-aot-harness-fixed-token

echo "[preflight] $(df -h / | tail -1)"

# 0) V0 形态闸（fail-closed: 形态不过 ⇒ 根本不开跑）
if [ ! -x "$HOST" ]; then echo "[致命] 被测二进制不存在/不可执行: $HOST"; exit 5; fi
python3 "$DIR/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)

rm -f "$CALLS" "$TURNS"; : > "$CALLS"

# 1) 该臂配置目录（整目录覆写; 不污染产品 config/base）
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$ARM" "$MODEL" "$BADMODEL" <<'PY'
import re, sys
path, port, arm, model, badmodel = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
if arm in ("B", "BP"):
    mp = model if arm == "B" else badmodel
    src += f"""
# R423 臂{arm}: 本地通道开启 (AllowGeneral=false ⇒ 主回答仍远端)
local:
  model_path: {mp}
  context_size: 4608
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: true
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] arm={arm} 改写了 {n} 处 request_address → 桩 :{port}; local 段={'有' if arm != 'A' else '无'}"
      + (f"; model_path={badmodel} (故意缺失)" if arm == "BP" else ""))
PY

# 2) 远端桩（外部真值计数）
python3 -u "$DIR/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!

# 3) 宿主（真链）— 隔离 cwd: 空 ./data ⇒ 无旧 sessions/计划续跑污染; 复制 master.key ⇒ 角色可解密
RUNDIR="$DIR/run-$ARM"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key"
cd "$RUNDIR"
ROLE_ARG=""
[ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" $ROLE_ARG > "$HOSTLOG" 2>&1 &
HOST_PID=$!

cleanup() { kill "$HOST_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT

# 4) 就绪门（轮询, 不盲等）
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主已退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }

# 5) 驱动固定任务脚本（与 R413 逐字相同）
python3 -u "$DIR/drive_task.py" "$API_PORT" "$DIR/task.json" "$TURNS" || echo "[warn] 驱动器非零退出"

# 6) 结算（桩侧真值 + 二进制身份绑定）
python3 - "$CALLS" "$ARM" "$DIR" "$HOST" "$BIN_SHA" <<'PY'
import json, sys, os
calls, arm, d, host, sha = sys.argv[1:6]
rows = [json.loads(l) for l in open(calls, encoding="utf-8") if l.strip()] if os.path.exists(calls) else []
pt = sum(r.get("prompt_tokens_est", 0) for r in rows)
ct = sum(r.get("completion_tokens_est", 0) for r in rows)
b = os.path.getsize(host)
out = {"arm": arm, "remote_calls": len(rows), "prompt_tokens_est": pt,
       "completion_tokens_est": ct, "total_tokens_est": pt + ct,
       "binary": host, "binary_sha256": sha, "binary_bytes": b}
json.dump(out, open(os.path.join(d, f"budget-{arm}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("[budget]", json.dumps(out, ensure_ascii=False))
PY
