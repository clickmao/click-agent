#!/usr/bin/env bash
# EXP1-Q42 step 6: 受影响行 (r476, 器具=bind_evidence.py) 定向重审 + 声明刷新 + 双闸复核
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42
REG=docs/verification-registry.json
INST=eval/capability/instruments.json

echo "--- 定向重审 r476 (器具=bind_evidence.py, 本轮被反解修复改动) ---"
python3 eval/capability/bind_evidence.py --apply --round EXP1-Q42 --only r476.evidence-binding-round-param \
  >> "$D/bind_apply_q42.txt" 2>&1; echo "apply_rc=$?"
grep -E "SER_ASSERT|ONLY_SCOPE|UNCHANGED|TOUCHED" "$D/bind_apply_q42.txt" | tail -4 | cut -c1-160

echo "--- 声明刷新 (定向) ---"
python3 eval/capability/decl_sweep.py --apply > "$D/decl_apply_q42.txt" 2>&1; echo "decl_apply_rc=$?"
grep -E "RE_AUDITED|checked|drifted|DECL_SWEEP" "$D/decl_apply_q42.txt" | tail -6 | cut -c1-200

echo "--- 改动量 ---"
git diff --numstat -- "$REG" "$INST"
echo "--- 复核: bind_evidence --check ---"
python3 eval/capability/bind_evidence.py --check > "$D/bind_check_q42b.txt" 2>&1; echo "bind_check_rc=$?"
grep -E "FROZEN_EVIDENCE_DRIFT|VIOLATION|CHECKED_WITH|R2E" "$D/bind_check_q42b.txt" | head -6 | cut -c1-200
echo "--- 复核: decl_sweep (只读) ---"
python3 eval/capability/decl_sweep.py > "$D/decl_check_q42c.txt" 2>&1; echo "decl_rc=$?"; tail -2 "$D/decl_check_q42c.txt" | cut -c1-160
