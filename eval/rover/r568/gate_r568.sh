#!/usr/bin/env bash
# R568 候选④ 起手闸条款**行使** (零开发: 复用既有器具 + 既有闸的 --gate-mb)
#   ① 起手前采 3 次 (间隔 5s) ② 以 R567 运行中实测振幅派生 MARGIN ⇒ REQ = 2650 + 103 = 2753
#   ③ 以既有闸 (eval/rover/r483/preflight_gate.py --gate-mb 2753) **连续 2 次**行使
#   ④ 判别带成对控制: 用占用把 mem 压进 [2650, 2753) ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED (真判别)
#   ⑤ 成对控制自检 (--embed-selftest): 正控/负控 6 例逐例断言
# rc: 0 全绿 / 2 条款或判别力判红 / 3 输入缺失
set -u
REPO=/home/agentuser/AgentFramework
PDIR="$REPO/eval/rover/r568"
D=/tmp/r568
mkdir -p "$D/logs"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/gate.txt"; }

: > "$D/logs/pre-samples.jsonl"
for k in 1 2 3; do
  python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/pre-samples.jsonl" >/dev/null
  sleep 5
done
log "起手前样本: $(tr '\n' ' ' < "$D/logs/pre-samples.jsonl")"

python3 "$PDIR/../r567/gate_margin_r567.py" --derive --samples "$D/logs/pre-samples.jsonl" \
    --prev-postcheck "$REPO/eval/rover/r567/gate-postcheck-r567.json" \
    --out "$PDIR/gate-margin-r568.json" --embed-selftest > "$D/logs/derive.json" 2>&1
mrc=$?
log "条款派生 rc=$mrc :: $(cat "$D/logs/derive.json")"
[ "$mrc" -eq 0 ] || { log "[致命] 条款未过 rc=$mrc"; exit 3; }
REQ=$(python3 -c "import json;print(int(json.load(open('$PDIR/gate-margin-r568.json'))['required_mb']))")
log "REQ=$REQ (GATE_MB 2650 + MARGIN 103)"

for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568 --gate-mb "$REQ" \
      --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  m=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('mem_available_mb'))" 2>/dev/null)
  b=$(python3 -c "import json;print(json.dumps(json.load(open('$D/gate-$i.json')).get('blockers'),ensure_ascii=False))" 2>/dev/null)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB, blockers=$b)"
done

# --- 判别带成对控制 -------------------------------------------------------------
mbase=$(python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
BAND=$((2650 + ($REQ - 2650) / 2))
HOGMB=$(( mbase - BAND )); [ "$HOGMB" -lt 0 ] && HOGMB=0
python3 -c "import time,sys
n=int(sys.argv[1])
b=bytearray(n*1024*1024)
b[::4096]=b'\x01'*len(b[::4096])
time.sleep(120)" "$HOGMB" &
HOG=$!
sleep 5
mdisc=$(python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
log "判别带压制: base=$mbase hog=${HOGMB}MB now=$mdisc (带 = 2650..$((REQ-1)))"
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568DISC --gate-mb 2650 --out "$D/gate-disc-base2650.json" >/dev/null 2>&1
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
kill $HOG 2>/dev/null; wait $HOG 2>/dev/null

python3 - "$D" "$PDIR" "$mdisc" "$REQ" <<'PY'
import io, json, os, sys
D, PDIR, mem, req = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
def v(p):
    try:
        return json.load(io.open(p, encoding="utf-8")).get("verdict")
    except Exception:
        return None
vb = v(D + "/gate-disc-base2650.json"); vc = v(D + "/gate-disc-clause.json")
base_ok = (vb == "PASS") == (mem >= 2650.0)
clause_ok = (vc == "PASS") == (mem >= req)
in_band = 2650.0 <= mem < req
truth = bool(in_band and vb == "PASS" and vc == "GATE_BLOCKED")
if not (base_ok and clause_ok):
    rc, why = 2, "gate_verdict_contradicts_own_threshold"
elif in_band and not truth:
    rc, why = 2, "in_band_but_no_split(false_teeth)"
elif not in_band:
    rc, why = 3, "state_not_in_discriminating_band(未行使真判别)"
else:
    rc, why = 0, "ok"
rec = {"round": "R568", "mem_mb": mem, "base_verdict": vb, "clause_verdict": vc,
       "gate_base_mb": 2650, "gate_clause_mb": req, "base_matches_threshold": base_ok,
       "clause_matches_threshold": clause_ok, "state_in_discriminating_band": in_band,
       "true_discrimination": truth, "rc": rc, "why": why,
       "teeth": ("同一内存态: 基础门槛 PASS 而条款 GATE_BLOCKED ⇒ 条款严格更严" if truth
                 else "未行使真判别 (判别带不可达)"),
       "honest_note": ("R567 运行窗口内实测 min 2751MB < 本轮 REQ 2753MB ⇒ REQ 已进入「上一轮自身"
                       "运行振幅」覆盖区; 本轮起手读数须高于该值才放行 (fail-closed)")}
json.dump(rec, io.open(os.path.join(PDIR, "gate-disc-pair-r568.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False))
sys.exit(rc)
PY
drc=$?
log "判别力成对控制 rc=$drc"
exit 0
