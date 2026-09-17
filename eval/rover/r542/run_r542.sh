#!/usr/bin/env bash
# R542 同窗剂量消融 —— g1(随机游戏长任务, 58 隐藏用例) 的 **执行回灌修复预算** 轴
#
# 动因 (R540 收口实测): g1 两窗 rc=5(stage=expect_stdout_exhausted) 且失败面**含题面公开用例**
#   w1: wythoff#43-public/#44-public stdout_mismatch(模型自测 s10 实测 `WIN 6 0` vs 期望 `WIN 15 15`)
#   w2: life#00-public/#01-public rc=1(自测 s7 TypeError, stderr 已回显)
#   ⇒ 自测闸生效、缺陷已回显, 但 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1 的**单轮**回灌修复不足。
#   本轴: 单变量 = MAX_EXEC_REPAIR ∈ {1,2,3} × 3 次独立 session; 另补 g1 的 A1-on 旧路径基线(EXP1-Q51 点名缺失面)。
#
# 铁律: 禁 push; 串行起臂(2 vCPU); 零产品源码改动 ⇒ 沿用 R539 二进制; 缺任一前提 ⇒ fail-closed; 口径: 付费真值取中继 usage。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r542
TS=$R/taskset-r542.json
PORT=${R542_ADAPTER_PORT:-48977}
W=${R542_WINDOW:-w1}
D=${R542_RUN_DIR:-$R/run-$W}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R542_AGENT_BIN:-/tmp/pub_r539/agenthost}
TMO=${R542_TIMEOUT:-300}
A1_TMO=${R542_A1_TIMEOUT:-720}
ROLE=$R/role-r542.txt
SIDE_RUNNER=$REPO/eval/rover/r540/proj_run_side_r540.py
SMOKE=$D/smoke
unset AGENTFRAMEWORK_R1_ROLE_FILE 2>/dev/null || true

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] || { echo "[致命] 缺题集 $TS"; exit 3; }
[ -f "$ROLE" ] || { echo "[致命] 缺 role 额外数据 $ROLE"; exit 3; }
[ -f "$SIDE_RUNNER" ] || { echo "[致命] 缺旧路径跑器 $SIDE_RUNNER"; exit 3; }
mkdir -p "$D"/{adapter,logs,smoke}
cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r542"
echo "R542 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"   # 同仓并发闸: 后续节拍见 claim 即让路 (EXIT trap 清除)

cleanup_r542() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r542 EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1           # 契约修复轮固定 1 (非本轮变量)
cd "$REPO" || exit 3

# --- 1 同输入硬门 (sha256/md5 逐项机检; 不一致 ⇒ 不起臂) ---------------------
python3 - "$R" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
R, D = sys.argv[1], sys.argv[2]
pin = json.load(io.open(os.path.join(R, "input-pins-r542.json"), encoding="utf-8"))["g1"]
ts = json.load(io.open(os.path.join(R, "taskset-r542.json"), encoding="utf-8"))
t = [x for x in ts["tasks"] if x["tid"] == "g1"][0]
p = t["prompt"]; h = hashlib.sha256(p.encode()).hexdigest()
def md5(rel):
    return hashlib.md5(open(os.path.join("/home/agentuser/AgentFramework", rel), "rb").read()).hexdigest()
io.open(os.path.join(D, "task-g1-prompt.txt"), "w", encoding="utf-8").write(p)
rows = [
  ("prompt_sha256", h, pin["prompt_sha256"], h == pin["prompt_sha256"] == t.get("prompt_sha256")),
  ("hidden_cases", str(t["hidden_cases"]), str(pin["hidden_cases"]), str(t["hidden_cases"]) == str(pin["hidden_cases"])),
  ("cases_script_md5", md5("eval/rover/r542/cases/run_cases_r521.py"), pin["cases_script_md5"],
   md5("eval/rover/r542/cases/run_cases_r521.py") == pin["cases_script_md5"]),
  ("role_file_md5", md5("eval/rover/r542/role-r542.txt"), pin["role_file_md5"],
   md5("eval/rover/r542/role-r542.txt") == pin["role_file_md5"]),
  ("cases_json_md5", md5("eval/rover/r542/cases/cases-r521.json"), pin["cases_json_md5"],
   md5("eval/rover/r542/cases/cases-r521.json") == pin["cases_json_md5"]),
  ("xref_r540_r531_r536", "byte-identical", "declared", all(x["same"] for x in pin["xref"])),
]
bad = sum(1 for *_, ok in rows if not ok)
for k, got, exp, ok in rows:
    print("  %-22s got=%s exp=%s ok=%s" % (k, str(got)[:20], str(exp)[:20], ok))
print("同输入硬门:", "PASS" if bad == 0 else "FAIL(%d)" % bad)
sys.exit(0 if bad == 0 else 3)
PY
prc=$?; cat "$D/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (g1 题面 sha256 / 用例脚本 + 题集 md5 / role md5 全同)"

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R542 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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

# --- 3.5 接线冒烟 (fail-fast, 不挂 role) ------------------------------------
mkdir -p "$SMOKE/work"
env AGENTFRAMEWORK_WORKSPACE="$SMOKE/work" AGENTFRAMEWORK_PY_RUN=1 \
    AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_TRANSCRIPT="$SMOKE/transcript.json" \
    AGENTFRAMEWORK_R1_TAG="R542-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id "r542-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
srole=$(grep -o '"role_note_chars": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
[ "$src" = "0" ] || { log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; }

# --- 4 R1 剂量臂 (9 = {1,2,3}×3reps, 交错次序以抑时序漂移) -------------------
run_r1(){   # $1 = 臂目录名(同时是 tag) $2 = exec 修复预算 $3 = rep 标签
  local A=$1 XR=$2 REP=$3 i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$A/g1/work"
  env "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work" AGENTFRAMEWORK_PY_RUN=1 \
      "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/g1/audit" \
      AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/g1/transcript.json" \
      "AGENTFRAMEWORK_R1_TAG=R542-$W-$A" \
      "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=$XR" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
        --session-id "r542-$A-$REP" > "$D/$A/g1/reply.txt" 2> "$D/$A/g1/stderr.txt"
  rc=$?
  i1=$(maxidx)
  log "臂 $A/g1 xr=$XR rc=$rc session=$REP adapter_range=[$((i0+1)),$i1]"
  echo "$A-g1 $((i0+1)) $i1 $XR" >> "$D/logs/idx.txt"
}

for rep in a b c; do
  for xr in 1 2 3; do
    run_r1 "R1x${xr}${rep}" "$xr" "$rep"
  done
done

# --- 5 臂 A1on (旧路径 agent, 同窗同题 g1; EXP1-Q51 点名缺失面) --------------
j0=$(maxidx)
env -u AGENTFRAMEWORK_R1_CONTRACT -u AGENTFRAMEWORK_R1_TRANSCRIPT -u AGENTFRAMEWORK_R1_TAG \
    -u AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR -u AGENTFRAMEWORK_R1_ROLE_FILE -u AGENTFRAMEWORK_R1_MAX_REPAIR \
    python3 "$SIDE_RUNNER" --side agent --arm A1on --out "$D/A1on" \
      --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
      --taskset "$TS" --tasks g1 --timeout "$A1_TMO" > "$D/logs/run-A1on.txt" 2>&1
arc=$?
j1=$(maxidx)
log "臂 A1on/g1 rc=$arc adapter_range=[$((j0+1)),$j1] $(tail -1 "$D/logs/run-A1on.txt" 2>/dev/null | head -c 220)"
echo "A1on-g1 $((j0+1)) $j1 0" >> "$D/logs/idx.txt"

# --- 6 判分 (隐藏用例真跑; 与题集 cases 同源, 独立进程) ----------------------
for A in R1x1a R1x1b R1x1c R1x2a R1x2b R1x2c R1x3a R1x3b R1x3c A1on; do
  sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='g1'][0])")
  ( cd "$D/$A/g1/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$A/g1/cases.txt" 2>&1
  echo $? >> "$D/$A/g1/cases.txt"
  np=$(grep -c '^CASE .* PASS' "$D/$A/g1/cases.txt" || true)
  [ -z "$(find "$D/$A/g1/work" -type f -print -quit 2>/dev/null)" ] && \
    log "[警告] 产物树为空: $D/$A/g1/work (按 fail-closed 记账, 不得当绿)"
  log "判分 $A/g1: PASS=$np/58 rc=$(tail -1 "$D/$A/g1/cases.txt")"
done

# --- 7 仓内快照 + 自报表 (铁律 11 前置器可发现形态) -------------------------
python3 - "$D" "$R" "$W" "$TS" >> "$D/logs/run.txt" 2>&1 <<'PY'
import json, os, shutil, sys
D, R, W, TS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ts = json.load(open(TS, encoding="utf-8"))
hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
snap = os.path.join(R, "snapshots", W); ev = os.path.join(R, "evidence/windows", W)
os.makedirs(snap, exist_ok=True); os.makedirs(ev, exist_ok=True)
ARMS = ["R1x1a","R1x1b","R1x1c","R1x2a","R1x2b","R1x2c","R1x3a","R1x3b","R1x3c","A1on"]
rows = []; manifest = {"window": W, "run_dir": os.path.relpath(D, os.path.dirname(R)), "arms": {}}
for arm in ARMS:
    src = os.path.join(D, arm, "g1", "work"); dst = os.path.join(snap, "agent%s-g1" % arm, "g1")
    if os.path.isdir(src):
        if os.path.isdir(dst): shutil.rmtree(dst)
        shutil.copytree(src, dst)
    cpath = os.path.join(D, arm, "g1", "cases.txt")
    npass = ntot = 0; rc = None
    if os.path.isfile(cpath):
        lines = open(cpath, encoding="utf-8", errors="replace").read().splitlines()
        if lines and lines[-1].strip().isdigit():
            rc = int(lines[-1].strip()); lines = lines[:-1]
        npass = sum(1 for l in lines if l.startswith("CASE ") and l.strip().endswith("PASS"))
        ntot = sum(1 for l in lines if l.startswith("CASE "))
    all_pass = bool(rc == 0 and ntot > 0 and npass == ntot and ntot == hid.get("g1", -1))
    rows.append({"arm": "%s-g1" % arm, "tid": "g1", "side": "agent", "all_pass": all_pass,
                 "cases_pass": npass, "cases_total": ntot, "hidden_cases": hid.get("g1"), "cases_rc": rc})
    manifest["arms"]["%s-g1" % arm] = {"snapshot": os.path.relpath(dst, R), "all_pass": all_pass}
json.dump({"rows": rows}, open(os.path.join(ev, "report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(manifest, open(os.path.join(ev, "artifacts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("快照+自报表: " + ", ".join("%s=%s(%s/%s)" % (r["arm"], r["all_pass"], r["cases_pass"], r["cases_total"]) for r in rows))
PY

# --- 8 分析 (剂量-代价曲线 + 同窗判据 + 实发 prompt 机检) --------------------
python3 "$R/analyze_r542.py" --run-dir "$D" --window "$W" --taskset "$TS" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 9 铁律 11 收口器 (rc 原样记录; rc≠0 ⇒ 降幅标「参考(未可验收)」) --------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r542 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -20 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 10 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R542 同窗剂量消融 ($W) $(date -Is)"
  echo "run=$D"
  echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "题面: $(cat "$D/logs/input-pin.txt" | tr '\n' ' | ')"
  echo "单变量: AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR ∈ {1,2,3} × 3 独立 session; 另 A1on(旧路径)"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"
} > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
