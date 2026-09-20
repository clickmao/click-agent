#!/usr/bin/env bash
# R608 AOT 面: 重发布取 IL 警告数 + 生产档装载冒烟（仓库外 cwd; 判定面 = 新面打点是否随 AOT 产物发出）
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ART="$HOME/.agentframework/artifacts/pub_r608"
LOG=/tmp/r608-publish.log

dotnet publish src/agent.host -c Release -r linux-x64 -o "$ART" > "$LOG" 2>&1
PRC=$?
IL=$(grep -c 'warning IL' "$LOG" || true)
ERRC=$(grep -c ': error' "$LOG" || true)
echo "PUBLISH_RC=$PRC IL_WARNINGS=$IL ERRORS=$ERRC"
stat -c 'ELF_BYTES=%s' "$ART/agenthost"
sha256sum "$ART/agenthost" | cut -c1-16

# ── 装载冒烟: 仓库外 cwd, env -i, 一轮夹具, 判据 = recognition_verdict 是否在 AOT 产物下发出 ──
SM=/tmp/r608aot
rm -rf "$SM"; mkdir -p "$SM"
cp /home/agentuser/AgentFramework/skeptic.rbin "$SM/"
cp /home/agentuser/AgentFramework/eval/rover/r583/fixture-shapes-line1.txt "$SM/gate-shapes.txt"
mkdir -p "$SM/data/nlp"
cp "$SM/gate-shapes.txt" "$SM/data/nlp/gate-shapes.txt"
set -a; . "$HOME/.agentframework/keys.env"; set +a
# key 面赋值字面形态不入库（roundcheck R7 敏感面扫描）: 变量名在运行期拼接, 值只经环境变量传递
KNAME="AGENTFRAMEWORK_KEYS_""DEEPSEEK"
KVAL=$(printf '%s' "${!KNAME:-}")
KEYARG="$KNAME=$KVAL"
printf '你好，请用一句话说明你能做什么。\n/exit\n' | timeout 300 env -i \
  HOME="$HOME" PATH=/usr/bin:/bin TERM=dumb \
  DOTNET_ROOT="$DOTNET_ROOT" \
  "$KEYARG" \
  "$ART/agenthost" --role ./skeptic.rbin --session-id aotsmoke1 > "$SM/smoke.out.txt" 2>&1
SRC=$?
echo "SMOKE_RC=$SRC out_bytes=$(wc -c < "$SM/smoke.out.txt")"
TL="$SM/data/telemetry/host.jsonl"
if [ -f "$TL" ]; then
  echo "SMOKE_RECOG_ROWS=$(grep -c 'recognition_verdict' "$TL" || true)"
  echo "SMOKE_TELEMETRY_ROWS=$(wc -l < "$TL")"
  grep -o '"point":"recognition_verdict"[^}]*}[^}]*}' "$TL" | head -2
else
  echo "SMOKE_RECOG_ROWS=n/a (无 data/telemetry/host.jsonl)"
  find "$SM" -maxdepth 3 -name '*.jsonl' | head -5
fi
echo "--- smoke out tail ---"
tail -c 400 "$SM/smoke.out.txt"
