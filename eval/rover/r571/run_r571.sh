#!/usr/bin/env bash
# R571 驱动器: **同窗单变量对照轮 (第五窗集)** —— 既有开关 AGENTFRAMEWORK_R1_MAX_REPAIR (**契约不过时的最大修复轮数**)
#             取值 **1 (产品默认, 控制臂) vs 3** × 外部真值 codex, 5 新窗 w149..w153。
# 承重问题: 既有 env 开关清单里**唯一从未被单变量化**的一个 (R542/R544/R547/R550/R551/R552/R558/R559/R560/R566/R567/R570
#             的预注册均把它恒设为 1 或取默认)。先量分布 (96 份归档 transcript):
#             `repair_rounds=1` 23/96 (24.0%) 且其中 `stage=contract` rc=4 **5 例** = 修复预算被用尽仍不过契约 ⇒ 本轴**有靶人群**,
#             天花板 ≈ 5/96 = 5.2% (运行级); `repair_rounds=0` 73/96。
# 同一枚二进制 (R556 交付件 sha 320d0eb1…) ⇒ 单变量由**构造**保证 (全臂除该开关取值外 env 逐项相同);
# 同窗 3 臂 (codex 真值 + R571M1 契约修复轮=1 + R571M3 契约修复轮=3), 5 新窗 (w149..w153; 与历轮窗集 **并列不相减**)。
# 骨架同 run_r570.sh (逐字节复用), 本轮差异 (逐条声明, 其余相同):
#   ① 轮号命名空间 R570→R571 / r570→r571 (工作目录 /tmp/r571, 端口 49531);
#   ② 窗号 WIN0 143→149, NWIN 6→5;
#   ③ 本侧臂 env: 唯一变量键 = AGENTFRAMEWORK_R1_MAX_REPAIR (取值 1 / 3, 两臂都显式落盘);
#      全局 export MAX_REPAIR 已删除 (避免继承与显式值并存); 显式 `unset AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL` (两臂恒关, R570 轴)。
#   ④ 起手闸条款 `--prev-postcheck` 仍指 **R569** 件 (swing_mb=90) —— **先于起臂声明**: R570 的 290 振幅经本轮归因件
#      判为**自体成本**(与 w144 长窗同步, 见 ownrss 归因), 不得作为**外来**余量输入; 该选择非事后调参。
#   ⑤ 判别力成对控制 (同内存态 2650 vs REQ 反判 + 占用负控) 保留;
#   ⑥ 运行中采样器升级为 v2 (逐样本同时落 `mem_available_mb` 与 **本运行血统**进程 RSS 合计 `own_rss_mb`)。
# 用法: D=/tmp/r571 PORT=49531 WIN0=149 NWIN=5 bash eval/rover/r571/run_r571.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-/tmp/r571}
PORT=${PORT:-49531}
WIN0=${WIN0:-149}
NWIN=${NWIN:-3}
REPS=${REPS:-4}
ARMS_DOSE="R571M1:agentM1:1 R571M3:agentM3:3"
CMAXT=${CMAXT:-900}
AMAXT=${AMAXT:-900}
CFGSRC=/tmp/r455_env/agent/cfg
PDIR=$REPO/eval/rover/r571
TS=$REPO/eval/rover/r560/taskset-r560.json   # 冻结题集 (与 R559/R560 逐字节同件; 复用不复制)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r560/cases/run_cases_r521.py   # 冻结判分器 (sha a67215a7…, 与 matrix 的 ERRSHA 同源)
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-/tmp/pub_r556/agenthost/agenthost}
BIN_SHA=320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$PDIR/prereg-r571.json
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
assert d["round"] == "R571" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R571M1", "R571M3"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 27, d["evidence_scope"]["require"]
assert str(d.get("criterion_version", "")).startswith("v2"), d.get("criterion_version")
_doses = {a: {k: v for k, v in d["arms"][a]["env"].items() if "MAX_" in k or "EARLY_STOP" in k}
          for a in ("R571M1", "R571M3")}
assert set(_doses["R571M1"]) == {"AGENTFRAMEWORK_R1_MAX_REPAIR"}, _doses
assert set(_doses["R571M3"]) == {"AGENTFRAMEWORK_R1_MAX_REPAIR"}, _doses
assert int(_doses["R571M1"]["AGENTFRAMEWORK_R1_MAX_REPAIR"]) == 1, _doses
assert int(_doses["R571M3"]["AGENTFRAMEWORK_R1_MAX_REPAIR"]) == 3, _doses
print("[先写后跑闸] prereg ok: arms=%s require=%d doses=%s" % (
    sorted(d["arms"]), len(d["evidence_scope"]["require"]), _doses))
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { echo "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
[ "$(sha256sum "$BIN" | cut -d' ' -f1)" = "$BIN_SHA" ] || { echo "[致命] 二进制 sha 不符 R556 交付件 ⇒ 臂身份不成立"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { echo "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R571 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r571.json" <<'PY'
import hashlib, io, json, os, sys
def h(p):
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
pre = json.load(io.open(sys.argv[3], encoding="utf-8"))
rep = {"note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 全臂共用同一枚二进制 ⇒ 臂身份单变量由构造保证。",
       "bin_all_arms": h(sys.argv[1]), "codex": h(sys.argv[2]),
       "arm_env": {k: pre["arms"][k].get("env") for k in ("R571M1", "R571M3")}}
json.dump(rep, io.open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[钉死] bin=%s arm_env=%s" % (rep["bin_all_arms"]["sha256"][:16], rep["arm_env"]))
PY
cp -r "$CFGSRC"/. "$D/agent-cfg"/
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
export DOTNET_ROOT="$HOME/.dotnet"

cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
  rm -f "$REPO/.git/ROUND_CLAIM"; return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1
unset AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL   # R570 轴: 两臂恒关 (产品默认 0)
unset AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR   # 探针轴停用 (R551-R553 已判无增益)
# AGENTFRAMEWORK_R1_MAX_REPAIR 不在全局导出: 唯一变量键由 run_agent 逐臂显式落盘 (1 / 3)
cd "$REPO" || exit 3

# --- 1 同输入硬门 -----------------------------------------------------------
cp "$TS" "$D/taskset.json"
python3 - "$TS" "$D" "$PROMPT_SHA_EXP" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, sys
ts, D, exp = sys.argv[1], sys.argv[2], sys.argv[3]
t = [x for x in json.load(io.open(ts, encoding="utf-8"))["tasks"] if x["tid"] == "g1"][0]
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
io.open(D + "/task-g1-prompt.txt", "w", encoding="utf-8").write(t["prompt"])
print("prompt_sha256 %s exp=%s ok=%s chars=%d hidden_cases=%s" % (h, exp, h == exp, len(t["prompt"]), t.get("hidden_cases")))
sys.exit(0 if h == exp else 3)
PY
rc=$?; cat "$D/logs/input-pin.txt"; [ "$rc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$rc"; exit 3; }

# --- 2 起手闸 A (振幅余量条款 + 连续 2 次) + B (独立执行路径禁泄漏) ----------
# 候选③: 擦边 PASS 不算窗口。起手前采 3 次 (间隔 5s) 派生 REQ = GATE_MB + MARGIN,
# 以**既有闸的 --gate-mb** 生效 (零新逻辑进闸) ⇒ 闸内部即判 mem >= REQ ∧ blockers 空。
: > "$D/logs/pre-samples.jsonl"
for k in 1 2 3; do
  python3 "$PDIR/mem_sample_once.py" "$D/logs/pre-samples.jsonl"
  sleep 5
done
python3 "$PDIR/gate_margin_r571.py" --derive --samples "$D/logs/pre-samples.jsonl" \
    --prev-postcheck "$REPO/eval/rover/r569/gate-postcheck-r569.json" \
    --out "$PDIR/gate-margin-r571.json" --embed-selftest | tee -a "$D/logs/run.txt"
mrc=${PIPESTATUS[0]}
log "起手闸条款 (振幅余量): rc=$mrc"
[ "$mrc" -eq 0 ] || { log "[致命] 振幅余量条款未过 (rc=$mrc) ⇒ 不算窗口, 不起臂"; exit 2; }
REQ=$(python3 -c "import json;print(int(json.load(open('$PDIR/gate-margin-r571.json'))['required_mb']))")
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R571 --gate-mb "$REQ" --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
# --- 2a 判别力成对控制 (候选③, 承重): 把内存态**压进判别带** [2650, REQ) 再反判 --------
# 自捕#1 (首次起跑即拦): 条款不得**无条件**要求两闸异判 —— 内存态在 REQ 之上时两闸皆 PASS 是正确行为。
#   正确形态 = 用占用把 mem 压进判别带中点, 再看基础门槛 PASS / 条款 GATE_BLOCKED;
#   带内不进 (不可达) ⇒ rc=3 如实记「真判别未行使」, 不当 FAIL (与 R562「诱饵控制前提静默落空」同族教训)。
mbase=$(python3 "$PDIR/mem_sample_once.py" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
BAND=$((2650 + ($REQ - 2650) / 2))
HOGMB=$(( mbase - BAND )); [ "$HOGMB" -lt 0 ] && HOGMB=0
python3 -c "import time,sys
n=int(sys.argv[1])
b=bytearray(n*1024*1024)
b[::4096]=b'\x01'*len(b[::4096])
time.sleep(90)" "$HOGMB" & HOG=$!
sleep 4
mdisc=$(python3 "$PDIR/mem_sample_once.py" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
log "判别带压制: base=$mbase hog=${HOGMB}MB now=$mdisc (带 = 2650..$((REQ-1)) )"
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R571DISC --gate-mb 2650 --out "$D/gate-disc-base2650.json" >/dev/null 2>&1
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R571DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
if [ -n "${HOG:-}" ]; then kill $HOG 2>/dev/null; wait $HOG 2>/dev/null; unset HOG; fi
vb=$(python3 -c "import json;print(json.load(open('$D/gate-disc-base2650.json')).get('verdict'))" 2>/dev/null)
vc=$(python3 -c "import json;print(json.load(open('$D/gate-disc-clause.json')).get('verdict'))" 2>/dev/null)
python3 - "$D" "$mdisc" "$vb" "$vc" "$REQ" <<'PY'
import io, json, sys
D, mem, vb, vc, req = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4], float(sys.argv[5])
base_ok = (vb == "PASS") == (mem >= 2650.0)
clause_ok = (vc == "PASS") == (mem >= req)
in_band = 2650.0 <= mem < req
truth = bool(in_band and vb == "PASS" and vc == "GATE_BLOCKED")
if not (base_ok and clause_ok):
    rc, why = 2, "gate_verdict_contradicts_own_threshold"
elif in_band and not truth:
    rc, why = 2, "in_band_but_no_split(false_teeth)"
elif not in_band:
    rc, why = 3, "state_not_in_discriminating_band(不可达 ⇒ 真判别未行使)"
else:
    rc, why = 0, "ok"
rec = {"mem_mb": mem, "base_verdict": vb, "clause_verdict": vc, "gate_base_mb": 2650, "gate_clause_mb": req,
       "base_matches_threshold": base_ok, "clause_matches_threshold": clause_ok,
       "state_in_discriminating_band": in_band, "true_discrimination": truth, "rc": rc, "why": why,
       "teeth": ("同一内存态: 基础门槛 PASS 而条款 GATE_BLOCKED ⇒ 条款严格更严" if truth else
                 "未行使真判别: 两闸各自按自己的门槛判 (判别带不可达)")}
json.dump(rec, io.open(D + "/gate-disc-pair.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False))
sys.exit(rc)
PY
drc=$?
log "判别力成对控制 rc=$drc (0 真判别行使 / 3 未行使已如实登记)"
[ "$drc" -eq 2 ] && { log "[致命] 判别力成对控制判红 ⇒ 条款空心/器具缺陷, 不起臂"; exit 2; }

python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 rc=$lrc"; exit 2; }

# --- 2b 运行中内存采样器 (5s; 收尾 postcheck 用) ----------------------------
: > "$D/logs/run-samples.jsonl"
python3 "$PDIR/mem_sampler.py" "$D/logs/run-samples.jsonl" 5 "$D" "$PORT" > "$D/logs/sampler.log" 2>&1 &
echo "$!" > "$D/logs/sampler.pid"
echo "sampler pid=$(cat "$D/logs/sampler.pid")" >> "$D/logs/run.txt"

# --- 3 adapter (两臂同一会话) ----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪"; exit 2; }
log "adapter 就绪 port=$PORT (w$WIN0..w$((WIN0+NWIN-1)); 每窗 = codex 真值 ×1 + R571M1(契约修复轮=1) ×$REPS + R571M3(契约修复轮=3) ×$REPS)"

# --- 4 逐窗逐重复: 本轴效应是**运行级** (契约修复轮用尽 ⇒ 整次运行契约死) ----------
# 靶人群先量 (96 份归档 transcript): repair_rounds=1 占 24.0%, 其中 stage=contract rc=4 占 5/96 = 5.2%。
# 5.2% 的运行级效应在「每臂每窗 1 跑次」的分辨率下等于 0 (期望 0.26/臂) ⇒ 必须**重复臂**:
# 每窗每臂 REPS 个独立会话 (同窗同题同 env, 仅 session-id 不同) ⇒ 24 跑次/臂, 分辨率抬到
# 期望 ≈1.25 例靶运行 —— 仍不高, 故本轴**预注册写成「分辨率上界 + 天花板算式」**, 不得把
# 「未测到差异」读成「无效应」(详见 prereg `resolution_bound`)。
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  local t0 t1
  mkdir -p "$D/$win/$sub/g1/work"
  t0=$(dmax agent)
  local -a ENVS=("AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" "AGENTFRAMEWORK_R1_CONTRACT=1"
                 "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win"
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  [ "$dose" = "unset" ] || ENVS+=("AGENTFRAMEWORK_R1_MAX_REPAIR=$dose")
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
  python3 "$PDIR/kpi_r571.py" --D "$D" --pd "$PDIR" --win "$W" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"reps\":$REPS}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/kpi_r571.py" --D "$D" --pd "$PDIR" 2>&1 | tee -a "$D/logs/run.txt" || log "KPI 汇总 rc=$? (见下)"

# --- 4b 运行中采样收尾: 基础门槛是否被击穿 + 观测振幅 (供下轮派生) ----------
if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
python3 "$PDIR/gate_margin_r571.py" --postcheck --samples "$D/logs/run-samples.jsonl" \
    --out "$PDIR/gate-postcheck-r571.json" | tee -a "$D/logs/run.txt"
log "起手闸条款 postcheck rc=$?" 

# --- 5 铁律 11 前置器 (独立重跑隐藏 58 用例) --------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r571 --out "$D/precond-r571.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R571 完成"
