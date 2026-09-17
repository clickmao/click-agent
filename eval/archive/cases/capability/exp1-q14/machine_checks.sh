#!/usr/bin/env bash
# EXP1-Q14 机检: 脚本内不得出现后缀字面量 (语言无关纪律); 顺带清理 pycache 并查台账幂等
set -u
cd /home/agentuser/AgentFramework || exit 1
S=eval/capability/exp1-q14/real_candidate_review.py
echo "=== suffix literal check ==="
grep -nE '"\.[a-zA-Z]{1,4}"' "$S" | head -5
echo "literal_hits=$(grep -cE '"\.[a-zA-Z]{1,4}"' "$S" || true)"
echo "=== gitignore check ==="
git check-ignore -v eval/capability/exp1-q14/__pycache__ 2>&1 | head -2
rm -rf eval/capability/exp1-q14/__pycache__
echo "=== kpi ledger idempotence ==="
echo "already_present=$(grep -c 'EXP1-Q14' eval/capability/kpi.jsonl || true)"
echo "=== sibling activity ==="
n=$(pgrep -f 'dotnet|MSBuild|VBCSCompiler' | wc -l)
echo "build_procs=$n"
free -m | head -2
