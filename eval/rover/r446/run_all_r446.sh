#!/usr/bin/env bash
# R446 三臂串行批 (同网格 M20, 同二进制 /tmp/pub_r446/agenthost)
#   A(-s1) 分母臂 / BRJ(-s2) 基线 / BRJC(-s3) 判官紧凑 prompt
# 内存起手闸: MemAvailable >= 2650 MB (导出下界: llama RSS 2.39G + 余量)
set -u
cd /home/agentuser/AgentFramework || exit 1
AV=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "[$(date +%H:%M:%S)] R446 批次启动  MemAvailable=${AV}MB"
if [ "$AV" -lt 2650 ]; then echo "[致命] 内存起手闸红 (${AV}MB < 2650MB)"; exit 4; fi
run() { # arm ns stub api
  echo "[$(date +%H:%M:%S)] >>> arm=$1 ns=$2"
  R446_GRID=M20 R446_NS="$2" bash eval/rover/r446/run_arm_r446.sh "$1" "$3" "$4" >> /tmp/r446_arms.log 2>&1
  echo "[$(date +%H:%M:%S)] <<< arm=$1 rc=$?"
}
run A    -s1 48350 48352
run BRJ  -s2 48360 48362
run BRJC -s3 48370 48372
echo "[$(date +%H:%M:%S)] R446 批次结束"
