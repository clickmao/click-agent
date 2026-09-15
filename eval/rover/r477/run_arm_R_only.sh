#!/usr/bin/env bash
# R477 R 臂单跑 (Arole 已于 05:44:15 完成并归档)。
# 存在理由: run_both_r477.sh 在 Arole 收口后 12s 就做 R 臂起手闸, 而上一臂的本地 r1
# (llama-server, RSS 1.83GB) 彼时**尚未释放** ⇒ MemAvailable=1318MB 假阴性, R 臂被闸下。
# 本封装只在**调用臂执行器之前**做「沉降等待」(≤120s: MemAvailable≥2650MB ∧ 无 llama-server 残留),
# 不碰臂执行器内的判据/读数, 臂内起手闸保持与 Arole 逐字节同源。
set -u
cd /home/agentuser/AgentFramework
export R477_UPSTREAM_KEY="$(sed -n 's/^AGENTFRAMEWORK_KEYS_DEEPSEEK=//p' .env.local | head -1)"
[ -n "${R477_UPSTREAM_KEY:-}" ] || { echo "[致命] .env.local 未取到 key"; exit 9; }
for i in $(seq 1 24); do
  MA=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  LP=$(pgrep -c -f '[l]lama-server' 2>/dev/null || true)
  echo "[settle] MemAvailable=${MA}MB llama-server=${LP:-0}"
  [ "$MA" -ge 2650 ] && [ "${LP:-0}" -eq 0 ] && break
  sleep 5
done
bash eval/rover/r477/run_arm_real_r477.sh R 48214 48213 || { echo "[r-only] R 失败 rc=$?"; exit 2; }
echo "[r-only] R ok $(date +%H:%M:%S)"
