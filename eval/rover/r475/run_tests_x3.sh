#!/usr/bin/env bash
# R475 全量单测 ×3 (连续顺序隔离, R468 §候选④ 口径) —— 判据: 每次 Failed: 0 且执行数一致。
set -u
export DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework
LOG=/tmp/r475_tests_x3.log
: > "$LOG"
for i in 1 2 3; do
  echo "=== run $i $(date -Is) ===" >> "$LOG"
  "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Debug --nologo \
    >> "$LOG" 2>&1
  echo "rc=$? run=$i" >> "$LOG"
done
cp -f "$LOG" /home/agentuser/AgentFramework/eval/rover/r475/tests_x3_r475.log
grep -E "^(Failed!|Passed!|rc=)" "$LOG" | tail -20
