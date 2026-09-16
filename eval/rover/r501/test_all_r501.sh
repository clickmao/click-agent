#!/usr/bin/env bash
# R501: src 改动 ⇒ 全量套件 (含形式门禁真名) + 执行数>0 断言 + 构建输出含 error 即失败
set -u
export DOTNET_ROOT="$HOME/.dotnet"
DN="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework
LOG=/tmp/r501_test.log
: >"$LOG"
echo "== build ==" | tee -a "$LOG"
"$DN" build src/agent.host/agent.host.csproj -c Release --nologo 2>&1 | tail -5 | tee -a "$LOG"
echo "== test (全量) ==" | tee -a "$LOG"
"$DN" test src/agent.tests/agentframework.tests.csproj -c Release --nologo 2>&1 | tee -a "$LOG" | tail -25
echo "== 汇总 ==" | tee -a "$LOG"
grep -cE "error [A-Z]+[0-9]+" "$LOG" | sed 's/^/build_error_lines=/' | tee -a "$LOG"
grep -E "^(Passed|Failed)!" "$LOG" | tail -3 | tee -a "$LOG"
python3 - <<'PY' | tee -a "$LOG"
import re, io
t = io.open("/tmp/r501_test.log", encoding="utf-8", errors="replace").read()
m = re.findall(r"(?:Passed|Failed|Total)!\s*-\s*Failed:\s*(\d+),\s*Passed:\s*(\d+),\s*Skipped:\s*(\d+),\s*Total:\s*(\d+)", t)
if not m:
    print("EXEC0 ⇒ 假绿风险: 未取到执行数")
else:
    f, p, s, tot = map(int, m[-1])
    print("EXEC f=%d p=%d s=%d tot=%d" % (f, p, s, tot))
    print("VERDICT=" + ("GREEN" if f == 0 and tot > 0 else "RED"))
PY
