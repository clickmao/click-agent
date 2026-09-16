#!/usr/bin/env bash
# R493 臂执行器 —— 由 R492 版机**派生** (diff 见 eval/rover/r493/run_arm_real_r493.diff)。
# 相对 R492 的差异逐条:
#   1) 命名空间 r492 → r493 (DIR / round / key 变量名 / 端口 / 中继日志前缀)
#      但被测二进制**仍是 R492 冻结产物** (/tmp/pub_r492/agenthost, sha256 048a2d56…) ——
#      R493 不改链代码 ⇒ 不重发布 AOT ⇒ 三臂与 R492 四臂同产物, 跨臂可比
#   2) 窗内网格换为 R493 对抗族加严网格 (eval/rover/r493/grid/task-p12-adv.json):
#      第 1 轮追加多轮前置真值 (3 加 5 等于 8 / 圆周率是无理数), t10..t12 =
#      假断言(承前置真值) / 反事实改写 / 不可能前提 ⇒ 同窗内用**新夹具**跑
#      B/R/T 三臂, 拿到同窗分母 (R492 只有 T 臂, 旧 p12 夹具)
#   3) 臂矩阵 = B(Arole: 门关+重复跳过关) / R(门+重复跳过) / T(门+重复跳过+声明门),
#      B 与 R 的 pair_trim=off, T 的 pair_trim=on ⇒ 单变量阶梯见 analyze_r493.py 明示
#   4) flags-*.json 增记 judge_adv_sha256 / prereg_sha256 (器具 ↔ 证据绑定)
# 远端: 本地中继 relay_real_r475.py(v2) → 真供应商端点; 宿主侧 key 仍为 dummy
#   (key 只在中继进程的 env 里, 不落任何文件/日志)。
# 用法: bash run_arm_real_r493.sh <Arole|R|T> [tag] [relay_port] [api_port] [pair_trim:off|on]
set -u
ARM=${1:?用法: run_arm_real_r493.sh <Arole|R|T> [tag] [relay_port] [api_port] [pair_trim:off|on]}
TAG=${2:-}
RELAY_PORT=${3:-49210}
API_PORT=${4:-49212}
PAIR_TRIM=${5:-off}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r493
for f in teardown_assert.py; do [ -f "$DIR/$f" ] || { echo "[致命] aux 缺失: $f ⇒ 拒跑 (防 teardown 空跑泄漏)"; exit 12; }; done
RELAY=$ROOT/eval/rover/r475/relay_real_r475.py
TOOLS=$ROOT/eval/rover/r430
GRID=p12adv
TASK=$DIR/grid/task-p12-adv.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r492/agenthost}
M3B=/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf
ROLE_GROWTH=$ROOT/eval/rover/r431/fixture/skeptic-growth.rbin
CFG=$DIR/config-$ARM$TAG
CALLS=$DIR/calls-$ARM$TAG.jsonl
USAGE=$DIR/usage-$ARM$TAG.jsonl
TURNS=$DIR/turns-$ARM$TAG.jsonl
HOSTLOG=$DIR/host-$ARM$TAG.log
RELAYLOG=$DIR/relay-$ARM$TAG.log
SERVLOG=$DIR/server-$ARM$TAG.txt
case "$ARM" in
  Arole|R|T) CWD_NAME=run-$ARM$TAG$([ "$PAIR_TRIM" = on ] && echo -pt) ;;
  *) echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
RUNDIR=$DIR/$CWD_NAME
ARCH=$DIR/rundata-$ARM$TAG
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数"; exit 7; }
[ -s "$USAGE" ] && { echo "[致命] REFUSE_NS_COLLISION: $USAGE 已有读数"; exit 7; }
[ -e "$ARCH" ] && { echo "[致命] REFUSE_NS_COLLISION: $ARCH 已存在"; exit 7; }
[ -e "$DIR/flags-$ARM$TAG.json" ] && { echo "[致命] REFUSE_NS_COLLISION: flags-$ARM$TAG.json 已存在"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST"; exit 5; }
# 起手闸/沉降**单一源** (禁手抄) —— 阈值/build-server shutdown/沉降轮询全在
#   eval/rover/r483/preflight_gate.py 内; 本文件不含任何阈值字面量 (机检 grep 计数 0)。
python3 "$ROOT/eval/rover/r483/preflight_gate.py" --out "$DIR/preflight-$ARM$TAG.json" --round R493 \
  || { echo "[致命] 起手闸未通过 (rc=$?)"; exit 10; }
[ -n "${R493_UPSTREAM_KEY:-}" ] || { echo "[致命] R493_UPSTREAM_KEY 未传入"; exit 9; }
export R475_UPSTREAM_KEY="$R493_UPSTREAM_KEY"   # v2 中继只读此名; 不落文件/日志

export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r493-harness-fixed-token
echo "[preflight] arm=$ARM cwd=$CWD_NAME bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM$TAG.json" "$HOST" || { echo "[致命] V0 形态闸红"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$USAGE" "$TURNS"; : > "$CALLS"; : > "$USAGE"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
case "$ARM" in
  Arole) MP=$M3B; GATE=false; RJ=true;  ROLE="$ROLE_GROWTH"; RS=off; TD=off ;;
  R)     MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; RS=on ; TD=off ;;
  T)     MP=$M3B; GATE=true;  RJ=true;  ROLE="$ROLE_GROWTH"; RS=on ; TD=on  ;;
esac
export AGENTFRAMEWORK_GATE_REPEAT_SKIP=$RS
# R492 声明面按需: **显式**导出 (禁"未设=默认"含糊; 门默认关 ⇒ 生产行为不变)
export AGENTFRAMEWORK_TOOL_DECL_GATE=$TD
# R492 回放配对剪裁: **显式**导出 (默认关 ⇒ 与 R491 逐字节同行为; on = 剔除零远端调用轮的 user 侧回放)
case "$PAIR_TRIM" in off|on) : ;; *) echo "[致命] pair_trim 只接受 off|on (got=$PAIR_TRIM)"; exit 12 ;; esac
# 产品取值只认 1/true (ReplayPairTrim.Decide) ⇒ 人面 on|off 必须**显式映射**,
# 否则 "on" 会被静默当关 (假阴性: 臂自称门开、产品实则门关)。
if [ "$PAIR_TRIM" = on ]; then export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=1; else export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=0; fi
unset AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY
unset AGENTFRAMEWORK_LOCAL_WARMUP
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD pair_trim=$PAIR_TRIM"
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
# R493 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)
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
python3 - "$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" "$TAG" "$TD" "$PAIR_TRIM" <<'PY'
import hashlib, json, os, re, sys
d, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td, pt = sys.argv[1:14]
t = open(cfg, encoding="utf-8").read()
loc = re.search(r"(?ms)^local:\n(.*?)(?=^\S|\Z)", t).group(1)
def fld(k):
    m = re.search(r"(?m)^\s+%s:\s*(\S+)" % k, loc)
    return m.group(1) if m else None
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""
flags = {
    "arm": arm, "arm_class_note": "由 denominator_gate.arm_class_of(flags) 单一来源派生 (脚本不自报类别)",
    "turn_gate": fld("turn_gate"), "relation_judge": fld("relation_judge"), "repeat_skip": rs,
    "tool_decl_gate": td,   # R493: 声明面按需开关 (off=B/R; on=T)
    "replay_pair_trim": pt,  # R493: 同上 (off=B/R 臂; on=T 臂)
    "repeat_priority": os.environ.get("AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY", "(unset=on)"),
    "warmup": os.environ.get("AGENTFRAMEWORK_LOCAL_WARMUP", "(unset=off)"),
    "gpu_layers": fld("gpu_layers"), "context_size": fld("context_size"), "parallel": fld("parallel"),
    "max_tokens": fld("max_tokens"), "max_prompt_tokens": fld("max_prompt_tokens"),
    "allow_general": fld("allow_general"), "model_path": fld("model_path"),
    "allowed_kinds": (re.search(r"(?m)^\s+allowed_kinds:\s*(.+)$", loc) or [None, ""])[1].strip(),
    "role_fixture": role, "role_sha256": sha(role),
    "grid": grid, "grid_sha256": sha(task),
    "host_bin": host, "host_sha256": bsha,
    "config_sha256": sha(cfg), "rundir_cwd": "eval/rover/%s/%s" % (os.path.basename(d), cwdname), "arm_key": arm + tag,
    "remote_path": "eval/rover/r475/relay_real_r475.py (v2) → https://api.deepseek.com/v1/chat/completions",
    "judge_adv_sha256": sha(os.path.join(d, "judge_adv_r493.py")),
    "prereg_sha256": sha(os.path.join(d, "prereg_r493.json")),
    "grid_note": "R493 对抗族加严网格: 第1轮带多轮前置真值; t10/t11/t12=承前置真值的假断言/反事实改写/不可能前提",
}
open(os.path.join(d, "flags-%s%s.json" % (arm, tag)), "w", encoding="utf-8").write(json.dumps(flags, ensure_ascii=False, indent=1))
print("[flags] " + json.dumps({k: flags[k] for k in ("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "tool_decl_gate",
                            "replay_pair_trim", "rundir_cwd")}, ensure_ascii=False))
PY
python3 -u "$RELAY" "$RELAY_PORT" 40 0.15 "$DIR" "$ARM$TAG" > "$RELAYLOG" 2>&1 &
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
mkdir -p "$DIR/tel-$ARM$TAG"
cp "$RUNDIR/data/telemetry/host.jsonl" "$DIR/tel-$ARM$TAG/host.jsonl" 2>/dev/null || true
grep -c '"correction_judge"' "$RUNDIR/data/telemetry/host.jsonl" > "$DIR/telcount-$ARM$TAG.txt" 2>/dev/null || true
mv "$RUNDIR" "$ARCH" && echo "[archive] $ARCH"
echo "[relay] calls=$(wc -l < "$USAGE") usage_rows; blocked=$(grep -c '\"blocked\": true' "$USAGE" 2>/dev/null || echo 0)"
python3 "$DIR/teardown_assert.py" --arm "$ARM$TAG" --api-port "$API_PORT" --relay-port "$RELAY_PORT" --reap \
  --out "$DIR/teardown-$ARM$TAG.json" || { echo "[致命] teardown 断言红"; exit 11; }
echo "[done] arm=$ARM"
