#!/usr/bin/env bash
# R555 驱动器 —— 契约轴单变量 (契约 v1 vs v2 加厚), 同题面/夹具/role/预算, 同轮内两臂各 3 独立窗。
# 结构复用 R553 驱动器骨架 (先写后跑闸 → 同输入硬门 → 起手闸 A/B → adapter → 逐窗 → 汇总)。
# 本轮差异 (逐条声明):
#   ① 起手闸 C **判废** (依 R553 §4: 真阳 0/假阴 7 ⇒ 零判别力) ⇒ 本驱动器不含该闸;
#      口径变更: 每窗少 1 次契约面调用 ⇒ 与 R553 的调用数**不可相减**。
#   ② 两臂 = 同一题面/夹具/role/预算, 唯一差 = 契约版本 (prefix_chars 15119 vs 15291, +172 字节)。
#   ③ 剂量面/早停轴/探针修复轴: R551-R553 已判无增益 ⇒ 本轮不再重跑 (MAX_PROBE_REPAIR 保持 unset)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r555
D=${D:-/tmp/r555}
PORT=${PORT:-49501}
CFGSRC=/tmp/r455_env/agent/cfg
TS=$R/taskset-r555.json
ROLE=$REPO/eval/rover/r542/role-r542.txt
SC=$R/cases/run_cases_r521.py
BIN_V1=/tmp/pub_r551/agenthost
BIN_V1_SHA=e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b
BIN_V2=/tmp/pub_r555/agenthost
PROMPT_SHA_EXP=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
PREREG=$R/prereg-r555.json
mkdir -p "$D"/{adapter,logs,agent-cfg}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) ---------------------------------------------------
[ -f "$PREREG" ] || { echo "[致命] 缺预注册 $PREREG"; exit 3; }
python3 - "$PREREG" <<'PY' || { echo "[致命] 预注册机检不过"; exit 3; }
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
assert d["round"] == "R555" and d["written_before_run"] is True
assert set(d["arms"]) == {"A0", "A1"}, sorted(d["arms"])
assert d["arms"]["A0"]["windows"] == [83, 84, 85] and d["arms"]["A1"]["windows"] == [80, 81, 82]
assert d["axes"] if "axes" in d else d["axis"]
print("[先写后跑闸] prereg ok: arms=A0(83-85) A1(80-82)")
PY
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg"; exit 3; }
[ -x "$BIN_V1" ] && [ -x "$BIN_V2" ] || { echo "[致命] 缺 AOT 件"; exit 3; }
[ "$(sha256sum "$BIN_V1" | cut -d' ' -f1)" = "$BIN_V1_SHA" ] || { echo "[致命] v1 二进制 sha 不符"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占"; exit 4; }
grep -q R555 "$REPO/.git/ROUND_CLAIM" 2>/dev/null || { echo "[致命] ROUND_CLAIM 非本作业"; exit 4; }
cp -r "$CFGSRC"/. "$D/agent-cfg"/
grep -rl '486[0-9][0-9]' "$D/agent-cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent-cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
cleanup(){ for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done; return 0; }
trap cleanup EXIT
export AGENTFRAMEWORK_CONFIG="$D/agent-cfg"
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
export AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1
export AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR=1
export AGENTFRAMEWORK_R1_MAX_REPAIR=1
unset AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR
cd "$REPO" || exit 3

# --- 1 同输入硬门 ----------------------------------------------------------
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
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R555 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
lrc=$?; log "起手闸 B (leak-selfcheck): rc=$lrc"
[ "$lrc" -eq 0 ] || { log "[致命] 起手闸 B 未过"; exit 2; }

# --- 3 adapter -------------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
for k in $(seq 1 40); do ss -ltn 2>/dev/null | grep -q ":$PORT " && break; sleep 1; done
ss -ltn 2>/dev/null | grep -q ":$PORT " || { log "[致命] adapter 未就绪"; exit 2; }
log "adapter 就绪 port=$PORT (两臂各 3 窗, 起手闸 C 已判废 ⇒ 不含该闸)"

# --- 4 逐窗 ----------------------------------------------------------------
run_window(){
  local arm=$1 win=$2 bin=$3 tag=$4
  mkdir -p "$D/${arm}_$win/work"
  local ws we
  ws=$(date +%s)
  env "AGENTFRAMEWORK_WORKSPACE=$D/${arm}_$win/work" AGENTFRAMEWORK_R1_CONTRACT=1 \
      "AGENTFRAMEWORK_R1_TRANSCRIPT=$D/${arm}_$win/transcript.json" "AGENTFRAMEWORK_R1_TAG=$tag-$win" \
      "AGENTFRAMEWORK_R1_ROLE_FILE=$ROLE" \
      timeout 900 "$bin" -q "$(cat "$D/task-g1-prompt.txt")" --output-mode text \
        --session-id "r555-$tag-$win" > "$D/${arm}_$win/reply.txt" 2> "$D/${arm}_$win/stderr.txt"
  echo "$?" > "$D/${arm}_$win/cli_rc.txt"
  we=$(date +%s); echo "$ws $we" > "$D/${arm}_$win/window.txt"
  ( cd "$D/${arm}_$win/work" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$D/${arm}_$win/cases.txt" 2>&1
  log "$arm 窗$win cli_rc=$(cat "$D/${arm}_$win/cli_rc.txt") $(tail -1 "$D/${arm}_$win/cases.txt")"
}
run_window A0 83 "$BIN_V1" R555A0
run_window A0 84 "$BIN_V1" R555A0
run_window A0 85 "$BIN_V1" R555A0
run_window A1 80 "$BIN_V2" R555A1
run_window A1 81 "$BIN_V2" R555A1
run_window A1 82 "$BIN_V2" R555A1

# --- 5 汇总 (口径: 调用/新算 prompt/命中率取**中继 dump 时间轴**; transcript 只取形态字段) ---
python3 - "$D" <<'PY'
import glob, io, json, os, sys
D = sys.argv[1]
ARMS = {"A0": [83, 84, 85], "A1": [80, 81, 82]}
dumps = sorted(glob.glob(os.path.join(D, "adapter", "side-agent-*.json")))
recs = []
for f in dumps:
    try:
        d = json.load(io.open(f, encoding="utf-8-sig"))
    except Exception:
        continue
    u = ((d.get("response") or {}).get("usage")) or {}
    recs.append((os.path.getmtime(f), os.path.basename(f), u))
rows = []
for arm, wins in ARMS.items():
    for w in wins:
        b = os.path.join(D, "%s_%d" % (arm, w))
        cf = os.path.join(b, "cases.txt")
        tot = pas = 0
        fails = []
        if os.path.exists(cf):
            for x in io.open(cf, encoding="utf-8", errors="replace"):
                if x.startswith("CASE"):
                    tot += 1
                    if "PASS" in x:
                        pas += 1
                    else:
                        fails.append(x.split()[1])
        t = {}
        tp = os.path.join(b, "transcript.json")
        if os.path.exists(tp):
            t = json.load(io.open(tp, encoding="utf-8"))
        ws, we = [int(x) for x in io.open(os.path.join(b, "window.txt")).read().split()]
        sel = [r for r in recs if ws - 3 <= r[0] <= we + 8]
        calls = len(sel)
        pt = sum(int(r[2].get("prompt_tokens") or 0) for r in sel)
        ct = sum(int(r[2].get("completion_tokens") or 0) for r in sel)
        hit = sum(int(r[2].get("prompt_cache_hit_tokens") or 0) for r in sel)
        miss = sum(int(r[2].get("prompt_cache_miss_tokens") or 0) for r in sel)
        unreported = sum(1 for r in sel if "prompt_cache_hit_tokens" not in r[2])
        rows.append({"arm": arm, "win": w, "pass": pas, "total": tot, "fails": fails,
                     "calls_dump": calls, "prompt_sum": pt, "completion_sum": ct,
                     "hit_sum": hit, "miss_sum": miss, "unreported": unreported,
                     "v_all": round(hit / (hit + miss), 4) if (hit + miss) else None,
                     "cli_rc": io.open(os.path.join(b, "cli_rc.txt")).read().strip(),
                     "rc": t.get("rc"), "stage": t.get("stage"), "calls_self": t.get("calls"),
                     "prefix_chars": t.get("prefix_chars"), "prefix_sha256": t.get("prefix_sha256"),
                     "self_test_unmet": t.get("self_test_unmet"),
                     "correctness_asserted": t.get("correctness_asserted"),
                     "public_probe_ran": t.get("public_probe_ran"),
                     "public_probe_total": t.get("public_probe_total"),
                     "public_probe_failed": t.get("public_probe_failed"),
                     "probe_repairs": t.get("probe_repairs"), "exec_repairs": t.get("exec_repairs")})
out = {"tag": "R555", "rows": rows}
for arm in ARMS:
    vw = [r for r in rows if r["arm"] == arm]
    ok = sorted(r["pass"] for r in vw)
    out[arm] = {"passes": [r["pass"] for r in vw], "median": ok[len(ok) // 2],
                "range": max(ok) - min(ok), "calls": sum(r["calls_dump"] for r in vw),
                "prompt": sum(r["prompt_sum"] for r in vw), "completion": sum(r["completion_sum"] for r in vw),
                "prefix_chars": sorted({r["prefix_chars"] for r in vw})}
json.dump(out, io.open(os.path.join(D, "summary-r555.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print("  %s 窗%-3d %d/%d 调用=%-2d prompt=%-6d comp=%-6d v_all=%-6s rc=%-3s stage=%-24s prefix=%-5s probe=%s/%s fails=%s"
          % (r["arm"], r["win"], r["pass"], r["total"], r["calls_dump"], r["prompt_sum"], r["completion_sum"],
             r["v_all"], r["rc"], r["stage"], r["prefix_chars"], r["public_probe_failed"],
             r["public_probe_total"], ",".join(r["fails"][:4])))
for arm in ("A0", "A1"):
    print("  %s: 中位=%s 极差=%s 调用Σ=%s 新算promptΣ=%s completionΣ=%s prefix=%s"
          % (arm, out[arm]["median"], out[arm]["range"], out[arm]["calls"], out[arm]["prompt"],
             out[arm]["completion"], out[arm]["prefix_chars"]))
PY
log "汇总完成"
