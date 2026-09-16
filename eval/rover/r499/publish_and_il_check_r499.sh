#!/usr/bin/env bash
# R499 AOT 重发布 + IL 检查 + 特征存在性机检
# 方法更正 (R499): AOT 二进制里 **环境变量字面量不可明文 grep** (UTF-8/UTF-16 均 0 命中,
# 见 /tmp/r499_strprobe.py) ⇒ 存在性判据改用 **元数据类型/方法名表** (ascii 文本),
# 环境变量串命中只作信息项, 不作拒跑依据。
set -u
cd /home/agentuser/AgentFramework || exit 1
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
OUT=/tmp/pub_r499
LOG=/tmp/r499_publish.log
"$DOTNET_ROOT/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o "$OUT" >"$LOG" 2>&1
rc=$?
echo "PUBLISH_RC=$rc"
echo "IL_WARN_LINES=$(grep -ciE 'warning IL[0-9]' "$LOG")"
echo "ERROR_LINES=$(grep -ciE ': error ' "$LOG")"
[ "$rc" -eq 0 ] || { echo "[致命] 发布失败"; exit 1; }
ls -l "$OUT/agenthost" | awk '{print "BIN_BYTES="$5}'
sha256sum "$OUT/agenthost" | cut -c1-16 | sed 's/^/BIN_SHA16=/'
python3 - "$OUT/agenthost" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
need = ["LocalParaphraseChannel", "ReplayPairTrim", "ToolDeclGate", "LocalDecisionLedger",
        "MicroStepIsolationGate", "ActionLoop", "IndustrialAgentV2"]
bad = []
for k in need:
    n = data.count(k.encode("ascii"))
    print("CLASS %-26s = %d" % (k, n))
    if n == 0:
        bad.append(k)
print("CLASS_MISSING=" + ",".join(bad))
sys.exit(1 if bad else 0)
PY
cls=$?
echo "CLASS_CHECK_RC=$cls"
[ "$cls" -eq 0 ] || { echo "[致命] 特征类名缺失 ⇒ 拒跑"; exit 1; }
printf '/exit\n' | timeout 30 env -i "$OUT/agenthost" --version >/tmp/r499_smoke.txt 2>&1
echo "SMOKE_RC=$?"
head -1 /tmp/r499_smoke.txt
