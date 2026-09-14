#!/usr/bin/env bash
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
python3 -u eval/probe/run_probe.py --kind program --families json_mini --n 6 --seed 419 \
  --turns 2 --correction onfail --solver agent --tag r419dagent-b3092030 \
  > eval/rover/r419/logs/r419dagent-b3092030.log 2>&1
echo "STEP_EXIT_agent=$?"
python3 eval/probe/process_metrics.py --multiturn > eval/rover/r419/logs/process_metrics-b3092030.out 2>&1
python3 eval/rover/r419/check_multiturn.py --prefix r419d --ns b3092030 > eval/rover/r419/logs/check-b3092030.out 2>&1
echo "CHECK_EXIT=$?"
tail -3 eval/rover/r419/logs/check-b3092030.out
