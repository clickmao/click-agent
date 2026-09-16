#!/usr/bin/env bash
# R462 E2E: setup + run + 负控
set -uo pipefail
A=/home/agentuser/AgentFramework
bash "$A/eval/rover/r462/r462_setup.sh" 2>&1 | tee /tmp/r462_setup.log
echo "=== run ==="
bash "$A/eval/rover/r462/r462_run.sh" 2>&1 | tee /tmp/r462_run.log
echo "=== 负控 (R461 实发面 + R462 判据) ==="
R462_ENV=/tmp/r461_env R462_OUT=/tmp/r462_negctl.json python3 "$A/eval/rover/r462/judge_r462.py" 2>&1 | tail -3
