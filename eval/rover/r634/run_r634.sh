#!/usr/bin/env bash
# R634 驱动器（**主线对照轮**：新窗集 w228..w230；每窗 = codex 真值 ×1 + 产品默认档 ×3）——
# 派生 = eval/rover/r631/run_r631.sh（结构复用）+ 下列**逐条声明的差异**:
#   ① 轮号/命名空间 R631→R634、r631→r634；D=$HOME/.agentframework/harness/runs/r634；端口 49795→**49799**。
#   ② 窗号 WIN0 **228**（w228..w230；与历史窗集 w184..w227 **不相交**）。题集 = r610 冻结件**逐字节复制**（文件 sha e0c667c2…；aux 目录 `cases/run_cases_r521.py` 同批携带，sha d9aecf4d…）。
#   ②b **本轮实盘常量**（声明与实盘逐项一致，承 R632 D3）：WIN0=228 NWIN=3 REPS=3 PORT=49799 PREV_SWING=60 GATE_MB=2650 R634 起手闸 REQ = GATE+clamp(swing,floor60) = 2650+60 = 2710
#   ③ **臂表**：本轮**无单变量轴**（测量轮，预注册自陈，禁计为单变量轮 —— 同 R589/R628 先例）
#      ⇒ 单一产品默认档臂 **P**（剂量键全部 unset = 产品缺省）+ 外部真值 **C1**（codex）。
#      与 R631 的 T/C 轴臂相比：本轮**无** `AGENTFRAMEWORK_R1_ACTION_EXEC` 注入（该轴已被 R631 定案关闭，不再开）。
#   ④ 被测件：`$HOME/.agentframework/artifacts/pub_r630/agenthost`（sha16 cefd045e8d1d）与 R631 逐字节同件
#      ⇒ 与 R585–R631 各轮**禁相减、只并列**（零产品源码改动 ⇒ 跳步 构建/AOT）。
#   ⑤ hered/常量面：`AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy` + `AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1`（两臂同值 = held-constant）
#      ⇒ 前缀 sha 必须 == `F_env.prefix.legacy_anchor`（a9792fdb…，judge M1 机检）。
#   ⑥ 前提闸改绑：单跑次「产品默认档」⇒ transcript `prefix_sha256 == legacy 锚` ∧ `plan_steps_total > 0`（不再断言执行面回退）。
#   ⑦ 判据器 = eval/rover/r634/judge_r634.py（**自足件**：只 import kpi_r599 helpers；判据族 = M1 锚面 / Q1 配对质量 /
#      Q2 整题全对 / C 成本三列 / W 有效窗 / Y 自证边界诊断 / LD 诊断；rc 分层 0/1/2/3）。
#   ⑧ 起手闸摆动余量 PREV_SWING = **119MB**（同源口径 = R631 起手闸 `--min-avail-mb 2769` − 产品门槛 2650；
#      R632 器件面收口轮未开窗 ⇒ 无新 swing 可派生，沿用 R631 值并在此声明）。
# 用法: bash eval/rover/r634/run_r634.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r634}
PORT=${PORT:-49799}
WIN0=${WIN0:-228}
NWIN=${NWIN:-3}
REPS=${REPS:-3}
ARMS_DOSE="P:agentP:unset"
CMAXT=${CMAXT:-600}
AMAXT=${AMAXT:-600}
CFGSRC=${CFGSRC:-$HARNESS/agent/cfg}
PDIR=$REPO/eval/rover/r634
TS=$REPO/eval/rover/r634/taskset-r634.json     # 冻结题集**逐字节复制件** (文件 sha e0c667c2… = r610 件)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r610/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
MEM_ONCE=$REPO/eval/rover/r571/mem_sample_once.py
SAMPLER=$REPO/eval/rover/r571/mem_sampler.py
GATE=$REPO/eval/rover/r483/preflight_gate.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-$HOME/.agentframework/artifacts/pub_r630/agenthost}
GATE_MB=2650
PREREG=$PDIR/prereg-r634.json
LEGACY_ANCHOR=a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e
TASKSET_PIN=e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a
GRADE_TMO=${GRADE_TMO:-10}
export AGENTFRAMEWORK_GRADE_TIMEOUT=$GRADE_TMO
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }
dmax(){ python3 -c "
import os,sys
d,s=sys.argv[1],sys.argv[2]; n=0
for fn in os.listdir(d):
    if fn.startswith('side-%s-'%s) and fn.endswith('.json'):
        try: n=max(n,int(fn[:-5].rsplit('-',1)[1]))
        except Exception: pass
print(n)" "$D/adapter" "$1"; }

# --- 0 守卫 (fail-closed) ----------------------------------------------------
mkdir -p "$D"/{adapter,logs,agent-cfg} "$PDIR"/{snapshots,evidence/windows}
[ -f "$PREREG" ] || { echo "[致命] 缺预注册 $PREREG (先写后跑闸)"; exit 3; }
python3 - "$PREREG" <<'PY' || { echo "[致命] 预注册机检不过"; exit 3; }
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
assert d["round"] == "R634" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "P"}, sorted(d["arms"])
assert d["arms"]["C1"]["side"] == "codex" and d["arms"]["P"]["side"] == "agent"
# 无轴轮: 产品臂 env 必须是产品缺省（剂量键 unset 或显式空 ⇒ 不得出现任何 R1 剂量键）
for k in ("AGENTFRAMEWORK_R1_ACTION_EXEC", "AGENTFRAMEWORK_R1_ACTION_CANDIDATES",
          "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR", "AGENTFRAMEWORK_R1_MAX_REPAIR",
          "AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL",
          "AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER"):
    assert k not in d["arms"]["P"]["env"], "无轴轮不得注入剂量键: %s" % k
assert d["arms"]["P"]["env"]["AGENTFRAMEWORK_R1_ACTION_PROMPT"] == "legacy"
assert d["arms"]["P"]["env"]["AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK"] == "1"
assert sorted(d["windows"]["set"]) == ["w228", "w229", "w230"], d["windows"]["set"]
assert d["windows"]["disjoint_from_history"] is True
assert d["single_variable"]["axis"] == "无", d["single_variable"]["axis"]
assert len(d["criteria"]) >= 5, sorted(d["criteria"])
# R634 修正版窗有效性策略「先写后跑」机检闸（承 R633 自捕缺陷 ③；声明先于跑）
up = d["unreliable_policy"]
assert up["declared_before_run"] is True, up.get("declared_before_run")
assert "跑通" in up["rule"] and "非自败例" in up["rule"], up["rule"]
assert up["bars"]["B1"].startswith("窗有效"), up["bars"]["B1"]
assert "整题全对" not in up["rule"], "R633 构造缺陷复现：窗有效性不得绑在「真值整题全对」上"
print("[先写后跑闸] prereg ok: arms=%s windows=%s criterion=%s"
      % (sorted(d["arms"]), d["windows"]["set"], d["criterion_version"][:12]))
PY

# --- 0a 前置存在检查 --------------------------------------------------------
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT 发布件 $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { log "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { log "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
# R633 自捕缺陷 ① 的预防：**派生驱动器必须同批携带 aux 目录**（后置器按「轮目录 + task["cases"]」解析）
AUX=$PDIR/cases/run_cases_r521.py
[ -f "$AUX" ] || { log "[致命] 派生件缺 aux 用例脚本 $AUX（前置器会全臂 missing_case_script）"; exit 3; }
AUX_SHA=$(sha256sum "$AUX" | cut -d' ' -f1)
[ "$AUX_SHA" = "d9aecf4d397550b8bb1ca0af2afa34821dd7eb9c3cb633824df61df596a89daf" ] || { log "[致命] aux 用例脚本 sha 漂移: $AUX_SHA"; exit 3; }
TS_SHA=$(sha256sum "$TS" | cut -d' ' -f1)
[ "$TS_SHA" = "$TASKSET_PIN" ] || { log "[致命] 题集文件 sha 漂移: $TS_SHA ≠ $TASKSET_PIN"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { log "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R634 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
BIN_SHA_BEFORE=$(sha256sum "$BIN" | cut -d' ' -f1)
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r634.json" "$CFGSRC" <<'PY'
import hashlib, io, json, os, sys
def h(p):
    if os.path.isdir(p):
        acc = {}
        for root, _, fs in os.walk(p):
            for f in sorted(fs):
                fp = os.path.join(root, f)
                acc[os.path.relpath(fp, p)] = hashlib.sha256(io.open(fp, "rb").read()).hexdigest()
        return {"path": p, "files": acc}
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
pre = json.load(io.open(sys.argv[3], encoding="utf-8"))
rep = {"note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 全臂共用同一枚二进制 ⇒ 臂身份单变量由构造保证。",
       "bin_all_arms": h(sys.argv[1]), "codex": h(sys.argv[2]), "cfg_src": h(sys.argv[5]),
       "arm_env": {k: pre["arms"][k].get("env") for k in sorted(pre["arms"])}}
json.dump(rep, io.open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[钉死] bin=%s cfg_files=%d" % (rep["bin_all_arms"]["sha256"][:16], len(rep["cfg_src"]["files"])))
PY
cp -r "$CFGSRC"/. "$D/agent-cfg"/
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
export DOTNET_ROOT="$HOME/.dotnet"

cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
  rm -f "$REPO/.git/ROUND_CLAIM"; return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1
# 产品默认档: 剂量键**全部显式 unset**（防继承）。本轮无轴 ⇒ 不再注入任何剂量键。
unset AGENTFRAMEWORK_R1_MAX_REPAIR AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR
unset AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR AGENTFRAMEWORK_R1_ACTION_CANDIDATES AGENTFRAMEWORK_R1_ACTION_PROMPT AGENTFRAMEWORK_R1_ACTION_EXEC
cd "$REPO" || exit 3

# --- 1 同输入硬门 -----------------------------------------------------------
cp "$TS" "$D/taskset.json"
python3 - "$TS" "$D" <<'PY'
import hashlib, io, json, sys
ts, D = sys.argv[1], sys.argv[2]
d = json.load(io.open(ts, encoding="utf-8"))
t = [x for x in d["tasks"] if x["tid"] == "g1"][0]
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
io.open(D + "/task-g1-prompt.txt", "w", encoding="utf-8").write(t["prompt"])
io.open(D + "/logs/input-pin.txt", "w", encoding="utf-8").write(
    "prompt_sha256 %s chars=%d hidden_cases=%s\n" % (h, len(t["prompt"]), t.get("hidden_cases")))
print("prompt_sha256 %s chars=%d" % (h, len(t["prompt"])))
PY

# --- 2 起手闸 (内存裕量条款: 阈值 + 观测振幅余量 + 连续 2 次) ----------------
PREV_SWING=${PREV_SWING:-60}
: > "$D/logs/pre-samples.jsonl"
for _s in 1 2 3; do python3 "$MEM_ONCE" "$D/logs/pre-samples.jsonl" >/dev/null; sleep 1; done
read -r CEIL SPREAD < <(python3 - "$D/logs/pre-samples.jsonl" <<'PY'
import io, json, sys
v = [json.loads(l)["mem_available_mb"] for l in io.open(sys.argv[1], encoding="utf-8") if l.strip()]
print(min(v), max(v) - min(v))
PY
)
[ "$CEIL" -gt 0 ] || { log "[致命] 起手前采样空 (窗口不可开, fail-closed)"; exit 2; }
if [ "$SPREAD" -gt 50 ]; then
  log "[致命] 起手前 3 样本极差 ${SPREAD}MB > 50MB ⇒ 跨态, 窗口不可开 (fail-closed)"; exit 2; fi
log "起手前采样: ceiling(min of 3)=$CEIL spread=${SPREAD}MB"
MARGIN=$(( PREV_SWING > 60 ? PREV_SWING : 60 ))
CAP=$(( CEIL - GATE_MB - 60 ))
CAP_BINDING=false
[ "$MARGIN" -gt "$CAP" ] && { MARGIN=$CAP; CAP_BINDING=true; }
if [ "$MARGIN" -lt 60 ]; then
  log "[致命] 顶棚 $CEIL 装不下下限 60MB ⇒ 窗口不可开 (fail-closed)"; exit 2; fi
REQ=$(( GATE_MB + MARGIN ))
log "起手闸条款: ceiling=$CEIL prev_swing=$PREV_SWING margin=$MARGIN REQ=$REQ (cap=$CAP cap_binding=$CAP_BINDING spread=${SPREAD}MB)"
python3 - "$PDIR/gate-margin-r634.json" "$PREV_SWING" "$CEIL" "$MARGIN" "$REQ" "$CAP" "$CAP_BINDING" "$SPREAD" <<'PY'
import io, json, sys
out, prev, ceil, margin, req, cap, binding, spread = sys.argv[1:9]
json.dump({"round": "R634", "criterion": "C3 起手闸余量条款（R631 派生版；余量源沿用 R631 同态实测）",
           "clause": "MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE-floor); REQ=GATE+MARGIN",
           "prev_swing_effective": int(prev),
           "prev_swing_source": "R631 起手闸 (--min-avail-mb 2769 − 产品门槛 2650 = 119MB)；R632 未开窗 ⇒ 无新 swing",
           "ceiling_min_of_3": int(ceil), "pre_sample_spread_mb": int(spread), "spread_clause": "<=50MB else fail-closed",
           "margin": int(margin), "req": int(req), "cap": int(cap), "cap_binding": binding == "true",
           "preflight_min_avail_mb": 2769,
           "note": "cap_binding=true ⇒ 振幅项退化（收紧的是上界而非下界，R590 已登记）"},
          io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[条款] 派生件落盘", out)
PY
for i in 1 2; do
  python3 "$GATE" --round R634 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-A$i.json')).get('verdict'))" 2>/dev/null)
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 rc=$lrc"; exit 2; }

# --- 2b 运行中内存采样器 ----------------------------------------------------
: > "$D/logs/run-samples.jsonl"
python3 "$SAMPLER" "$D/logs/run-samples.jsonl" 5 "$D" "$PORT" > "$D/logs/sampler.log" 2>&1 &
echo "$!" > "$D/logs/sampler.pid"

# --- 3 adapter (两臂同一会话) ----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪"; exit 2; }
log "adapter 就绪 port=$PORT (w$WIN0..$((WIN0+NWIN-1)); 每窗 = codex 真值 ×1 + 产品默认档 ×$REPS)"

# --- 3b 前提闸 (fail-closed, 起臂前 1 跑次; 不计入臂表) ----------------------
#   R634 语义: 无轴测量轮 ⇒ 前提 = 「同件同题集同 held-constant 锚」：产品默认档单跑次必须
#   `prefix_sha256 == legacy 锚`（证明口径未漂移）∧ `plan_steps_total > 0`（计划面真被行使）。
mkdir -p "$D/premise/g1/work"
env AGENTFRAMEWORK_WORKSPACE="$D/premise/g1/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
    AGENTFRAMEWORK_R1_TRANSCRIPT="$D/premise/g1/transcript.json" AGENTFRAMEWORK_R1_TAG=premise-r634 \
    AGENTFRAMEWORK_R1_ROLE_FILE="$ROLE" AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy \
    timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
    --session-id "premise-r634" > "$D/premise/g1/reply.txt" 2> "$D/premise/g1/stderr.txt"
echo "$? " > "$D/premise/g1/cli_rc.txt"
python3 - "$D/premise/g1/transcript.json" "$PDIR/premise-r634.json" "$LEGACY_ANCHOR" <<'PY'
import io, json, sys
tp, out, anchor = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    t = json.load(io.open(tp, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print("[前提闸] 缺 transcript: %s" % str(e)[:120]); raise SystemExit(5)
sha = t.get("prefix_sha256")
plan_n = t.get("plan_steps_total")
ok_ctx = (sha == anchor)
ok_state = ((plan_n or 0) > 0)
rec = {"premise": "无轴测量轮 ⇒ 同件/同题集/同 held-constant 前缀锚（legacy 档）",
       "prefix_sha256": sha, "legacy_anchor": anchor, "plan_steps_total": plan_n,
       "state_gate": bool(ok_state), "context_gate": bool(ok_ctx),
       "rc": 0 if (ok_state and ok_ctx) else 5}
json.dump(rec, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[前提闸] sha=%s plan=%s rc=%d" % ((sha or "")[:12], plan_n, rec["rc"]))
raise SystemExit(rec["rc"])
PY
_prc=$?; [ "$_prc" -eq 0 ] || { log "[致命] 前提闸未过 rc=$_prc ⇒ 零臂起跑（fail-closed）"; exit 5; }
log "前提闸 PASS: 前缀锚 + 计划面均成立"

# --- 4 逐窗逐重复 ----------------------------------------------------------
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  local t0 t1
  rm -rf "$D/$win/$sub/g1"
  mkdir -p "$D/$win/$sub/g1/work"
  t0=$(dmax agent)
  local -a ENVS=("AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" "AGENTFRAMEWORK_R1_CONTRACT=1"
                 "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win"
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE"
                 "AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy")
  case "$dose" in
    unset) : ;;                                              # 产品默认档（本轮唯一本侧档位）
    *) ENVS+=("AGENTFRAMEWORK_R1_MAX_REPAIR=$dose") ;;        # 保留档（本轮不用，防误用）
  esac
  printf '%s\n' "${ENVS[@]}" > "$D/$win/$sub/g1/arm_env.txt"
  env "${ENVS[@]}" timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
      --session-id "$arm-$win-$sub" > "$D/$win/$sub/g1/reply.txt" 2> "$D/$win/$sub/g1/stderr.txt"
  echo "$? " > "$D/$win/$sub/g1/cli_rc.txt"
  t1=$(dmax agent)
  echo "$t0 $t1"
}
: > "$D/logs/runs.jsonl"
for i in $(seq "$WIN0" $((WIN0 + NWIN - 1))); do
  W=w$i
  mkdir -p "$D/$W/codex/g1/work"
  WSTART=$(date +%s)
  c0=$(dmax codex)
  python3 "$SIDE" --side codex --arm C1 --taskset "$TS" --tasks g1 \
      --out "$D/$W/codex" --adapter-dir "$D/adapter" --adapter-port "$PORT" \
      --codex-bin "$CODEX_BIN" --model deepseek-flash --timeout "$CMAXT" \
      > "$D/$W/codex/side.log" 2>&1
  echo "$? " > "$D/$W/codex/rc.txt"
  c1=$(dmax codex)
  echo "{\"arm\":\"C1\",\"win\":\"$W\",\"rep\":1,\"sub\":\"codex\",\"range\":[$c0,$c1]}" >> "$D/logs/runs.jsonl"
  for r in $(seq 1 "$REPS"); do
    for spec in $ARMS_DOSE; do
      arm=${spec%%:*}; rest=${spec#*:}; base=${rest%%:*}; dose=${rest##*:}
      sub="$base-r$r"
      read -r t0 t1 < <(run_agent "$arm" "$W" "$sub" "$dose")
      echo "{\"arm\":\"$arm\",\"win\":\"$W\",\"rep\":$r,\"sub\":\"$sub\",\"range\":[$t0,$t1]}" >> "$D/logs/runs.jsonl"
    done
  done
  WEND=$(date +%s)
  for d in "$D/$W"/*/; do
    sub=$(basename "$d")
    [ -d "$d/g1/work" ] || continue
    ( cd "$d/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$d/g1/cases.txt" 2>&1
  done
  rm -rf "$PDIR/snapshots/$W"
  for d in "$D/$W"/*/; do
    sub=$(basename "$d")
    [ -d "$d/g1/work" ] || continue
    mkdir -p "$PDIR/snapshots/$W/$sub/g1"
    cp -a "$d/g1/work/." "$PDIR/snapshots/$W/$sub/g1/"
  done
  python3 "$PDIR/judge_r634.py" --D "$D" --pd "$PDIR" --win "$W" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"reps\":$REPS}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/judge_r634.py" --D "$D" --pd "$PDIR" 2>&1 | tee -a "$D/logs/run.txt" || log "KPI 汇总 rc=$? (见下)"

# --- 4b 收尾: 采样器 + 二进制 sha 一致性 (臂身份) ---------------------------
if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
BIN_SHA_AFTER=$(sha256sum "$BIN" | cut -d' ' -f1)
if [ "$BIN_SHA_BEFORE" = "$BIN_SHA_AFTER" ]; then echo "{\"bin_sha_stable\":true,\"sha\":\"$BIN_SHA_BEFORE\"}" > "$D/bin-sha-check.json"
else echo "{\"bin_sha_stable\":false,\"before\":\"$BIN_SHA_BEFORE\",\"after\":\"$BIN_SHA_AFTER\"}" > "$D/bin-sha-check.json"; log "[致命] 运行期二进制被替换 ⇒ 臂身份不成立"; fi

# --- 5 铁律 11 前置器 -------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r634 --out "$D/precond-r634.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
# 重新汇总一次（把 precond rc 带进判决件）
python3 "$PDIR/judge_r634.py" --D "$D" --pd "$PDIR" >/dev/null 2>&1 || true
log "R634 完成"
