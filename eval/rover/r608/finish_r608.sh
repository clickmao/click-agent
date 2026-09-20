#!/usr/bin/env bash
# R608 收口门禁: status_gen 重生成 + --check / decl_sweep --check / 形式门禁定向
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
echo "=== status_gen (regen) ==="
python3 eval/capability/status_gen.py > /tmp/r608-statusgen.log 2>&1
echo "REGEN_RC=$?"
echo "=== status_gen --check ==="
python3 eval/capability/status_gen.py --check 2>&1 | tail -6
echo "=== decl_sweep --check ==="
python3 eval/capability/decl_sweep.py --check 2>&1 | tail -3
echo "=== 形式门禁 ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" \
  --nologo -v q 2>&1 | tail -3
