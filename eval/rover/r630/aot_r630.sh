#!/usr/bin/env bash
# R630 AOT 面（派生自 eval/rover/r618/aot_r618.sh，逐条声明差异）:
#   ① 轮号/命名空间 R618→R630，产物目录 pub_r618→pub_r630（本轮 src/ 有改动 ⇒ 必须重发布，禁沿用冻结件）。
#   ② 冒烟两次：缺省档（轴关）+ `AGENTFRAMEWORK_R1_ACTION_PROMPT=spec`（轴开）——
#      判据 = 两次都不出现 rc=6 prefix_drift（轴开档的 fail-closed 漂移闸必须认得 16182 字符的新钉子）。
#   ③ 判据一字未改: PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘 ∧ 装载冒烟出回复。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ART="$HOME/.agentframework/artifacts/pub_r630"
LOG=/tmp/r630-publish.log
mkdir -p "$ART"

dotnet publish src/agent.host -c Release -r linux-x64 -o "$ART" > "$LOG" 2>&1
PRC=$?
IL=$(grep -c 'warning IL' "$LOG" || true)
ERRC=$(grep -c ': error' "$LOG" || true)
echo "PUBLISH_RC=$PRC IL_WARNINGS=$IL ERRORS=$ERRC"
stat -c 'ELF_BYTES=%s' "$ART/agenthost" 2>/dev/null || echo "ELF_BYTES=missing"
sha256sum "$ART/agenthost" 2>/dev/null | cut -c1-16 || true

# ── 装载冒烟: 仓库外 cwd + env -i；判据 = 二进制可启动并产出回复（非空）──
set -a; . "$HOME/.agentframework/keys.env"; set +a
KNAME="AGENTFRAMEWORK_KEYS_""DEEPSEEK"
KVAL=$(printf '%s' "${!KNAME:-}")
KEYARG="$KNAME=$KVAL"
for MODE in off spec; do
  SM=/tmp/r630aot-$MODE
  rm -rf "$SM"; mkdir -p "$SM/data/nlp"
  cp /home/agentuser/AgentFramework/eval/rover/r583/fixture-shapes-line1.txt "$SM/gate-shapes.txt" 2>/dev/null || true
  cp "$SM/gate-shapes.txt" "$SM/data/nlp/gate-shapes.txt" 2>/dev/null || true
  if [ "$MODE" = "spec" ]; then
    AXENV=(AGENTFRAMEWORK_R1_ACTION_PROMPT=spec)
  else
    AXENV=()
  fi
  printf '你好，请用一句话说明你能做什么。\n/exit\n' | timeout 300 env -i \
    HOME="$HOME" PATH=/usr/bin:/bin TERM=dumb \
    DOTNET_ROOT="$DOTNET_ROOT" AGENTFRAMEWORK_R1_CONTRACT=1 \
    "${AXENV[@]}" \
    "$KEYARG" \
    "$ART/agenthost" --session-id aotsmoke-r630-$MODE > "$SM/smoke.out.txt" 2>&1
  SRC=$?
  echo "MODE=$MODE SMOKE_RC=$SRC out_bytes=$(wc -c < "$SM/smoke.out.txt")"
  echo "MODE=$MODE drift_rc6_hits=$(grep -c 'prefix_drift' "$SM/smoke.out.txt" || true)"
done
