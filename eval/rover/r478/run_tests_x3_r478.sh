#!/usr/bin/env bash
# R478 全量单测 x3（含形式门禁）；结果落 /tmp/tests_r478_run{1,2,3}.log
set -u
export DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework
DN="$HOME/.dotnet/dotnet"
for i in 1 2 3; do
  "$DN" test src/agent.tests/agentframework.tests.csproj -c Release --no-build > "/tmp/tests_r478_run${i}.log" 2>&1
  rc=$?
  echo "run${i}_rc=${rc}"
  grep -E "Passed!|Failed!" "/tmp/tests_r478_run${i}.log" | tail -1
done
