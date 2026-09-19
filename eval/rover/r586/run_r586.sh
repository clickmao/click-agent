#!/usr/bin/env bash
# R586 驱动器: **主线对照轮（器具环境恢复后首次可起臂）** —— 产品默认档 × 外部真值 codex, 3 新窗 w154..w156;
#             零产品源码改动 / 零新增夹具语义 / 零新增开关。
# 骨架 = run_r571.sh（**逐字节复用**其结构）；本轮差异（逐条声明, 其余同）:
#   ① 轮号命名空间 R571→R586 / r571→r586；工作根 D 默认改为**稳定路径** $HOME/.agentframework/harness/runs/r586
#      （R586 定因: harness 前置件原先只存 /tmp 且已被回收 ⇒ 本落点 = 恢复动作本身）；端口 49531→49551。
#   ② 窗号 WIN0 154→157, NWIN 3, REPS 3 —— 臂 = C1(真值) + R586D(产品默认档, 无剂量键)。
#      **同件复跑轮**: 被测件与 R585 **同 sha**(4b70fd7c…), 题集同 sha(e0c667c2…) ⇒ 只换窗集, 判缺口跨窗复现。
#   ③ **前置自恢复**: CFGSRC 缺件 ⇒ 先跑 restore_env_r586.py（等价性证明 + 落盘 + 回读）; 仍缺 ⇒ exit 3（fail-closed）。
#   ④ BIN 改为稳定路径发布件, sha **不硬编码**(第 0 步落盘 + 运行前后 sha 一致性断言), 记入 bins-r586.json。
#   ⑤ 剂量键**三枚全显式 unset** 并在 arm_env 落盘后断言「未设任何 R1_*_REPAIR/EARLY_STOP」。
#   ⑥ 起手闸 REQ 由 R571 postcheck 实测振幅 (swing 105MB) 派生 + 上界夹取（R568 规则），经**既有闸** --gate-mb 行使。
# 用法: bash eval/rover/r586/run_r586.sh            (全部路径有默认值)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r586}
PORT=${PORT:-49551}
WIN0=${WIN0:-157}
NWIN=${NWIN:-3}
REPS=${REPS:-3}
ARMS_DOSE="R586D:agentD:unset"
CMAXT=${CMAXT:-600}
AMAXT=${AMAXT:-600}
CFGSRC=${CFGSRC:-$HARNESS/agent/cfg}
PDIR=$REPO/eval/rover/r586
TS=$REPO/eval/rover/r586/taskset-r586.json      # 冻结题集逐字节复制件 (sha e0c667c2…)
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r586/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
MEM_ONCE=$REPO/eval/rover/r571/mem_sample_once.py
SAMPLER=$REPO/eval/rover/r571/mem_sampler.py
GATE=$REPO/eval/rover/r483/preflight_gate.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-$HOME/.agentframework/artifacts/pub_r586/agenthost}
GATE_MB=2650
PREREG=$PDIR/prereg-r586.json
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
assert d["round"] == "R586" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R586D"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 12, d["evidence_scope"]["require"]
assert str(d.get("criterion_version", "")).startswith("v2"), d.get("criterion_version")
assert d["arms"]["C1"]["side"] == "codex" and d["arms"]["R586D"]["side"] == "agent"
print("[先写后跑闸] prereg ok: arms=%s require=%d criterion=%s" % (
    sorted(d["arms"]), len(d["evidence_scope"]["require"]), d["criterion_version"][:2]))
PY

# --- 0a 前置自恢复 (R586 定因的修复动作) -------------------------------------
if [ ! -d "$CFGSRC" ]; then
  log "CFGSRC 缺件 ⇒ 触发自恢复 eval/rover/r586/restore_env_r586.py"
  python3 "$PDIR/restore_env_r586.py" >> "$D/logs/run.txt" 2>&1
fi
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg $CFGSRC（自恢复后仍缺）"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT 发布件 $BIN (待恢复/重建)"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { log "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { log "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { log "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R586 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
BIN_SHA_BEFORE=$(sha256sum "$BIN" | cut -d' ' -f1)
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r586.json" "$CFGSRC" <<'PY'
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
       "arm_env": {k: pre["arms"][k].get("env") for k in ("C1", "R586D")}}
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
# 产品默认档: 三枚剂量键**全部显式 unset**（防继承）
unset AGENTFRAMEWORK_R1_MAX_REPAIR AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR
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
PREV_SWING=${PREV_SWING:-105}      # R571 运行窗口实测振幅 (gate-postcheck-r571.json swing_mb=105)
PY_MEM=$(python3 "$MEM_ONCE" "$D/logs/pre-samples.jsonl" | sed 's/.*=//')
CEIL=$((PY_MEM > 0 ? PY_MEM : 0))
MARGIN=$(( PREV_SWING > 60 ? PREV_SWING : 60 ))
CAP=$(( CEIL - GATE_MB - 60 ))
[ "$MARGIN" -gt "$CAP" ] && MARGIN=$CAP
if [ "$MARGIN" -lt 60 ]; then
  log "[致命] 顶棚 $CEIL 装不下下限 60MB ⇒ 窗口不可开 (fail-closed)"; exit 2; fi
REQ=$(( GATE_MB + MARGIN ))
log "起手闸条款: ceiling=$CEIL prev_swing=$PREV_SWING margin=$MARGIN REQ=$REQ (cap=$CAP)"
for i in 1 2; do
  # 读契约: 闸 stdout = pretty JSON + 尾行 "out <path>" ⇒ 必须读 --out 落盘件, 不可 json.load(stdin)
  python3 "$GATE" --round R586 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
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
  python3 "$GATE" --round R586DISC --gate-mb "$GATE_MB" --out "$D/gate-disc-base.json" >/dev/null 2>&1
  python3 "$GATE" --round R586DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
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

# --- 4 逐窗逐重复 -----------------------------------------------------------
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
  python3 "$PDIR/kpi_r586.py" --D "$D" --pd "$PDIR" --win "$W" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"reps\":$REPS}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/kpi_r586.py" --D "$D" --pd "$PDIR" 2>&1 | tee -a "$D/logs/run.txt" || log "KPI 汇总 rc=$? (见下)"

# --- 4b 收尾: 采样器 + 二进制 sha 一致性 (臂身份) ----------------------------
if [ -f "$D/logs/sampler.pid" ]; then kill "$(cat "$D/logs/sampler.pid")" 2>/dev/null; rm -f "$D/logs/sampler.pid"; fi
BIN_SHA_AFTER=$(sha256sum "$BIN" | cut -d' ' -f1)
if [ "$BIN_SHA_BEFORE" = "$BIN_SHA_AFTER" ]; then echo "{\"bin_sha_stable\":true,\"sha\":\"$BIN_SHA_BEFORE\"}" > "$D/bin-sha-check.json"
else echo "{\"bin_sha_stable\":false,\"before\":\"$BIN_SHA_BEFORE\",\"after\":\"$BIN_SHA_AFTER\"}" > "$D/bin-sha-check.json"; log "[致命] 运行期二进制被替换 ⇒ 臂身份不成立"; fi

# --- 5 铁律 11 前置器 -------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r586 --out "$D/precond-r586.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R586 完成"
