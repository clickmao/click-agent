#!/usr/bin/env bash
# R458 构建+定向单测 —— 构建失败必须**显式失败** (R458 run1 教训: 无 set -e + --no-build ⇒ 陈旧二进制假绿)。
set -euo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
cd /home/agentuser/AgentFramework
echo "=== build ==="
"$HOME/.dotnet/dotnet" build src/agent.tests/agentframework.tests.csproj -c Release -v q --nologo 2>&1 | tail -25
echo "=== test (构建成功才会走到这里) ==="
"$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release --no-build --filter "ContinuationBriefTests" --logger "console;verbosity=normal" 2>&1 | tail -40
