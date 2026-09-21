#!/usr/bin/env bash
# R619 AOT 面（派生自 eval/rover/r618/aot_r618.sh，逐条声明差异）:
#   ① 轮号/命名空间 R618→R619，产物目录 pub_r618→pub_r619（本轮 src/ 有改动 ⇒ 必须重发布，禁沿用冻结件）。
#   ② 冒烟 **两档**（新增）：轴缺省（off）与轴显式开（=1，含本轮回退语义）各跑一次 ⇒ 两条路径都验证「可装载 + 出非空回复」。
#      判据一字未改: 每档 PUBLISH 前置条件同前 ⇒ rc=0 ∧ 回复字节 > 0。
#   ③ 判据一字未改: PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘 ∧ 装载冒烟出回复。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ART="$HOME/.agentframework/artifacts/pub_r619"
LOG=/tmp/r619-publish.log
mkdir -p "$ART"

dotnet publish src/agent.host -c Release -r linux-x64 -o "$ART" > "$LOG" 2>&1
PRC=$?
IL=$(grep -c 'warning IL' "$LOG" || true)
ERRC=$(grep -c ': error' "$LOG" || true)
echo "PUBLISH_RC=$PRC IL_WARNINGS=$IL ERRORS=$ERRC"
stat -c 'ELF_BYTES=%s' "$ART/agenthost" 2>/dev/null || echo "ELF_BYTES=missing"
sha256sum "$ART/agenthost" 2>/dev/null | cut -c1-16 || true

set -a; . "$HOME/.agentframework/keys.env"; set +a
KNAME="AGENTFRAMEWORK_KEYS_""DEEPSEEK"
KVAL=$(printf '%s' "${!KNAME:-}")
KEYARG="$KNAME=$KVAL"

smoke() {
  local tag="$1"; shift
  local SM="/tmp/r619aot-$tag"
  rm -rf "$SM"; mkdir -p "$SM/data/nlp"
  cp "$HOME/AgentFramework/skeptic.rbin" "$SM/" 2>/dev/null || true
  cp "$HOME/AgentFramework/eval/rover/r583/fixture-shapes-line1.txt" "$SM/gate-shapes.txt" 2>/dev/null || true
  cp "$SM/gate-shapes.txt" "$SM/data/nlp/gate-shapes.txt" 2>/dev/null || true
  printf '你好，请用一句话说明你能做什么。\n/exit\n' | timeout 300 env -i \
    HOME="$HOME" PATH=/usr/bin:/bin TERM=dumb \
    DOTNET_ROOT="$DOTNET_ROOT" AGENTFRAMEWORK_R1_CONTRACT=1 \
    "$KEYARG" "$@" \
    "$ART/agenthost" --role ./skeptic.rbin --session-id "aotsmoke-r619-$tag" > "$SM/smoke.out.txt" 2>&1
  local SRC=$?
  echo "SMOKE[$tag]_RC=$SRC out_bytes=$(wc -c < "$SM/smoke.out.txt")"
  local TL="$SM/data/telemetry/host.jsonl"
  if [ -f "$TL" ]; then echo "SMOKE[$tag]_TELEMETRY_ROWS=$(wc -l < "$TL")"; else echo "SMOKE[$tag]_TELEMETRY_ROWS=n/a"; fi
  echo "--- smoke[$tag] out tail ---"
  tail -c 300 "$SM/smoke.out.txt"
  echo
}

smoke off
smoke on "AGENTFRAMEWORK_R1_ACTION_EXEC=1"
echo "AOT_R619_DONE"
