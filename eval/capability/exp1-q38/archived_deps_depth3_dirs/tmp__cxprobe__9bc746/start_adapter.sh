#!/usr/bin/env bash
# 起适配器(48613) —— 用 pidfile 管理，避免 pgrep -f 自匹配
set -uo pipefail
set -a; . /home/agentuser/AgentFramework/.env.local; set +a
PIDF=/tmp/cxprobe/adapter.pid
if [ -f "$PIDF" ]; then kill -9 "$(cat "$PIDF")" 2>/dev/null; sleep 1; fi
cd /tmp/cxprobe
DEMO_OUT=/tmp/r455_env/logs/adapter setsid nohup python3 /home/agentuser/AgentFramework/eval/rover/r455/adapter_tools.py 48615 > /tmp/cxprobe/adapter455c.log 2>&1 &
echo $! > "$PIDF"
sleep 3
echo "pid=$(cat $PIDF)"; cat /tmp/cxprobe/adapter455c.log
