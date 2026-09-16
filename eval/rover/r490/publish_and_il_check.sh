#!/usr/bin/env bash
# R490 AOT 重发布 + IL 警告机检 (单一源: 发布日志 → 计数)。禁 push 环境下只本地。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r490 > /tmp/pub_r490_il.log 2>&1
RC=$?
echo "publish_rc=$RC"
echo "IL_warnings=$(grep -c 'warning IL' /tmp/pub_r490_il.log)"
echo "all_warnings=$(grep -c 'warning' /tmp/pub_r490_il.log)"
echo "size_r490=$(stat -c %s /tmp/pub_r490/agenthost)"
if [ -f /tmp/pub_r489/agenthost ]; then echo "size_r489=$(stat -c %s /tmp/pub_r489/agenthost)"; else echo "size_r489=n/a"; fi
sha256sum /tmp/pub_r490/agenthost | cut -c1-16
tail -3 /tmp/pub_r490_il.log
