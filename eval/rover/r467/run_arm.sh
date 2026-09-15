#!/usr/bin/env bash
# R467 臂执行器 —— 分母固化: 判官路由标志 = 唯一变量 (同二进制/同桩/同网格 p12/同 role 夹具)
#   Arole = 门关 + relation_judge=on      ← 生产等价分母 (期望逐位复现 R466 Arole 13/32,097)
#   Aroff = 门关 + relation_judge=off     ← 单变量负控  (期望逐位复现 R465 Arole 21/33,323)
#   R     = 门开 + rj=on + repeat_skip=on ← 生产主判据面 (期望逐位复现 R466 R 6/14,529)
#   R2    = R 复跑                        ← 预注册 C6 (期望 6/14,531)
#
# 【cwd 钉字】宿主 prompt 的 system 首条含 `根目录: <宿主 cwd>` (逐位进 prompt)。
#   故 Arole 与 Aroff **共用同一字面 cwd** `eval/rover/r467/run-Arole` (r467 与 r465/r466 仅差一位数字;
#   已由 R465/R466 Arole 主调用 prompt_tokens 序列逐位相等实测证明该位数字 token 中性)
#   ⇒ 两臂 prompt 字节完全一致 ⇒ 复现判据可用精确等值 (不用 Δchar 折算)。
#   R/R2 沿用历史字面 run-R / run-R2 以复现 14,529 / 14,531。
#   每臂跑完把 run 目录归档为 rundata-<ARM>/ 后置 cwd 归位 (取消 rm -rf 竞态)。
# 用法: bash run_arm.sh <Arole|Aroff|R|R2> [stub_port] [api_port]
set -u
ARM=${1:?用法: run_arm.sh <Arole|Aroff|R|R2>}
STUB_PORT=${2:-48010}
API_PORT=${3:-48012}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r467
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
SERVLOG=$DIR/server-$ARM.txt
case "$ARM" in
  Arole|Aroff) CWD_NAME=run-Arole ;;
  R)           CWD_NAME=run-R ;;
  R2)          CWD_NAME=run-R2 ;;
  *) echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
RUNDIR=$DIR/$CWD_NAME
ARCH=$DIR/rundata-$ARM
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数 ⇒ 拒绝覆盖"; exit 7; }
[ -e "$ARCH" ] && { echo "[致命] REFUSE_NS_COLLISION: $ARCH 已存在 ⇒ 拒绝覆盖"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r467-harness-fixed-token
echo "[preflight] arm=$ARM cwd=$CWD_NAME bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM.json" "$HOST" || { echo "[致命] V0 形态闸红 ⇒ 拒绝跑测"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$TURNS"; : > "$CALLS"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  Arole) MP=$M3B; GATE=false; RJ=true;  ROLE="$ROLE_GROWTH"; RS=off ;;
  Aroff) MP=$M3B; GATE=false; RJ=false; ROLE="$ROLE_GROWTH"; RS=off ;;
  R|R2)  MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; RS=on  ;;
esac
export AGENTFRAMEWORK_GATE_REPEAT_SKIP=$RS
unset AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY
unset AGENTFRAMEWORK_LOCAL_WARMUP
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ role=on repeat_skip=$RS (priority/warmup = 生产默认, 未设)"
python3 - "$CFG/base/models.yaml" "$STUB_PORT" "$MP" "$GATE" "$RJ" <<'PY'
import re, sys
path, port, model, gate, rj = sys.argv[1:6]
src = open(path, encoding="utf-8").read()
src = "\n".join(l for l in src.splitlines() if not l.startswith("local:")) + "\n"
n = len(re.findall(r"request_address:", src))
src = re.sub(r"(request_address:\s*)\S+", lambda m: m.group(1) + f"http://127.0.0.1:{port}/v1/chat/completions", src)
src = re.sub(r"(?m)^(  (model_path|context_size|parallel|gpu_layers|max_tokens|max_prompt_tokens|allowed_kinds|allow_general|turn_gate|relation_judge):.*)$", "", src)
src += f"""
# R467 臂 (单变量 = relation_judge; 其余与生产 config/base/models.yaml 逐字同)
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
# R467: 臂声明台账 (从**生成后的 config** 回读, 不信脚本注释; 附二进制/夹具/cwd 字面)
python3 - "$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" <<'PY'
import hashlib, json, os, re, sys
d, arm, cfg, host, role, grid, rs, bsha, task, cwdname = sys.argv[1:11]
t = open(cfg, encoding="utf-8").read()
loc = re.search(r"(?ms)^local:\n(.*?)(?=^\S|\Z)", t).group(1)
def fld(k):
    m = re.search(r"(?m)^\s+%s:\s*(\S+)" % k, loc)
    return m.group(1) if m else None
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""
gate, rj = fld("turn_gate"), fld("relation_judge")
flags = {
    "arm": arm, "arm_class_note": "由 denominator_gate.arm_class_of(flags) 单一来源派生 (脚本不自报类别)", "arm_class_unused": ("production_equivalent" if (gate == "true" and rj == "true" and rs == "on")
                              else "denominator_rj_probe"),
    "turn_gate": gate, "relation_judge": rj, "repeat_skip": rs,
    "repeat_priority": os.environ.get("AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY", "(unset=on)"),
    "warmup": os.environ.get("AGENTFRAMEWORK_LOCAL_WARMUP", "(unset=off)"),
    "gpu_layers": fld("gpu_layers"), "context_size": fld("context_size"), "parallel": fld("parallel"),
    "max_tokens": fld("max_tokens"), "max_prompt_tokens": fld("max_prompt_tokens"), "allow_general": fld("allow_general"),
    "model_path": fld("model_path"),
    "allowed_kinds": (re.search(r"(?m)^\s+allowed_kinds:\s*(.+)$", loc) or [None, ""])[1].strip(),
    "role_fixture": role, "role_sha256": sha(role),
    "grid": grid, "grid_sha256": sha(task),
    "host_bin": host, "host_sha256": bsha,
    "config_sha256": sha(cfg), "rundir_cwd": "eval/rover/%s/%s" % (os.path.basename(d), cwdname),
}
open(os.path.join(d, "flags-%s.json" % arm), "w", encoding="utf-8").write(json.dumps(flags, ensure_ascii=False, indent=1))
print("[flags] " + json.dumps({k: flags[k] for k in ("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "rundir_cwd")}, ensure_ascii=False))
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
echo "[server] 采样行=$(wc -l < "$SERVLOG" 2>/dev/null); 不同 pid=$(sort -u -k2 "$SERVLOG" 2>/dev/null | wc -l)"
# 显式停机 (先杀宿主再归档 cwd, 避免归档期间宿主继续写)
pkill -P "$HOST_PID" 2>/dev/null || true; kill "$HOST_PID" 2>/dev/null || true
for i in $(seq 1 20); do kill -0 "$HOST_PID" 2>/dev/null || break; sleep 0.5; done
kill "$MON_PID" 2>/dev/null || true; kill "$STUB_PID" 2>/dev/null || true; sleep 1
grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" > "$DIR/telcount-$ARM.txt" 2>/dev/null || true
mv "$RUNDIR" "$ARCH" && echo "[archive] $ARCH"
python3 -u "$DIR/settle_r467.py" "$DIR" "$ARM"
