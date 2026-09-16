#!/usr/bin/env bash
# EXP1-Q42 step 11: 证据件收尾提交 + 提交态复核 + 收口读数
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42

python3 - <<'PY' > "$D/stage_paths_q42b.txt" 2>&1
import subprocess
out = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout
picked = [l[3:].strip().strip('"') for l in out.splitlines() if l[3:].strip().startswith('eval/capability/exp1-q42/')]
print('\n'.join(sorted(picked)))
PY
mapfile -t PATHS < "$D/stage_paths_q42b.txt"
echo "REMAINING_PATHS=${#PATHS[@]}"
if [ "${#PATHS[@]}" -gt 0 ]; then
  git add -- "${PATHS[@]}"
  git commit -q -m "EXP1-Q42 证据件收尾: 分步脚本/日志/现场读数 (提交面两次真读数留档)" 2>&1 | tail -2
  echo "commit3_rc=$?"
fi
echo "--- 提交态复核 (committed-state 器具) ---"
python3 eval/capability/exp1-q30/check_committed_state_q30.py > "$D/committed_state_q42.txt" 2>&1; echo "committed_state_rc=$?"
tail -6 "$D/committed_state_q42.txt" | cut -c1-200
echo "--- bind_evidence --check (提交后) ---"
python3 eval/capability/bind_evidence.py --check > "$D/bind_check_final_q42.txt" 2>&1; echo "bind_check_rc=$?"
grep -E "R2E|VIOLATION|FROZEN_EVIDENCE_DRIFT|CHECKED_WITH" "$D/bind_check_final_q42.txt" | head -4 | cut -c1-200
echo "--- 本侧工作区残余 ---"
git status --porcelain | grep -E "exp1-q4|verification-registry|bind_evidence.py|instruments.json" | head -8 || echo CLEAN
echo "--- log ---"
git log --oneline -3
