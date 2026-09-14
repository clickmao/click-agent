#!/usr/bin/env bash
# R412 AOT 校验（改 agent 链代码后必跑）: 发布原生产物 + 数 IL 警告 + 报体积。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r412 > /tmp/r412_publish.log 2>&1
echo "publish_exit=$?"
echo "IL_warnings=$(grep -cE 'IL[0-9]{4}' /tmp/r412_publish.log || true)"
grep -E 'IL[0-9]{4}' /tmp/r412_publish.log | head -5
echo "--- 产物 ---"
ls -l /tmp/pub_r412 | head -10
