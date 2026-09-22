#!/usr/bin/env bash
# R631 驱动器（RF0004.2 · M3 **第五刀 = 等价面分辨率取证（reps 3→6）+ 判据分级**）——
# 派生 = eval/rover/r617/run_r617.sh（结构复用）+ 下列**逐条声明的差异**:
#   ① 轮号/命名空间 R617→R631、r617→r631；D=$HOME/.agentframework/harness/runs/r631；端口 49792→49793。
#   ② 窗号 WIN0 208→**211**（w211..w213；与历史窗集 w184..w210 **不相交**）。题集 = r617 冻结件逐字节复制件（sha e0c667c2…）。
#   ③ 被测件变更（$HOME/.agentframework/artifacts/pub_r630/agenthost；本轮 src/ 有改动 ⇒ AOT 重发布件，sha 886db888d744a619…）
#      ⇒ 与 R585–R617 冻结件轮**禁相减**，只并列。
#   ④ **单变量改写**：新轴 `AGENTFRAMEWORK_R1_ACTION_EXEC`（产品缺省 **off**）
#      T 档 显式 `=1`（执行面 = 采纳候选映射出的节点）vs C 档 `unset`（产品缺省 = 旧行为：执行面读 `plan`）。
#      与 R617 的档位约定相反是**故意的**：本轴缺省 off ⇒ 「轴关 = 旧行为」的臂就是缺省臂（R546 同一纪律）。
#      轴关断言随之改写（pre-prereg 机检）：C 档不得带该键；T 档必须恰为 "1"。
#   ⑤ 器具（两臂同开，**非被测变量**）：R610 的 `action_candidates_present` 到达面遥测 + R631 四字段台账
#      —— 四字段由**产品侧轴**决定（轴关恒缺席），不是臂注入。
#   ⑥ 判据器 = eval/rover/r631/judge_r631.py（import kpi_r599.py helpers + r604 的 J3 v2 公式模块；
#      J0/J1 块按本轮单变量重写，J2/J2b/J3/J4/J5/W_floor/LD 逐字继承）。
#   ⑦ 起手闸摆动余量 PREV_SWING = **125MB**（口径 = R631 起手闸 `--min-avail-mb 2775` − 产品门槛 2650；
#      同源实测 = r617 同态在飞窗 run-samples n=377 swing 81MB ⇒ 125 为含观测台阶的上界值）；
#      本轮运行期另落采样供下轮派生。
#   ⑧ J5 前表指针 → eval/rover/r617/kpi-table-r617.json（并列、禁相减）；其余沿用
#      （bins 落盘块 / 逐跑次洁净工作区 / 收尾 bin sha 一致性检查 / 铁律 11 前置器）一字未改。
# 用法: bash eval/rover/r631/run_r631.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r631}
PORT=${PORT:-49795}
WIN0=${WIN0:-223}
NWIN=${NWIN:-2}
REPS=${REPS:-3}
ARMS_DOSE="T:agentT:exec1 C:agentC:unset"
CMAXT=${CMAXT:-600}
AMAXT=${AMAXT:-600}
CFGSRC=${CFGSRC:-$HARNESS/agent/cfg}
PDIR=$REPO/eval/rover/r631
TS=$REPO/eval/rover/r631/taskset-r631.json      # 冻结题集逐字节复制件 (sha e0c667c2… = r610 件)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r610/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
MEM_ONCE=$REPO/eval/rover/r571/mem_sample_once.py
SAMPLER=$REPO/eval/rover/r571/mem_sampler.py
GATE=$REPO/eval/rover/r483/preflight_gate.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-$HOME/.agentframework/artifacts/pub_r630/agenthost}
GATE_MB=2650
PREREG=$PDIR/prereg-r631.json
GRADE_TMO=${GRADE_TMO:-10}   # 派生差异 ⑦: 逐用例判分超时 (判分器默认 60; 见 prereg v2 零回归控制)
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
assert d["round"] == "R631" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "T", "C"}, sorted(d["arms"])
assert len(d["artifacts_required"]) == 7, d["artifacts_required"]
assert len(d["evidence_scope"]["require"]) >= 2, d["evidence_scope"]["require"]
assert str(d.get("criterion_version", "")).startswith("v4"), d.get("criterion_version")
assert d["arms"]["C1"]["side"] == "codex" and d["arms"]["T"]["side"] == "agent" and d["arms"]["C"]["side"] == "agent"
assert d["arms"]["T"]["env"]["AGENTFRAMEWORK_R1_ACTION_EXEC"] == "1", "治疗档必须显式取新轴 =1"
assert "AGENTFRAMEWORK_R1_ACTION_EXEC" not in d["arms"]["C"]["env"], "对照档必须是产品缺省（轴键 unset = 旧行为）"
assert d["arms"]["T"]["env"]["AGENTFRAMEWORK_R1_ACTION_PROMPT"] == "legacy" and \
       d["arms"]["C"]["env"]["AGENTFRAMEWORK_R1_ACTION_PROMPT"] == "legacy", \
    "R631: 提示尾块 = held-constant 上下文（非被测变量）⇒ 两臂必须同值 legacy"
for k, arm in (("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "T"), ("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "C"),
               ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "T"), ("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR", "C"),
               ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "T"), ("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "C")):
    assert k not in d["arms"][arm]["env"], "%s 本轮不是被测变量（两臂皆缺省: %s）" % (k, arm)
assert sorted(d["windows"]["set"]) == ["w223", "w224"], d["windows"]["set"]
assert d["windows"]["disjoint_from_history"] is True
print("[先写后跑闸] prereg ok: arms=%s require=%d criterion=%s windows=%s" % (
    sorted(d["arms"]), len(d["evidence_scope"]["require"]), d["criterion_version"][:2], d["windows"]["set"]))
PY

# --- 0a 前置自恢复 (R610 定因的修复动作) -------------------------------------
if [ ! -d "$CFGSRC" ]; then
  log "CFGSRC 缺件 ⇒ 触发自恢复 eval/rover/r631/restore_env_r631.py"
  python3 "$PDIR/restore_env_r631.py" >> "$D/logs/run.txt" 2>&1
fi
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg $CFGSRC（自恢复后仍缺）"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT 发布件 $BIN (待恢复/重建)"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { log "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { log "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { log "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R631 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
BIN_SHA_BEFORE=$(sha256sum "$BIN" | cut -d' ' -f1)
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r631.json" "$CFGSRC" <<'PY'
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
# 产品默认档: 剂量键**全部显式 unset**（防继承）；新轴 AGENTFRAMEWORK_R1_ACTION_EXEC 由臂表逐档注入。
unset AGENTFRAMEWORK_R1_MAX_REPAIR AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR
unset AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR AGENTFRAMEWORK_R1_ACTION_CANDIDATES AGENTFRAMEWORK_R1_ACTION_PROMPT AGENTFRAMEWORK_R1_ACTION_EXEC
cd "$REPO" || exit 3

# --- 1 同输入硬门 -----------------------------------------------------------
cp "$TS" "$D/taskset.json"
python3 - "$TS" "$D" <<'PY'
import hashlib, io, json, sys
ts, D = sys.argv[1], sys.argv[2]
t = [x for x in json.load(io.open(ts, encoding="utf-8"))["tasks"] if x["tid"] == "g1"][0]
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
io.open(D + "/task-g1-prompt.txt", "w", encoding="utf-8").write(t["prompt"])
io.open(D + "/logs/input-pin.txt", "w", encoding="utf-8").write(
    "prompt_sha256 %s chars=%d hidden_cases=%s\n" % (h, len(t["prompt"]), t.get("hidden_cases")))
print("prompt_sha256 %s chars=%d" % (h, len(t["prompt"])))
PY

# --- 2 起手闸 (内存裕量条款: 阈值 + 观测振幅余量 + 连续 2 次) -----------------
PREV_SWING=${PREV_SWING:-119}
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
  log "[致命] 起手前 3 样本极差 ${SPREAD}MB > 50MB ⇒ 跨态, 窗口不可开 (fail-closed; R590 候选③ 条款)"; exit 2; fi
log "起手前采样: ceiling(min of 3)=$CEIL spread=${SPREAD}MB"
PY_MEM=$CEIL
MARGIN=$(( PREV_SWING > 60 ? PREV_SWING : 60 ))
CAP=$(( CEIL - GATE_MB - 60 ))
CAP_BINDING=false
[ "$MARGIN" -gt "$CAP" ] && { MARGIN=$CAP; CAP_BINDING=true; }
if [ "$MARGIN" -lt 60 ]; then
  log "[致命] 顶棚 $CEIL 装不下下限 60MB ⇒ 窗口不可开 (fail-closed)"; exit 2; fi
REQ=$(( GATE_MB + MARGIN ))
log "起手闸条款: ceiling=$CEIL prev_swing=$PREV_SWING margin=$MARGIN REQ=$REQ (cap=$CAP cap_binding=$CAP_BINDING spread=${SPREAD}MB)"
python3 - "$PDIR/gate-margin-r631.json" "$PREV_SWING" "$CEIL" "$MARGIN" "$REQ" "$CAP" "$CAP_BINDING" "$SPREAD" <<'PY'
import io, json, sys
out, prev, ceil, margin, req, cap, binding, spread = sys.argv[1:9]
json.dump({"round": "R631", "criterion": "C3 起手闸余量条款（R590 派生版；候选⑤ 余量源按 R591 在同一飞窗实测重派生）",
           "clause": "MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE-floor); REQ=GATE+MARGIN",
           "prev_swing_effective": int(prev),
           "prev_swing_source": "前窗r620/logs/run-samples.jsonl (同态在飞窗, n=191, swing=78; 口径 = R620 起手闸 2769 − 产品门槛 2650)",
           "ceiling_min_of_3": int(ceil), "pre_sample_spread_mb": int(spread), "spread_clause": "<=50MB else fail-closed",
           "margin": int(margin), "req": int(req), "cap": int(cap), "cap_binding": binding == "true",
           "preflight_min_avail_mb": 2769,
           "note": "cap_binding=true ⇒ 振幅项退化（收紧的是上界而非下界，R590 已登记）"},
          io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[条款] 派生件落盘", out)
PY
for i in 1 2; do
  python3 "$GATE" --round R631 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-A$i.json')).get('verdict'))" 2>/dev/null)
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
# 判别力成对控制 (同内存态: 基础门槛 PASS 而条款 GATE_BLOCKED)
BAND=$((GATE_MB + (REQ - GATE_MB) / 2))
HOGMB=$(( PY_MEM - BAND )); [ "$HOGMB" -lt 0 ] && HOGMB=0
if [ "$HOGMB" -gt 0 ]; then
  python3 -c "import time,sys
n=int(sys.argv[1]); b=bytearray(n*1024*1024); b[::4096]=b'\x01'*len(b[::4096]); time.sleep(60)" "$HOGMB" &
  HOG=$!; sleep 4
  mdisc=$(python3 "$MEM_ONCE" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
  python3 "$GATE" --round R631DISC --gate-mb "$GATE_MB" --out "$D/gate-disc-base.json" >/dev/null 2>&1
  python3 "$GATE" --round R631DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
  kill $HOG 2>/dev/null; wait $HOG 2>/dev/null
  python3 - "$D" "$mdisc" "$REQ" <<'PY'
import io, json, sys
D, mem, req = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
vb = json.load(io.open(D + "/gate-disc-base.json")).get("verdict")
vc = json.load(io.open(D + "/gate-disc-clause.json")).get("verdict")
in_band = 2650.0 <= mem < req
truth = bool(in_band and vb == "PASS" and vc == "GATE_BLOCKED")
rc = 0 if truth else 3
json.dump({"mem_mb": mem, "base": vb, "clause": vc, "in_band": in_band, "true_discrimination": truth, "rc": rc},
          io.open(D + "/gate-disc-pair.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"rc": rc, "mem": mem, "base": vb, "clause": vc, "truth": truth}, ensure_ascii=False))
PY
  log "判别力成对控制 rc=$? (0 真判别行使 / 3 未行使已如实登记)"
else
  log "判别力成对控制: 压制量 0 (内存已在带内不可压) ⇒ 未行使, 如实登记"
fi
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
#   R631 语义: held-constant 提示尾块 = legacy ⇒ 模型不给候选字段 ⇒ 采纳面为空
#   ⇒ `ActionExecPlan.Decide` 应走 **回退** 支。前提不成立 ⇒ 零臂起跑（rc=5），不烧 21 跑次。
mkdir -p "$D/premise/g1/work"
env AGENTFRAMEWORK_WORKSPACE="$D/premise/g1/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
    AGENTFRAMEWORK_R1_TRANSCRIPT="$D/premise/g1/transcript.json" AGENTFRAMEWORK_R1_TAG=premise-r631 \
    AGENTFRAMEWORK_R1_ROLE_FILE="$ROLE" AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy AGENTFRAMEWORK_R1_ACTION_EXEC=1 \
    timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
    --session-id "premise-r631" > "$D/premise/g1/reply.txt" 2> "$D/premise/g1/stderr.txt"
echo "$? " > "$D/premise/g1/cli_rc.txt"
python3 - "$D/premise/g1/transcript.json" "$PDIR/premise-r631.json" "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e" <<'PY'
import io, json, sys
tp, out, anchor = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    t = json.load(io.open(tp, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print("[前提闸] 缺 transcript: %s" % str(e)[:120]); raise SystemExit(5)
present = t.get("action_candidates_present")
sha = t.get("prefix_sha256")
src = t.get("exec_source")
fb = t.get("exec_fallback")
plan_n = t.get("plan_steps_total")
ok_state = (src == "plan_fallback" and fb == "candidates_absent" and (plan_n or 0) > 0)
ok_ctx = (sha == anchor)
rec = {"premise": "legacy 提示尾块 ⇒ 候选键未到达 ⇒ 回退支（plan_fallback / candidates_absent）",
       "action_candidates_present": present, "prefix_sha256": sha, "legacy_anchor": anchor,
       "exec_source": src, "exec_fallback": fb, "plan_steps_total": plan_n,
       "state_gate": bool(ok_state), "context_gate": bool(ok_ctx),
       "rc": 0 if (ok_state and ok_ctx) else 5}
json.dump(rec, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[前提闸] present=%s sha=%s src=%s fb=%s plan=%s rc=%d"
      % (present, (sha or "")[:12], src, fb, plan_n, rec["rc"]))
raise SystemExit(rec["rc"])
PY
_prc=$?; [ "$_prc" -eq 0 ] || { log "[致命] 前提闸未过 rc=$_prc ⇒ 零臂起跑（fail-closed）"; exit 5; }
log "前提闸 PASS: 回退触发面成立 (plan_fallback / candidates_absent)"

# --- 4 逐窗逐重复 -----------------------------------------------------------
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  local t0 t1
  # 逐跑次**洁净工作区**（残留树下读数不可归因，R617 实测）
  rm -rf "$D/$win/$sub/g1"
  mkdir -p "$D/$win/$sub/g1/work"
  t0=$(dmax agent)
  local -a ENVS=("AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" "AGENTFRAMEWORK_R1_CONTRACT=1"
                 "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win"
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE"
                 "AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy")  # R631 held-constant 上下文（非被测变量；两臂同值）
  case "$dose" in
    exec1) ENVS+=("AGENTFRAMEWORK_R1_ACTION_EXEC=1") ;;      # 治疗档: 执行面 = 采纳候选映射
    unset) : ;;                                              # 对照档: 产品缺省（轴关 = 旧行为逐位）
    ac0) ENVS+=("AGENTFRAMEWORK_R1_ACTION_CANDIDATES=0") ;;  # 保留档（本轮不用，防误用）
    carry0) ENVS+=("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER=0") ;;  # 保留档（本轮不用，防误用）
    *) ENVS+=("AGENTFRAMEWORK_R1_MAX_REPAIR=$dose") ;;
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
  python3 "$PDIR/judge_r631.py" --D "$D" --pd "$PDIR" --win "$W" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"reps\":$REPS}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/judge_r631.py" --D "$D" --pd "$PDIR" 2>&1 | tee -a "$D/logs/run.txt" || log "KPI 汇总 rc=$? (见下)"

# --- 4b 收尾: 采样器 + 二进制 sha 一致性 (臂身份) ----------------------------
if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
BIN_SHA_AFTER=$(sha256sum "$BIN" | cut -d' ' -f1)
if [ "$BIN_SHA_BEFORE" = "$BIN_SHA_AFTER" ]; then echo "{\"bin_sha_stable\":true,\"sha\":\"$BIN_SHA_BEFORE\"}" > "$D/bin-sha-check.json"
else echo "{\"bin_sha_stable\":false,\"before\":\"$BIN_SHA_BEFORE\",\"after\":\"$BIN_SHA_AFTER\"}" > "$D/bin-sha-check.json"; log "[致命] 运行期二进制被替换 ⇒ 臂身份不成立"; fi

# --- 5 铁律 11 前置器 -------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r631 --out "$D/precond-r631.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R631 完成"
