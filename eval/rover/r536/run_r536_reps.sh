#!/usr/bin/env bash
# R536 追加：**同臂复跑 (reps)** —— 只为把「摆动 vs 效应」分开，不进验收面。
#
# 为什么需要：w1 里挂 role 臂 0/30（自造模块名）而不挂 role 臂 30/30（1 调用）——
# 单窗 n=1 不能区分「role 轴效应」与「本窗模型输出质量摆动」（R523 纪律）。
# 因此**不改判据、不改产品**，只把两条 R1 臂各再跑 2 次，报逐窗读数 + 极差。
# 复跑落在 run-reps/<k>/ 且**不写 evidence/windows** ⇒ 前置器的验收面不受影响（非交付面）。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r536
D=$R/run-reps
PORT=${R536_REPS_PORT:-48937}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R536_AGENT_BIN:-/tmp/pub_r536/agenthost}
TMO=900
ROLE=$R/role-r536.txt
unset AGENTFRAMEWORK_R1_ROLE_FILE
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺 AOT $AGENT_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
mkdir -p "$D"/{adapter,logs}
cp -r "$CFGSRC" "$D/agent-cfg" || exit 3
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
echo "reps=$D port=$PORT bin=$AGENT_BIN $(date -Is)" > "$D/.owner-r536-reps"

cleanup(){ kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg" AGENTFRAMEWORK_PY_RUN=1 ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1
cd "$REPO" || exit 3

[ -f "$D/task-t1-prompt.txt" ] || cp "$R/run-w1/task-t1-prompt.txt" "$D/task-t1-prompt.txt"

set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; exit 3; }
log "adapter 就绪 pid=$APID"

maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }

run_r1(){  # $1=rep 序号 $2=臂名 $3=role(1|0)
  local K=$1 A=$2 ROL=$3 i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$K/$A/work"
  local E=(env "AGENTFRAMEWORK_WORKSPACE=$D/$K/$A/work" AGENTFRAMEWORK_PY_RUN=1
           AGENTFRAMEWORK_R1_CONTRACT=1
           "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$K/$A/transcript.json"
           "AGENTFRAMEWORK_R1_TAG=R536-rep${K}-${A}")
  [ "$ROL" = "1" ] && E+=("AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  "${E[@]}" timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-t1-prompt.txt")" --output-mode text \
      --session-id "r536-rep${K}-$(echo "$A" | tr 'A-Z' 'a-z')" > "$D/$K/$A/reply.txt" 2> "$D/$K/$A/stderr.txt"
  rc=$?
  i1=$(maxidx)
  log "rep$K $A rc=$rc role=$ROL adapter_range=[$((i0+1)),$i1]"
  echo "$K-$A $((i0+1)) $i1" >> "$D/logs/idx.txt"
}

for K in r2 r3; do
  run_r1 $K R1nr 0
  run_r1 $K R1r  1
done

# 判分（隐藏用例真跑；与题集 cases 同源）
for pair in r2:R1nr r2:R1r r3:R1nr r3:R1r; do
  K=${pair%%:*}; A=${pair##*:}
  sc=$(python3 -c "import json;d=json.load(open('$R/taskset-r536.json'));print([t['cases'] for t in d['tasks'] if t['tid']=='t1'][0])")
  ( cd "$D/$K/$A/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$K/$A/cases.txt" 2>&1
  echo $? >> "$D/$K/$A/cases.txt"
  np=$(grep -c ' PASS' "$D/$K/$A/cases.txt" || true)
  rc=$(tail -1 "$D/$K/$A/cases.txt")
  trc=$(python3 -c "import json;print(json.load(open('$D/$K/$A/transcript.json')).get('rc'))" 2>/dev/null)
  stg=$(python3 -c "import json;print(json.load(open('$D/$K/$A/transcript.json')).get('stage'))" 2>/dev/null)
  stm=$(python3 -c "import json;print(json.load(open('$D/$K/$A/transcript.json')).get('self_test_unmet'))" 2>/dev/null)
  log "判分 $K/$A: PASS=$np/30 judge_rc=$rc R1rc=$trc stage=$stg self_test_unmet=$stm"
done

python3 "$R/analyze_r536.py" --run-dir "$D" --window reps > "$D/logs/analyze.txt" 2>&1
log "分析 rc=$?"
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
log "reps 完成: $D"
exit 0
