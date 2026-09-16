#!/usr/bin/env bash
# R497 前置构建链: 全量单测 (env -u) → AOT 重发布 (IL 警告须 0)
set -u
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
ROOT=/home/agentuser/AgentFramework
cd "$ROOT" || exit 1
PUB=/tmp/pub_r497
echo "=== [1/2] TEST  $(date +%H:%M:%S) ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  "$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Debug --nologo \
  > /tmp/r497_tests.log 2>&1
echo "test_rc=$?"
grep -E "^(Passed!|Failed!|错误|已通过|失败)" /tmp/r497_tests.log | tail -3
grep -cE "^\s+Failed " /tmp/r497_tests.log > /tmp/r497_tests_failedcount.txt 2>/dev/null || true
echo "=== [2/2] AOT PUBLISH  $(date +%H:%M:%S) ==="
rm -rf "$PUB"
"$DOTNET" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o "$PUB" \
  > /tmp/r497_publish.log 2>&1
echo "publish_rc=$?"
echo "IL_warnings=$(grep -cE 'IL[0-9]{4}' /tmp/r497_publish.log)"
grep -E "IL[0-9]{4}" /tmp/r497_publish.log | head -5
if [ -x "$PUB/agenthost" ]; then
  echo "host_sha256=$(sha256sum "$PUB/agenthost" | cut -d' ' -f1)"
  echo "host_bytes=$(stat -c %s "$PUB/agenthost")"
fi
echo "=== DONE $(date +%H:%M:%S) ==="
