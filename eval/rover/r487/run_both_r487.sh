#!/usr/bin/env bash
# R487 三臂顺序执行 (A0 → Arole485 → R485); key 只从 .env.local 取一次, 不回显。机派生自 run_both_r477.sh。
set -u
cd /home/agentuser/AgentFramework
export R487_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R487_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[both-r487] start $(date +%H:%M:%S) key_len=${#R487_UPSTREAM_KEY}"
# R487 候选⑦: 起手闸前置 (fail-closed; 单一源器具, 本脚本不自带 mem 判定)。
python3 eval/rover/r483/preflight_gate.py --out eval/rover/r487/preflight-both.json --round R487 \
  || { echo "[both-r487] 起手闸未通过 (rc=$?) ⇒ 拒跑"; exit 10; }
echo "[both-r487] gate PASS $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r479v2/agenthost bash eval/rover/r487/run_arm_real_r487.sh A0 "" 48710 48712 || { echo "[both-r487] A0 失败 rc=$?"; exit 1; }
echo "[both-r487] A0 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh Arole 485 48714 48713 || { echo "[both-r487] Arole485 失败 rc=$?"; exit 2; }
echo "[both-r487] Arole485 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh R 485 48716 48715 || { echo "[both-r487] R485 失败 rc=$?"; exit 3; }
echo "[both-r487] R ok $(date +%H:%M:%S)"
echo "[both-r487] ALLDONE $(date +%H:%M:%S)"
