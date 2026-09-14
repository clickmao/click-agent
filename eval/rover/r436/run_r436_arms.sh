#!/usr/bin/env bash
# R436 臂矩阵顺序执行器（单条命令内串行, 每臂独立端口 + 独立 NS）
set -u
cd /home/agentuser/AgentFramework/eval/rover/r436
LOG=/home/agentuser/AgentFramework/eval/rover/r436/arms-run.log
: > "$LOG"
run() {  # run <arm> <ns> <stub> <api>
  echo "===== $(date +%H:%M:%S) ARM=$1 NS=${2:-} =====" | tee -a "$LOG"
  R436_NS="$2" R436_GRID=p12 bash run_arm.sh "$1" "$3" "$4" 2>&1 | tee -a "$LOG"
  echo "[exit=$?] $(date +%H:%M:%S) ARM=$1 NS=${2:-}" | tee -a "$LOG"
  pgrep -af 'llama-server' | grep -v grep | head -3 | tee -a "$LOG"
}
run A   ""    47980 47982
run B   ""    47984 47986
run BP  ""    47988 47990
run BRJ ""    47992 47994
run BRJ -2    47996 47998
echo "===== ALL DONE $(date +%H:%M:%S) =====" | tee -a "$LOG"
