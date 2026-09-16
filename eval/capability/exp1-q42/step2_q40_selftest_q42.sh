#!/usr/bin/env bash
# EXP1-Q42 step 2: 转正后 Q40 尾 LF 提交面 selftest 的期望是否过期 (E5 = 默认关)
set -u
cd /home/agentuser/AgentFramework
OUT=eval/capability/exp1-q42/taillf_q40_selftest_after_promotion_q42.txt
timeout 300 python3 eval/capability/exp1-q40/selftest_q40_taillf.py > "$OUT" 2>&1
echo "rc=$?"
grep -n "E5\|checks\|verdict\|PASS\|FAIL" "$OUT" | tail -25 | cut -c1-200
