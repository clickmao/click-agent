#!/usr/bin/env bash
# R568 候选④ 起手闸条款**行使** (b 版: 收尾 → 采样 → 派生 → 判别带成对)
# 与 a 版差异: 采样前先跑一次既有闸 (其自带收尾/reap 是本轮之前的固定工序) ⇒ 读数反映真实可支配顶棚。
# 零开发: 只调既有器具 (gate_margin_r567.py / preflight_gate.py)。
set -u
REPO=/home/agentuser/AgentFramework
PDIR="$REPO/eval/rover/r568"
D=/tmp/r568
mkdir -p "$D/logs"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/gate-b.txt"; }

log "S0 既有闸收尾 (自带 reap) + 测当前可支配顶棚"
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568S0 --gate-mb 2650 --out "$D/gate-s0.json" >/dev/null 2>&1
python3 -c "import json;d=json.load(open('$D/gate-s0.json'));print('  S0 mem=%sMB verdict=%s reaped=%d'%(d['mem_available_mb'],d['verdict'],len(d['own_tool_reap']['reaped'])))" | tee -a "$D/logs/gate-b.txt"
sleep 10

: > "$D/logs/pre-samples-b.jsonl"
for k in 1 2 3; do
  python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/pre-samples-b.jsonl" >/dev/null
  sleep 5
done
log "S1 起手前 3 样本: $(python3 -c "
import json
v=[json.loads(l)['mem_available_mb'] for l in open('$D/logs/pre-samples-b.jsonl')]
print('%s 顶棚=%d 极差=%d'%(v,max(v),max(v)-min(v)))")"

python3 "$REPO/eval/rover/r567/gate_margin_r567.py" --derive --samples "$D/logs/pre-samples-b.jsonl" \
    --prev-postcheck "$REPO/eval/rover/r567/gate-postcheck-r567.json" \
    --out "$PDIR/gate-margin-r568.json" --embed-selftest > "$D/logs/derive-b.json" 2>&1
drc=$?
log "S2 条款派生 rc=$drc (rc=2 ⇒ 条款在当前宿主**不可行使**, fail-closed)"
REQ=$(python3 -c "import json;print(int(json.load(open('$PDIR/gate-margin-r568.json'))['required_mb']))")
CEIL=$(python3 -c "import json;print(json.load(open('$PDIR/gate-margin-r568.json'))['ceiling_mb'])")

log "S3 判别带成对行使 (同一状态下 基础门槛 vs 条款)"
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568BASE --gate-mb 2650 --out "$D/gate-disc-base2650.json" >/dev/null 2>&1
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568CLAU --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1

python3 - "$D" "$PDIR" "$REQ" "$CEIL" "$drc" <<'PY'
import io, json, os, sys
D, PDIR, req, ceil = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
drc = int(sys.argv[5])
def g(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
def m(p):
    return g(p).get("mem_available_mb")
mb, mc = m(D + "/gate-disc-base2650.json"), m(D + "/gate-disc-clause.json")
vb, vc = g(D + "/gate-disc-base2650.json").get("verdict"), g(D + "/gate-disc-clause.json").get("verdict")
band = (mb is not None and 2650.0 <= mb < req)
disc = bool(band and vb == "PASS" and vc == "GATE_BLOCKED")
derived = g(os.path.join(PDIR, "gate-margin-r568.json"))
marg_cap = max(0.0, (ceil if ceil else 0.0) - 2650.0)
req_cap = 2650.0 + min(derived.get("margin_mb", 0.0) or 0.0, marg_cap)
rec = {
    "round": "R568", "candidate": "④ 起手闸 REQ 行使 (零开发)",
    "gate_base_mb": 2650, "gate_clause_mb": req,
    "derive_rc": drc, "ceiling_mb": ceil, "margin_mb": derived.get("margin_mb"),
    "prev_swing_mb": derived.get("prev_swing_mb"), "spread_mb": derived.get("spread_mb"),
    "clause_satisfiable": drc == 0,
    "discrimination": {"state_mb_at_base_call": mb, "state_mb_at_clause_call": mc,
                       "base_verdict": vb, "clause_verdict": vc,
                       "state_in_band": band, "true_discrimination": disc,
                       "why": ("同一状态 (≈%sMB) 下 基础门槛 PASS 而条款 GATE_BLOCKED ⇒ 条款确实更严" % mb if disc
                               else "未落在判别带内 ⇒ 本轮未行使真判别 (不得据此刻度)")},
    "reachability_defect": {
        "headroom_mb": marg_cap, "clause_margin_used_mb": derived.get("margin_mb"),
        "verdict": ("自适应余量 (>可支配余量) ⇒ 条款**不可满足**: 顶棚 %sMB < REQ %sMB; "
                    "与 v1 常数(200⇒2850)同一缺陷族 — 只是把「常数拍脑袋」换成「数据派生但未夹上界」"
                    % (ceil, req)),
        "implied_margin_cap_mb": marg_cap, "implied_req_mb": req_cap,
        "rule_next": ("MARGIN := min(上一轮观测振幅, 顶棚 − GATE − 安全地板); 本宿主 ⇒ min(103, %.0f) = %.0f ⇒ REQ=%.0f"
                      % (marg_cap, min(derived.get("margin_mb") or 0.0, marg_cap), req_cap))},
    "rc": (3 if (mb is None or mc is None) else (0 if disc else 2)),
    "rc_semantics": "0 条款可行使且判别力为真 / 2 条款当前不可行使 (判别力已证, 缺陷入档) 或 判别力未行使 / 3 输入缺失",
}
json.dump(rec, io.open(os.path.join(PDIR, "gate-disc-pair-r568.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False))
PY
log "S4 成对结果已落盘 gate-disc-pair-r568.json"
exit 0
