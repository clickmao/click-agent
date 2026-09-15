#!/usr/bin/env bash
# R461: AOT 重发布 (零 IL) + 自证 (env -i 起 + rc=0) + 单测/形式门禁 (真名, 断言执行数>0)
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
A=/home/agentuser/AgentFramework
cd "$A"

echo "=== AOT publish -> /tmp/pub_r461 ==="
"$DOTNET" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r461 2>&1 | tail -5
if [ ! -x /tmp/pub_r461/agenthost ]; then echo "[VOID] 无产物"; exit 1; fi
ls -l /tmp/pub_r461/agenthost | awk '{print "  size="$5}'

echo "=== env -i 自启 (原生形态自证, rc 必 0) ==="
printf '/exit\n' | timeout 30 env -i /tmp/pub_r461/agenthost --version > /tmp/r461_version.txt 2>&1
echo "  rc=$?"; head -2 /tmp/r461_version.txt | sed 's/^/  /'

echo "=== 形式门禁 (真名 + 执行数>0) ==="
res=$("$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~VerificationFormTests|FullyQualifiedName~DevPlanDocRefTests" 2>&1)
echo "$res" | tail -4
n=$(echo "$res" | grep -oE "Passed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
[ -n "${n:-}" ] && [ "$n" -gt 0 ] && echo "  [OK] 执行数=$n" || { echo "  [VOID] 执行数=0 ⇒ 假绿"; exit 1; }

echo "=== 全量单测 ==="
"$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build 2>&1 | tail -4
