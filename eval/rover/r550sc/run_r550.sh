#!/usr/bin/env bash
# R550 驱动器 (仓内可复现件): 单变量 = 既有开关 AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {0,1}
#
# 结构复用 R547 驱动器 (run_r547.sh) 的**同输入硬门 + 起手闸 + adapter + 逐窗判分 + 快照** 骨架;
# 本轮新增的只有**起手闸第 3 条**: `exec_precondition.py --leak-selfcheck` (R549 遗留的孤儿执行体
# 仪器自检, 此前只在收口时手工跑 ⇒ R550 候选③ 把它做成起手闸, 未过即不起臂)。
#
# 用法: SELFCHECK=1 D=/tmp/r550s PORT=49013 WIN0=4 bash eval/rover/r550/run_r550.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
SELFCHECK=${SELFCHECK:-1}
D=${D:-/tmp/r550s}
PORT=${PORT:-49013}
WIN0=${WIN0:-4}
NWIN=${NWIN:-3}
TAG=${TAG:-R550$([ "$SELFCHECK" = "1" ] && echo on || echo off)}
CFGSRC=/tmp/r455_env/agent/cfg
TS=$REPO/eval/rover/r542/taskset-r542.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r542/cases/run_cases_r521.py
AGENT_BIN=${AGENT_BIN:-/tmp/pub_r548b/agenthost}
BIN_SHA_EXP=00d42dc1b68591188d489723b4dbea7a1ba572e034c87d820d3b12e6a141335e
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
mkdir -p "$D"/{adapter,logs,agent-cfg}
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺 AOT $AGENT_BIN"; exit 3; }
[ "$(sha256sum "$AGENT_BIN" | cut -d' ' -f1)" = "$BIN_SHA_EXP" ] || { echo "[致命] 二进制 sha 不符(单变量要求逐位同)"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] || { echo "[致命] 缺题集/role/用例脚本"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM"; exit 4; }
echo "R550 $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
cp -r "$CFGSRC"/. "$D/agent-cfg"/
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
export DOTNET_ROOT="$HOME/.dotnet"

cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done; rm -f "$REPO/.git/ROUND_CLAIM"; return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
if [ "$SELFCHECK" = "1" ]; then export AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1; else unset AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK; fi
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=${MAXEXEC:-1}
export AGENTFRAMEWORK_R1_MAX_REPAIR=${MAXREP:-1}
SESS=${SESS:-r550-$SELFCHECK}
cd "$REPO" || exit 3

# --- 1 同输入硬门 -----------------------------------------------------------
cp "$TS" "$D/taskset.json"
python3 - "$TS" "$D" "$PROMPT_SHA_EXP" > "$D/logs/input-pin.txt" 2>&1 <<'PY'
import hashlib, io, json, sys
ts, D, exp = sys.argv[1], sys.argv[2], sys.argv[3]
t = [x for x in json.load(io.open(ts, encoding="utf-8"))["tasks"] if x["tid"] == "g1"][0]
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
io.open(D + "/task-g1-prompt.txt", "w", encoding="utf-8").write(t["prompt"])
ok = (h == exp)
print("prompt_sha256 %s exp=%s ok=%s chars=%d hidden_cases=%s" % (h, exp, ok, len(t["prompt"]), t.get("hidden_cases")))
sys.exit(0 if ok else 3)
PY
rc=$?; cat "$D/logs/input-pin.txt"; [ "$rc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$rc"; exit 3; }

# --- 2 起手闸 A: 机器空闲 (连续 2 次) --------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R550 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2b 起手闸 B (R550 候选③): 独立执行路径**禁泄漏孤儿执行体** -------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?
tail -4 "$D/logs/leak-selfcheck.txt"
log "起手闸 B (leak-selfcheck): rc=$lrc $(python3 -c "import json;d=json.load(open('$D/leak-selfcheck.json'));print('LEAK_SELFCHECK_OK=%s'%d['results']['LEAK_SELFCHECK_OK'])" 2>/dev/null)"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 (leak-selfcheck rc=$lrc) ⇒ 不起臂"; exit 2; }

# --- 3 adapter --------------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "adapter 就绪 port=$PORT (selfcheck=$SELFCHECK, 窗 $WIN0..$((WIN0+NWIN-1)))" || { log "[致命] adapter 未就绪"; exit 3; }

# --- 4 窗口 ----------------------------------------------------------------
for i in $(seq "$WIN0" $((WIN0 + NWIN - 1))); do
  mkdir -p "$D/r1_$i/work"
  env "AGENTFRAMEWORK_WORKSPACE=$D/r1_$i/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/r1_$i/transcript.json" "AGENTFRAMEWORK_R1_TAG=$TAG-$i" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout 900 "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
        --session-id "$SESS-$i" > "$D/r1_$i/reply.txt" 2> "$D/r1_$i/stderr.txt"
  echo "$?" > "$D/r1_$i/cli_rc.txt"
  ( cd "$D/r1_$i/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/r1_$i/cases.txt" 2>&1
  log "窗$i cli_rc=$(cat "$D/r1_$i/cli_rc.txt") $(tail -1 "$D/r1_$i/cases.txt")"
done

# --- 5 判分汇总 (含 VOID 判定: 契约面/执行面无效窗不冒充能力读数) ------------
python3 - "$D" "$TAG" "$SELFCHECK" "$WIN0" "$NWIN" <<'PY'
import io, json, os, sys
D, TAG, SC_, W0, NW = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
rows = []
for i in range(W0, W0 + NW):
    b = os.path.join(D, "r1_%d" % i)
    cf, tp = os.path.join(b, "cases.txt"), os.path.join(b, "transcript.json")
    tot = pas = 0; fails = {}
    if os.path.exists(cf):
        L = io.open(cf, encoding="utf-8", errors="replace").read().splitlines()
        tot = sum(1 for x in L if x.startswith("CASE")); pas = sum(1 for x in L if x.startswith("CASE") and "PASS" in x)
        for x in L:
            if x.startswith("CASE") and "PASS" not in x:
                g = x.split()[1].split("#")[0]; fails[g] = fails.get(g, 0) + 1
    t = json.load(io.open(tp, encoding="utf-8")) if os.path.exists(tp) else {}
    stage, trc = t.get("stage"), t.get("rc")
    # VOID: 契约面不过 / 空产物 ⇒ 链没走到产物面, 该窗对能力命题无信息量
    void = bool(trc == 4 or tot == 0)
    rows.append({"win": i, "pass": pas, "total": tot, "fails": fails, "void": void,
                 "calls": t.get("calls"), "prompt": t.get("prompt_tokens"), "hit": t.get("cache_hit_tokens"),
                 "miss": t.get("cache_miss_tokens"), "completion": t.get("completion_tokens"),
                 "rc": trc, "stage": stage, "probe_total": t.get("public_probe_total"),
                 "probe_failed": t.get("public_probe_failed"), "probe_ran": t.get("public_probe_ran"),
                 "exec_repairs": t.get("exec_repairs"), "prefix_chars": t.get("prefix_chars")})
valid = [r for r in rows if not r["void"]]
json.dump({"tag": TAG, "selfcheck": SC_, "rows": rows,
           "valid_windows": [r["win"] for r in valid], "void_windows": [r["win"] for r in rows if r["void"]],
           "median_pass": sorted(r["pass"] for r in valid)[len(valid) // 2] if valid else None,
           "range": (max(r["pass"] for r in valid) - min(r["pass"] for r in valid)) if valid else None},
          io.open(os.path.join(D, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print("  窗%-3d %s %-7s 调用=%-4s prompt=%-7s comp=%-6s rc=%-3s stage=%-24s probe=%s/%s exec_repairs=%s" % (
        r["win"], "%d/%d" % (r["pass"], r["total"]), "VOID" if r["void"] else "", r["calls"], r["prompt"],
        r["completion"], r["rc"], r["stage"], (r["probe_total"] or 0) - (r["probe_failed"] or 0),
        r["probe_total"], r["exec_repairs"]))
print("有效窗=%s VOID窗=%s 中位=%s 极差=%s" % ([r["win"] for r in valid], [r["win"] for r in rows if r["void"]],
                                          sorted(r["pass"] for r in valid)[len(valid) // 2] if valid else None,
                                          (max(r["pass"] for r in valid) - min(r["pass"] for r in valid)) if valid else None))
PY
log "完成: $D"
