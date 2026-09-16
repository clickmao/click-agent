#!/usr/bin/env bash
# EXP1-Q42 step 7 (M3): 形式门禁 (登记表/证据改动后当轮必跑)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
D=eval/capability/exp1-q42
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" \
  --nologo -v q > "$D/form_gate_q42.txt" 2>&1
rc=$?
echo "FORM_GATE_rc=$rc"
tail -12 "$D/form_gate_q42.txt" | cut -c1-200
awk '/MemAvailable/{printf "MemAvailable_MB=%d\n",$2/1024}' /proc/meminfo
