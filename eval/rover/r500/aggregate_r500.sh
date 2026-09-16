#!/usr/bin/env bash
set -u
cd /home/agentuser/AgentFramework
D=eval/rover/r499
echo "== teardown 断言 (4 臂) =="
python3 - "$D" <<'PY'
import io, json, os, sys
d = sys.argv[1]
for tag, sfx in [("C", ""), ("P1", "1"), ("P2", "2"), ("P3", "3")]:
    p = os.path.join(d, "teardown-%s%s.json" % (tag[:1] if tag != "C" else "C", sfx))
    if not os.path.isfile(p):
        print(tag, "MISSING"); continue
    j = json.load(io.open(p, encoding="utf-8-sig"))
    print("%-3s verdict=%s procs=%s listeners=%s" % (tag, j.get("verdict"), j.get("procs"), j.get("listeners")))
PY
echo "== 臂 flags (关键项) =="
python3 - "$D" <<'PY'
import io, json, os, sys
d = sys.argv[1]
ks = ("local_paraphrase", "replay_pair_trim", "tool_decl_channel", "local_decision_mount", "action_boundary", "turn_gate", "repeat_skip")
for f in ["flags-C.json", "flags-P1.json", "flags-P2.json", "flags-P3.json"]:
    p = os.path.join(d, f)
    if not os.path.isfile(p):
        print(f, "MISSING"); continue
    j = json.load(io.open(p, encoding="utf-8-sig"))
    print(f, json.dumps({k: j.get(k) for k in ks}, ensure_ascii=False))
PY
echo "== 汇总器 =="
python3 eval/rover/r499/analyze_r499.py --dir "$D" --out eval/rover/r499/analyze_r499.json 2>&1 | tail -25
echo "ANALYZE_RC=$?"
