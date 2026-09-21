#!/usr/bin/env bash
# R614 AOT 面: 重发布 R610 被测件（src/tools 与 R610 提交 bc6a74de 零 diff）⇒ pub_r610/agenthost
# 判据: PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘 ∧ 装载冒烟（仓库外 cwd）
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ART="$HOME/.agentframework/artifacts/pub_r610"
LOG=/tmp/r614-publish.log
mkdir -p "$ART"

dotnet publish src/agent.host -c Release -r linux-x64 -o "$ART" > "$LOG" 2>&1
PRC=$?
IL=$(grep -c 'warning IL' "$LOG" || true)
ERRC=$(grep -c ': error' "$LOG" || true)
echo "PUBLISH_RC=$PRC IL_WARNINGS=$IL ERRORS=$ERRC"
stat -c 'ELF_BYTES=%s' "$ART/agenthost" 2>/dev/null || echo "ELF_BYTES=missing"
sha256sum "$ART/agenthost" 2>/dev/null | cut -c1-16 || true

# ── 装载冒烟: 仓库外 cwd + env -i；判据 = 二进制可启动并产出回复（非空），且动作候选三计数可发出 ──
SM=/tmp/r614aot
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
  "$ART/agenthost" --role ./skeptic.rbin --session-id aotsmoke-r614 > "$SM/smoke.out.txt" 2>&1
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
