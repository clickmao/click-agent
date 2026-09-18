#!/usr/bin/env bash
# R559 驱动器: 执行面修复预算轴**最后一档剂量 (3)** 补扫 (AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR ∈ {0,3}),
# 同一枚二进制 (R556 交付件) ⇒ 单变量由构造保证; 同窗 3 臂 = codex 真值 + B0(0) + B3(3), 3 新窗 (w104..w106)。
# 结构同 run_r557.sh (同输入硬门 + 起手闸 A/B + adapter + 逐窗判分 + 快照 + 铁律11 前置器) 骨架。
# 本轮差异 (逐条声明):
#   ① **单变量 = 唯一 env** `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR`; 四臂共用同一二进制 sha 320d0eb1… (本文件钉死并机检)
#      ⇒ 无 AOT 重发布 (零产品源码改动), 无新增夹具, 无新开关;
#   ② 每窗 = [codex C1] + [B0 exec=0] + [B3 exec=3];
#   ③ 计量按 adapter dump **索引区段**归属 (R555 已证 transcript.calls 漏记续写调用) + 逐臂对照 transcript.calls (账差登记);
#   ④ 主判据读数 = cases_pass + transcript.exec_repairs/public_probe_* (剂量是否被行使)。
# 用法: D=/tmp/r559 PORT=49441 WIN0=104 NWIN=3 bash eval/rover/r559/run_r559.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-/tmp/r559}
PORT=${PORT:-49441}
WIN0=${WIN0:-104}
NWIN=${NWIN:-3}
CMAXT=${CMAXT:-900}
AMAXT=${AMAXT:-900}
CFGSRC=/tmp/r455_env/agent/cfg
PDIR=$REPO/eval/rover/r559
TS=$PDIR/taskset-r559.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$PDIR/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
BIN=${BIN:-/tmp/pub_r556/agenthost/agenthost}
BIN_SHA=320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$PDIR/prereg-r559.json
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
assert d["round"] == "R559" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R559B0", "R559B3"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 9, d["evidence_scope"]["require"]
assert d["arms"]["R559B0"]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] == "0"
assert d["arms"]["R559B3"]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] == "3"
print("[先写后跑闸] prereg ok: arms=%s require=%d dose=%s" % (
    sorted(d["arms"]), len(d["evidence_scope"]["require"]),
    [d["arms"][k]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"] for k in ("R559B0","R559B3")]))
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { echo "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
[ "$(sha256sum "$BIN" | cut -d' ' -f1)" = "$BIN_SHA" ] || { echo "[致命] 二进制 sha 不符 R556 交付件 ⇒ 臂身份不成立"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { echo "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM: $(cat "$REPO/.git/ROUND_CLAIM")"; exit 4; }
echo "R559 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
python3 - "$BIN" "$CODEX_BIN" "$PREREG" "$PDIR/bins-r559.json" <<'PY'
import hashlib, io, json, os, sys
def h(p):
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
pre = json.load(io.open(sys.argv[3], encoding="utf-8"))
rep = {"note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 本轮四臂共用同一枚二进制 ⇒ 单变量 = env 开关。",
       "bin_all_arms": h(sys.argv[1]), "codex": h(sys.argv[2]),
       "arm_env": {k: pre["arms"][k].get("env") for k in ("R559B0", "R559B3")}}
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
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R559 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
  read -r a00 a01 < <(run_agent R559B0 "$W" agentB0 0)
  read -r a20 a21 < <(run_agent R559B3 "$W" agentB3 3)
  WEND=$(date +%s)
  for sub in codex agentB0 agentB3; do
    ( cd "$D/$W/$sub/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/$W/$sub/g1/cases.txt" 2>&1
  done
  rm -rf "$PDIR/snapshots/$W"
  mkdir -p "$PDIR/snapshots/$W/C1/g1" "$PDIR/snapshots/$W/R559B0/g1" "$PDIR/snapshots/$W/R559B3/g1"
  cp -a "$D/$W/codex/g1/work/." "$PDIR/snapshots/$W/C1/g1/"
  cp -a "$D/$W/agentB0/g1/work/." "$PDIR/snapshots/$W/R559B0/g1/"
  cp -a "$D/$W/agentB3/g1/work/." "$PDIR/snapshots/$W/R559B3/g1/"
  python3 "$PDIR/ingest_r559.py" --D "$D" --W "$W" --pd "$PDIR" \
      --codex-range "$c0,$c1" --b0-range "$a00,$a01" --b3-range "$a20,$a21" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":\"$(cat "$D/$W/codex/rc.txt")\",\"b0_rc\":$(cat "$D/$W/agentB0/g1/cli_rc.txt"),\"b3_rc\":$(cat "$D/$W/agentB3/g1/cli_rc.txt"),\"ranges\":{\"codex\":[$c0,$c1],\"b0\":[$a00,$a01],\"b3\":[$a20,$a21]}}" >> "$D/logs/windows.jsonl"
  sleep 2
done

python3 "$PDIR/kpi_r559.py" --D "$D" --out "$PDIR/kpi-table-r559.json" | tee -a "$D/logs/run.txt"

# --- 5 铁律 11 前置器 (独立重跑隐藏 58 用例) --------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r559 --out "$D/precond-r559.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -10 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R559 完成"
