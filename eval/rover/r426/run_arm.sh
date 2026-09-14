#!/usr/bin/env bash
# R426 臂执行器 — 「关系判官 (CorrectionDetector L2) 本地化」成对臂 (判据 C3..C10)
#   臂 A = 本地通道关闭（分母: 判官走远端, = R425 现状, 兼 C8 零回归对照）
#   臂 B = 门开 + relation_judge=false（R425 臂 B 口径, 判官仍走远端）
#   臂 C = 门开 + relation_judge=true + r1 在（治疗臂: 判官本地化）
#   臂 D = 同 C 但 model_path 不存在（无设备负控/归因臂: 判官须全部 remote_fallback）
# 用法: bash run_arm.sh A|B|C|D <k> [桩端口] [api端口] [role.rbin]
# 与 R425 差别: (1) 臂语义 A/B/C/D + relation_judge 开关; (2) 驱动后加 25s 结算静默, 让后台判官落地
set -u
ARM=${1:?用法: run_arm.sh A|B|C|D <k> [桩端口] [api端口] [role.rbin]}
K=${2:?缺 k (4|6|8)}
STUB_PORT=${3:-47900}
API_PORT=${4:-47901}
ROLE=${5:-}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r426
SFX=${R426_NS:-}          # 批次命名空间 (R419 教训: 每次测量唯一后缀, 同 NS 重跑必拒)
TASK=$DIR/grid/task-k$K.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/aot-r426/agenthost}
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
BADMODEL=/tmp/models/__r423_missing_model.gguf
CFG=$DIR/config-$ARM-k$K$SFX
CALLS=$DIR/calls-$ARM-k$K$SFX.jsonl
TURNS=$DIR/turns-$ARM-k$K$SFX.jsonl
HOSTLOG=$DIR/host-$ARM-k$K$SFX.log
STUBLOG=$DIR/stub-$ARM-k$K$SFX.log

# NS 闸: 同一 (臂,格) 重跑 = 静默覆盖读数 (R419 教训) ⇒ fail-closed
[ -f "$DIR/budget-$ARM-k$K$SFX.json" ] && { echo "[致命] REFUSE_NS_COLLISION: budget-$ARM-k$K$SFX.json 已存在 ⇒ 换 NS 或先归档"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }

export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r426-harness-fixed-token

echo "[preflight] k=$K arm=$ARM $(df -h / | tail -1)"

# 0) V0 形态闸 (fail-closed)
if [ ! -x "$HOST" ]; then echo "[致命] 被测二进制不存在/不可执行: $HOST"; exit 5; fi
python3 "$DIR/prov_check.py" --json "$DIR/prov-$ARM-k$K$SFX.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)

rm -f "$CALLS" "$TURNS"; : > "$CALLS"

# 1) 该臂配置目录 (整目录覆写; 不污染产品 config/base)
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$ARM" "$MODEL" "$BADMODEL" <<'PY'
import re, sys
path, port, arm, model, badmodel = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
if arm in ("B", "C", "D"):
    mp = badmodel if arm == "D" else model
    gate = "true"
    rel = "true" if arm in ("C", "D") else "false"
    src += f"""
# R426 臂{arm}: 本地通道开启 (AllowGeneral=false ⇒ 主回答仍远端); relation_judge={rel}
local:
  model_path: {mp}
  context_size: 4608
  gpu_layers: 0
  max_tokens: 256
  max_prompt_tokens: 4096
  allowed_kinds: [context_compression, keyword_tagging, tendency_analysis, intent_classification]
  allow_general: false
  turn_gate: {gate}
  relation_judge: {rel}
"""
open(path, "w", encoding="utf-8").write(src)
print(f"[config] arm={arm} 改写了 {n} 处 request_address → 桩 :{port}; local 段={'有' if arm != 'A' else '无'}"
      + (f"; relation_judge={rel}" if arm != "A" else "") + (f"; model_path={badmodel} (故意缺失)" if arm == "D" else ""))
PY

# 2) 远端桩 (外部真值计数)
python3 -u "$DIR/stub_openai.py" "$STUB_PORT" "$CALLS" > "$STUBLOG" 2>&1 &
STUB_PID=$!

# 3) 宿主 (真链) — 隔离 cwd
RUNDIR="$DIR/run-$ARM-k$K$SFX"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key"
cd "$RUNDIR"
ROLE_ARG=""
[ -n "$ROLE" ] && ROLE_ARG="--role $ROLE"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" $ROLE_ARG > "$HOSTLOG" 2>&1 &
HOST_PID=$!

cleanup() { pkill -P "$HOST_PID" 2>/dev/null || true   # R425: 框架自启的 llama-server 是宿主子进程
           kill "$HOST_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT

# 4) 就绪门 (轮询, 不盲等)
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主已退出, 见 $HOSTLOG"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }

# 5) 驱动该格任务脚本 (+25s 结算静默: 后台判官是 Task.Run, 不静默会漏掉尾轮判官证据)
python3 -u "$DIR/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
sleep 25

# 6) 结算 (桩侧真值 + 二进制身份绑定 + 遥测)
python3 - "$CALLS" "$ARM" "$DIR" "$HOST" "$BIN_SHA" "$K" "$SFX" <<'PY'
import json, sys, os, glob
calls, arm, d, host, sha, k, sfx = sys.argv[1:8]
rows = [json.loads(l) for l in open(calls, encoding="utf-8") if l.strip()] if os.path.exists(calls) else []
pt = sum(r.get("prompt_tokens_est", 0) for r in rows)
ct = sum(r.get("completion_tokens_est", 0) for r in rows)
judge = [r for r in rows if "判定用户消息相对上一轮回答" in json.dumps(r.get("messages", ""), ensure_ascii=False)]
tel = glob.glob(os.path.join(d, f"run-{arm}-k{k}{sfx}", "data/telemetry/*.jsonl"))
cp_pts = []
for f in tel:
    for l in open(f, encoding="utf-8-sig", errors="replace"):
        if '"correction_judge"' in l:
            try: cp_pts.append(json.loads(l))
            except Exception: pass
srcs = {}
for p in cp_pts:
    s = (p.get("kv") or {}).get("source", "<none>")
    srcs[s] = srcs.get(s, 0) + 1
b = os.path.getsize(host)
out = {"arm": arm, "k": int(k), "ns": sfx.lstrip("-") or "b1", "remote_calls": len(rows),
       "judge_calls": len(judge), "prompt_tokens_est": pt, "completion_tokens_est": ct,
       "total_tokens_est": pt + ct,
       "judge_prompt_tokens_est": sum(r.get("prompt_tokens_est", 0) for r in judge),
       "judge_completion_tokens_est": sum(r.get("completion_tokens_est", 0) for r in judge),
       "telemetry_correction_judge_pts": len(cp_pts),
       "telemetry_sources": srcs,
       "binary": host, "binary_sha256": sha, "binary_bytes": b}
json.dump(out, open(os.path.join(d, f"budget-{arm}-k{k}{sfx}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("[budget]", json.dumps(out, ensure_ascii=False))
PY
