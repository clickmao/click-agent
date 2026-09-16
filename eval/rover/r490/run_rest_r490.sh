#!/usr/bin/env bash
# R490 顺序执行: Arole(基线×1) → R(生产形态×1) → T(声明门×2); key 只从 .env.local 取一次, 不回显。
#   单变量链: Arole →(本地闸)→ R →(声明面按需)→ T。四跑同一 AOT 产物 / 同一夹具(p12) / 同一窗。
#   端口段 49010..49024 (R489 用 48910..48924; 无重叠 ⇒ 无跨轮串扰)。
set -u
cd /home/agentuser/AgentFramework
export R490_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R490_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[rest-r490] start $(date +%H:%M:%S) key_len=${#R490_UPSTREAM_KEY} bin=$(sha256sum /tmp/pub_r490/agenthost | cut -c1-16)"
python3 eval/rover/r483/preflight_gate.py --out eval/rover/r490/preflight-rest.json --round R490 \
  || { echo "[rest-r490] 起手闸未通过 (rc=$?) ⇒ 拒跑"; exit 10; }
echo "[rest-r490] gate PASS $(date +%H:%M:%S)"
B=/tmp/pub_r490/agenthost
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r490/run_arm_real_r490.sh Arole b 49010 49012 || { echo "[rest-r490] Arole 失败 rc=$?"; exit 1; }
echo "[rest-r490] Arole ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r490/run_arm_real_r490.sh R 1 49014 49016 || { echo "[rest-r490] R1 失败 rc=$?"; exit 2; }
echo "[rest-r490] R1 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r490/run_arm_real_r490.sh T 1 49018 49020 || { echo "[rest-r490] T1 失败 rc=$?"; exit 3; }
echo "[rest-r490] T1 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r490/run_arm_real_r490.sh T 2 49022 49024 || { echo "[rest-r490] T2 失败 rc=$?"; exit 4; }
echo "[rest-r490] T2 ok $(date +%H:%M:%S)"
echo "[rest-r490] ALLDONE $(date +%H:%M:%S)"
