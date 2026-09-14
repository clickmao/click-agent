#!/usr/bin/env bash
# R415 本地提交器 — 只本地 commit, 绝不 push (推送暂停令 2026-09-13 未解除)
set -eu
cd /home/agentuser/AgentFramework
git add eval/rover/r415/README-evidence.md eval/rover/r415/verdict.py eval/rover/r415/verdict-r415.json
git add eval/rover/r415/fake_llama.py eval/rover/r415/fake_llama_bin.sh eval/rover/r415/run_arm.sh
git add eval/rover/r415/stub_openai.py eval/rover/r415/drive_task.py eval/rover/r415/task.json
git add eval/rover/r415/skills eval/rover/r415/calls-pin.jsonl eval/rover/r415/calls-off.jsonl
git add eval/rover/r415/calls-pin-aot.jsonl eval/rover/r415/calls-off-aot.jsonl
git add eval/rover/r415/llamareq-pin.jsonl eval/rover/r415/llamareq-off.jsonl
git add eval/rover/r415/llamareq-pin-aot.jsonl eval/rover/r415/llamareq-off-aot.jsonl
git add eval/rover/r415/turns-pin.jsonl eval/rover/r415/turns-off.jsonl
git add eval/rover/r415/turns-pin-aot.jsonl eval/rover/r415/turns-off-aot.jsonl
git add eval/rover/r415/budget-pin.json eval/rover/r415/budget-off.json
git add eval/rover/r415/budget-pin-aot.json eval/rover/r415/budget-off-aot.json
git add docs/plans/v0.37.0-r415-gate-input-chain-pin.md docs/improvements.md
git add docs/verification-registry.json eval/capability/kpi.jsonl
# 凭据/运行期产物守门 (误入库前硬拦)
if git diff --cached --name-only | grep -Eq 'master\.key|config-|run-|\.log$|token|key'; then
  echo "[拒] 暂存区含运行期产物或凭据候选"; git diff --cached --name-only | grep -E 'master\.key|config-|run-|\.log$|token|key'; exit 9
fi
git commit -q -m "R415: 链级钉死前置门入参=用户原文(真链+确定性假本地后端, 22断言x2形态 PASS) + 仪器两项教训入档"
git --no-pager log --oneline -1
echo "[ok] 已本地提交; 推送三道闸未动 (PUSH_PAUSED 仍在)"
