#!/usr/bin/env bash
# R608 器具修复验证: ① key 面字面形态已清除 ② JIT 构建读数落盘(0 Error(s)) ③ AOT 脚本重跑(发布+冒烟)并比对 sha
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
RD=eval/rover/r608

echo "=== ① R7 敏感面扫描（用 roundcheck 自身的 scan_secrets） ==="
python3 - <<'PY'
import sys
sys.path.insert(0, 'tools/roundcheck')
import roundcheck
for p in ['eval/rover/r608/aot_r608.sh', 'eval/rover/r608/run_r608.sh']:
    t = open(p, encoding='utf-8', errors='replace').read()
    print(p, '=>', roundcheck.scan_secrets(t) or 'CLEAN')
PY

echo "=== ② JIT 构建读数落盘 ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet build src/agent.host/agent.host.csproj -c Release --nologo -v q > "$RD/build-jit-r608.log" 2>&1
echo "JIT_BUILD_RC=$?"
grep -E "Warning\(s\)|Error\(s\)" "$RD/build-jit-r608.log" | tail -2

echo "=== ③ AOT 脚本重跑（发布 + 生产档装载冒烟） ==="
bash "$RD/aot_r608.sh" 2>&1 | tail -12
