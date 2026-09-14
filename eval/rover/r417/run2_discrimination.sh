#!/usr/bin/env bash
# R417 步 3+4: 判别力自证 (正控 oracle / 负控 2 个缺陷注入) + 真机 agent 新族读数
set -u
cd /home/agentuser/AgentFramework
export PYTHONDONTWRITEBYTECODE=1
export PROBE_AGENT_BIN=/tmp/pub_r414/agenthost
LOG=/tmp/r416-disc.log
: > "$LOG"

echo "=== [A] 正控: oracle 新族必须满分 (题可解 / 隐藏答案自洽) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families topo_min,vm_run --n 4 --seed 20260914 \
  --solver oracle --out data/probe/probe-r416-new-oracle.json 2>&1 | tail -14 | tee -a "$LOG"

echo "=== [B] 负控: topo_dfs 缺陷注入 (整题全对须 = 0) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families topo_min --n 4 --seed 20260914 \
  --solver mutation:topo_dfs --out data/probe/probe-r416-mut-topodfs.json 2>&1 | tail -14 | tee -a "$LOG"

echo "=== [C] 负控: vm_noerr 缺陷注入 (整题全对须 = 0) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families vm_run --n 4 --seed 20260914 \
  --solver mutation:vm_noerr --out data/probe/probe-r416-mut-vmnoerr.json 2>&1 | tail -14 | tee -a "$LOG"

echo "=== [D] 真机: agent 新族 (反饱和读数) ===" | tee -a "$LOG"
python3 eval/probe/run_probe.py --kind program --families topo_min,vm_run --n 6 --seed 20260914 \
  --solver agent --out data/probe/probe-r416-hard-agent.json 2>&1 | tail -20 | tee -a "$LOG"

echo "R417_RUN2_EXIT=$?" | tee -a "$LOG"
