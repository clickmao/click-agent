#!/usr/bin/env bash
# EXP1-Q46 归档补全: commit_q46.txt 的 tee 尾部落盘晚于首次 add ⇒ 首版不完整, 补一次提交
set -u
cd /home/agentuser/AgentFramework || exit 3
git add -- eval/capability/exp1-q46/commit_q46.txt
git commit -q -m "EXP1-Q46: 归档补全 commit_q46.txt (tee 尾部落盘晚于 add, 首版不完整)"
git log -1 --format='HEAD=%h %s' | cut -c1-90
echo "DIRTY_IN_SCOPE=$(git status --porcelain | grep -cE 'exp1-q46|kpi.jsonl|dynamic-telemetry')"
