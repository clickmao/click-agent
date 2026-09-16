#!/usr/bin/env bash
# R497 测试链: 全量 → flaky 类定向复跑 (证明与 R497 改动无关)
set -u
export DOTNET_ROOT="$HOME/.dotnet"
DT="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework || exit 1
T=src/agent.tests/agentframework.tests.csproj
run() {
  env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DT" test "$T" -c Debug --nologo "$@" 
}
run > /tmp/r497_tests3.log 2>&1
echo "suite_rc=$?"
grep -E "^(Passed!|Failed!)" /tmp/r497_tests3.log
grep "  Failed " /tmp/r497_tests3.log | head -5
i=0
for cls in TelemetryPendingTests FrontendAskSameConnTests R497FingerprintAndSynonymTests; do
  i=$((i+1))
  run --filter "FullyQualifiedName~$cls" > "/tmp/r497_t_$cls.log" 2>&1
  echo "[$cls] rc=$? $(grep -E '^(Passed!|Failed!)' "/tmp/r497_t_$cls.log" | head -1)"
done
echo "done $(date +%H:%M:%S)"
