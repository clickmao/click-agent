#!/usr/bin/env bash
# R560 驱动器: 剂量 3 **扩窗复跑** (n=3→6) —— 把 R559 的「执行面修复预算上限档 (3) 质量单臂 C2 达成」
# 从 3 窗升级为 6 窗稳定性读数 (AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR ∈ {0,3} 两枚本侧臂 + codex 真值)。
# 同一枚二进制 (R556 交付件 sha 320d0eb1…) ⇒ 单变量由构造保证; 同窗 3 臂, 6 新窗 (w107..w112)。
# 结构同 run_r559.sh (同输入硬门 + 起手闸 A/B + adapter + 逐窗判分 + 快照 + 铁律11 前置器) 骨架。
# 本轮差异 (逐条声明; 除下列 6 处外与 run_r559.sh **逐字节相同** —— 已用 token 映射回比 diff 空集机检):
#   ① 轮号命名空间 R559→R560 / r559→r560 (工作目录 /tmp/r560, 端口 49442);
#   ② 窗号 WIN0 104→107, NWIN 3→6 (6 新窗 w107..w112, 与 R559 的 w104..w106 **并列不相减**);
#   ③ 预注册机检 require 计数 9→18 (6 窗 × 3 臂全部进验收面);
#   ④ 头部注释随本轮目标刷新 (注释, 不影响行为);
#   ⑤ 单变量 = 唯一 env `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` ∈ {0,3}; 三臂共用同一二进制 sha 320d0eb1… (本文件钉死并机检)
# 用法: D=/tmp/r560 PORT=49442 WIN0=107 NWIN=6 bash eval/rover/r560/run_r560.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-/tmp/r560}
PORT=${PORT:-49442}
WIN0=${WIN0:-107}
NWIN=${NWIN:-6}
CMAXT=${CMAXT:-900}
AMAXT=${AMAXT:-900}
CFGSRC=/tmp/r455_env/agent/cfg
PDIR=$REPO/eval/rover/r560
TS=$PDIR/taskset-r560.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$PDIR/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-/tmp/pub_r556/agenthost/agenthost}
BIN_SHA=320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$PDIR/prereg-r560.json
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
assert d["round"] == "R560" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R560B0", "R560B3"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 18, d["evidence_scope"]["require"]
assert d["arms"]["R560B0"]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] == "0"
assert d["arms"]["R560B3"]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] == "3"
print("[先写后跑闸] prereg ok: arms=%s require=%d dose=%s" % (
    sorted(d["arms"]), len(d["evidence_scope"]["require"]),
    [d["arms"][k]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] for k in ("R560B0","R560B3")]))
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { echo "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
[ "$(sha256sum "$BIN" | cut -d' ' -f1)" = "$BIN_SHA" ] || { echo "[致命] 二进制 sha 不符 R556 交付件 ⇒ 臂身份不成立"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { echo "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R560 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r560.json" <<'PY'
import hashlib, io, json, os, sys
def h(p):
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
pre = json.load(io.open(sys.argv[3], encoding="utf-8"))
rep = {"note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 本轮四臂共用同一枚二进制 ⇒ 单变量 = env 开关。",
       "bin_all_arms": h(sys.argv[1]), "codex": h(sys.argv[2]),
       "arm_env": {k: pre["arms"][k].get("env") for k in ("R560B0", "R560B3")}}
json.dump(rep, io.open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[钉死] bin=%s arm_env=%s" % (rep["bin_all_arms"]["sha256"][:16], rep["arm_env"]))
PY
cp -r "$CFGSRC"/. "$D/agent-cfg"/
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
export DOTNET_ROOT="$HOME/.dotnet"

cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done; rm -f "$REPO/.git/ROUND_CLAIM"; return 0; }
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

# --- 2 起手闸 A (连续 2 次) + B (独立执行路径禁泄漏) ------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R560 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 rc=$lrc"; exit 2; }

# --- 3 adapter (四臂同一会话) ----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪"; exit 2; }
log "adapter 就绪 port=$PORT (w$WIN0..w$((WIN0+NWIN-1)); 每窗 = codex + B0(exec=0) + B3(exec=3))"

# --- 4 逐窗: [codex C1] + [B0] + [B1] + [B2] -------------------------------
run_agent(){
  local arm=$1 win=$2 sub=$3 dose=$4
  local t0 t1
  mkdir -p "$D/$win/$sub/g1/work"
  t0=$(dmax agent)
  env "AGENTFRAMEWORK_WORKSPACE=$D/$win/$sub/g1/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=$dose" \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$win/$sub/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$arm-$win" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout "$AMAXT" "$BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
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
  read -r a00 a01 < <(run_agent R560B0 "$W" agentB0 0)
  read -r a20 a21 < <(run_agent R560B3 "$W" agentB3 3)
  WEND=$(date +%s)
  for sub in codex agentB0 agentB3; do
    ( cd "$D/$W/$sub/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/$W/$sub/g1/cases.txt" 2>&1
  done
  rm -rf "$PDIR/snapshots/$W"
  mkdir -p "$PDIR/snapshots/$W/C1/g1" "$PDIR/snapshots/$W/R560B0/g1" "$PDIR/snapshots/$W/R560B3/g1"
  cp -a "$D/$W/codex/g1/work/." "$PDIR/snapshots/$W/C1/g1/"
  cp -a "$D/$W/agentB0/g1/work/." "$PDIR/snapshots/$W/R560B0/g1/"
  cp -a "$D/$W/agentB3/g1/work/." "$PDIR/snapshots/$W/R560B3/g1/"
  python3 "$PDIR/ingest_r560.py" --D "$D" --W "$W" --pd "$PDIR" \
      --codex-range "$c0,$c1" --b0-range "$a00,$a01" --b3-range "$a20,$a21" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"b0_rc\":$(cat "$D/$W/agentB0/g1/cli_rc.txt"),\"b3_rc\":$(cat "$D/$W/agentB3/g1/cli_rc.txt"),\"ranges\":{\"codex\":[$c0,$c1],\"b0\":[$a00,$a01],\"b3\":[$a20,$a21]}}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/kpi_r560.py" --D "$D" --out "$PDIR/kpi-table-r560.json" | tee -a "$D/logs/run.txt"

# --- 5 铁律 11 前置器 (独立重跑隐藏 58 用例) --------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r560 --out "$D/precond-r560.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R560 完成"
