#!/usr/bin/env bash
# R552 驱动器 (仓内可复现件): 单变量 = 既有开关 AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR ∈ {unset(0=关), 1, 2}（剂量面）
#   —— **同一 AOT 二进制**（sha 钉死）⇒ 无源码改动、无重发布；SELFCHECK=1 三臂恒开。
#
# 结构复用 R551 驱动器 (run_r551.sh) 的「同输入硬门 + 起手闸 + adapter + 逐窗判分 + 快照」骨架;
# 本轮新增的只有: ① 第 0 步**先写后跑闸**（prereg-r552.json 必须已落盘，否则 fail-closed）
#                ② 逐窗**上游退化 fail-closed 闸**（R551 候选③：把事后人工判的
#                   「dump response.text 不可解析率 >0.25 ⇒ 该窗 VOID」做成逐窗机检；只改器具）。
#
# 用法: (a) MAXPROBE=0 D=/tmp/r552_b0 PORT=49041 WIN0=20 bash eval/rover/r552/run_r552.sh
#       (b) MAXPROBE=1 D=/tmp/r552_b1 PORT=49051 WIN0=23 bash eval/rover/r552/run_r552.sh
#       (c) MAXPROBE=2 D=/tmp/r552_b2 PORT=49061 WIN0=26 bash eval/rover/r552/run_r552.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
SELFCHECK=${SELFCHECK:-1}
MAXPROBE=${MAXPROBE:-0}
D=${D:-/tmp/r552_b0}
PORT=${PORT:-49041}
WIN0=${WIN0:-20}
NWIN=${NWIN:-3}
TAG=${TAG:-R552b$MAXPROBE}
CFGSRC=/tmp/r455_env/agent/cfg
TS=$REPO/eval/rover/r552/taskset-r552.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$REPO/eval/rover/r552/cases/run_cases_r521.py
AGENT_BIN=${AGENT_BIN:-/tmp/pub_r551/agenthost}
BIN_SHA_EXP=e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=${PREREG:-$REPO/eval/rover/r552/prereg-r552.json}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
mkdir -p "$D"/{adapter,logs,agent-cfg}
# 0a 先写后跑闸: 预注册必须**早于任何起臂**落盘，且声明了本轮轴与臂
[ -f "$PREREG" ] || { echo "[致命] 缺预注册 $PREREG (先写后跑闸)"; exit 3; }
python3 - "$PREREG" "$MAXPROBE" <<'PY' || { echo "[致命] 预注册机检不过"; exit 3; }
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
arm = "b%s" % sys.argv[2]
assert d["round"] == "R552" and d["written_before_run"] is True, d["round"]
assert arm in d["arms"], sorted(d["arms"])
print("[先写后跑闸] prereg ok: arm=%s windows=%s" % (arm, d["arms"][arm]["windows"]))
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺 AOT $AGENT_BIN"; exit 3; }
[ "$(sha256sum "$AGENT_BIN" | cut -d' ' -f1)" = "$BIN_SHA_EXP" ] || { echo "[致命] 二进制 sha 不符(单变量要求逐位同)"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$TS" ] && [ -f "$ROLE" ] && [ -f "$SC" ] || { echo "[致命] 缺题集/role/用例脚本"; exit 3; }
[ -e "$REPO/.git/ROUND_CLAIM" ] && { echo "[致命] 已有 ROUND_CLAIM"; exit 4; }
echo "R552 b$MAXPROBE $D $(date -Is)" > "$REPO/.git/ROUND_CLAIM"
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
# R552 单变量: 探针证据回灌的独立预算剂量 (0=关 / 1 / 2)
if [ "$MAXPROBE" = "0" ]; then unset AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR; else export AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR=$MAXPROBE; fi
export AGENTFRAMEWORK_R1_MAX_REPAIR=${MAXREP:-1}
SESS=${SESS:-r552-b$MAXPROBE}
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

# --- 2 起手闸 A: 机器空闲 (连续 2 次) --------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R552 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2b 起手闸 B: 独立执行路径**禁泄漏孤儿执行体** ---------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?
tail -4 "$D/logs/leak-selfcheck.txt"
log "起手闸 B (leak-selfcheck): rc=$lrc $(python3 -c "import json;d=json.load(open('$D/leak-selfcheck.json'));print('LEAK_SELFCHECK_OK=%s'%d['results']['LEAK_SELFCHECK_OK'])" 2>/dev/null)"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过 (leak-selfcheck rc=$lrc) ⇒ 不起臂"; exit 2; }

# --- 3 adapter --------------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "adapter 就绪 port=$PORT (selfcheck=$SELFCHECK maxprobe=$MAXPROBE, 窗 $WIN0..$((WIN0+NWIN-1)))" || { log "[致命] adapter 未就绪"; exit 3; }

# --- 4 窗口 ----------------------------------------------------------------
for i in $(seq "$WIN0" $((WIN0 + NWIN - 1))); do
  mkdir -p "$D/r1_$i/work"
  WSTART=$(date +%s)
  env "AGENTFRAMEWORK_WORKSPACE=$D/r1_$i/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/r1_$i/transcript.json" "AGENTFRAMEWORK_R1_TAG=$TAG-$i" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout 900 "$AGENT_BIN" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
        --session-id "$SESS-$i" > "$D/r1_$i/reply.txt" 2> "$D/r1_$i/stderr.txt"
  echo "$?"> "$D/r1_$i/cli_rc.txt"
  WEND=$(date +%s)
  ( cd "$D/r1_$i/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/r1_$i/cases.txt" 2>&1
  # 4b 逐窗上游退化 fail-closed 闸 (候选③, 只改器具; R551 为事后人工判)
  python3 - "$D" "$i" "$WSTART" "$WEND" <<'PY'
import io, json, os, sys, glob
D, i, ws, we = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
ok = bad = 0; det = []
for f in sorted(glob.glob(os.path.join(D, "adapter", "side-agent-*.json"))):
    if os.path.getmtime(f) < ws - 2: continue
    try: d = json.load(io.open(f, encoding="utf-8-sig"))
    except Exception: continue
    t = (d.get("response") or {}).get("text") or ""
    try:
        json.loads(t); ok += 1
    except Exception as e:
        bad += 1; det.append({"file": os.path.basename(f), "len": len(t), "err": str(e)[:60]})
tot = ok + bad; rate = (bad / tot) if tot else 0.0
res = {"win": i, "secs": we - ws, "dumps_in_window": tot, "parseable": ok, "unparseable": bad,
       "rate": round(rate, 4), "void_upstream": bool(tot > 0 and rate > 0.25), "detail": det,
       "rule": "response.text 不可解析率 >0.25 ⇒ 该窗 VOID（R551 事后人工判的机件化）"}
json.dump(res, io.open(os.path.join(D, "voidchk-%d.json" % i), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("  [上游闸] 窗%d dumps=%d 不可解析=%d rate=%.3f void_upstream=%s" % (i, tot, bad, rate, res["void_upstream"]))
PY
  log "窗$i cli_rc=$(cat "$D/r1_$i/cli_rc.txt") $(tail -1 "$D/r1_$i/cases.txt")"
done

# --- 5 判分汇总 (含 VOID 判定: 契约面/空产物/上游退化 三类不冒充能力读数) ----
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
    uc = {}
    vp = os.path.join(D, "voidchk-%d.json" % i)
    if os.path.exists(vp):
        uc = json.load(io.open(vp, encoding="utf-8"))
    nf = sum(len(f) for _, _, f in os.walk(os.path.join(b, "work"))) if os.path.isdir(os.path.join(b, "work")) else 0
    # VOID: 契约面不过 / 空产物 / 上游退化 ⇒ 该窗对能力命题无信息量
    void = bool(trc == 4 or tot == 0 or nf == 0 or uc.get("void_upstream"))
    rows.append({"win": i, "pass": pas, "total": tot, "fails": fails, "void": void,
                 "void_reason": ("rc=4" if trc == 4 else ("no_cases" if tot == 0 else ("no_work_files" if nf == 0 else ("upstream_degraded" if uc.get("void_upstream") else None)))),
                 "calls": t.get("calls"), "prompt": t.get("prompt_tokens"), "hit": t.get("cache_hit_tokens"),
                 "miss": t.get("cache_miss_tokens"), "completion": t.get("completion_tokens"),
                 "rc": trc, "stage": stage, "probe_total": t.get("public_probe_total"),
                 "probe_failed": t.get("public_probe_failed"), "probe_ran": t.get("public_probe_ran"),
                 "exec_repairs": t.get("exec_repairs"), "prefix_chars": t.get("prefix_chars"),
                 "probe_repairs": t.get("probe_repairs"), "probe_repair_budget": t.get("probe_repair_budget"),
                 "upstream_parse": uc, "work_files": nf})
valid = [r for r in rows if not r["void"]]
json.dump({"tag": TAG, "selfcheck": SC_, "maxprobe": TAG.replace("R552b", ""), "rows": rows,
           "valid_windows": [r["win"] for r in valid], "void_windows": [r["win"] for r in rows if r["void"]],
           "median_pass": sorted(r["pass"] for r in valid)[len(valid) // 2] if valid else None,
           "range": (max(r["pass"] for r in valid) - min(r["pass"] for r in valid)) if valid else None},
          io.open(os.path.join(D, "summary-%s-%s.json" % (TAG, W0)), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print("  窗%-3d %s %-9s 调用=%-4s prompt=%-7s comp=%-6s rc=%-3s stage=%-26s probe=%s/%s probe_repairs=%s" % (
        r["win"], "%d/%d" % (r["pass"], r["total"]), "VOID(%s)" % r["void_reason"] if r["void"] else "", r["calls"],
        r["prompt"], r["completion"], r["rc"], r["stage"], r["probe_failed"], r["probe_total"], r["probe_repairs"]))
print("  有效窗 %s | 中位 %s | 极差 %s" % ([r["win"] for r in valid], sorted(r["pass"] for r in valid)[len(valid) // 2] if valid else None,
                                     (max(r["pass"] for r in valid) - min(r["pass"] for r in valid)) if valid else None))
PY
log "臂 b$MAXPROBE 完成: $(python3 -c "import json;d=json.load(open('$D/summary-$TAG-$WIN0.json'));print('有效窗',d['valid_windows'],'中位',d['median_pass'],'极差',d['range'])" 2>/dev/null)"
