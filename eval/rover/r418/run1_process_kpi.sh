#!/usr/bin/env bash
# R418: 探针「过程/成本」维度 KPI —— 仪器自检 + 真机归属化读数 + 成对负控
set -u
cd /home/agentuser/AgentFramework
export PYTHONDONTWRITEBYTECODE=1
export PROBE_AGENT_BIN=/tmp/pub_r414/agenthost
LOG=/tmp/r418-proc.log
: > "$LOG"

echo "=== [0] 仪器自检 ===" | tee -a "$LOG"
for m in process_metrics grade run_probe; do
  printf '%-16s ' "$m" | tee -a "$LOG"
  python3 eval/probe/$m.py --selftest 2>&1 | grep -E '^selftest' | tee -a "$LOG"
done

echo "=== [A] 真机 agent json_mini n=3 seed=20260916 (归档名带命名空间 s20260916) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families json_mini --n 3 --seed 20260916 \
  --solver agent --out data/probe/probe-r418-agent.json 2>&1 | tail -6 | tee -a "$LOG"

echo "=== [B] 负控 mutation:json_loose n=4 同 seed (整题全对必须=0) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families json_mini --n 4 --seed 20260916 \
  --solver mutation:json_loose --out data/probe/probe-r418-json-mut.json 2>&1 | tail -6 | tee -a "$LOG"

echo "=== [C] 过程/成本读数 (仅本轮批次) ===" | tee -a "$LOG"
python3 eval/probe/process_metrics.py --report \
  --glob 'data/probe/probe-r418-*.json' --out data/probe/process-metrics-r418.json 2>&1 | tee -a "$LOG"

echo "=== [D] 归档名核对 (归属证据) ===" | tee -a "$LOG"
ls -l --time-style=+%H:%M data/probe/replies/ | grep -E 's20260916' | tee -a "$LOG"
echo "R418_RUN1_DONE" | tee -a "$LOG"
