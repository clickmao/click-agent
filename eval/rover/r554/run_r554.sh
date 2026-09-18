#!/usr/bin/env bash
# R554 驱动器 (仓内可复现件): 主线补齐 —— 外部真值 codex-cli 与 R1 臂**同窗**对照。
#   · 结构复用 run_r552.sh (同输入硬门 + 起手闸 A/B + adapter + 逐窗判分 + 快照) 骨架;
#   · 唯一功能差: 每窗先跑 **外部真值臂**(codex, 经同一 adapter) 再跑本侧臂 ⇒ 同窗同会话;
#     两臂计量按 adapter dump **索引区段**归属 (禁跨轮相减); 每臂产物树各存一份仓内快照。
#   · 产品源码零改动; AOT 件 sha 钉死 (单变量 = 同窗性)。
# 用法: D=/tmp/r554 PORT=49311 WIN0=1 NWIN=3 bash eval/rover/r554/run_r554.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-/tmp/r554}
PORT=${PORT:-49311}
WIN0=${WIN0:-1}
NWIN=${NWIN:-3}
TAG=${TAG:-R554}
CMAXT=${CMAXT:-900}
AMAXT=${AMAXT:-900}
CFGSRC=/tmp/r455_env/agent/cfg
PDIR=$REPO/eval/rover/r554
TS=$PDIR/taskset-r554.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$PDIR/cases/run_cases_r521.py
SIDE=$REPO/eval/rover/r540/proj_run_side_r540.py
CODEX_BIN=$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex
AGENT_BIN=${AGENT_BIN:-/tmp/pub_r551/agenthost}
BIN_SHA_EXP=e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$PDIR/prereg-r554.json
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
assert d["round"] == "R554" and d["written_before_run"] is True, d.get("round")
assert set(d["arms"]) == {"C1", "R554"}, sorted(d["arms"])
assert len(d["evidence_scope"]["require"]) == 6, d["evidence_scope"]["require"]
print("[先写后跑闸] prereg ok: arms=%s require=%d" % (sorted(d["arms"]), len(d["evidence_scope"]["require"])))
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex 可执行 $CODEX_BIN"; exit 3; }
[ "$(sha256sum "$AGENT_BIN" | cut -d' ' -f1)" = "$BIN_SHA_EXP" ] || { echo "[致命] AOT sha 不符(单变量要求逐位同)"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] && [ -f "$SIDE" ] || { echo "[致命] 缺题集/role/用例脚本/侧跑器"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM"; exit 4; }
echo "R554 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
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
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=${MAXEXEC:-1}
export AGENTFRAMEWORK_R1_MAX_REPAIR=${MAXREP:-1}
unset AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR   # 候选②: 剂量轴停用
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

# --- 2 起手闸 A: 机器空闲 (连续 2 次; 未过 ⇒ 沉降后同参重试, 不换窗号) -------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R554 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2b 起手闸 B: 独立执行路径禁泄漏孤儿执行体 -------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; tail -3 "$D/logs/leak-selfcheck.txt"
log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 rc=$lrc"; exit 2; }

# --- 3 adapter (两侧**同一**会话) ------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "adapter 就绪 port=$PORT (两侧同会话; 窗 $WIN0..$((WIN0+NWIN-1)))" || { log "[致命] adapter 未就绪"; exit 3; }

# --- 4 窗口: 每窗 = [外部真值 codex] + [本侧 R1] -----------------------------
for i in $(seq "$WIN0" $((WIN0 + NWIN - 1))); do
  W=w$i
  mkdir -p "$D/$W/codex/g1/work" "$D/$W/agent/g1/work"
  WSTART=$(date +%s)
  c0=$(dmax codex)
  python3 "$SIDE" --side codex --arm C1 --taskset "$TS" --tasks g1 \
      --out "$D/$W/codex" --adapter-dir "$D/adapter" --adapter-port "$PORT" \
      --codex-bin "$CODEX_BIN" --model deepseek-flash --timeout "$CMAXT" \
      > "$D/$W/codex/side.log" 2>&1
  echo "$?" > "$D/$W/codex/rc.txt"
  c1=$(dmax codex)
  a0=$(dmax agent)
  env "AGENTFRAMEWORK_WORKSPACE=$D/$W/agent/g1/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/$W/agent/g1/transcript.json" "AGENTFRAMEWORK_R1_TAG=$TAG-$i" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout "$AMAXT" "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
        --session-id "$TAG-$i" > "$D/$W/agent/g1/reply.txt" 2> "$D/$W/agent/g1/stderr.txt"
  echo "$?" > "$D/$W/agent/g1/cli_rc.txt"
  a1=$(dmax agent)
  WEND=$(date +%s)
  ( cd "$D/$W/codex/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/$W/codex/g1/cases.txt" 2>&1
  ( cd "$D/$W/agent/g1/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/$W/agent/g1/cases.txt" 2>&1
  # 4b 仓内快照 (两臂各一份; 前置器只吃快照, 不吃活目录)
  rm -rf "$PDIR/snapshots/$W"; mkdir -p "$PDIR/snapshots/$W/codex/g1" "$PDIR/snapshots/$W/agent$TAG/g1"
  cp -a "$D/$W/codex/g1/work/." "$PDIR/snapshots/$W/codex/g1/"
  cp -a "$D/$W/agent/g1/work/." "$PDIR/snapshots/$W/agent$TAG/g1/"
  python3 "$PDIR/ingest_r554.py" --D "$D" --W "$W" --pd "$PDIR" --tag "$TAG" \
      --codex-range "$c0,$c1" --agent-range "$a0,$a1" | tee -a "$D/logs/run.txt"
  echo "{\"win\":\"$W\",\"secs\":$((WEND-WSTART)),\"codex_rc\":$(cat "$D/$W/codex/rc.txt"),\"agent_rc\":$(cat "$D/$W/agent/g1/cli_rc.txt"),\"codex_dumps\":[$c0,$c1],\"agent_dumps\":[$a0,$a1]}" >> "$D/logs/windows.jsonl"
done

# --- 5 铁律 11 前置器 (独立重跑隐藏 58 用例) ---------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r554 --json "$D/precond-r554.json" \
  > "$D/logs/precond.txt" 2>&1
prc=$?
log "铁律 11 前置器: rc=$prc"
tail -6 "$D/logs/precond.txt"
echo "$prc" > "$D/precond.rc"
log "R554 完成"
