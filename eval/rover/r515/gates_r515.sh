#!/usr/bin/env bash
# R515 提交前形式门禁 (与既有轮同口径): bind_evidence --check + decl_sweep --check + pre-commit 形式门
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO"
echo "== bind_evidence --check =="
python3 eval/capability/bind_evidence.py --check 2>&1 | tail -6
echo "BIND_RC=$?"
echo "== decl_sweep --check =="
python3 eval/capability/decl_sweep.py --check 2>&1 | tail -4
echo "DECL_RC=$?"
echo "== instruments_check =="
python3 eval/capability/instruments_check.py 2>&1 | tail -4
echo "INSTR_RC=$?"
echo "== registry 形式自检 =="
python3 - <<'PY'
import json
d = json.load(open("/home/agentuser/AgentFramework/docs/verification-registry.json", encoding="utf-8"))
rows = d["rows"]
bad = [r["id"] for r in rows if not r.get("id") or not r.get("owner_round") or "level" not in r]
print("ROWS=%d bad=%s updated_round=%s" % (len(rows), bad[:4], d.get("updated_round")))
PY
