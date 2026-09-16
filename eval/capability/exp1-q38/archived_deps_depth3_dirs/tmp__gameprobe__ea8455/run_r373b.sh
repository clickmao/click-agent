#!/usr/bin/env bash
# R373 修复后: 全量测试 + AOT 发布 + 真机探针 (首轮预算策略)
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
echo "=== 全量测试 ==="
dotnet test src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | grep -E "Passed!|Failed!|error CS" | tail -3
echo "=== AOT 发布 ==="
rm -rf /tmp/pub_r373b
dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r373b > /tmp/pub_r373b.log 2>&1
echo "IL_WARN=$(grep -cE 'IL[0-9]{4}' /tmp/pub_r373b.log)"
ls -l /tmp/pub_r373b/agenthost | awk '{print "BIN_BYTES="$5}'
ls /tmp/pub_r373b/config/base/ 2>/dev/null | head -2
echo "=== 修复后真机探针 ==="
bash /tmp/gameprobe/probe_r373b.sh
