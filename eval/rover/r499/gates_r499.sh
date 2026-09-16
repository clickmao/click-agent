#!/usr/bin/env bash
# R499 形式门禁 (三真名 + 执行数>0 断言; 本轮无 src 改动, 故不跑全量套件, 如实登记)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
OUT=/tmp/r499_gate.txt
: >"$OUT"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  "$DOTNET_ROOT/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release \
  --filter "FullyQualifiedName~VerificationFormTests|FullyQualifiedName~DevPlanDocRefTests|FullyQualifiedName~SkillGeneralizationTests" \
  2>&1 | tee "$OUT" | tail -6
rc=${PIPESTATUS[0]}
err=$(grep -ciE ": error " "$OUT" || true)
passed=$(grep -oE "Passed:\s*[0-9]+" "$OUT" | tail -1 | tr -dc '0-9')
failed=$(grep -oE "Failed:\s*[0-9]+" "$OUT" | tail -1 | tr -dc '0-9')
echo "GATE_RC=$rc ERR_LINES=$err PASSED=${passed:-0} FAILED=${failed:-0}"
[ "$err" -eq 0 ] || { echo "[致命] 构建/测试输出含 error"; exit 1; }
[ "${passed:-0}" -gt 0 ] || { echo "[致命] 执行数=0 (假绿)"; exit 1; }
[ "${failed:-0}" -eq 0 ] || { echo "[致命] 有失败"; exit 1; }
echo "形式门禁: 绿"
