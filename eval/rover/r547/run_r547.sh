#!/usr/bin/env bash
# R547 同窗单变量(剂量面) —— g1(随机游戏长任务, 58 隐藏用例) 的 **早停阈值** 对照, 窗 w2
#
# 单变量 = AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 1, 2, 3} —— 同一变量的 4 个水平:
#   δ=0  轴关(逐位旧行为, 零回归面)
#   δ=1  触发面最宽(pfail≥1) —— 点估计: 省调用最多
#   δ=2  = R546 已验的水平(本窗为第二窗复现)
#   δ=3  判别性**阴性对照**: 实测 pfail 分布上从不被跨过 ⇒ 应逐位等于 δ=0
#   其余全同: 题面/用例/role/二进制/预算(MAX_EXEC_REPAIR=1, MAX_REPAIR=1)/探针开关(PUBLIC_SELFCHECK=1)
#   旧路径基线 A1on × 3 样本/窗(候选④: 该列跨窗 8.5× 摆动, 单样本不可判 ⇒ 两窗合计 n=6)
#
# 本轮**零产品源码改动** ⇒ 复用 R546 同一 AOT 二进制(sha256 起臂前机检)。
# 铁律: 禁 push; 串行起臂(2 vCPU); 缺任一前提 ⇒ fail-closed; 口径: 三列分列(调用数/新算 prompt/completion), 付费真值取中继 usage。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r547
TS=$R/taskset-r547.json
PORT=${R547_ADAPTER_PORT:-48994}
W=${R547_WINDOW:-w2}
D=${R547_RUN_DIR:-$R/run-$W}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R547_AGENT_BIN:-/tmp/pub_r546/agenthost}
BIN_SHA_EXP=1224d3f4ec61d267dc70306e7d7c1a3cf4b8618d83403910ce5651fe6985e246
TMO=${R547_TIMEOUT:-420}
A1_TMO=${R547_A1_TIMEOUT:-720}
ROLE=$R/role-r547.txt
SIDE_RUNNER=$REPO/eval/rover/r540/proj_run_side_r540.py
SMOKE=$D/smoke
REPS="a b c d e"
D3_REPS="a b c"
A1_REPS=${R547_A1_REPS:-3}
ARMS="E0a E0b E0c E0d E0e E1a E1b E1c E1d E1e D1a D1b D1c D1d D1e D3a D3b D3c A1on A1onb A1onc"
unset AGENTFRAMEWORK_R1_ROLE_FILE 2>/dev/null || true

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ "$(sha256sum "$AGENT_BIN" | cut -d' ' -f1)" = "$BIN_SHA_EXP" ] || { echo "[致命] 二进制 sha256 与 R546 不同(本轮零源码改动, 复用必须逐位同)"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] || { echo "[致命] 缺题集 $TS"; exit 3; }
[ -f "$ROLE" ] || { echo "[致命] 缺 role 额外数据 $ROLE"; exit 3; }
[ -f "$SIDE_RUNNER" ] || { echo "[致命] 缺旧路径跑器 $SIDE_RUNNER"; exit 3; }
# 同仓并发闸: 上一轮 claim 未清 ⇒ 让路 (用户令: 检出 sibling 作业即停手)
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
mkdir -p "$D"/{adapter,logs,smoke}
cp -r "$CFGSRC" "$D/agent-cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent-cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r547"
echo "R547 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
export DOTNET_ROOT="$HOME/.dotnet"

cleanup_r547() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r547 EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 (sha256/md5 逐项机检; 不一致 ⇒ 不起臂) ---------------------
python3 - "$R" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
R, D = sys.argv[1], sys.argv[2]
pin = json.load(io.open(os.path.join(R, "input-pins-r547.json"), encoding="utf-8"))["g1"]
ts = json.load(io.open(os.path.join(R, "taskset-r547.json"), encoding="utf-8"))
t = [x for x in ts["tasks"] if x["tid"] == "g1"][0]
p = t["prompt"]; h = hashlib.sha256(p.encode()).hexdigest()
def md5(rel):
    return hashlib.md5(open(os.path.join("/home/agentuser/AgentFramework", rel), "rb").read()).hexdigest()
io.open(os.path.join(D, "task-g1-prompt.txt"), "w", encoding="utf-8").write(p)
c1 = md5("eval/rover/r547/cases/run_cases_r521.py")
c2 = md5("eval/rover/r547/cases/cases-r521.json")
c3 = md5("eval/rover/r547/role-r547.txt")
rows = [
  ("prompt_sha256", h, pin["prompt_sha256"], h == pin["prompt_sha256"] == t.get("prompt_sha256")),
  ("hidden_cases", str(t["hidden_cases"]), str(pin["hidden_cases"]), str(t["hidden_cases"]) == str(pin["hidden_cases"])),
  ("cases_script_md5", c1, pin["cases_script_md5"], c1 == pin["cases_script_md5"]),
  ("cases_json_md5", c2, pin["cases_json_md5"], c2 == pin["cases_json_md5"]),
  ("role_file_md5", c3, pin["role_file_md5"], c3 == pin["role_file_md5"]),
  ("xref_r546_all_same", "byte-identical", "declared", all(x["same"] for x in pin["xref"])),
]
bad = sum(1 for *_, ok in rows if not ok)
for k, got, exp, ok in rows:
    print("  %-22s got=%s exp=%s ok=%s" % (k, str(got)[:20], str(exp)[:20], ok))
print("同输入硬门:", "PASS" if bad == 0 else "FAIL(%d)" % bad)
sys.exit(0 if bad == 0 else 3)
PY
prc=$?; cat "$D/logs/input-pin.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (g1 题面 sha256 / 用例脚本 + 题集 md5 / role md5 全同, 且与 r546 逐字节同)"

# --- 1b 预注册范围闸 (声明面: require 臂必须真起) ----------------------------
python3 "$REPO/eval/rover/r507pre/prereg_scope_gate.py" --prereg "$R/prereg-r547.json" --windows "$W" \
  > "$D/logs/prereg-scope.txt" 2>&1
sgr=$?; cat "$D/logs/prereg-scope.txt"
[ "$sgr" -eq 0 ] || { log "[致命] 预注册范围闸 rc=$sgr ⇒ 停手"; exit 3; }

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R547 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
env -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_WORKSPACE="$SMOKE/work" AGENTFRAMEWORK_PY_RUN=1 \
    AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_TRANSCRIPT="$SMOKE/transcript.json" \
    AGENTFRAMEWORK_R1_TAG="R547-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id "r547-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
srole=$(grep -o '"role_note_chars": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
[ "$src" = "0" ] || { log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; }

# --- 4 臂 (δ∈{0,1,2} × 5 rep 交错 + δ=3 阴控 × 3 + A1on × 3) -----------------
run_r1(){   # $1 = 臂目录名(同时是 tag) $2 = 剂量 δ(0 ⇒ 变量不设) $3 = rep 标签
  local A=$1 DOSE=$2 REP=$3 i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$A/g1/work"
  if [ "$DOSE" = "0" ]; then
    env -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work" AGENTFRAMEWORK_PY_RUN=1 \
        "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/g1/audit" \
        AGENTFRAMEWORK_R1_CONTRACT=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/g1/transcript.json" \
        "AGENTFRAMEWORK_R1_TAG=R547-$W-$A" \
        AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1 \
        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \
        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \
        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
        timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
          --session-id "r547-$A-$REP" > "$D/$A/g1/reply.txt" 2> "$D/$A/g1/stderr.txt"
  else
    env "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work" AGENTFRAMEWORK_PY_RUN=1 \
        "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/g1/audit" \
        AGENTFRAMEWORK_R1_CONTRACT=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/g1/transcript.json" \
        "AGENTFRAMEWORK_R1_TAG=R547-$W-$A" \
        AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1 \
        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \
        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \
        "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL=$DOSE" \
        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
        timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
          --session-id "r547-$A-$REP" > "$D/$A/g1/reply.txt" 2> "$D/$A/g1/stderr.txt"
  fi
  rc=$?
  i1=$(maxidx)
  log "臂 $A/g1 δ=$DOSE rc=$rc session=$REP adapter_range=[$((i0+1)),$i1]"
  echo "$A-g1 $((i0+1)) $i1 d$DOSE" >> "$D/logs/idx.txt"
}

for rep in $REPS; do
  run_r1 "E0$rep" 0 "$rep"
  run_r1 "E1$rep" 2 "$rep"
  run_r1 "D1$rep" 1 "$rep"
done
for rep in $D3_REPS; do
  run_r1 "D3$rep" 3 "$rep"
done

# --- 5 臂 A1on (旧路径 agent, 同窗同题 g1 × 3 样本) --------------------------
a1_label(){ case "$1" in 0) echo "A1on";; 1) echo "A1onb";; 2) echo "A1onc";; esac; }
for k in $(seq 0 $((A1_REPS - 1))); do
  AL=$(a1_label "$k")
  j0=$(maxidx)
  env -u AGENTFRAMEWORK_R1_CONTRACT -u AGENTFRAMEWORK_R1_TRANSCRIPT -u AGENTFRAMEWORK_R1_TAG \
      -u AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR -u AGENTFRAMEWORK_R1_MAX_REPAIR -u AGENTFRAMEWORK_R1_ROLE_FILE \
      -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK -u AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL \
      python3 "$SIDE_RUNNER" --side agent --arm "$AL" --out "$D/$AL" \
        --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
        --taskset "$TS" --tasks g1 --timeout "$A1_TMO" > "$D/logs/run-$AL.txt" 2>&1
  arc=$?
  j1=$(maxidx)
  log "臂 $AL/g1 rc=$arc adapter_range=[$((j0+1)),$j1] $(tail -1 "$D/logs/run-$AL.txt" 2>/dev/null | head -c 200)"
  echo "$AL-g1 $((j0+1)) $j1 0" >> "$D/logs/idx.txt"
done

# --- 6 判分 (隐藏用例真跑; 独立进程) ----------------------------------------
for A in $ARMS; do
  sc=$(python3 -c "import json;d=json.load(open('$TS'));print([t['cases'] for t in d['tasks'] if t['tid']=='g1'][0])")
  ( cd "$D/$A/g1/work" 2>/dev/null && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$R/$sc" ) > "$D/$A/g1/cases.txt" 2>&1
  echo $? >> "$D/$A/g1/cases.txt"
  np=$(grep -c '^CASE .* PASS' "$D/$A/g1/cases.txt" || true)
  [ -z "$(find "$D/$A/g1/work" -type f -print -quit 2>/dev/null)" ] && \
    log "[警告] 产物树为空: $D/$A/g1/work (按 fail-closed 记账, 不得当绿)"
  log "判分 $A/g1: PASS=$np/58 rc=$(tail -1 "$D/$A/g1/cases.txt")"
done

# --- 7 仓内快照 + 自报表 (铁律 11 前置器可发现形态) -------------------------
python3 - "$D" "$R" "$W" "$TS" "$ARMS" > "$D/logs/snapshot.txt" 2>&1 <<'PY'
import json, os, shutil, sys
D, R, W, TS, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split()
ts = json.load(open(TS, encoding="utf-8"))
hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
snap = os.path.join(R, "snapshots", W); ev = os.path.join(R, "evidence/windows", W)
os.makedirs(snap, exist_ok=True); os.makedirs(ev, exist_ok=True)
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
cat "$D/logs/snapshot.txt"

# --- 8 分析 (剂量曲线 + 机制断言 + 三列代价) --------------------------------
python3 "$R/analyze_r547.py" --run-dir "$D" --window "$W" --taskset "$TS" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 9 铁律 11 收口器 (rc 原样记录; rc≠0 ⇒ 降幅标「参考(未可验收)」) --------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r547 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -20 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 9.5 收口 rc 回填读数 (口径: rc 原样, 不做任何事后改判) ------------------
python3 - "$R" "$W" "$pcr" <<'PY'
import io, json, os, sys
R, W, pcr = sys.argv[1], sys.argv[2], int(sys.argv[3])
p = os.path.join(R, "readings-%s.json" % W)
d = json.load(io.open(p, encoding="utf-8"))
d["judgments"]["K8_收口"]["precond_rc"] = pcr
d["judgments"]["K8_收口"]["acceptance_label"] = ("可验收" if pcr == 0 else "参考(未可验收)")
d["precond_rc"] = pcr
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("readings-%s.json: precond_rc=%d label=%s" % (W, pcr, d["judgments"]["K8_收口"]["acceptance_label"]))
PY

# --- 10 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R547 早停阈值剂量面 ($W) $(date -Is)"
  echo "run=$D"
  echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "题面: $(cat "$D/logs/input-pin.txt" | tr '\n' ' | ')"
  echo "单变量: 早停阈值 — AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0(轴关),1,2,3}; δ=1/2 各 5 session, δ=3 阴控 3, δ=0 5; 另 A1on × 3(旧路径)"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"
} > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
