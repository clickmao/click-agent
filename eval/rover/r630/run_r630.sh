#!/usr/bin/env bash
# R630 驱动器（单变量轴 = 既有 env `AGENTFRAMEWORK_R1_ACTION_PROMPT` 第四取值 `spec`）
# 派生 = eval/rover/r618/run_r618.sh（结构复用）+ 下列**逐条声明的差异**:
#   ① 轮号/命名空间 R630；D=$HOME/.agentframework/harness/runs/r630；窗号 WIN0 208→**211**（w211..w212，与历史窗集不相交）。
#   ② 被测件 = $HOME/.agentframework/artifacts/pub_r630/agenthost（本轮 src/ 有改动 ⇒ AOT 重发布件，sha cefd045e8d1d4258…）。
#   ③ **单变量改写**：轴改回 `AGENTFRAMEWORK_R1_ACTION_PROMPT`，T 档显式取新值 `spec`（= 缺省块正文 + 规格保真尾块），
#      C 档 **unset** ⇒ 产品缺省（= R617 现盘块逐字节）。两臂共用同一枚二进制 ⇒ 臂身份由构造保证。
#   ④ **本窗不跑 codex 臂**（差异声明）：外部真值列改为**跨窗并列**引用 baselines id
#      `F_merge.quality.cases_median_truth`（同冻结题集 sha e0c667c2…，窗不同）⇒ 报告里标「参考」，
#      不作 J2 主判据（预注册 evidence_scope.foreign_forbidden 已写明）。
#   ⑤ 判据器 = eval/rover/r630/judge_r630.py（前缀锚**从 prefix-r630.json 读**，不写常量；含 5 态影子自检）。
#      先跑自检（器具可用才起臂）；自检不过 ⇒ rc=2 不起臂。
#   ⑥ 起手闸: 沿用 r618 条款（阈值 + 观测振幅余量 + 连续 2 次）；PREV_SWING 取 baselines `F_env.gate.prev_swing_mb`。
#   ⑦ 逐跑次**洁净工作区** + 逐跑次独立会话；跑完逐跑次判分（run_cases_r521.py）+ 落盘 transcript。
# 用法: bash eval/rover/r630/run_r630.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r630}
PORT=${PORT:-49794}
WIN0=${WIN0:-211}
NWIN=${NWIN:-2}
REPS=${REPS:-3}
AMAXT=${AMAXT:-900}
CFGSRC=${CFGSRC:-$HARNESS/agent/cfg}
PDIR=$REPO/eval/rover/r630
TS=$REPO/eval/rover/r618/taskset-r618.json      # 冻结题集逐字节复制件 (sha e0c667c2…)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r610/cases/run_cases_r521.py
BIN=${BIN:-$HOME/.agentframework/artifacts/pub_r630/agenthost}
PREREG=$PDIR/prereg-r630.json
GATE_MB=2650
PREV_SWING=${PREV_SWING:-285}   # baselines F_env.gate.prev_swing_mb
ARMS="T:agentT:spec C:agentC:unset"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

mkdir -p "$D"/{logs,agent-cfg} "$PDIR"/{snapshots,evidence/windows}

# --- 0a 判据器影子自检 (器具可用才起臂) --------------------------------------
python3 "$PDIR/judge_r630.py" --selftest > "$D/logs/judge-selftest.txt" 2>&1
jrc=$?
log "判据器影子自检 rc=$jrc"
[ "$jrc" -eq 0 ] || { log "[致命] 判据器自检未过 ⇒ 不起臂"; exit 2; }

# --- 0b 先写后跑闸 -----------------------------------------------------------
[ -f "$PREREG" ] || { log "[致命] 缺预注册 $PREREG (先写后跑闸)"; exit 3; }
python3 - "$PREREG" <<'PY' || { log "[致命] 预注册机检不过"; exit 3; }
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
assert d["round"] == "R630" and d["written_before_run"] is True, d.get("round")
assert len(d["evidence_scope"]["require"]) == 7, len(d["evidence_scope"]["require"])
assert str(d.get("criterion_version", "")).startswith("v3"), d.get("criterion_version")
sv = d["single_variable"]
assert sv["axis"] == "AGENTFRAMEWORK_R1_ACTION_PROMPT", sv["axis"]
assert sv["T"].startswith("spec") and sv["C"].startswith("unset"), (sv["T"], sv["C"])
assert d["windows"]["set"] == ["w211", "w212"], d["windows"]["set"]
assert d["windows"]["disjoint_from_history"] is True
assert len(d["thresholds_cite_baselines"]) >= 5, d["thresholds_cite_baselines"]
# 负控①: 本轮被测轴不得是上一轮(R618)的 exec 轴（防复制粘贴错轮）
assert sv["axis"] != "AGENTFRAMEWORK_R1_ACTION_EXEC"
# 负控②: 另三枚 R610–R618 轴键不得出现在被声明为 T/C 的取值里
for k in ("AGENTFRAMEWORK_R1_ACTION_CANDIDATES", "AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR",
          "AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER"):
    assert k not in json.dumps(sv, ensure_ascii=False)
print("[先写后跑闸] prereg ok: axis=%s windows=%s criterion=%s baselines=%d" % (
    sv["axis"], d["windows"]["set"], d["criterion_version"][:2], len(d["thresholds_cite_baselines"])))
PY

# --- 0c 资产/环境守卫 (fail-closed) -----------------------------------------
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT 发布件 $BIN"; exit 3; }
[ -f "$REPO/.env.local" ] || { log "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] || { log "[致命] 缺题集/role/用例脚本"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { log "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R630 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
BIN_SHA_BEFORE=$(sha256sum "$BIN" | cut -d' ' -f1)
sha256sum "$BIN" > "$D/logs/bin-sha.txt"

cp -r "$CFGSRC"/. "$D/agent-cfg"/
# 差异⑤: cfg 端口替换（r618 同款工序）——适配器是本轮**模型通道**（relay），不是可选项:
#   未替换则 cfg 指向 48600 无监听 ⇒ 全跑次 rc=6/llm_transport ⇒ 整轮 VOID（本轮首跑实测）。
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
export DOTNET_ROOT="$HOME/.dotnet"
cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  rm -f "$REPO/.git/ROUND_CLAIM"; return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"
export AGENTFRAMEWORK_PY_RUN=1
export AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1
unset AGENTFRAMEWORK_R1_MAX_REPAIR AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR
unset AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR
unset AGENTFRAMEWORK_R1_ACTION_CANDIDATES AGENTFRAMEWORK_R1_ACTION_EXEC AGENTFRAMEWORK_R1_ACTION_PROMPT
cd "$REPO" || exit 3

# --- 1 同输入硬门 (题面逐字节 + prompt sha 落盘) ------------------------------
cp "$TS" "$D/taskset.json"
python3 - "$TS" "$D" <<'PY'
import hashlib, io, json, sys
ts, D = sys.argv[1], sys.argv[2]
t = [x for x in json.load(io.open(ts, encoding="utf-8"))["tasks"] if x["tid"] == "g1"][0]
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
io.open(D + "/task-g1-prompt.txt", "w", encoding="utf-8").write(t["prompt"])
io.open(D + "/logs/input-pin.txt", "w", encoding="utf-8").write(
    "prompt_sha256 %s chars=%d hidden_cases=%s taskset_sha256 %s\n"
    % (h, len(t["prompt"]), t.get("hidden_cases"), hashlib.sha256(io.open(ts, 'rb').read()).hexdigest()))
print("prompt_sha256 %s chars=%d" % (h, len(t["prompt"])))
PY

# --- 2 起手闸 (内存裕量条款: 阈值 + 观测振幅余量 + 连续 2 次) -----------------
: > "$D/logs/pre-samples.jsonl"
for _s in 1 2 3; do python3 "$REPO/eval/rover/r571/mem_sample_once.py" "$D/logs/pre-samples.jsonl" >/dev/null; sleep 1; done
read -r CEIL SPREAD < <(python3 - "$D/logs/pre-samples.jsonl" <<'PY'
import io, json, sys
v = [json.loads(l)["mem_available_mb"] for l in io.open(sys.argv[1], encoding="utf-8") if l.strip()]
print(min(v), max(v) - min(v))
PY
)
[ "${CEIL:-0}" -gt 0 ] || { log "[致命] 起手前采样空 (fail-closed)"; exit 2; }
if [ "$SPREAD" -gt 50 ]; then log "[致命] 起手前 3 样本极差 ${SPREAD}MB > 50MB ⇒ 跨态, 窗口不可开"; exit 2; fi
CAP=$(( CEIL - GATE_MB - 60 ))
MARGIN=$PREV_SWING; CAP_BINDING=false
[ "$CAP" -lt 60 ] && { log "[致命] 顶棚 $CEIL 装不下下限 60MB ⇒ 窗口不可开"; exit 2; }
if [ "$MARGIN" -gt "$CAP" ]; then MARGIN=$CAP; CAP_BINDING=true; fi
REQ=$(( GATE_MB + MARGIN ))
log "起手闸条款: ceiling=$CEIL prev_swing=$PREV_SWING margin=$MARGIN REQ=$REQ (cap=$CAP cap_binding=$CAP_BINDING spread=${SPREAD}MB)"
python3 - "$PDIR/gate-margin-r630.json" "$PREV_SWING" "$CEIL" "$MARGIN" "$REQ" "$CAP" "$CAP_BINDING" "$SPREAD" <<'PY'
import io, json, sys
out, prev, ceil, margin, req, cap, binding, spread = sys.argv[1:9]
json.dump({"round": "R630",
           "criterion": "C3 起手闸余量条款（R618 派生版；余量源按 baselines F_env.gate.prev_swing_mb）",
           "clause": "MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE-floor); REQ=GATE+MARGIN",
           "prev_swing_effective": int(prev),
           "ceiling_min_of_3": int(ceil), "pre_sample_spread_mb": int(spread),
           "spread_clause": "<=50MB else fail-closed",
           "margin": int(margin), "req": int(req), "cap": int(cap), "cap_binding": binding == "true",
           "note": "cap_binding=true ⇒ 振幅项退化（收紧的是上界而非下界，R590 已登记）；擦边 PASS 不算窗口"},
          io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[条款] 派生件落盘", out)
PY
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R630 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-A$i.json')).get('verdict'))" 2>/dev/null)
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 rc=$lrc"; exit 2; }

# --- 3 逐窗逐重复 -----------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
set -a; . "$HOME/.agentframework/keys.env"; set +a
# --- 2c 模型通道（适配器 relay）起臂前就绪 -----------------------------------
mkdir -p "$D/adapter"
DEMO_OUT="$D/adapter" ADAPTER_DUMP_FULL=1 setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪（无模型通道 ⇒ 全跑次必 VOID）"; exit 2; }
log "adapter 就绪 port=$PORT (模型通道; 未就绪则整轮 VOID)"
: > "$D/logs/runs.jsonl"
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  rm -rf "$D/$win/$sub/g1"; mkdir -p "$D/$win/$sub/g1/work"
  local -a ENVS=("AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" "AGENTFRAMEWORK_R1_CONTRACT=1"
                 "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win"
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  case "$dose" in
    spec) ENVS+=("AGENTFRAMEWORK_R1_ACTION_PROMPT=spec") ;;
    unset) : ;;
    *) ENVS+=("AGENTFRAMEWORK_R1_ACTION_PROMPT=$dose") ;;
  esac
  printf '%s\n' "${ENVS[@]}" > "$D/$win/$sub/g1/arm_env.txt"
  env "${ENVS[@]}" timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
      --session-id "$arm-$win-$sub" > "$D/$win/$sub/g1/reply.txt" 2> "$D/$win/$sub/g1/stderr.txt"
  echo "$? " > "$D/$win/$sub/g1/cli_rc.txt"
}
for i in $(seq "$WIN0" $((WIN0 + NWIN - 1))); do
  W=w$i
  WSTART=$(date +%s)
  for r in $(seq 1 "$REPS"); do
    for spec in $ARMS; do
      arm=${spec%%:*}; rest=${spec#*:}; base=${rest%%:*}; dose=${rest##*:}
      sub="$base-r$r"
      t0=$(date +%s)
      run_agent "$arm" "$W" "$sub" "$dose"
      t1=$(date +%s)
      echo "{\"arm\":\"$arm\",\"win\":\"$W\",\"rep\":$r,\"sub\":\"$sub\",\"cli_rc\":\"$(cat "$D/$W/$sub/g1/cli_rc.txt")\",\"secs\":$((t1-t0))}" >> "$D/logs/runs.jsonl"
      log "跑次 $arm $W $sub rc=$(cat "$D/$W/$sub/g1/cli_rc.txt") $((t1-t0))s"
    done
  done
  for d in "$D/$W"/*/; do
    sub=$(basename "$d"); [ -d "$d/g1/work" ] || continue
    ( cd "$d/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$d/g1/cases.txt" 2>&1
  done
  rm -rf "$PDIR/snapshots/$W"
  for d in "$D/$W"/*/; do
    sub=$(basename "$d"); [ -d "$d/g1/work" ] || continue
    mkdir -p "$PDIR/snapshots/$W/$sub/g1"
    cp -a "$d/g1/work/." "$PDIR/snapshots/$W/$sub/g1/"
  done
  python3 "$PDIR/judge_r630.py" --D "$D" --pd "$PDIR" --win "$W" >> "$D/logs/run.txt" 2>&1 || true
  echo "{\"win\":\"$W\",\"secs\":$(( $(date +%s) - WSTART )),\"reps\":$REPS}" >> "$D/logs/windows.jsonl"
  sleep 2
done

# --- 4 汇总判决 + 收尾 ------------------------------------------------------
python3 "$PDIR/judge_r630.py" --D "$D" --pd "$PDIR" --win w211 --win w212 \
  --out "$PDIR/judge-r630.json" | tee -a "$D/logs/run.txt"
JRC=${PIPESTATUS[0]}
echo "$JRC" > "$D/judge.rc"
log "判据器 rc=$JRC"

BIN_SHA_AFTER=$(sha256sum "$BIN" | cut -d' ' -f1)
if [ "$BIN_SHA_BEFORE" = "$BIN_SHA_AFTER" ]; then
  echo "{\"bin_sha_stable\":true,\"sha\":\"$BIN_SHA_BEFORE\"}" > "$D/bin-sha-check.json"
else
  echo "{\"bin_sha_stable\":false,\"before\":\"$BIN_SHA_BEFORE\",\"after\":\"$BIN_SHA_AFTER\"}" > "$D/bin-sha-check.json"
  log "[致命] 运行期二进制被替换 ⇒ 臂身份不成立"
fi

# --- 5 铁律 11 前置器 -------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r630 --out "$D/precond-r630.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"; tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R630 完成 (judge_rc=$JRC)"
