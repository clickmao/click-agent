#!/usr/bin/env bash
# R482 双臂顺序执行 (Arole → R); key 只从 .env.local 取一次, 不回显。机派生自 run_both_r477.sh。
set -u
cd /home/agentuser/AgentFramework
export R482_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R482_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[both-r482] start $(date +%H:%M:%S) key_len=${#R482_UPSTREAM_KEY}"
bash eval/rover/r482/run_arm_real_r482.sh Arole 48210 48212 || { echo "[both-r482] Arole 失败 rc=$?"; exit 1; }
echo "[both-r482] Arole ok $(date +%H:%M:%S)"
bash eval/rover/r482/run_arm_real_r482.sh R 48214 48213 || { echo "[both-r482] R 失败 rc=$?"; exit 2; }
echo "[both-r482] R ok $(date +%H:%M:%S)"
echo "[both-r482] ALLDONE $(date +%H:%M:%S)"
