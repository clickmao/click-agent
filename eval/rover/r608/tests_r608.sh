#!/usr/bin/env bash
# R608 全量单测（含形式门禁族）+ 形式门禁定向跑，分别落盘 rc 与摘要。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
OUT=/tmp/r608-tests.log
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj --nologo -v q > "$OUT" 2>&1
echo "FULL_RC=$?"
grep -E "^(Passed!|Failed!|Total tests|  Failed)" "$OUT" | head -5
echo "FAILED_NAMES:"
grep -E "^\[xUnit.net .*\] +agent\.tests\." "$OUT" | head -20
echo "FORM_GATE:"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q 2>&1 | tail -3
echo "FORM_RC=$?"
