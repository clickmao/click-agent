#!/usr/bin/env bash
# R618 · API 基线重生成 + 差异收窄检查
set -uo pipefail
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
cp docs/api-surface.baseline.txt /tmp/api-base-before-r618.txt
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  AGENTFRAMEWORK_API_BASELINE_WRITE=1 \
  timeout 400 "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj \
  --no-build --filter "FullyQualifiedName~PublicApiSurface" --nologo -v q 2>&1 | tail -5
echo "=== diff (only R618 lines expected) ==="
diff /tmp/api-base-before-r618.txt docs/api-surface.baseline.txt | head -40
echo "changed_lines=$(diff /tmp/api-base-before-r618.txt docs/api-surface.baseline.txt | grep -c '^[<>]')"
