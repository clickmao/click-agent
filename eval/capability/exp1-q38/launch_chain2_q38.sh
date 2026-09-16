#!/usr/bin/env bash
# 把 Q38 三面等待链**脱离本会话**启动 (setsid 在脚本内部 ⇒ 命令本身只是 `bash <本文件>`)。
# 动机: cron 会话结束会回收其后台进程 ⇒ 长等待链必须脱离会话才能在下轮被接管。
set -u
cd /home/agentuser/AgentFramework
for p in $(ps -eo pid,args | grep -E 'chain_wait_and_run[_]q38\.sh' | grep -v grep | awk '{print $1}'); do
  kill "$p" 2>/dev/null && echo "killed old chain pid=$p"
done
setsid nohup bash eval/capability/exp1-q38/chain_wait_and_run2_q38.sh > /tmp/q38_chain2.out 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 2
pgrep -af 'chain_wait_and_run2[_]q38' | head -2
echo "LAUNCH_DONE $(date -Is)"
