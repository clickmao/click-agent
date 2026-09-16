#!/usr/bin/env bash
# R501 AOT 重发布 + IL 检查 + 特征存在性机检
# 方法沿用 R499 更正: AOT 二进制里环境变量字面量**不可**明文 grep ⇒ 存在性判据用
# **元数据类型/方法名表** (ascii 文本); 环境变量串命中只作信息项。
# R501 追加: 改写族豁免是**表达式级**改动 ⇒ 类名表不变, 故另加「行为面判据」(由真机遥测给)。
set -u
cd /home/agentuser/AgentFramework || exit 1
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
OUT=/tmp/pub_r501
LOG=/tmp/r501_publish.log
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
printf '/exit\n' | timeout 30 env -i "$OUT/agenthost" --version >/tmp/r501_smoke.txt 2>&1
echo "SMOKE_RC=$?"
head -1 /tmp/r501_smoke.txt
