#!/usr/bin/env bash
# EXP1-Q42 step 8 (M4/M5): 提交面 — 显式路径 staging + 钩子两态 + 真提交 + 现场读数
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42

python3 - "$D" <<'PY' > "$D/stage_paths_q42.txt" 2>&1
import subprocess, sys
out = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout
pref = ('eval/capability/exp1-q42/', 'eval/capability/exp1-q40/selftest_q40_taillf',
        'eval/capability/bind_evidence.py', 'eval/capability/instruments.json',
        'docs/verification-registry.json')
picked = []
for line in out.splitlines():
    st, path = line[:2], line[3:].strip().strip('"')
    if any(path == p or path.startswith(p) for p in pref):
        picked.append(path)
print('\n'.join(sorted(picked)))
PY
echo "--- 待提交路径 (显式, 逐字取自 porcelain) ---"
cat "$D/stage_paths_q42.txt"

mapfile -t PATHS < "$D/stage_paths_q42.txt"
if [ "${#PATHS[@]}" -eq 0 ]; then echo "STAGE_SET_EMPTY ⇒ 中止"; exit 3; fi
git add -- "${PATHS[@]}"
echo "STAGED=$(git diff --cached --name-only | wc -l)"
git diff --cached --name-only | sed 's/^/  + /' | head -40

echo "--- 钩子干跑 (不提交) ---"
bash tools/hooks/pre-commit > "$D/hook_dryrun_q42.txt" 2>&1; echo "hook_dryrun_rc=$?"
tail -14 "$D/hook_dryrun_q42.txt" | cut -c1-200
echo "TAIL_LOG_AFTER_DRYRUN:"; tail -3 /tmp/tail_lf_precommit.log 2>/dev/null | cut -c1-160
