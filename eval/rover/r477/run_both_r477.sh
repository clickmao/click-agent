#!/usr/bin/env bash
# R477 双臂顺序执行 (Arole → R); key 只从 .env.local 取一次, 不回显。
# 与 R474 的 run_both.sh 差异: 变量名 R474_ → R477_; 调用 r477 臂执行器。
set -u
cd /home/agentuser/AgentFramework
export R477_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R477_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[both-r477] start $(date +%H:%M:%S) key_len=${#R477_UPSTREAM_KEY}"
bash eval/rover/r477/run_arm_real_r477.sh Arole 48210 48212 || { echo "[both-r477] Arole 失败 rc=$?"; exit 1; }
echo "[both-r477] Arole ok $(date +%H:%M:%S)"
bash eval/rover/r477/run_arm_real_r477.sh R 48214 48213 || { echo "[both-r477] R 失败 rc=$?"; exit 2; }
echo "[both-r477] R ok $(date +%H:%M:%S)"
echo "[both-r477] ALLDONE $(date +%H:%M:%S)"
