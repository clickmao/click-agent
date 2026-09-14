#!/usr/bin/env bash
# R371 D7/D1 验收臂执行器 — 真链 + 确定性远端桩 (半行截断 / 空正文 / 完整正文)
# 用法: bash run_arm.sh <ok|truncate|empty|empty_always> [桩端口=47830] [api端口=47831]
set -u
ARM=${1:?用法: run_arm.sh <ok|truncate|empty|empty_always> [桩端口] [api端口]}
STUB_PORT=${2:-47830}
API_PORT=${3:-47831}
FORM=${4:-jit}   # jit | aot : AOT 发布形态复跑时用后缀区分, 不覆盖 JIT 证据
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r371d7
HOST=${AGENTFRAMEWORK_HOST_BIN:-$ROOT/src/agent.host/bin/Release/net10.0/agenthost}
SUF=$([ "$FORM" = "jit" ] && echo "" || echo "-$FORM")
CFG=$DIR/config-$ARM$SUF
CALLS=$DIR/calls-$ARM$SUF.jsonl
TURNS=$DIR/turns-$ARM$SUF.jsonl
TEL=$DIR/tel-$ARM$SUF.jsonl
HOSTLOG=$DIR/host-$ARM$SUF.log
STUBLOG=$DIR/stub-$ARM$SUF.log
echo "[form] $FORM host=$HOST"

export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=stub-harness-fixed-token

echo "[preflight] $(df -h / | tail -1)"
rm -f "$CALLS" "$TURNS" "$TEL"; : > "$CALLS"

# 1) 该臂配置目录 (整目录覆写; 不污染产品 config/base): 远端地址指向桩, 无 local 段
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
python3 - "$CFG/base/models.yaml" "$STUB_PORT" <<'PY'
import re, sys
path, port = sys.argv[1], sys.argv[2]
src = open(path, encoding="utf-8").read()
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + "http://127.0.0.1:%s/v1/chat/completions" % port, src)
open(path, "w", encoding="utf-8").write(src)
print("[config] 改写了 %d 处 request_address -> 桩 :%s" % (n, port))
PY

# 2) 桩 (外部真值)
python3 -u "$DIR/stub_arm.py" "$STUB_PORT" "$CALLS" "$ARM" > "$STUBLOG" 2>&1 &
STUB_PID=$!

# 3) 宿主 (真链) — 隔离 cwd: 空 ./data; 复制 master.key
RUNDIR="$DIR/run-$ARM"
rm -rf "$RUNDIR"; mkdir -p "$RUNDIR/data"
cp -f "$ROOT/data/master.key" "$RUNDIR/data/master.key"
cd "$RUNDIR"
AGENTFRAMEWORK_CONFIG="$CFG" "$HOST" --frontend-api "$API_PORT" > "$HOSTLOG" 2>&1 &
HOST_PID=$!

cleanup() {
  kill "$HOST_PID" 2>/dev/null || true
  kill "$STUB_PID" 2>/dev/null || true
  wait "$HOST_PID" 2>/dev/null || true
  wait "$STUB_PID" 2>/dev/null || true
}
trap cleanup EXIT

# 就绪探测 (无盲等)
for i in $(seq 1 40); do
  if python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(0 if s.connect_ex(('127.0.0.1',$API_PORT))==0 else 1)"; then
    echo "[ready] api :$API_PORT ($((i*500))ms)"; break
  fi
  sleep 0.5
done

python3 -u "$DIR/drive_d7.py" "$API_PORT" "$DIR/task.json" "$TURNS"
DRIVE_EXIT=$?
echo "DRIVE_EXIT=$DRIVE_EXIT"

# 4) 遥测落库 + 外部真值摘要
TELSRC="$RUNDIR/data/telemetry/host.jsonl"
[ -f "$TELSRC" ] && cp -f "$TELSRC" "$TEL"
python3 - "$CALLS" "$TEL" "$ARM" <<'PY'
import json, sys
calls, tel, arm = sys.argv[1], sys.argv[2], sys.argv[3]
n = sum(1 for _ in open(calls, encoding="utf-8"))
ev = {}
try:
    for line in open(tel, encoding="utf-8"):
        try: o = json.loads(line.lstrip("\ufeff"))
        except Exception: continue
        ev[o.get("point")] = ev.get(o.get("point"), 0) + 1
except FileNotFoundError:
    pass
print("[truth] arm=%s 远端请求=%d 遥测事件=%s" % (arm, n, json.dumps({k: v for k, v in sorted(ev.items()) if "llm" in k or "trunc" in k}, ensure_ascii=False)))
PY
