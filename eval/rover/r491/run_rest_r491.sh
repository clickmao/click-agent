#!/usr/bin/env bash
# R491 顺序执行: Arole(基线×1) → R(生产形态×1) → T(声明门×2); key 只从 .env.local 取一次, 不回显。
#   单变量链: Arole →(本地闸)→ R →(声明面按需)→ T。四跑同一 AOT 产物 / 同一夹具(p12) / 同一窗。
#   端口段 49110..49124 (R489 用 48910..48924; 无重叠 ⇒ 无跨轮串扰)。
set -u
cd /home/agentuser/AgentFramework
export R491_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R491_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 9; }
echo "[rest-r491] start $(date +%H:%M:%S) key_len=${#R491_UPSTREAM_KEY} bin=$(sha256sum /tmp/pub_r491/agenthost | cut -c1-16)"
python3 eval/rover/r483/preflight_gate.py --out eval/rover/r491/preflight-rest.json --round R491 \
  || { echo "[rest-r491] 起手闸未通过 (rc=$?) ⇒ 拒跑"; exit 10; }
echo "[rest-r491] gate PASS $(date +%H:%M:%S)"
B=/tmp/pub_r491/agenthost
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r491/run_arm_real_r491.sh T 1 49114 49116 || { echo "[rest-r491] T1 失败 rc=$?"; exit 2; }
echo "[rest-r491] T1 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r491/run_arm_real_r491.sh T 2 49118 49120 || { echo "[rest-r491] T2 失败 rc=$?"; exit 2; }
echo "[rest-r491] T2 ok $(date +%H:%M:%S)"
AGENTFRAMEWORK_HOST_BIN=$B bash eval/rover/r491/run_arm_real_r491.sh T 3 49122 49124 || { echo "[rest-r491] T3 失败 rc=$?"; exit 2; }
echo "[rest-r491] T3 ok $(date +%H:%M:%S)"
echo "[rest-r491] ALLDONE $(date +%H:%M:%S)"
