#!/usr/bin/env bash
# R474 双臂顺序执行 (Arole → R); 端口按臂隔离以避开 TIME_WAIT; key 只从 .env.local 取一次, 不回显
set -u
cd /home/agentuser/AgentFramework
export R474_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R474_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[both] start $(date +%H:%M:%S) key_len=${#R474_UPSTREAM_KEY}"
bash eval/rover/r474/run_arm_real.sh Arole 48110 48112 || { echo "[both] Arole 失败 rc=$?"; exit 1; }
echo "[both] Arole ok $(date +%H:%M:%S)"
bash eval/rover/r474/run_arm_real.sh R 48114 48113 || { echo "[both] R 失败 rc=$?"; exit 2; }
echo "[both] R ok $(date +%H:%M:%S)"
echo "[both] ALLDONE $(date +%H:%M:%S)"
