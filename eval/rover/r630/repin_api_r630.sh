#!/usr/bin/env bash
# R630 · API 基线重生成 + 差异收窄检查（派生自 eval/rover/r618/repin_api_r618.sh，仅轮号/路径替换）
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
cp docs/api-surface.baseline.txt /tmp/api-base-before-r630.txt
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  AGENTFRAMEWORK_API_BASELINE_WRITE=1 \
  timeout 400 "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj \
  --no-build --filter "FullyQualifiedName~PublicApiSurface" --nologo -v q 2>&1 | tail -5
echo "=== diff (only R630 lines expected) ==="
diff /tmp/api-base-before-r630.txt docs/api-surface.baseline.txt | head -40
echo "changed_lines=$(diff /tmp/api-base-before-r630.txt docs/api-surface.baseline.txt | grep -c '^[<>]')"
