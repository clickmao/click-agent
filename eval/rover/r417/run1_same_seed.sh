#!/usr/bin/env bash
# R417 步 1+2: 仪器自检 + 同题复跑 (seed 20260913, AOT R414 二进制) —— 与 2026-09-13 基线同题对比
set -u
cd /home/agentuser/AgentFramework
export PYTHONDONTWRITEBYTECODE=1
export PROBE_AGENT_BIN=/tmp/pub_r414/agenthost
LOG=/tmp/r416-probe.log
: > "$LOG"

echo "=== [1] 仪器自检 (三件 + kpi) ===" | tee -a "$LOG"
for m in tasks grade run_probe; do
  echo "--- $m --selftest" | tee -a "$LOG"
  python3 "eval/probe/$m.py" --selftest 2>&1 | tail -3 | tee -a "$LOG"
done
echo "--- kpi_probe --selftest" | tee -a "$LOG"
python3 scripts/kpi_probe.py --selftest 2>&1 | tail -3 | tee -a "$LOG"

echo "=== [2] 同题复跑 seed=20260913 agent (AOT $(basename -a /tmp/pub_r414/agenthost) ) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind both --n 3 --seed 20260913 --solver agent \
  --tag r416 --out data/probe/probe-r416-agent-seed20260913.json 2>&1 | tail -25 | tee -a "$LOG"

echo "R417_RUN1_EXIT=$?" | tee -a "$LOG"
