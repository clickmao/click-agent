#!/usr/bin/env bash
# 脱离本会话启动 Q38 末轮重跑链 (setsid 在脚本内部)。
set -u
cd /home/agentuser/AgentFramework
for p in $(ps -eo pid,args | grep -E 'chain_wait_and_run[23][_]q38\.sh' | grep -v grep | awk '{print $1}'); do
  kill "$p" 2>/dev/null && echo "killed pid=$p"
done
setsid nohup bash eval/capability/exp1-q38/chain_wait_and_run3_q38.sh > /tmp/q38_chain3.out 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 2
pgrep -af 'chain_wait_and_run3[_]q38' | head -2
echo "LAUNCH3_DONE $(date -Is)"
