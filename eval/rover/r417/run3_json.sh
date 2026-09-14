#!/usr/bin/env bash
set -u
cd /home/agentuser/AgentFramework
export PYTHONDONTWRITEBYTECODE=1
export PROBE_AGENT_BIN=/tmp/pub_r414/agenthost
LOG=/tmp/r416-json.log
: > "$LOG"
echo "=== [A] oracle json_mini n=2 (正控: 必须满分) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families json_mini --n 2 --seed 20260915 --solver oracle --out data/probe/probe-r416-json-oracle.json 2>&1 | tail -8 | tee -a "$LOG"
echo "=== [B] mutation:json_loose n=4 (负控: 整题全对必须=0) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families json_mini --n 4 --seed 20260915 --solver mutation:json_loose --out data/probe/probe-r416-json-mut.json 2>&1 | tail -8 | tee -a "$LOG"
echo "=== [C] agent json_mini n=3 (真机) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families json_mini --n 3 --seed 20260915 --solver agent --out data/probe/probe-r416-json-agent.json 2>&1 | tail -8 | tee -a "$LOG"
echo "R417_RUN3_DONE" | tee -a "$LOG"
