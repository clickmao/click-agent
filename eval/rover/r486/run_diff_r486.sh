#!/usr/bin/env bash
# R486 差分器: 「空正文(带 tool_calls)⇒ 浪费重试」是否已被修复消除 —— in-vitro 确定性, 不依赖真供应商/凭据。
# 臂 = 二进制 (pre=/tmp/pub_r476/agenthost, post=/tmp/pub_r479v2/agenthost) × 模式 (empty_toolcall / plain)
# 起手闸: 内存 <2650MB 或对侧会话在建/在测 ⇒ 直接拒跑 (exit 10)
set -u
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r486
TASK=$DIR/task-r486.json
ROLE=$(ls $ROOT/eval/rover/r43*/fixture/*.rbin 2>/dev/null | head -1)
export AGENTFRAMEWORK_FRONTEND_TOKEN=r486-harness-fixed-token
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_ACTION_LOOP=off
export AGENTFRAMEWORK_LLAMA_BIN=/bin/false

MEM=$(awk '/MemAvailable/{printf "%d",$2/1024}' /proc/meminfo)
HOT=$(pgrep -af 'dotnet (build|publish|test)|MSBuild.dll' | grep -v pgrep | wc -l)
echo "[preflight] MemAvailable=${MEM}MB (gate 2650) dotnet_hot=${HOT}"
[ "$MEM" -ge 2650 ] || { echo "[拒跑] 起手闸: 内存不足"; exit 10; }
[ "$HOT" -eq 0 ] || { echo "[拒跑] 对侧会话正在构建/测试 dotnet ⇒ 让行"; exit 11; }
[ -f "$TASK" ] || { echo "[拒跑] 缺夹具"; exit 3; }

idx=0
for ARM in pre post; do
  if [ "$ARM" = pre ]; then BIN=/tmp/pub_r476/agenthost; else BIN=/tmp/pub_r479v2/agenthost; fi
  [ -x "$BIN" ] || { echo "[拒跑] 二进制缺失 $BIN"; exit 3; }
  for MODE in empty_toolcall plain; do
    TAG=$ARM-$(echo "$MODE" | cut -c1-5)
    SPORT=$((48600 + idx)); APORT=$((48620 + idx)); idx=$((idx + 1))
    RD=$DIR/run-$TAG; CFG=$DIR/config-$TAG
    rm -rf "$RD" "$CFG"; mkdir -p "$RD/data" "$CFG/base"
    cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
    cp -f "$ROOT/data/master.key" "$RD/data/master.key" 2>/dev/null || true
    python3 - "$CFG/base/models.yaml" "$SPORT" <<'PY'
import re, sys
p, port = sys.argv[1], sys.argv[2]
src = open(p, encoding="utf-8").read()
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
def rw(m):
    if "/user/balance" in m.group(2):
        return m.group(0)
    return m.group(1) + "http://127.0.0.1:%s/v1/chat/completions" % port
src = re.sub(r"(request_address:\s*)(\S+)", rw, src)
src += """
# R486 臂: 远端端点 = 本地确定性桩; 本地通道关闭(只测远端空正文路径)
local:
  model_path: /home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
  context_size: 4608
  parallel: 1
  gpu_layers: 0
  max_tokens: 512
  max_prompt_tokens: 4096
  allowed_kinds: []
  allow_general: false
  turn_gate: false
  relation_judge: false
"""
open(p, "w", encoding="utf-8").write(src)
PY
    python3 -u "$DIR/stub_upstream_r486.py" "$SPORT" "$MODE" "$DIR" "$TAG" >"$DIR/stub-$TAG.log" 2>&1 &
    SPID=$!
    sleep 0.8
    kill -0 "$SPID" 2>/dev/null || { echo "[拒跑] 桩未起 $TAG"; exit 4; }
    ( cd "$RD" && AGENTFRAMEWORK_CONFIG="$CFG" "$BIN" --frontend-api "$APORT" ${ROLE:+--role "$ROLE"} >"$DIR/host-$TAG.log" 2>&1 ) &
    HPID=$!
    ok=0
    for _ in $(seq 1 60); do ss -ltn 2>/dev/null | grep -q ":$APORT " && { ok=1; break; }; sleep 1; done
    if [ "$ok" != 1 ]; then
      echo "[拒跑] $TAG 宿主未监听"; tail -15 "$DIR/host-$TAG.log"; kill "$HPID" "$SPID" 2>/dev/null; exit 5
    fi
    python3 -u "$ROOT/eval/rover/r430/drive_task.py" "$APORT" "$TASK" "$DIR/turns-$TAG.jsonl" || echo "[warn] 驱动器非零 $TAG"
    last=-1; stable=0; waited=0
    while [ $waited -lt 180 ]; do
      c=$(wc -l <"$DIR/stub-requests-$TAG.jsonl" 2>/dev/null || echo 0)
      if [ "$c" = "$last" ]; then stable=$((stable + 1)); else stable=0; fi
      last=$c
      [ $stable -ge 6 ] && break
      sleep 2; waited=$((waited + 2))
    done
    kill "$HPID" 2>/dev/null; wait "$HPID" 2>/dev/null; kill "$SPID" 2>/dev/null; sleep 0.5
    mkdir -p "$DIR/tel"; cp "$RD/data/telemetry/host.jsonl" "$DIR/tel/tel-$TAG.jsonl" 2>/dev/null || true
    REQN=$(wc -l <"$DIR/stub-requests-$TAG.jsonl" 2>/dev/null || echo 0)
    echo "[arm] $TAG bin=$(basename "$BIN") stub_requests=$REQN quiesce=${waited}s"
  done
done
echo "[done] r486"
