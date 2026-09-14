#!/usr/bin/env bash
# R414 收尾: AOT 重发布 (改链代码后必做) + 0 IL 警告核对 + 产物大小
set -u
export DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework || exit 1
LOG=/tmp/r414-aot.log
rm -rf /tmp/pub_r414
"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r414 > "$LOG" 2>&1
echo "PUBLISH_EXIT=$?" >> "$LOG"
echo "IL_WARN=$(grep -c 'IL[0-9][0-9][0-9][0-9]' "$LOG")" >> "$LOG"
ls -la /tmp/pub_r414/agenthost >> "$LOG" 2>&1
echo "DONE"
