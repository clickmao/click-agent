#!/usr/bin/env bash
# R544 同窗单变量对照 —— g1(随机游戏长任务, 58 隐藏用例) 的 **产物侧公开用例独立回放** 轴
#
# 动因 (R542 收口实测): 9 个 r1 臂里 rc=0 的 4 臂产物仅 43–55/58, 唯一 58/58 的 r1 臂 rc=5
#   ⇒ 「模型自述完成」(rc=0) 不是正确性证据; R542 候选① 点名唯一有证据支撑的挂点 =
#     产物侧独立自检: 题面**公开用例**机械抽取 + 独立回放(禁模型自撰期望、禁模型裁判) + 管道自产证据回灌。
#  本轴: 单变量 = AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {off, on} × 3 次独立 session; 另 A1on 旧路径同窗基线。
#
# 铁律: 禁 push; 串行起臂(2 vCPU); 改了产品源码 ⇒ 必重发布 AOT(不带 -p:PublishAot); 缺任一前提 ⇒ fail-closed;
#       口径: 三列分列(调用数 / 新算 prompt / completion), 付费真值取中继 usage。
set -uo pipefail

REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r544
TS=$R/taskset-r544.json
PORT=${R544_ADAPTER_PORT:-48991}
W=${R544_WINDOW:-w1}
D=${R544_RUN_DIR:-$R/run-$W}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R544_AGENT_BIN:-/tmp/pub_r544/agenthost}
TMO=${R544_TIMEOUT:-420}
A1_TMO=${R544_A1_TIMEOUT:-720}
ROLE=$R/role-r544.txt
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
echo "run=$D port=$PORT bin=$AGENT_BIN window=$W ts=$(date -Is)" > "$D/.owner-r544"
echo "R544 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"   # 同仓并发闸: 后续节拍见 claim 即让路 (EXIT trap 清除)

cleanup_r544() {
  kill "${APID:-0}" 2>/dev/null
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM" 2>/dev/null
  return 0
}
trap cleanup_r544 EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"     # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 (sha256/md5 逐项机检; 不一致 ⇒ 不起臂) ---------------------
python3 - "$R" "$D" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, os, sys
R, D = sys.argv[1], sys.argv[2]
pin = json.load(io.open(os.path.join(R, "input-pins-r544.json"), encoding="utf-8"))["g1"]
ts = json.load(io.open(os.path.join(R, "taskset-r544.json"), encoding="utf-8"))
t = [x for x in ts["tasks"] if x["tid"] == "g1"][0]
p = t["prompt"]; h = hashlib.sha256(p.encode()).hexdigest()
def md5(rel):
    return hashlib.md5(open(os.path.join("/home/agentuser/AgentFramework", rel), "rb").read()).hexdigest()
io.open(os.path.join(D, "task-g1-prompt.txt"), "w", encoding="utf-8").write(p)
rows = [
  ("prompt_sha256", h, pin["prompt_sha256"], h == pin["prompt_sha256"] == t.get("prompt_sha256")),
  ("hidden_cases", str(t["hidden_cases"]), str(pin["hidden_cases"]), str(t["hidden_cases"]) == str(pin["hidden_cases"])),
  ("cases_script_md5", md5("eval/rover/r544/cases/run_cases_r521.py"), pin["cases_script_md5"],
   md5("eval/rover/r544/cases/run_cases_r521.py") == pin["cases_script_md5"]),
  ("role_file_md5", md5("eval/rover/r544/role-r544.txt"), pin["role_file_md5"],
   md5("eval/rover/r544/role-r544.txt") == pin["role_file_md5"]),
  ("cases_json_md5", md5("eval/rover/r544/cases/cases-r521.json"), pin["cases_json_md5"],
   md5("eval/rover/r544/cases/cases-r521.json") == pin["cases_json_md5"]),
  ("xref_r542", "byte-identical", "declared", all(x["same"] for x in pin["xref"])),
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

# --- 1b 预注册范围闸 (声明面: require 臂必须真起) ----------------------------
python3 "$REPO/eval/rover/r507pre/prereg_scope_gate.py" --prereg "$R/prereg-r544.json" --windows "$W" \
  > "$D/logs/prereg-scope.txt" 2>&1
sgr=$?; cat "$D/logs/prereg-scope.txt"
[ "$sgr" -eq 0 ] || { log "[致命] 预注册范围闸 rc=$sgr ⇒ 停手"; exit 3; }

# --- 2 起手闸: 连续 2 次 PASS ----------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R544 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
    AGENTFRAMEWORK_R1_TAG="R544-smoke" AGENTFRAMEWORK_R1_STEP_TIMEOUT=60 \
    timeout 300 "$AGENT_BIN" -q '在工作根下写一个 sols/hello.py：内容为 print(6*7)；然后用 python3 运行它，期望 stdout 为 42。' \
      --output-mode text --session-id "r544-smoke-$W" > "$SMOKE/reply.txt" 2> "$SMOKE/stderr.txt"
src=$?
sr1=$(grep -o '"rc": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
srole=$(grep -o '"role_note_chars": *[0-9]*' "$SMOKE/transcript.json" 2>/dev/null | head -1)
log "冒烟: cli_rc=$src $sr1 $srole hello=$([ -f "$SMOKE/work/sols/hello.py" ] && echo yes || echo no)"
[ "$src" = "0" ] || { log "[中止] 接线冒烟未通过 (fail-closed, 不起臂)"; exit 9; }

# --- 4 臂 (off/on × 3rep 交错 + A1on) --------------------------------------
run_r1(){   # $1 = 臂目录名(同时是 tag) $2 = 开关(on|off) $3 = rep 标签
  local A=$1 SW=$2 REP=$3 i0 i1 rc
  i0=$(maxidx)
  mkdir -p "$D/$A/g1/work"
  if [ "$SW" = "on" ]; then
    env "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work" AGENTFRAMEWORK_PY_RUN=1 \
        "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/g1/audit" \
        AGENTFRAMEWORK_R1_CONTRACT=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/g1/transcript.json" \
        "AGENTFRAMEWORK_R1_TAG=R544-$W-$A" \
        AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1 \
        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \
        AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \
        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
        timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
          --session-id "r544-$A-$REP" > "$D/$A/g1/reply.txt" 2> "$D/$A/g1/stderr.txt"
  else
    env -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK "AGENTFRAMEWORK_WORKSPACE=$D/$A/g1/work" AGENTFRAMEWORK_PY_RUN=1 \
        "AGENTFRAMEWORK_ACTION_AUDIT=$D/$A/g1/audit" \
        AGENTFRAMEWORK_R1_CONTRACT=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$A/g1/transcript.json" \
        "AGENTFRAMEWORK_R1_TAG=R544-$W-$A" \
        AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1 \
        AGENTFRAMEWORK_R1_MAX_REPAIR=1 \
        "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
        timeout "$TMO" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
          --session-id "r544-$A-$REP" > "$D/$A/g1/reply.txt" 2> "$D/$A/g1/stderr.txt"
  fi
  rc=$?
  i1=$(maxidx)
  log "臂 $A/g1 sw=$SW rc=$rc session=$REP adapter_range=[$((i0+1)),$i1]"
  echo "$A-g1 $((i0+1)) $i1 $SW" >> "$D/logs/idx.txt"
}

for rep in a b c; do
  case $rep in a) OFF=P0a; ON=P1a;; b) OFF=P0b; ON=P1b;; c) OFF=P0c; ON=P1c;; esac
  run_r1 "$OFF" "off" "$rep"
  run_r1 "$ON" "on" "$rep"
done

# --- 5 臂 A1on (旧路径 agent, 同窗同题 g1) ----------------------------------
j0=$(maxidx)
env -u AGENTFRAMEWORK_R1_CONTRACT -u AGENTFRAMEWORK_R1_TRANSCRIPT -u AGENTFRAMEWORK_R1_TAG \
    -u AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR -u AGENTFRAMEWORK_R1_MAX_REPAIR -u AGENTFRAMEWORK_R1_ROLE_FILE \
    -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK \
    python3 "$SIDE_RUNNER" --side agent --arm A1on --out "$D/A1on" \
      --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
      --taskset "$TS" --tasks g1 --timeout "$A1_TMO" > "$D/logs/run-A1on.txt" 2>&1
arc=$?
j1=$(maxidx)
log "臂 A1on/g1 rc=$arc adapter_range=[$((j0+1)),$j1] $(tail -1 "$D/logs/run-A1on.txt" 2>/dev/null | head -c 220)"
echo "A1on-g1 $((j0+1)) $j1 0" >> "$D/logs/idx.txt"

# --- 6 判分 (隐藏用例真跑; 独立进程) ----------------------------------------
ARMS="P0a P0b P0c P1a P1b P1c A1on"
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
python3 - "$D" "$R" "$W" "$TS" > "$D/logs/snapshot.txt" 2>&1 <<'PY'
import json, os, shutil, sys
D, R, W, TS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ts = json.load(open(TS, encoding="utf-8"))
hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
snap = os.path.join(R, "snapshots", W); ev = os.path.join(R, "evidence/windows", W)
os.makedirs(snap, exist_ok=True); os.makedirs(ev, exist_ok=True)
ARMS = ["P0a", "P0b", "P0c", "P1a", "P1b", "P1c", "A1on"]
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

# --- 8 分析 (单变量对照 + 机制启用断言 + 三列代价) --------------------------
python3 "$R/analyze_r544.py" --run-dir "$D" --window "$W" --taskset "$TS" > "$D/logs/analyze.txt" 2>&1
anrc=$?; cat "$D/logs/analyze.txt"
log "分析 rc=$anrc"

# --- 9 铁律 11 收口器 (rc 原样记录; rc≠0 ⇒ 降幅标「参考(未可验收)」) --------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r544 > "$D/logs/precond.txt" 2>&1
pcr=$?
echo "PRECOND_RC=$pcr" >> "$D/logs/precond.txt"
tail -20 "$D/logs/precond.txt"
log "PRECOND_RC=$pcr (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 10 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R544 同窗单变量对照 ($W) $(date -Is)"
  echo "run=$D"
  echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "题面: $(cat "$D/logs/input-pin.txt" | tr '\n' ' | ')"
  echo "单变量: AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {off,on} × 3 独立 session; 另 A1on(旧路径)"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  echo "precond_rc=$pcr"
} > "$D/SUMMARY-$W.txt" 2>&1
log "完成: $D"
exit 0
