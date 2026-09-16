#!/usr/bin/env bash
# R496 臂执行器 —— 由 R494 版机**派生** (逐条差异见下方"相对 R494 的差异")。
#
# 相对 R494 的差异:
#   1) 命名空间 r494 → r496 (DIR / 端口 / 臂名集 / 中继日志前缀)
#   2) 被测二进制 = **R496 重新 AOT 发布产物** (/tmp/pub_r496/agenthost) —— 本轮改了链代码
#      (本地决策台账落盘 + 尾部挂载) ⇒ 必须重发布; sha256 记入 flags-*.json.host_sha256, 三臂同产物
#   3) 臂矩阵 (3 臂, 单变量阶梯):
#        B  = 全关 (turn_gate off / repeat_skip off / 声明门 off / pair_trim off / 通道 off / 挂载 off) ← 同窗分母
#        T0 = R494 的 T1 逐位复现 (gate on / skip on / 声明门 on / pair_trim on / 通道 on) + 挂载轴 **off**
#        T1 = T0 + **挂载轴 on** (AGENTFRAMEWORK_LOCAL_DECISION_MOUNT=1 + 台账落盘路径) ← 本轮唯一新增变量
#      ⇒ T0↔T1 差 = 台账挂载单变量; B↔T1 = 同窗总降幅 (验收口径)
#   4) 夹具: 前 12 轮逐字节继承 R494 网格, **追加 3 轮**"链自持台账核对码"必错族 (t13/t14/t15)
#      ⇒ 与 R494 非同窗 (只作参照, 禁跨窗相减)
#   5) 收口断言: 臂末跑 assert_face_r496.py (fail-closed) —— 机检"挂载面三源一致 (实发/落盘/打点)"+
#      隔离通道面 (继承 R494)
#
# 远端: 本地中继 relay_real_r475.py(v2) → 真供应商端点 (与 R494 同一端点/同一模型名);
#   宿主侧 key 仍为 dummy (key 只在臂进程 env 里, 不落文件/日志)。
# 用法: bash run_arm_real_r496.sh <B|T0|T1> [tag] [relay_port] [api_port]
set -u
ARM=${1:?用法: run_arm_real_r496.sh <B|T0|T1> [tag] [relay_port] [api_port]}
TAG=${2:-}
RELAY_PORT=${3:-49610}
API_PORT=${4:-49612}
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r496
for f in teardown_assert.py assert_face_r496.py; do
  [ -f "$DIR/$f" ] || { echo "[致命] aux 缺失: $f ⇒ 拒跑 (防 teardown/收口空跑泄漏)"; exit 12; }
done
RELAY=$ROOT/eval/rover/r475/relay_real_r475.py
TOOLS=$ROOT/eval/rover/r430
GRID=p15code
TASK=$DIR/grid/task-p15-code.json
HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r496/agenthost}
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
  B|T0|T1) CWD_NAME=run-$ARM$TAG ;;
  *) echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac
RUNDIR=$DIR/$CWD_NAME
ARCH=$DIR/rundata-$ARM$TAG
[ -s "$CALLS" ] && { echo "[致命] REFUSE_NS_COLLISION: $CALLS 已有读数"; exit 7; }
[ -s "$USAGE" ] && { echo "[致命] REFUSE_NS_COLLISION: $USAGE 已有读数"; exit 7; }
[ -e "$ARCH" ] && { echo "[致命] REFUSE_NS_COLLISION: $ARCH 已存在"; exit 7; }
[ -e "$DIR/flags-$ARM$TAG.json" ] && { echo "[致命] REFUSE_NS_COLLISION: flags-$ARM$TAG.json 已存在"; exit 7; }
[ -f "$TASK" ] || { echo "[致命] 任务脚本缺失: $TASK"; exit 8; }
[ -x "$HOST" ] || { echo "[致命] 被测二进制不存在: $HOST (先跑 AOT 发布)"; exit 5; }
# 起手闸/沉降**单一源** (禁手抄): 阈值/build-server shutdown/沉降轮询全在
#   eval/rover/r483/preflight_gate.py 内; 本文件不含任何阈值字面量。
python3 "$ROOT/eval/rover/r483/preflight_gate.py" --out "$DIR/preflight-$ARM$TAG.json" --round R496 \
  || { echo "[致命] 起手闸未通过 (rc=$?)"; exit 10; }
# key 来源: 优先专用名, 退回环境已配的供应商凭据 (两者都只进 env, 不落文件/日志)
if [ -n "${R496_UPSTREAM_KEY:-}" ]; then UP_KEY="$R496_UPSTREAM_KEY"
elif [ -n "${R494_UPSTREAM_KEY:-}" ]; then UP_KEY="$R494_UPSTREAM_KEY"
elif [ -n "${HERMES_CUSTOM_LIGHTVELA_DEEPSEEK_API_KEY:-}" ]; then UP_KEY="$HERMES_CUSTOM_LIGHTVELA_DEEPSEEK_API_KEY"
else echo "[致命] 无可用上游 key (R494_UPSTREAM_KEY / 环境凭据均未设)"; exit 9; fi
export R475_UPSTREAM_KEY="$UP_KEY"

export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
export AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy-key
export AGENTFRAMEWORK_KEYS_BIGMODEL=dummy-key
export AGENTFRAMEWORK_FRONTEND_TOKEN=r496-harness-fixed-token
echo "[preflight] arm=$ARM cwd=$CWD_NAME bin=$HOST grid=$GRID $(df -h / | tail -1)"
python3 "$TOOLS/prov_check.py" --json "$DIR/prov-$ARM$TAG.json" "$HOST" || { echo "[致命] V0 形态闸红"; exit 6; }
BIN_SHA=$(sha256sum "$HOST" | cut -d' ' -f1)
rm -f "$CALLS" "$USAGE" "$TURNS"; : > "$CALLS"; : > "$USAGE"
rm -rf "$CFG"; mkdir -p "$CFG/base"
cp "$ROOT"/config/base/*.yaml "$CFG/base/" 2>/dev/null || true
# 阶梯 (R493 连续 + 通道轴):
#   B  = 全关
#   T0 = gate/skip/声明门/pair_trim 全开 (R493 T 逐位)
#   T1 = T0 + 通道轴
case "$ARM" in
  B)  MP=$M3B; GATE=false; RJ=true; ROLE="$ROLE_GROWTH"; RS=off; TD=off; PT=off; CH=off; MOUNT=off; AB=on ;;
  T0) MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=off; MOUNT=off; AB=on ;;
  T1) MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=on;  MOUNT=on;  AB=on ;;
esac
export AGENTFRAMEWORK_GATE_REPEAT_SKIP=$RS
export AGENTFRAMEWORK_TOOL_DECL_GATE=$TD
# 产品取值只认 1/true ⇒ 人面 on|off 必须**显式映射** (否则 "on" 被静默当关: 臂自称门开、产品实则门关)
case "$PT" in off|on) : ;; *) echo "[致命] pair_trim 只接受 off|on"; exit 12 ;; esac
if [ "$PT" = on ]; then export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=1; else export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=0; fi
# R494 通道轴: 同样**显式映射** (默认关; 未设不得被当成开)
case "$CH" in off|on) : ;; *) echo "[致命] channel 只接受 off|on"; exit 12 ;; esac
if [ "$CH" = on ]; then export AGENTFRAMEWORK_TOOL_DECL_CHANNEL=1; else export AGENTFRAMEWORK_TOOL_DECL_CHANNEL=0; fi
# R496 台账挂载轴 (本轮唯一新增变量): 关 = 提示面零字节 (产品默认); 开 = 尾部追加台账块。
case "$MOUNT" in off|on) : ;; *) echo "[致命] mount 只接受 off|on"; exit 12 ;; esac
if [ "$MOUNT" = on ]; then export AGENTFRAMEWORK_LOCAL_DECISION_MOUNT=1; else export AGENTFRAMEWORK_LOCAL_DECISION_MOUNT=0; fi
export AGENTFRAMEWORK_LOCAL_DECISION_LEDGER="$RUNDIR/data/ledger/local-decisions.jsonl"
# R496 收口轴 (候选③-a): 命令面越界拒执行 —— 本轮**三臂同值 = 常量** (非本轮变量; 消融对照留给后续轮),
#   故仅作 flags 记录; 关掉它的唯一办法是显式 AGENTFRAMEWORK_ACTION_BOUNDARY=0。
case "$AB" in off|on) : ;; *) echo "[致命] action_boundary 只接受 off|on"; exit 12 ;; esac
if [ "$AB" = on ]; then export AGENTFRAMEWORK_ACTION_BOUNDARY=1; else export AGENTFRAMEWORK_ACTION_BOUNDARY=0; fi

unset AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY
unset AGENTFRAMEWORK_LOCAL_WARMUP
echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD channel=$CH pair_trim=$PT mount=$MOUNT boundary=$AB"
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
# R494 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)
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
python3 - "$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" "$TAG" "$TD" "$PT" "$CH" "$MOUNT" "$AB" <<'PY'
import hashlib, json, os, re, sys
d, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td, pt, ch, mount, ab = sys.argv[1:17]
t = open(cfg, encoding="utf-8").read()
loc = re.search(r"(?ms)^local:\n(.*?)(?=^\S|\Z)", t).group(1)
def fld(k):
    m = re.search(r"(?m)^\s+%s:\s*(\S+)" % k, loc)
    return m.group(1) if m else None
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""
flags = {
    "arm": arm, "arm_class_note": "由 denominator_gate.arm_class_of(flags) 单一来源派生 (脚本不自报类别)",
    "turn_gate": fld("turn_gate"), "relation_judge": fld("relation_judge"), "repeat_skip": rs,
    "ledger_mount": mount,         # R496 台账挂载轴 (off=B/T0; on=T1) ← 本轮唯一新增变量
    "ledger_path_env": os.environ.get("AGENTFRAMEWORK_LOCAL_DECISION_LEDGER", ""),
    # R496 候选①: 真值形态与文案面的**机检锚** (判据器按这些锚核实发字节)
    "ledger_code_mode": "hmac-sha256(process-csprng-key32) [:12] —— 真值不落盘/不进打点 (只留 code8/key_id 指纹)",
    "mount_authorize_restate": "on (显式授权复述: 旧「用户无法从别处得到」金丝雀措辞已删)",
    "action_boundary": ab,         # R496 候选③-a 收口: 命令面越界拒执行 —— 三臂**同值常量**
    "recall_gate_redact": "on (候选③-b: 越界子句正文隐去, 与 action_boundary 同批上)",
    "tool_decl_gate": td,          # 意图轴 (off=B; on=T0/T1)
    "tool_decl_channel": ch,       # R494 通道轴 (off=B/T0; on=T1) ← 本轮唯一新增变量
    "replay_pair_trim": pt,        # off=B; on=T0/T1
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
    "judge_adv_sha256": sha(os.path.join(d, "judge_adv_r496.py")),
    "prereg_sha256": sha(os.path.join(d, "prereg_r496.json")),
    "grid_note": "R496: 前 12 轮与判据器逐字节继承 R494/R493 (前段同窗可比); t13-15 = 必错族 (真值只在挂载块内); "
    "**订正 (R496 自抓)**: 臂阶梯 B→T0→T1 中 T0→T1 实为**两轴** (通道轴 + 挂载轴), 不是单变量 ⇒ 挂载单轴需第四臂 T2; "
    "同时三臂共有常量 action_boundary=on / recall_gate_redact=on (非本轮变量)",
}
open(os.path.join(d, "flags-%s%s.json" % (arm, tag)), "w", encoding="utf-8").write(json.dumps(flags, ensure_ascii=False, indent=1))
print("[flags] " + json.dumps({k: flags[k] for k in ("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "tool_decl_gate",
                            "tool_decl_channel", "replay_pair_trim", "rundir_cwd")}, ensure_ascii=False))
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
cp "$RUNDIR/data/ledger/local-decisions.jsonl" "$DIR/ledger-$ARM$TAG.jsonl" 2>/dev/null || true
mv "$RUNDIR" "$ARCH" && echo "[archive] $ARCH"
echo "[relay] calls=$(wc -l < "$USAGE") usage_rows; blocked=$(grep -c '\"blocked\": true' "$USAGE" 2>/dev/null || echo 0)"
# teardown 先行 (夹具收口不受判据结果影响), 再跑收口断言 (fail-closed)
python3 "$DIR/teardown_assert.py" --arm "$ARM$TAG" --api-port "$API_PORT" --relay-port "$RELAY_PORT" --reap \
  --out "$DIR/teardown-$ARM$TAG.json" || { echo "[致命] teardown 断言红"; exit 11; }
python3 "$DIR/assert_face_r496.py" --arm "$ARM$TAG" --dir "$DIR" --channel "$CH" --mount "$MOUNT" \
  || { echo "[致命] 通道轴实发面断言红 (fail-closed)"; exit 13; }
echo "[done] arm=$ARM"
