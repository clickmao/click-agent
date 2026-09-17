#!/usr/bin/env bash
# R536 同窗复跑 —— **R535 两处未闭合项闭合后的同题复跑**（同一 AOT / 同题面 / 同判分脚本）
#
# 本轮轴（全部来自 R535 的未闭合项）:
#   ① 契约死路分支已修 ⇒ 挂 role 臂应恢复可推进（R535: 两次补全皆 plan=[] ⇒ rc=4 / 0-30）;
#   ② rc 域区分 ⇒ 不挂 role 臂应 rc=8 self_test_unmet（产物在盘）而非 rc=5「链未达成」;
#   ③ 成本/质量读数照旧分列（每臂 n=1 单窗 ⇒ 只作参考读数, 不作稳定增益结论）。
#
# 铁律: 禁 push; 串行起臂 (2 vCPU); 缺任一前提 ⇒ fail-closed 停手。口径: 付费真值取中继 usage。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r536
TS=$R/taskset-r536.json
PORT=${R536_ADAPTER_PORT:-48931}
W=${R536_WINDOW:-w1}
D=${R536_RUN_DIR:-$R/run-$W}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R536_AGENT_BIN:-/tmp/pub_r536/agenthost}
TMO=${R536_TIMEOUT:-1800}
ROLE=$R/role-r536.txt
SMOKE=$D/smoke
TIDS="${R536_TIDS:-t1}"                 # 本轮只跑 t1 (跨族面 m1/g1 不做)
unset AGENTFRAMEWORK_R1_ROLE_FILE

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] || { echo "[致命] 缺题集 $TS"; exit 3; }
[ -f "$ROLE" ] || { echo "[致命] 缺 role 额外数据 $ROLE"; exit 3; }
mkdir -p "$D"/{adapter,logs,smoke}
cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r536"
echo "R536 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"   # 同仓并发闸: 后续节拍见claim即让路 (EXIT trap 清除)

# 收口兜底: **必须在任何 exit 之前装好** —— R535 实测两次踩坑 (本脚本沿用同一收口):
#   ① 冒烟中止路径曾漏杀 adapter ⇒ 端口被占, 后续起手闸假阴性;
#   ② 起手闸未过时 trap 尚未安装 ⇒ ROUND_CLAIM 残留, 阻塞下一轮。
cleanup_r536() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r536 EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 + 题面物化 (三题逐条核 sha) --------------------------------
python3 - "$TS" "$TIDS" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
ts, tids, D = sys.argv[1], sys.argv[2].split(), sys.argv[3]
d = json.load(io.open(ts, encoding="utf-8"))
bad = 0
for tid in tids:
    t = [x for x in d["tasks"] if x["tid"] == tid][0]
    p = t.get("prompt") or ""
    h = hashlib.sha256(p.encode()).hexdigest()
    decl = t.get("prompt_sha256")
    io.open(os.path.join(D, "task-%s-prompt.txt" % tid), "w", encoding="utf-8").write(p)
    ok = (h == decl)
    bad += 0 if ok else 1
    print("tid=%s family=%s prompt_sha256=%s declared=%s self_consistent=%s cases=%s ok=%s"
          % (tid, t.get("family"), h[:16], (decl or "")[:16], h == decl, t.get("hidden_cases"), ok))
sys.exit(0 if bad == 0 else 3)
PY
prc=$?; cat "$D/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (三题题面 sha256 自洽; 题面物化 $D/task-*-prompt.txt)"

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R536 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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

# --- 3.5 接线冒烟 (fail-fast, 不挂 role): 接线不通则中止, 不浪费同窗预算 -------
mkdir -p "$SMOKE/work"
env AGENTFRAMEWORK_WORKSPACE="$SMOKE/work" AGENTFRAMEWORK_PY_RUN=1 \
    AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_TRANSCRIPT="$SMOKE/transcript.json" \
    AGENTFRAMEWORK_R1_TAG="R536-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id "r536-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
srole=$(grep -o '"role_note_chars": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
if [ "$src" != "0" ]; then log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; fi

# --- 4 R1 臂 (结构化契约管道): 单条路径, 无工具面/无纪律尾块 -----------------
run_r1(){   # $1 = 臂目录名(同时也是 tag) $2 = tid $3 = role(1|0)
  local A=$1 T=$2 ROL=$3
  local i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$A/$T/work"
  local E=(env "AGENTFRAMEWORK_WORKSPACE=$D/$A/$T/work" AGENTFRAMEWORK_PY_RUN=1
           "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/$T/audit"
           AGENTFRAMEWORK_R1_CONTRACT=1
           "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/$T/transcript.json"
           "AGENTFRAMEWORK_R1_TAG=R536-$W-$A")
  [ "$ROL" = "1" ] && E+=("AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  "${E[@]}" timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-$T-prompt.txt")" --output-mode text \
      --session-id "r536-$(echo "$A" | tr 'A-Z' 'a-z')-$T-$W" > "$D/$A/$T/reply.txt" 2> "$D/$A/$T/stderr.txt"
  rc=$?
  i1=$(maxidx)
  log "臂 $A/$T rc=$rc role=$ROL adapter_range=[$((i0+1)),$i1]"
  echo "$A-$T $((i0+1)) $i1" >> "$D/logs/idx.txt"
}

run_r1 R1nr t1 0      # role 挂载 A/B 控制臂 (rc 域修复的观测位)
run_r1 R1r  t1 1      # 主管道臂 (挂 role 额外数据) —— R535 该臂 0/30 的唯一阻塞项

# --- 5 臂 A1-on (本侧 agent 旧路径, 同窗同题 t1) ----------------------------
j0=$(maxidx)
env python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm A1-on --out "$D/A1-on" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
  --taskset "$TS" --tasks t1 --timeout "$TMO" > "$D/logs/run-A1-on.txt" 2>&1
arc=$?
j1=$(maxidx)
log "臂 A1-on/t1 rc=$arc adapter_range=[$((j0+1)),$j1]"
echo "A1-on-t1 $((j0+1)) $j1" >> "$D/logs/idx.txt"

# --- 6 判分 (隐藏用例真跑; 与题集 cases 同源) --------------------------------
for pair in R1nr:t1 R1r:t1 A1-on:t1; do
  A=${pair%%:*}; T=${pair##*:}
  sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='$T'][0])")
  ( cd "$D/$A/$T/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$A/$T/cases.txt" 2>&1
  echo $? >> "$D/$A/$T/cases.txt"
  np=$(grep -c ' PASS' "$D/$A/$T/cases.txt" || true)
  [ -z "$(find "$D/$A/$T/work" -type f -print -quit 2>/dev/null)" ] && \
    log "[警告] 产物树为空: $D/$A/$T/work (按 fail-closed 记账, 不得当绿)"
  log "判分 $A/$T: PASS=$np/$(python3 -c "import json;d=json.load(open('$TS'));print([t['hidden_cases'] for t in d['tasks'] if t['tid']=='$T'][0])") rc=$(tail -1 "$D/$A/$T/cases.txt")"
done

# --- 7 仓内快照 + 自报表 (铁律 11 前置器的可发现形态) ------------------------
python3 - "$D" "$R" "$W" "$TS" >> "$D/logs/run.txt" 2>&1 <<'PY'
import json, os, shutil, sys
D, R, W, TS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ts = json.load(open(TS, encoding="utf-8"))
hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
snap = os.path.join(R, "snapshots", W)
ev = os.path.join(R, "evidence/windows", W)
os.makedirs(snap, exist_ok=True); os.makedirs(ev, exist_ok=True)
rows = []
manifest = {"window": W, "run_dir": os.path.relpath(D, os.path.dirname(R)), "arms": {}}
for pair in ("R1nr:t1", "R1r:t1", "A1-on:t1"):
    arm, tid = pair.split(":")
    src = os.path.join(D, arm, tid, "work")
    dst = os.path.join(snap, "agent%s-%s" % (arm, tid), tid)
    if os.path.isdir(src):
        if os.path.isdir(dst): shutil.rmtree(dst)
        shutil.copytree(src, dst)
    cpath = os.path.join(D, arm, tid, "cases.txt")
    npass = ntot = 0; rc = None
    if os.path.isfile(cpath):
        lines = open(cpath, encoding="utf-8", errors="replace").read().splitlines()
        if lines and lines[-1].strip().isdigit():
            rc = int(lines[-1].strip()); lines = lines[:-1]
        npass = sum(1 for l in lines if l.strip().endswith("PASS") and l.startswith("CASE "))
        ntot = sum(1 for l in lines if l.startswith("CASE "))
    all_pass = bool(rc == 0 and ntot > 0 and npass == ntot and ntot == hid.get(tid, -1))
    rows.append({"arm": "%s-%s" % (arm, tid), "tid": tid, "side": "agent",
                 "all_pass": all_pass, "cases_pass": npass, "cases_total": ntot,
                 "hidden_cases": hid.get(tid), "cases_rc": rc})
    manifest["arms"]["%s-%s" % (arm, tid)] = {"snapshot": os.path.relpath(dst, R), "all_pass": all_pass}
json.dump({"rows": rows}, open(os.path.join(ev, "report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(manifest, open(os.path.join(ev, "artifacts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("快照+自报表: " + ", ".join("%s=%s(%s/%s)" % (r["arm"], r["all_pass"], r["cases_pass"], r["cases_total"])
                                 for r in rows))
PY

# --- 8 分析 (实发 prompt 机检 + 成本分列 + role A/B) -------------------------
python3 "$R/analyze_r536.py" --run-dir "$D" --window "$W" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 9 铁律 11 收口器 (照跑, rc 原样记录; rc≠0 ⇒ 降幅一律标「参考(未可验收)」) ---
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r536 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -16 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 10 收口 --------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R536 同窗收口 ($W) $(date -Is)"
  echo "run=$D"
  echo "agent_bin=$AGENT_BIN"
  sha256sum "$AGENT_BIN"
  echo "题面: $(cat "$D/logs/input-pin.txt" | tr '\n' ' | ')"
  echo "臂: R1nr-t1(不挂role) / R1r-t1(挂role) / A1-on-t1"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"
} > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
