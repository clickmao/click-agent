#!/usr/bin/env bash
# R461: 构建 + 真名过滤单测。
# 假绿防线: ① 构建输出出现 "error" ⇒ 立即失败退出 (禁在旧 dll 上跑测试);
#           ② 断言执行数 > 0 (0 匹配 rc=0 也是假绿)。
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework

build() { # $1=proj $2=tag
  local out; out=$("$DOTNET" build "$1" -c Release 2>&1)
  echo "$out" | tail -4
  if echo "$out" | grep -qE ": error "; then
    echo "[VOID] $2 构建失败 —— 后续测试不执行 (禁假绿)"; exit 1
  fi
  echo "  [$2] 0 error"
}

echo "=== build agent ===";  build src/agent/agent.csproj Release
echo "=== build tests ===";  build src/agent.tests/agentframework.tests.csproj tests

echo "=== 过滤单测 (真名) ==="
res=$("$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~ContinuationBriefTests|FullyQualifiedName~FormalPromptContractTests|FullyQualifiedName~ArtifactRepairTests|FullyQualifiedName~SessionHistorySearchTests|FullyQualifiedName~PlanResumeTests" 2>&1)
echo "$res" | tail -6
passed=$(echo "$res" | grep -oE "Passed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
if [ -z "${passed:-}" ] || [ "$passed" -lt 1 ]; then
  echo "[VOID] 执行数 = 0/未知 ⇒ 假绿, 判不通过"; exit 1
fi
echo "  [OK] 执行数 = $passed (>0)"
