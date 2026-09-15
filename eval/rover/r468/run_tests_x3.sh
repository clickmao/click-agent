#!/usr/bin/env bash
# R468 形式校验: 全量单测 ×3 (候选④ 顺序隔离: 判据 = 连续 3 次全绿且执行数一致)
set -u
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$HOME/.dotnet:$PATH"
cd /home/agentuser/AgentFramework
LOG=/tmp/r468_tests_x3.log
: > "$LOG"
for i in 1 2 3; do
  echo "===== RUN $i =====" >> "$LOG"
  timeout 900 "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release --no-build 2>&1 \
    | grep -E "^(Passed!|Failed!|  Failed |A total of)" >> "$LOG"
  echo "rc=$?" >> "$LOG"
done
echo "===== DONE =====" >> "$LOG"
grep -cE "^(Passed!|Failed!)" "$LOG"
