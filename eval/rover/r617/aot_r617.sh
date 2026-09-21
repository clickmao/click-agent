#!/usr/bin/env bash
# R617 AOT 面（派生自 eval/rover/r614/aot_r614.sh，逐条声明差异）:
#   ① 轮号/命名空间 R616→R617，产物目录 pub_r610→pub_r617（本轮 src/ 有改动 ⇒ 必须重发布，禁沿用 R610 冻结件）。
#   ② 装载冒烟 env 增列轴变量两档之一（缺省 = 新块）；轴关档的逐位等价由单测+sha 判据承担，不靠冒烟。
#   ③ 判据一字未改: PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘 ∧ 装载冒烟出回复。
# 判据: PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘 ∧ 装载冒烟（仓库外 cwd）
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ART="$HOME/.agentframework/artifacts/pub_r617"
LOG=/tmp/r617-publish.log
mkdir -p "$ART"

dotnet publish src/agent.host -c Release -r linux-x64 -o "$ART" > "$LOG" 2>&1
PRC=$?
IL=$(grep -c 'warning IL' "$LOG" || true)
ERRC=$(grep -c ': error' "$LOG" || true)
echo "PUBLISH_RC=$PRC IL_WARNINGS=$IL ERRORS=$ERRC"
stat -c 'ELF_BYTES=%s' "$ART/agenthost" 2>/dev/null || echo "ELF_BYTES=missing"
sha256sum "$ART/agenthost" 2>/dev/null | cut -c1-16 || true

# ── 装载冒烟: 仓库外 cwd + env -i；判据 = 二进制可启动并产出回复（非空）──
SM=/tmp/r617aot
rm -rf "$SM"; mkdir -p "$SM/data/nlp"
cp /home/agentuser/AgentFramework/skeptic.rbin "$SM/" 2>/dev/null || true
cp /home/agentuser/AgentFramework/eval/rover/r583/fixture-shapes-line1.txt "$SM/gate-shapes.txt" 2>/dev/null || true
cp "$SM/gate-shapes.txt" "$SM/data/nlp/gate-shapes.txt" 2>/dev/null || true
set -a; . "$HOME/.agentframework/keys.env"; set +a
KNAME="AGENTFRAMEWORK_KEYS_""DEEPSEEK"
KVAL=$(printf '%s' "${!KNAME:-}")
KEYARG="$KNAME=$KVAL"
printf '你好，请用一句话说明你能做什么。\n/exit\n' | timeout 300 env -i \
  HOME="$HOME" PATH=/usr/bin:/bin TERM=dumb \
  DOTNET_ROOT="$DOTNET_ROOT" AGENTFRAMEWORK_R1_CONTRACT=1 \
  "$KEYARG" \
  "$ART/agenthost" --role ./skeptic.rbin --session-id aotsmoke-r617 > "$SM/smoke.out.txt" 2>&1
SRC=$?
echo "SMOKE_RC=$SRC out_bytes=$(wc -c < "$SM/smoke.out.txt")"
TL="$SM/data/telemetry/host.jsonl"
if [ -f "$TL" ]; then
  echo "SMOKE_TELEMETRY_ROWS=$(wc -l < "$TL")"
else
  echo "SMOKE_TELEMETRY_ROWS=n/a"
fi
echo "--- smoke out tail ---"
tail -c 300 "$SM/smoke.out.txt"
