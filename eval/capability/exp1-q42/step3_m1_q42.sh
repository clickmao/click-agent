#!/usr/bin/env bash
# EXP1-Q42 step 3: M1 负控 (前态/现态成对) + 刷新后期望全跑
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42
python3 "$D/nc_prestate_q42.py" > "$D/nc_prestate_q42.txt" 2>&1; echo "NC_rc=$?"
cat "$D/nc_prestate_q42.txt"
timeout 300 python3 eval/capability/exp1-q40/selftest_q40_taillf.py > "$D/taillf_q40_selftest_refreshed_q42.txt" 2>&1; echo "SELFTEST_rc=$?"
cat "$D/taillf_q40_selftest_refreshed_q42.txt"
