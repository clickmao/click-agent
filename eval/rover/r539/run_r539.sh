#!/usr/bin/env bash
# R539 同窗复跑 —— 主线对照(外部真值 codex 外侧臂修复后首跑) + role 轴 n=3 独立窗 + 候选②③④⑤闭合
#
# 本轮轴（全部候选 + 未闭合遗留并入同一轮, 禁单步）:
#   ① 主线段: role 轴 n≥3 独立窗(w1/w2/w3) + **codex 外侧对照臂修复并真跑**(R534 减法批删掉
#      eval/rover/r504/codex_solver_r504.py, 而 proj_run_side.py 仍引用它 ⇒ 该臂断链)。
#      修法: codex 跑器落在本轮目录(eval/rover/r539/codex_solver_r539.py, 内容取自 22dd360),
#      并由 eval/rover/r539/proj_run_side_r539.py 指向它(不改受护历史轮目录)。
#   ② rc=8 成对报「自测未达成 ∧ 产物可疑」+ 机检「rc=8 不作正确性证据」(rc8_evidence_guard.py)
#   ③ 缺信息停链(rc=2)路径首测: ms1 探针臂(期望 rc=2 ∧ 零副作用), 三态记账
#   ④ 生成器 --check 挂进提交钩子(fail-closed, 旁路 AGENTFRAMEWORK_R1GEN_CHECK=0)
#   ⑤ 预注册增补器具 fail-closed(tools/prereg_amend.py, 只插入不改写全文)
#
# 铁律: 禁 push; 串行起臂(2 vCPU); 缺任一前提 ⇒ fail-closed 停手; 口径=付费真值取中继 usage。
# 验收: 收口前跑 exec_precondition --round r539; rc≠0 ⇒ 降幅一律标「参考(未可验收)」。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r539
TS=$R/taskset-r539.json
WINS="${R539_WINDOWS:-w1 w2 w3}"
PORT=${R539_ADAPTER_PORT:-48961}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R539_AGENT_BIN:-/tmp/pub_r539/agenthost}
TMO=${R539_TIMEOUT:-1800}
ROLE=$R/role-r539.txt
CODEX_BIN=${R539_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
SKIP_CODEX=${R539_SKIP_CODEX:-0}
export DOTNET_ROOT="$HOME/.dotnet"
unset AGENTFRAMEWORK_R1_ROLE_FILE

# --- 0 全局守卫 (fail-closed) -------------------------------------------------
[ -f "$TS" ] || { echo "[致命] 缺题集 $TS"; exit 3; }
[ -f "$ROLE" ] || { echo "[致命] 缺 role 额外数据 $ROLE"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$R/codex_solver_r539.py" ] || { echo "[致命] 缺 codex 跑器 $R/codex_solver_r539.py"; exit 3; }
if [ "$SKIP_CODEX" != "1" ]; then
  [ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
fi
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
for W in $WINS; do [ -e "$R/run-$W" ] && { echo "[致命] $R/run-$W 已存在(禁覆盖)"; exit 4; }; done
mkdir -p "$R/logs"
echo "R539 (loop $(date -Is))" > "$REPO/.git/ROUND_CLAIM"

cleanup_r539() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r539 EXIT
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 (硬条件①): 题面自洽 + 与 R536 逐字节对拍 ----------------------
python3 - "$TS" "$WINS" "$R" > "$R/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
ts, wins, R = sys.argv[1], sys.argv[2].split(), sys.argv[3]
d = json.load(io.open(ts, encoding="utf-8"))
r536 = json.load(io.open("/home/agentuser/AgentFramework/eval/rover/r536/taskset-r536.json", encoding="utf-8"))
old = {t["tid"]: t for t in r536["tasks"]}
bad = 0
for t in d["tasks"]:
    p = t.get("prompt") or ""
    h = hashlib.sha256(p.encode()).hexdigest()
    same = (t["tid"] not in old) or (old[t["tid"]]["prompt"] == p)
    for w in wins:
        os.makedirs(os.path.join(R, "run-%s" % w), exist_ok=True)
        io.open(os.path.join(R, "run-%s" % w, "task-%s-prompt.txt" % t["tid"]), "w", encoding="utf-8").write(p)
    ok = (h == t.get("prompt_sha256")) and same
    bad += 0 if ok else 1
    print("tid=%s family=%s sha=%s declared=%s self=%s vs_r536_byte_identical=%s hidden=%s ok=%s"
          % (t["tid"], t.get("family"), h[:16], (t.get("prompt_sha256") or "")[:16],
             h == t.get("prompt_sha256"), "n/a(新题)" if t["tid"] not in old else same,
             t.get("hidden_cases"), ok))
# cases 脚本逐字节对拍 (t1/m1 与 R536 同源)
import filecmp
for cs in ("run_cases_r529.py", "run_cases_r531_math.py"):
    a = os.path.join(R, "cases", cs); b = "/home/agentuser/AgentFramework/eval/rover/r536/cases/" + cs
    same = os.path.isfile(a) and os.path.isfile(b) and filecmp.cmp(a, b, shallow=False)
    bad += 0 if same else 1
    print("cases %s byte_identical_to_r536=%s" % (cs, same))
raph = hashlib.md5(io.open(os.path.join(R, "role-r539.txt"), "rb").read()).hexdigest()
r536h = hashlib.md5(io.open("/home/agentuser/AgentFramework/eval/rover/r536/role-r536.txt", "rb").read()).hexdigest()
print("role md5=%s r536=%s identical=%s" % (raph, r536h, raph == r536h))
bad += 0 if raph == r536h else 1
sys.exit(0 if bad == 0 else 3)
PY
prc=$?; cat "$R/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { echo "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }

# --- 2 每窗: 起手闸 → adapter → 冒烟 → 臂 → 判分 → 快照 ------------------------
run_window() {
  local W=$1
  local D=$R/run-$W SMOKE=$R/run-$W/smoke
  mkdir -p "$D"/{adapter,logs,smoke}
  echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r539"
  cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; return 3; }
  grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
  grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; return 3; }
  [ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; return 3; }
  export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"   # 缺此项 ⇒ 请求绕过计量 adapter = 无读数

  for i in 1 2; do
    python3 "$REPO/eval/rover/r483/preflight_gate.py" --round "R539-$W" --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
    local v m
    v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
    m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
    echo "[$(date +%H:%M:%S)] 起手闸 $i: $v (mem=${m}MB)" | tee -a "$D/logs/run.txt"
    [ "$v" = "PASS" ] || { echo "[致命] 起手闸 $i 未过 ⇒ 不起臂 (fail-closed)"; return 2; }
  done

  set -a; . "$REPO/.env.local"; set +a
  DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
    > "$D/logs/adapter.log" 2>&1 &
  APID=$!
  local ok=0
  for i in $(seq 1 40); do
    curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
  done
  [ "$ok" = "1" ] || { echo "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; return 3; }
  sleep 3
  echo "[$(date +%H:%M:%S)] adapter 就绪 (pid=$APID, dump=$D/adapter)" | tee -a "$D/logs/run.txt"
  maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }

  mkdir -p "$SMOKE/work"
  env AGENTFRAMEWORK_WORKSPACE="$SMOKE/work" AGENTFRAMEWORK_PY_RUN=1 \
      AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_TRANSCRIPT="$SMOKE/transcript.json" \
      AGENTFRAMEWORK_R1_TAG="R539-$W-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
      timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
        --output-mode text --session-id "r539-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
  local src=$?
  local sr1 srole
  sr1=$(python3 -c "import json,sys;print('rc=%s'%json.load(open('$SMOKE/transcript.json')).get('rc'))" 2>/dev/null || echo "rc=?")
  srole=$(python3 -c "import json;print('role_note_chars=%s'%json.load(open('$SMOKE/transcript.json')).get('role_note_chars'))" 2>/dev/null || echo "role=?")
  echo "[$(date +%H:%M:%S)] 冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)" | tee -a "$D/logs/run.txt"
  if [ "$src" != "0" ]; then
    echo "[中止] 接线冒烟未通过 (fail-closed, 不起臂)" | tee -a "$D/logs/run.txt"
    kill "$APID" 2>/dev/null
    return 9
  fi

  run_r1(){   # $1=臂名 $2=tid $3=role(1|0)
    local A=$1 T=$2 ROL=$3 i0 i1 rc
    i0=$(maxidx)
    mkdir -p "$D/$A/$T/work"
    local E=(env "AGENTFRAMEWORK_WORKSPACE=$D/$A/$T/work" AGENTFRAMEWORK_PY_RUN=1
             "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/$T/audit"
             AGENTFRAMEWORK_R1_CONTRACT=1
             "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/$T/transcript.json"
             "AGENTFRAMEWORK_R1_TAG=R539-$W-$A")
    [ "$ROL" = "1" ] && E+=("AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
    "${E[@]}" timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-$T-prompt.txt")" --output-mode text \
        --session-id "r539-$(echo "$A-$T-$W" | tr 'A-Z' 'a-z')" > "$D/$A/$T/reply.txt" 2> "$D/$A/$T/stderr.txt"
    rc=$?
    i1=$(maxidx)
    echo "[$(date +%H:%M:%S)] 臂 $A/$T rc=$rc role=$ROL adapter_range=[$((i0+1)),$i1]" | tee -a "$D/logs/run.txt"
    echo "$A-$T $((i0+1)) $i1" >> "$D/logs/idx.txt"
  }

  run_r1 R1nr t1 0
  run_r1 R1r  t1 1
  run_r1 R1r  m1 1
  [ "$W" = "w1" ] && run_r1 R1ms ms1 1

  local j0 j1 arc
  j0=$(maxidx)
  env python3 "$R/proj_run_side_r539.py" --side agent --arm A1-on --out "$D/A1-on" \
    --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
    --taskset "$TS" --tasks t1 --timeout "$TMO" > "$D/logs/run-A1-on.txt" 2>&1
  arc=$?; j1=$(maxidx)
  echo "[$(date +%H:%M:%S)] 臂 A1-on/t1 rc=$arc adapter_range=[$((j0+1)),$j1]" | tee -a "$D/logs/run.txt"
  echo "A1-on-t1 $((j0+1)) $j1" >> "$D/logs/idx.txt"

  if [ "$SKIP_CODEX" != "1" ]; then
    j0=$(maxidx)
    env python3 "$R/proj_run_side_r539.py" --side codex --arm C-codex --out "$D/C-codex" \
      --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
      --taskset "$TS" --tasks t1 --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
    arc=$?; j1=$(maxidx)
    echo "[$(date +%H:%M:%S)] 臂 C-codex/t1 rc=$arc adapter_range=[$((j0+1)),$j1] ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))" | tee -a "$D/logs/run.txt"
    echo "C-codex-t1 $((j0+1)) $j1" >> "$D/logs/idx.txt"
  fi

  # 判分 (隐藏用例真跑; 停链臂的 transcript 副本随快照带走, 供 ms1 判据机检)
  [ -f "$D/R1ms/ms1/transcript.json" ] && cp "$D/R1ms/ms1/transcript.json" "$D/R1ms/ms1/work/_r539_transcript.json"
  local PAIRS="R1nr:t1 R1r:t1 R1r:m1 A1-on:t1"
  [ "$W" = "w1" ] && PAIRS="$PAIRS R1ms:ms1"
  for pair in $PAIRS; do
    local A=${pair%%:*} T=${pair##*:} sc np
    sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='$T'][0])")
    ( cd "$D/$A/$T/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$A/$T/cases.txt" 2>&1
    echo $? >> "$D/$A/$T/cases.txt"
    np=$(grep -c '^CASE .* PASS' "$D/$A/$T/cases.txt" || true)
    echo "[$(date +%H:%M:%S)] 判分 $A/$T: PASS=$np/$(python3 -c "import json;d=json.load(open('$TS'));print([t['hidden_cases'] for t in d['tasks'] if t['tid']=='$T'][0])") rc=$(tail -1 "$D/$A/$T/cases.txt")" | tee -a "$D/logs/run.txt"
    [ -z "$(find "$D/$A/$T/work" -type f -not -name '_r539_*' -print -quit 2>/dev/null)" ] && \
      echo "[警告] 产物树为空: $D/$A/$T/work (按 fail-closed 记账, 不得当绿)" | tee -a "$D/logs/run.txt"
  done
  if [ "$SKIP_CODEX" != "1" ]; then
    local sc np
    sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='t1'][0])")
    ( cd "$D/C-codex/t1/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/C-codex/t1/cases.txt" 2>&1
    echo $? >> "$D/C-codex/t1/cases.txt"
    np=$(grep -c '^CASE .* PASS' "$D/C-codex/t1/cases.txt" || true)
    echo "[$(date +%H:%M:%S)] 判分 C-codex/t1: PASS=$np/30 rc=$(tail -1 "$D/C-codex/t1/cases.txt")" | tee -a "$D/logs/run.txt"
  fi

  kill "$APID" 2>/dev/null; sleep 1
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  ss -ltn 2>/dev/null | grep -q ":$PORT " && echo "[警告] 端口 $PORT 未释放" | tee -a "$D/logs/run.txt" || true

  # 快照 + 自报表 (铁律 11 前置器可发现形态)
  python3 - "$D" "$R" "$W" "$TS" >> "$D/logs/run.txt" 2>&1 <<'PY'
import json, os, shutil, sys
D, R, W, TS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ts = json.load(open(TS, encoding="utf-8"))
hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
snap = os.path.join(R, "snapshots", W); ev = os.path.join(R, "evidence/windows", W)
os.makedirs(snap, exist_ok=True); os.makedirs(ev, exist_ok=True)
rows = []; manifest = {"window": W, "run_dir": os.path.relpath(D, os.path.dirname(R)), "arms": {}}
pairs = [("R1nr", "t1", "agent"), ("R1r", "t1", "agent"), ("R1r", "m1", "agent"), ("A1-on", "t1", "agent")]
if W == "w1":
    pairs.append(("R1ms", "ms1", "agent"))
if os.path.isdir(os.path.join(D, "C-codex")):
    pairs.append(("C-codex", "t1", "codex"))
for arm, tid, side in pairs:
    if side == "codex":
        src = os.path.join(D, arm, tid, "work"); dst = os.path.join(snap, "codex", tid)
    else:
        src = os.path.join(D, arm, tid, "work"); dst = os.path.join(snap, "agent%s-%s" % (arm, tid), tid)
    if os.path.isdir(src):
        if os.path.isdir(dst): shutil.rmtree(dst)
        shutil.copytree(src, dst)
    cpath = os.path.join(D, arm, tid, "cases.txt")
    npass = ntot = 0; rc = None
    if os.path.isfile(cpath):
        lines = open(cpath, encoding="utf-8", errors="replace").read().splitlines()
        if lines and lines[-1].strip().isdigit():
            rc = int(lines[-1].strip()); lines = lines[:-1]
        npass = sum(1 for l in lines if l.startswith("CASE ") and l.strip().endswith("PASS"))
        ntot = sum(1 for l in lines if l.startswith("CASE "))
    all_pass = bool(rc == 0 and ntot > 0 and npass == ntot and ntot == hid.get(tid, -1))
    rows.append({"arm": "%s-%s" % (arm, tid), "tid": tid, "side": side,
                 "all_pass": all_pass, "cases_pass": npass, "cases_total": ntot,
                 "hidden_cases": hid.get(tid), "cases_rc": rc})
    manifest["arms"]["%s-%s" % (arm, tid)] = {"snapshot": os.path.relpath(dst, R), "all_pass": all_pass}
json.dump({"rows": rows}, open(os.path.join(ev, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(manifest, open(os.path.join(ev, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("快照+自报表 %s: %s" % (W, ", ".join("%s=%s(%s/%s)" % (r["arm"], r["all_pass"], r["cases_pass"], r["cases_total"]) for r in rows)))
PY
  return 0
}

for W in $WINS; do
  run_window "$W"; wrc=$?
  echo "WINDOW_RC $W $wrc" >> "$R/logs/run.txt"
done

# --- 3 分析 (role A/B + 成本分列 + rc8 机检) ---------------------------------
python3 "$R/analyze_r539.py" --round-dir "$R" > "$R/logs/analyze.txt" 2>&1
echo "ANALYZE_RC=$?" | tee -a "$R/logs/analyze.txt"
cat "$R/logs/analyze.txt"

python3 "$R/rc8_evidence_guard.py" --dir "$R" > "$R/logs/rc8-guard.txt" 2>&1
grc=$?
echo "RC8_GUARD_RC=$grc" >> "$R/logs/rc8-guard.txt"
tail -5 "$R/logs/rc8-guard.txt"

# --- 4 铁律 11 收口器 (rc 原样记录; rc≠0 ⇒ 降幅一律标「参考(未可验收)」) -------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r539 > "$R/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$R/logs/precond.txt"
tail -24 "$R/logs/precond.txt"

{ echo "R539 收口 $(date -Is)"
  echo "windows=$WINS"
  echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "input: $(head -6 "$R/logs/input-pin.txt" | tr '\n' ' | ')"
  for W in $WINS; do echo "idx[$W]: $(cat "$R/run-$W/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"; done
  echo "rc8_guard_rc=$grc"; echo "precond_rc=$pcr"
} > "$R/SUMMARY-r539.txt" 2>&1
echo "完成: $R"
exit 0
