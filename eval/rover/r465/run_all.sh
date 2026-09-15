#!/usr/bin/env bash
# R465 五臂顺序执行 (禁并发 llama-server)
set -u
D=/home/agentuser/AgentFramework/eval/rover/r465
LOG=$D/run_all.log
: > "$LOG"
AVAIL=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "[gate] MemAvailable=${AVAIL}MB" | tee -a "$LOG"
[ "$AVAIL" -lt 2650 ] && { echo "[致命] 内存未过闸 (<2650MB) ⇒ 拒绝起测" | tee -a "$LOG"; exit 9; }
if pgrep -f '[l]lama-server' >/dev/null; then echo "[致命] 已有 llama-server 在跑 ⇒ 拒绝" | tee -a "$LOG"; exit 9; fi
set -- "Arole 47990 47992" "B3B 47994 47996" "R 47998 48000" "R2 48002 48004" "W1 48006 48008"
for spec in "$@"; do
  arm=${spec%% *}; rest=${spec#* }; sp=${rest%% *}; ap=${rest##* }
  echo "=== [$(date +%H:%M:%S)] ARM=$arm stub=$sp api=$ap ===" | tee -a "$LOG"
  bash "$D/run_arm.sh" "$arm" "$sp" "$ap" >> "$LOG" 2>&1
  echo "=== [$(date +%H:%M:%S)] ARM=$arm rc=$? ===" | tee -a "$LOG"
done
python3 -u "$D/settle_r465.py" "$D" ALL 2>&1 | tee -a "$LOG"
echo "=== [$(date +%H:%M:%S)] ALL DONE ===" | tee -a "$LOG"
