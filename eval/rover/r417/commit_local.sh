#!/usr/bin/env bash
# R417 本地提交器: 只 local commit, 绝不 push (守 .git/PUSH_PAUSED)
set -euo pipefail
cd /home/agentuser/AgentFramework

if [ -e .git/PUSH_PAUSED ]; then echo "[闸] .git/PUSH_PAUSED 在位 ⇒ 只做本地提交"; else echo "[闸] 警告: 推送暂停标记不在位"; fi

git add docs/plans/v0.38.0-r417-probe-anti-saturation.md \
        eval/rover/r417 \
        eval/probe/tasks.py eval/probe/run_probe.py eval/probe/grade.py eval/probe/README.md \
        scripts/dev_return_digest.py docs/reports/dev-return-digest.md \
        docs/verification-registry.json docs/improvements.md \
        docs/plans/v715_dev_plan.taskplan.json

echo "--- staged ---"
git diff --cached --name-only

git -c user.name=agentframework -c user.email=agentframework@local commit -m "R417 探针反饱和: 3 个高判别力族(topo_min/vm_run/json_mini)+tight_gen 强制规格紧用例+族级缺陷注入负控(正负控成对); 同题复跑确认饱和; 真机仍饱和如实登记; digest 增探针分数段(含饱和标记)" -q
git log --oneline -1
echo "AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || git rev-list --count HEAD ^origin/main)"
