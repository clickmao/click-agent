#!/usr/bin/env bash
# R418 收尾门: 探针仪器 5 组 selftest + 全量单测 + 形式校验
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
D="$HOME/.dotnet/dotnet"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/probe/tasks.py --selftest 2>&1 | tail -2
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/probe/grade.py --selftest 2>&1 | tail -2
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/probe/run_probe.py --selftest 2>&1 | tail -2
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/probe/process_metrics.py --selftest 2>&1 | tail -2
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/kpi/kpi_probe.py --selftest 2>&1 | tail -2
echo "=== TESTS ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$D" test src/agent.tests/agentframework.tests.csproj -c Release --nologo -v q 2>&1 | tail -6
echo "=== FORMAL (VerificationFormTests) ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$D" test src/agent.tests/agentframework.tests.csproj -c Release --nologo -v q --filter FullyQualifiedName~VerificationFormTests 2>&1 | tail -4
echo "R418_GATES_EXIT=$?"
