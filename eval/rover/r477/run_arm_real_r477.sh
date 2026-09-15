#!/usr/bin/env bash
# R477 臂执行器 —— 由 R474 版机派生。差异逐条:
#   1) DIR r474 → r477 (读数命名空间隔离, 不覆盖 R474 证据)
#   2) 中继 relay_real.py(v1) → eval/rover/r475/relay_real_r475.py(v2: +finish_reason/empty_body/
#      reasoning_tokens/sampling/逐调用恒等式); v1 文件与 sha 保持不动 (证据↔器具绑定)
#   3) 二进制默认 /tmp/r470_publish/agenthost → /tmp/pub_r476/agenthost (含 R475 复述回放守卫 + R476 分档打点)
#   4) key 变量 R474_UPSTREAM_KEY → R477_UPSTREAM_KEY (仅转发为 v2 读取的 R475_UPSTREAM_KEY)
#   5) + MemAvailable 起手闸 (fail-closed, 2650MB, 与 R475/R476 同常数) 并落盘读数
# 其余(配置改写 / role 夹具 / 网格 / 预算闸 / quiesce / 归档)与 R474 逐字同。
#   Arole = 门关 + relation_judge=on   ← 生产等价分母
#   R     = 门开 + rj=on + repeat_skip=on ← 主判据面 (r1 在管道内)
# 与 R467 的差异: 远端由桩改成「本地中继 relay_real.py → 真 DeepSeek 端点」;
#   宿主侧 key 仍为 dummy (key 只在中继进程的 env 里, 不落任何文件/日志)。
# 用法: bash run_arm_real.sh <Arole|R> [relay_port] [api_port]
set -u
ARM=${1:?用法: run_arm_real.sh <Arole|R>}
RELAY_PORT=${2:-48110}
API_PORT=${3:-48112}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r477
RELAY=$ROOT/eval/rover/r475/relay_real_r475.py
TOOLS=$ROOT/eval/rover/r430
GRID=p12
TASK=$ROOT/eval/rover/r438/grid/task-$GRID.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r476/agenthost}
M3B=/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM
CALLS=$DIR/calls-$ARM.jsonl
USAGE=$DIR/usage-$ARM.jsonl
TURNS=$DIR/turns-$ARM.jsonl
HOSTLOG=$DIR/host-$ARM.log
RELAYLOG=$DIR/relay-$ARM.log
SERVLOG=$DIR/server-$ARM.txt
case "$ARM" in
  Arole) CWD_NAME=run-Arole ;;
  R)     CWD_NAME=run-R ;;
  *) echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
RUNDIR=$DIR/$CWD_NAME
ARCH=$DIR/rundata-$ARM
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数"; exit 7; }
[ -s "$USAGE" ] && { echo "[致命] REFUSE_NS_COLLISION: $USAGE 已有读数"; exit 7; }
[ -e "$ARCH" ] && { echo "[致命] REFUSE_NS_COLLISION: $ARCH 已存在"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
MEM_GATE_MB=2650
MEM_AVAIL_MB=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
echo "[memgate] MemAvailable=${MEM_AVAIL_MB}MB gate=${MEM_GATE_MB}MB"
[ "$MEM_AVAIL_MB" -ge "$MEM_GATE_MB" ] || { echo "[致命] MemAvailable ${MEM_AVAIL_MB}MB < ${MEM_GATE_MB}MB 起手闸"; exit 10; }
[ -n "${R477_UPSTREAM_KEY:-}" ] || { echo "[致命] R477_UPSTREAM_KEY 未传入"; exit 9; }
export R475_UPSTREAM_KEY="$R477_UPSTREAM_KEY"   # v2 中继只读此名; 不落文件/日志

export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r474-harness-fixed-token
echo "[preflight] arm=$ARM cwd=$CWD_NAME bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$USAGE" "$TURNS"; : > "$CALLS"; : > "$USAGE"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  Arole) MP=$M3B; GATE=false; RJ=true;  ROLE="$ROLE_GROWTH"; RS=off ;;
  R)     MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; RS=on  ;;
esac
export AGENTFRAMEWORK_GATE_REPEAT_SKIP=$RS
unset AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY
unset AGENTFRAMEWORK_LOCAL_WARMUP
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS"
python3 - "$CFG/base/models.yaml" "$RELAY_PORT" "$MP" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
n = len(re.findall(r"request_address:", src))
def _rw(m):
    url = m.group(2)
    if "/user/balance" in url:          # 余额接口不是聊天面 ⇒ 不改写 (它只读, dummy key 下必然 401, 不计费)
        return m.group(0)
    return m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions"
src = re.sub(r"(request_address:\s*)(\S+)", _rw, src)
src = re.sub(r"(?m)^(  (model_path|context_size|parallel|gpu_layers|max_tokens|max_prompt_tokens|allowed_kinds|allow_general|turn_gate|relation_judge):.*)$", "", src)
src += f"""
# R477 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)
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
print(f"[config] 端点改写 {n} 处 → 中继 :{port}; gate={gate} rj={rj} model={model}")
PY
python3 - "$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" <<'PY'
import hashlib, json, os, re, sys
d, arm, cfg, host, role, grid, rs, bsha, task, cwdname = sys.argv[1:11]
t = open(cfg, encoding="utf-8").read()
loc = re.search(r"(?ms)^local:\n(.*?)(?=^\S|\Z)", t).group(1)
def fld(k):
    m = re.search(r"(?m)^\s+%s:\s*(\S+)" % k, loc)
    return m.group(1) if m else None
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""
flags = {
    "arm": arm, "arm_class_note": "由 denominator_gate.arm_class_of(flags) 单一来源派生 (脚本不自报类别)",
    "turn_gate": fld("turn_gate"), "relation_judge": fld("relation_judge"), "repeat_skip": rs,
    "repeat_priority": os.environ.get("AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY", "(unset=on)"),
    "warmup": os.environ.get("AGENTFRAMEWORK_LOCAL_WARMUP", "(unset=off)"),
    "gpu_layers": fld("gpu_layers"), "context_size": fld("context_size"), "parallel": fld("parallel"),
    "max_tokens": fld("max_tokens"), "max_prompt_tokens": fld("max_prompt_tokens"),
    "allow_general": fld("allow_general"), "model_path": fld("model_path"),
    "allowed_kinds": (re.search(r"(?m)^\s+allowed_kinds:\s*(.+)$", loc) or [None, ""])[1].strip(),
    "role_fixture": role, "role_sha256": sha(role),
    "grid": grid, "grid_sha256": sha(task),
    "host_bin": host, "host_sha256": bsha,
    "config_sha256": sha(cfg), "rundir_cwd": "eval/rover/%s/%s" % (os.path.basename(d), cwdname),
    "remote_path": "eval/rover/r475/relay_real_r475.py (v2) → https://api.deepseek.com/v1/chat/completions",
}
open(os.path.join(d, "flags-%s.json" % arm), "w", encoding="utf-8").write(json.dumps(flags, ensure_ascii=False, indent=1))
print("[flags] " + json.dumps({k: flags[k] for k in ("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "rundir_cwd")}, ensure_ascii=False))
PY
python3 -u "$RELAY" "$RELAY_PORT" 40 0.15 "$DIR" "$ARM" > "$RELAYLOG" 2>&1 &
RELAY_PID=$!
sleep 1
kill -0 "$RELAY_PID" 2>/dev/null || { echo "[致命] 中继未启动"; tail -5 "$RELAYLOG"; exit 4; }
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
cleanup() { kill "$MON_PID" 2>/dev/null || true; pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true; kill "$RELAY_PID" 2>/dev/null || true; sleep 1; }
trap cleanup EXIT
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q ":$API_PORT " && { echo "[ready] api :$API_PORT (${i}s)"; break; }
  kill -0 "$HOST_PID" 2>/dev/null || { echo "[致命] 宿主已退出"; tail -20 "$HOSTLOG"; exit 3; }
  sleep 1
done
ss -ltn 2>/dev/null | grep -q ":$API_PORT " || { echo "[致命] 宿主 60s 未监听"; tail -20 "$HOSTLOG"; exit 4; }
T0=$(date +%s)
python3 -u "$TOOLS/drive_task.py" "$API_PORT" "$TASK" "$TURNS" || echo "[warn] 驱动器非零退出"
T1=$(date +%s)
last=""; stable=0; waited=0
while [ "$waited" -lt 1200 ]; do
  n=$(grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" 2>/dev/null); n=${n:-0}
  c=$(wc -l < "$USAGE" 2>/dev/null); c=${c:-0}
  key="$n/$c"
  [ "$key" = "$last" ] && stable=$((stable+1)) || stable=0
  last="$key"
  [ "$stable" -ge 14 ] && break
  sleep 5; waited=$((waited+5))
done
echo "[quiesce] drive=$((T1-T0))s wait=${waited}s judge/calls=$last bin_sha=$BIN_SHA"
echo "[server] 采样行=$(wc -l < "$SERVLOG" 2>/dev/null); 不同 pid=$(sort -u -k2 "$SERVLOG" 2>/dev/null | wc -l)"
pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true
for i in $(seq 1 20); do kill -0 "$HOST_PID" 2>/dev/null || break; sleep 0.5; done
kill "$MON_PID" 2>/dev/null || true; kill "$RELAY_PID" 2>/dev/null || true; sleep 1
mkdir -p "$DIR/tel-$ARM"
cp "$RUNDIR/data/telemetry/host.jsonl" "$DIR/tel-$ARM/host.jsonl" 2>/dev/null || true
grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" > "$DIR/telcount-$ARM.txt" 2>/dev/null || true
mv "$RUNDIR" "$ARCH" && echo "[archive] $ARCH"
echo "[relay] calls=$(wc -l < "$USAGE") usage_rows; blocked=$(grep -c '\"blocked\": true' "$USAGE" 2>/dev/null || echo 0)"
echo "[done] arm=$ARM"
