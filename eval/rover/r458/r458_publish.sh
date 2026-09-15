#!/usr/bin/env bash
# R458 AOT 重发布 (改链代码后必做) + 原生形态自证。
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
cd /home/agentuser/AgentFramework
rm -rf /tmp/pub_r458
"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r458 2>&1 | tail -12
echo "=== AOT 原生自证 (env -i, 无 IL 负控由既有 AOT 门覆盖) ==="
printf '/exit\n' | timeout 30 env -i /tmp/pub_r458/agenthost --version; echo "  rc=$?"
ls -l /tmp/pub_r458/agenthost | awk '{print "  size="$5" B"}'
