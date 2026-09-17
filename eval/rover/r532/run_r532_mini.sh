#!/usr/bin/env bash
# R532 迷你同窗对照 (接线轮): **R1 结构化契约管道 (新接线, env AGENTFRAMEWORK_R1_CONTRACT=1)**
#   vs 本侧 agent 臂 A1-on —— 同一 adapter 计量 / 同一题面 (t1 = F2 toolkit, 30 隐藏用例) / 同窗。
#
# 目的:
#   ① 证明接线**真实生效**(实发 prompt 机检: system 轮 == 恒定前缀 pin, 且来自 adapter 落盘而非产品自报);
#   ② 给出同窗成本读数 (远端调用数 / prompt+completion tokens) 与质量读数 (隐藏用例通过数) 的对照;
#   ③ 产物可实际执行 (判分 = 隐藏用例脚本真跑 `python3 -m toolkit <mod>`, 非人工阅读)。
# 铁律: 禁 push; 串行两臂 (2 vCPU); 缺任一前提 ⇒ fail-closed 停手。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r532
CASES=$REPO/eval/rover/r531/cases/run_cases_r529.py   # F2(t1) 冻结判分脚本 (与 R531 同源, 只读复用)
PORT=${R532_ADAPTER_PORT:-48921}
D=${R532_RUN_DIR:-/tmp/r532_mini}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R532_AGENT_BIN:-/tmp/pub_r532c/agenthost}
TASKSET=$REPO/eval/rover/r531/taskset-r531.json
TID=${R532_TID:-t1}
TMO=${R532_TIMEOUT:-1800}
W=${R532_WINDOW:-mini1}
SMOKE=$D/smoke

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TASKSET" ] || { echo "[致命] 缺题集 $TASKSET"; exit 3; }
mkdir -p "$D"/{adapter,logs,R1,A1-on,smoke}
cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r532"
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 + 题面物化 -----------------------------------------------
python3 - "$TASKSET" "$TID" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
ts, tid, D = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(ts, encoding="utf-8"))
t = [x for x in d["tasks"] if x["tid"] == tid][0]
p = t.get("prompt") or ""
h = hashlib.sha256(p.encode()).hexdigest()
decl = t.get("prompt_sha256")
io.open(os.path.join(D, "task-%s-prompt.txt" % tid), "w", encoding="utf-8").write(p)
ok = (h == decl)
print("tid=%s family=%s prompt_sha256=%s declared=%s self_consistent=%s cases=%s ok=%s"
      % (tid, t.get("family"), h[:16], (decl or "")[:16], h == decl, t.get("hidden_cases"), ok))
sys.exit(0 if ok else 3)
PY
prc=$?; cat "$D/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (题面 sha256 自洽; 题面物化 $D/task-$TID-prompt.txt)"

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R532 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 $i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂 (fail-closed)"; exit 2; }
done

# --- 3 adapter (计量 + FULL dump) ------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do
  curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
sleep 3
log "adapter 就绪 (pid=$APID, dump=$D/adapter, FULL=1)"
maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }

# --- 3.5 接线冒烟 (fail-fast): 若接线不通则中止, 不浪费同窗预算 ---------------
mkdir -p "$SMOKE/work"
env AGENTFRAMEWORK_WORKSPACE="$SMOKE/work" AGENTFRAMEWORK_PY_RUN=1 \
    AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_TRANSCRIPT="$SMOKE/transcript.json" \
    AGENTFRAMEWORK_R1_TAG="R532-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id r532-smoke > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
if [ "$src" != "0" ]; then log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; fi

# --- 4 臂 R1 (新接线): 单条路径 = 结构化契约管道 ---------------------------
i0=$(maxidx)
mkdir -p "$D/R1/$TID/work"
env AGENTFRAMEWORK_WORKSPACE="$D/R1/$TID/work" AGENTFRAMEWORK_PY_RUN=1 \
    AGENTFRAMEWORK_ACTION_AUDIT="$D/R1/$TID/audit" \
    AGENTFRAMEWORK_R1_CONTRACT=1 \
    AGENTFRAMEWORK_R1_TRANSCRIPT="$D/R1/$TID/transcript.json" \
    AGENTFRAMEWORK_R1_TAG="R532-$W-R1" \
    timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-$TID-prompt.txt")" --output-mode text \
      --session-id "r532-r1-$TID" > "$D/R1/$TID/reply.txt" 2> "$D/R1/$TID/stderr.txt"
r1rc=$?
i1=$(maxidx)
log "臂 R1 rc=$r1rc adapter_range=[$((i0+1)),$i1]"
echo "R1 $((i0+1)) $i1 0" >> "$D/logs/idx.txt"

# --- 5 臂 A1-on (本侧 agent, 同窗同题) -------------------------------------
j0=$(maxidx)
env python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm A1-on --out "$D/A1-on" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
  --taskset "$TASKSET" --tasks "$TID" --timeout "$TMO" > "$D/logs/run-A1-on.txt" 2>&1
arc=$?
j1=$(maxidx)
log "臂 A1-on rc=$arc adapter_range=[$((j0+1)),$j1]"
echo "A1-on $((j0+1)) $j1" >> "$D/logs/idx.txt"

# --- 6 判分 (隐藏用例真跑; 两侧同一脚本) -----------------------------------
run_cases(){  # $1 = 产物树 (工作根)   $2 = 输出
  ( cd "$1" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$CASES" ) > "$2" 2>&1
  echo $? >> "$2"
}
run_cases "$D/R1/$TID/work"    "$D/R1/$TID/cases.txt"
run_cases "$D/A1-on/$TID/work" "$D/A1-on/$TID/cases.txt"
for p in "$D/R1/$TID/work" "$D/A1-on/$TID/work"; do
  [ -z "$(find "$p" -type f -print -quit 2>/dev/null)" ] && \
    log "[警告] 产物树为空: $p (按 fail-closed 记账, 不得当绿)"
done
log "判分完成: R1=$(grep -c ' PASS' "$D/R1/$TID/cases.txt" || true) PASS ; A1-on=$(grep -c ' PASS' "$D/A1-on/$TID/cases.txt" || true) PASS"

# --- 7 分析 (实发 prompt 机检 + 成本分列) ----------------------------------
python3 "$R/analyze_r532.py" --run-dir "$D" --tid "$TID" --window "$W" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 8 铁律 11 收口器 (照跑, rc 原样记录; rc≠0 ⇒ 降幅一律标「参考(未可验收)」) ---
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r532 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -14 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 9 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R532 迷你同窗收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "题面: $TID (F2 toolkit, 30 隐藏用例) sha256=$(awk '{print $NF}' "$D/logs/input-pin.txt" | head -1)"
  echo "臂: R1(结构化契约管道, AGENTFRAMEWORK_R1_CONTRACT=1) / A1-on(本侧 agent 路径)"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"; } > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
