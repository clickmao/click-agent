#!/usr/bin/env bash
# R486 形式门禁 (对侧窗口退场后补跑): 构建 + 形式门禁三真名 + 执行数>0 断言 (假绿拦截) + 全量单测
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework
echo "=== 构建 (Release) ==="
"$DOTNET" build src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | tail -3
echo "=== 形式门禁 (真名: VerificationFormTests|DevPlanDocRefTests|SkillGeneralizationTests) ==="
res=$("$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~VerificationFormTests|FullyQualifiedName~DevPlanDocRefTests|FullyQualifiedName~SkillGeneralizationTests" 2>&1)
echo "$res" | tail -4
n=$(echo "$res" | grep -oE "Passed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
f=$(echo "$res" | grep -oE "Failed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
if [ -n "${n:-}" ] && [ "$n" -gt 0 ]; then echo "  [OK] 执行数=$n failed=${f:-0}"; else echo "  [VOID] 执行数=0 ⇒ 假绿"; exit 1; fi
[ "${f:-0}" = "0" ] || { echo "  [RED] 形式门禁有失败用例"; exit 2; }
echo "=== 全量单测 ==="
"$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build 2>&1 | tail -3
echo "GATE_DONE"
