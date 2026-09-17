#!/usr/bin/env bash
# R540 同窗对照 —— 横切修复(codex 引擎稳定位置/fail-closed) + 跨族长任务 g1 首跑 + 读数器修复 + 两窗成本判据
#
# 本轮轴 (全部来自 R539 收口后仍未闭合的候选, 同一轮并入):
#   ① 横切修复: codex 外侧臂引擎硬编码已被 R534 删除的 r504 路径 ⇒ 提稳定位置 eval/rover/lib/codex_solver.py
#      + 候选加载器 eval/rover/lib/codex_engine.py(fail-closed) + 三处历史调用点改走加载器;
#   ② 跨族覆盖: g1(随机游戏长任务, 58 隐藏用例)在 R1 管道上首跑(R539 因预算未跑);
#   ③ 读数器修复: R539 "role 段进实发 user 轮" 未证实 = 读数器只读 side-* 摘要(恒空) ⇒ 改用 full-* 裸消息数组;
#   ④ 成本判据(主线判据之一): 同窗同题 t1 上 R1r vs A1-on 的 calls/tokens 降幅, 两窗逐窗报。
#
# 铁律: 禁 push; 串行起臂(2 vCPU); 缺任一前提 ⇒ fail-closed 停手; 口径: 付费真值取中继 usage。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r540
TS=$R/taskset-r540.json
PORT=${R540_ADAPTER_PORT:-48971}
W=${R540_WINDOW:-w1}
D=${R540_RUN_DIR:-$R/run-$W}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R540_AGENT_BIN:-/tmp/pub_r539/agenthost}
TMO=${R540_TIMEOUT:-1800}
ROLE=$R/role-r540.txt
SMOKE=$D/smoke
TIDS="t1 g1"
CODEX_BIN=${R540_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
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
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
python3 "$REPO/eval/rover/lib/codex_engine.py" --check || { echo "[致命] codex 引擎加载器 fail-closed(候选全缺)"; exit 3; }
mkdir -p "$D"/{adapter,logs,smoke}
cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r540"
echo "R540 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"   # 同仓并发闸: 后续节拍见 claim 即让路 (EXIT trap 清除)

# 收口兜底: 必须装在**任何 exit 之前** (R535 实测两坑: 冒烟中止漏杀 adapter / claim 残留堵下一轮)
cleanup_r540() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r540 EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 + 题面物化 (逐条核 sha, 且与来源轮对拍) ---------------------
python3 - "$TS" "$TIDS" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
ts, tids, D = sys.argv[1], sys.argv[2].split(), sys.argv[3]
d = json.load(io.open(ts, encoding="utf-8"))
pins = json.load(io.open(os.path.join(os.path.dirname(ts), "input-pins-r540.json"), encoding="utf-8"))
bad = 0
for tid in tids:
    t = [x for x in d["tasks"] if x["tid"] == tid][0]
    p = t.get("prompt") or ""
    h = hashlib.sha256(p.encode()).hexdigest()
    decl = t.get("prompt_sha256")
    io.open(os.path.join(D, "task-%s-prompt.txt" % tid), "w", encoding="utf-8").write(p)
    pin = pins.get(tid, {})
    ok = (h == decl == pin.get("prompt_sha256"))
    xref_ok = all(x.get("same") for x in pin.get("xref", []))
    bad += 0 if (ok and xref_ok) else 1
    print("tid=%s family=%s prompt_sha256=%s declared_same=%s xref=%s bytes=%s cases=%s ok=%s"
          % (tid, t.get("family"), h[:16], h == decl, xref_ok, len(p.encode()), t.get("cases"), ok))
sys.exit(0 if bad == 0 else 3)
PY
prc=$?; cat "$D/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (t1/g1 题面 sha256 自洽 + 与 r539/r531/r536 对拍一致; 物化 $D/task-*-prompt.txt)"

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R540 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
    AGENTFRAMEWORK_R1_TAG="R540-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id "r540-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
srole=$(grep -o '"role_note_chars": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
if [ "$src" != "0" ]; then log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; fi

# --- 4 R1 臂 (结构化契约管道): 单条路径, 无工具面/无纪律尾块 ---------------
run_r1(){   # $1 = 臂目录名(同时是 tag) $2 = tid $3 = role(1|0)
  local A=$1 T=$2 ROL=$3
  local i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$A/$T/work"
  local E=(env "AGENTFRAMEWORK_WORKSPACE=$D/$A/$T/work" AGENTFRAMEWORK_PY_RUN=1
           "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/$T/audit"
           AGENTFRAMEWORK_R1_CONTRACT=1
           "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/$T/transcript.json"
           "AGENTFRAMEWORK_R1_TAG=R540-$W-$A")
  [ "$ROL" = "1" ] && E+=("AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  "${E[@]}" timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-$T-prompt.txt")" --output-mode text \
      --session-id "r540-$(echo "$A" | tr 'A-Z' 'a-z')-$T-$W" > "$D/$A/$T/reply.txt" 2> "$D/$A/$T/stderr.txt"
  rc=$?
  i1=$(maxidx)
  log "臂 $A/$T rc=$rc role=$ROL adapter_range=[$((i0+1)),$i1]"
  echo "$A-$T $((i0+1)) $i1" >> "$D/logs/idx.txt"
}

run_r1 R1nr t1 0      # role 挂载 A/B 控制臂
run_r1 R1r  t1 1      # 主管道臂 (挂 role 额外数据)
run_r1 R1r  g1 1      # 跨族 (随机游戏长任务, 58 隐藏用例)

# --- 5 臂 A1-on (本侧 agent 旧路径, 同窗同题 t1) ----------------------------
j0=$(maxidx)
env python3 "$R/proj_run_side_r540.py" --side agent --arm A1-on --out "$D/A1-on" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
  --taskset "$TS" --tasks t1 --timeout "$TMO" > "$D/logs/run-A1-on.txt" 2>&1
arc=$?
j1=$(maxidx)
log "臂 A1-on/t1 rc=$arc adapter_range=[$((j0+1)),$j1]"
echo "A1-on-t1 $((j0+1)) $j1" >> "$D/logs/idx.txt"

# --- 6 臂 C-codex (外部真值, 同模型, 同窗同题 t1) ---------------------------
k0=$(maxidx)
env python3 "$R/proj_run_side_r540.py" --side codex --arm C-codex --out "$D/C-codex" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$TS" --tasks t1 --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
crc=$?
k1=$(ls "$D/adapter" 2>/dev/null | grep -c '^side-codex-' || true)
log "臂 C-codex/t1 rc=$crc adapter_range=[$((k0+1)),$k1] ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))"
echo "C-codex-t1 $((k0+1)) $k1" >> "$D/logs/idx.txt"

# --- 7 判分 (隐藏用例真跑; 与题集 cases 同源) --------------------------------
for pair in R1nr:t1 R1r:t1 R1r:g1 A1-on:t1 C-codex:t1; do
  A=${pair%%:*}; T=${pair##*:}
  sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='$T'][0])")
  ( cd "$D/$A/$T/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$A/$T/cases.txt" 2>&1
  echo $? >> "$D/$A/$T/cases.txt"
  np=$(grep -c '^CASE .* PASS' "$D/$A/$T/cases.txt" || true)
  [ -z "$(find "$D/$A/$T/work" -type f -print -quit 2>/dev/null)" ] && \
    log "[警告] 产物树为空: $D/$A/$T/work (按 fail-closed 记账, 不得当绿)"
  log "判分 $A/$T: PASS=$np/$(python3 -c "import json;d=json.load(open('$TS'));print([t['hidden_cases'] for t in d['tasks'] if t['tid']=='$T'][0])") rc=$(tail -1 "$D/$A/$T/cases.txt")"
done

# --- 8 仓内快照 + 自报表 (铁律 11 前置器的可发现形态) ------------------------
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
for arm, tid, side in (("R1nr", "t1", "agent"), ("R1r", "t1", "agent"), ("R1r", "g1", "agent"),
                       ("A1-on", "t1", "agent"), ("C-codex", "t1", "codex")):
    src = os.path.join(D, arm, tid, "work")
    dst = os.path.join(snap, "%s%s-%s" % (side, arm, tid), tid)
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
json.dump({"rows": rows}, open(os.path.join(ev, "report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(manifest, open(os.path.join(ev, "artifacts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("快照+自报表: " + ", ".join("%s=%s(%s/%s)" % (r["arm"], r["all_pass"], r["cases_pass"], r["cases_total"])
                                 for r in rows))
PY

# --- 9 分析 (实发 prompt 机检 + 成本分列 + role A/B + 降幅) ------------------
python3 "$R/analyze_r540.py" --run-dir "$D" --window "$W" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 10 铁律 11 收口器 (照跑, rc 原样记录; rc≠0 ⇒ 降幅标「参考(未可验收)」) ---
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r540 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -16 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 11 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R540 同窗收口 ($W) $(date -Is)"
  echo "run=$D"
  echo "agent_bin=$AGENT_BIN"
  sha256sum "$AGENT_BIN"
  echo "题面: $(cat "$D/logs/input-pin.txt" | tr '\n' ' | ')"
  echo "臂: R1nr-t1(不挂role) / R1r-t1(挂role) / R1r-g1(跨族58) / A1-on-t1(旧路径) / C-codex-t1(外部真值)"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"
} > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
