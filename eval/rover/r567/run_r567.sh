#!/usr/bin/env bash
# R567 驱动器: **同窗单变量对照轮** —— 既有开关 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 取值 **0 vs 3** × 外部真值 codex,
#             6 新窗 w131..w136; 起手闸振幅余量条款按上轮实测振幅派生行使; 候选④ 指纹/命中率双口径新窗复核
#             (候选④行使臂由 B0 换为 B3 —— R566 实测 B0 每窗恒 1 调用 ⇒ C4-3 敏感性不可判; 判据文本不变)。
# 同一枚二进制 (R556 交付件 sha 320d0eb1…) ⇒ 单变量由**构造**保证 (全臂除该开关取值外 env 逐项相同);
# 同窗 3 臂 (codex 真值 + R567B0 轴=0 + R567B3 轴=3), 6 新窗 (w131..w136; 与 w119..w124 / w125..w130 **并列不相减**)。
# 结构同 run_r566.sh 骨架; 本轮差异 (逐条声明, 其余逐字节相同):
#   ① 轮号命名空间 R566→R567 / r566→r567 (工作目录 /tmp/r567, 端口 49447);
#   ② 窗号 WIN0 125→131, NWIN 6 (w131..w136);
#   ③ 本侧臂 env 定义: **两臂剂量键都显式落盘** (R567B0 =0 / R567B3 =3) —— 单变量 = 该键的**取值**, 其余 env
#      (R1_CONTRACT / R1_MAX_REPAIR=1 / PUBLIC_SELFCHECK / ROLE_FILE / TRANSCRIPT / WORKSPACE / TAG) 逐项相同;
#   ④ 起手闸条款以 `--prev-postcheck` 指 **R566** 运行窗口实测振幅 (swing_mb=70) 派生 MARGIN=70 / REQ=2720;
#   ⑤ 判别力成对控制 (同内存态 2650 vs REQ 反判 + 400MB 占用负控) 与候选④ 指纹/口径恒等式落盘;
#   ⑥ 端口替换规则已覆盖窗口名/臂名/dose 取值并逐项机检 + RESIDUAL 机检 (R566 自捕的遗漏项族)。
# 用法: D=/tmp/r567 PORT=49447 WIN0=131 NWIN=6 bash eval/rover/r567/run_r567.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-/tmp/r567}
PORT=${PORT:-49447}
WIN0=${WIN0:-131}
NWIN=${NWIN:-6}
CMAXT=${CMAXT:-900}
AMAXT=${AMAXT:-900}
CFGSRC=/tmp/r455_env/agent/cfg
PDIR=$REPO/eval/rover/r567
TS=$REPO/eval/rover/r560/taskset-r560.json   # 冻结题集 (与 R559/R560 逐字节同件; 复用不复制)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r560/cases/run_cases_r521.py   # 冻结判分器 (sha a67215a7…, 与 matrix 的 ERRSHA 同源)
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-/tmp/pub_r556/agenthost/agenthost}
BIN_SHA=320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$PDIR/prereg-r567.json
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
assert d["round"] == "R567" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R567B0", "R567B3"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 18, d["evidence_scope"]["require"]
assert str(d.get("criterion_version", "")).startswith("v2"), d.get("criterion_version")
_doses = {a: {k: v for k, v in d["arms"][a]["env"].items() if "MAX_" in k or "EARLY_STOP" in k}
          for a in ("R567B0", "R567B3")}
assert set(_doses["R567B0"]) == {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"}, _doses
assert set(_doses["R567B3"]) == {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"}, _doses
assert int(_doses["R567B0"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 0, _doses
assert int(_doses["R567B3"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 3, _doses
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
echo "R567 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r567.json" <<'PY'
import hashlib, io, json, os, sys
def h(p):
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
pre = json.load(io.open(sys.argv[3], encoding="utf-8"))
rep = {"note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 全臂共用同一枚二进制 ⇒ 臂身份单变量由构造保证。",
       "bin_all_arms": h(sys.argv[1]), "codex": h(sys.argv[2]),
       "arm_env": {k: pre["arms"][k].get("env") for k in ("R567B0", "R567B3")}}
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
export AGENTFRAMEWORK_R1_MAX_REPAIR=1
unset AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR   # 探针轴停用 (R551-R553 已判无增益)
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
python3 "$PDIR/gate_margin_r567.py" --derive --samples "$D/logs/pre-samples.jsonl" \
    --prev-postcheck "$REPO/eval/rover/r566/gate-postcheck-r566.json" \
    --out "$PDIR/gate-margin-r567.json" --embed-selftest | tee -a "$D/logs/run.txt"
mrc=${PIPESTATUS[0]}
log "起手闸条款 (振幅余量): rc=$mrc"
[ "$mrc" -eq 0 ] || { log "[致命] 振幅余量条款未过 (rc=$mrc) ⇒ 不算窗口, 不起臂"; exit 2; }
REQ=$(python3 -c "import json;print(int(json.load(open('$PDIR/gate-margin-r567.json'))['required_mb']))")
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R567 --gate-mb "$REQ" --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R567DISC --gate-mb 2650 --out "$D/gate-disc-base2650.json" >/dev/null 2>&1
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R567DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
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
python3 "$PDIR/mem_sampler.py" "$D/logs/run-samples.jsonl" 5 > "$D/logs/sampler.log" 2>&1 &
echo "$!" > "$D/logs/sampler.pid"
echo "sampler pid=$(cat "$D/logs/sampler.pid")" >> "$D/logs/run.txt"

# --- 3 adapter (两臂同一会话) ----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪"; exit 2; }
log "adapter 就绪 port=$PORT (w$WIN0..w$((WIN0+NWIN-1)); 每窗 = codex 真值 + R567B0(轴=0) + R567B3(轴=3))"

# --- 4 逐窗: [codex C1 外部真值] + [R567B0 产品默认档] ----------------------
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  local t0 t1
  mkdir -p "$D/$win/$sub/g1/work"
  t0=$(dmax agent)
  local -a ENVS=("AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" "AGENTFRAMEWORK_R1_CONTRACT=1"
                 "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win"
                 "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE")
  [ "$dose" = "unset" ] || ENVS+=("AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=$dose")
  printf '%s\n' "${ENVS[@]}" > "$D/$win/$sub/g1/arm_env.txt"
  env "${ENVS[@]}" timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
      --session-id "$arm-$win" > "$D/$win/$sub/g1/reply.txt" 2> "$D/$win/$sub/g1/stderr.txt"
  echo "$? " > "$D/$win/$sub/g1/cli_rc.txt"
  t1=$(dmax agent)
  echo "$t0 $t1"
}
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
  read -r a00 a01 < <(run_agent R567B0 "$W" agentB0 0)
  read -r a10 a11 < <(run_agent R567B3 "$W" agentB3 3)
  WEND=$(date +%s)
  for sub in codex agentB0 agentB3; do
    ( cd "$D/$W/$sub/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/$W/$sub/g1/cases.txt" 2>&1
  done
  rm -rf "$PDIR/snapshots/$W"
  mkdir -p "$PDIR/snapshots/$W/C1/g1" "$PDIR/snapshots/$W/R567B0/g1" "$PDIR/snapshots/$W/R567B3/g1"
  cp -a "$D/$W/codex/g1/work/." "$PDIR/snapshots/$W/C1/g1/"
  cp -a "$D/$W/agentB0/g1/work/." "$PDIR/snapshots/$W/R567B0/g1/"
  cp -a "$D/$W/agentB3/g1/work/." "$PDIR/snapshots/$W/R567B3/g1/"
  python3 "$PDIR/ingest_r567.py" --D "$D" --W "$W" --pd "$PDIR" \
      --codex-range "$c0,$c1" --b0-range "$a00,$a01" --b3-range "$a10,$a11" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"b0_rc\":$(cat "$D/$W/agentB0/g1/cli_rc.txt"),\"b3_rc\":$(cat "$D/$W/agentB3/g1/cli_rc.txt"),\"ranges\":{\"codex\":[$c0,$c1],\"b0\":[$a00,$a01],\"b3\":[$a10,$a11]}}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/fingerprint_r567.py" --D "$D" --out "$PDIR/fingerprint-r567.json" | tee -a "$D/logs/run.txt"
frc=${PIPESTATUS[0]}; log "候选④ 指纹/口径恒等式: rc=$frc"
python3 "$PDIR/kpi_r567.py" --D "$D" --out "$PDIR/kpi-table-r567.json" | tee -a "$D/logs/run.txt"

# --- 4b 运行中采样收尾: 基础门槛是否被击穿 + 观测振幅 (供下轮派生) ----------
if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
python3 "$PDIR/gate_margin_r567.py" --postcheck --samples "$D/logs/run-samples.jsonl" \
    --out "$PDIR/gate-postcheck-r567.json" | tee -a "$D/logs/run.txt"
log "起手闸条款 postcheck rc=$?" 

# --- 5 铁律 11 前置器 (独立重跑隐藏 58 用例) --------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r567 --out "$D/precond-r567.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R567 完成"
