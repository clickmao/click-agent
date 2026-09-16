#!/usr/bin/env bash
# R482 R 臂单跑 —— 机派生自 eval/rover/r477/run_arm_R_only.sh (只改名 r477→r482, R477_→R482_)。
# 存在理由 (R482 本轮复现): run_both_r482.sh 在 Arole 收口后即做 R 臂起手闸, 上一臂的本地 r1
# (llama-server) RSS 尚未释放 ⇒ 本轮实测 MemAvailable=2590MB < 2650MB 被闸下 (与 R477 同一机制)。
# 本封装只在**调用臂执行器之前**做沉降等待 (≤120s: MemAvailable≥2650MB ∧ 无 llama-server 残留),
# 不碰臂执行器内的判据/读数 —— 臂内起手闸与 Arole 逐字节同源。
set -u
cd /home/agentuser/AgentFramework
export R482_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R482_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 key"; exit 9; }
for i in $(seq 1 24); do
  MA=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  LP=$(pgrep -c -f '[l]lama-server' 2>/dev/null || true)
  echo "[settle] MemAvailable=${MA}MB llama-server=${LP:-0}"
  [ "$MA" -ge 2650 ] && [ "${LP:-0}" -eq 0 ] && break
  sleep 5
done
bash eval/rover/r482/run_arm_real_r482.sh R 48214 48213 || { echo "[r-only] R 失败 rc=$?"; exit 2; }
echo "[r-only] R ok $(date +%H:%M:%S)"
