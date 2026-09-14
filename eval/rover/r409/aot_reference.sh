#!/usr/bin/env bash
# R409: AOT 规范命令复核（参考证据；政策 aot_check_policy=release_tag_only ⇒ 非发布轮不作等级依据）
# 规范命令来源: docs/verification-registry.json → aot.publish.zero_il.evidence_cmd（不带 -p:PublishAot）
cd /home/agentuser/AgentFramework || exit 1
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
LOG=eval/rover/r409/aot-reference.log
{
  echo "=== 规范命令: dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_release（无 -p:PublishAot） ==="
  date -Is
  echo "--- HEAD: $(git rev-parse --short HEAD 2>/dev/null) ---"
  dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_release
  echo "AOT_EXIT=$?"
} > "$LOG" 2>&1
{
  echo "=== 判据 ==="
  echo "IL 警告数(IL2xxx/IL3xxx): $(grep -cE 'warning IL[0-9]{4}' "$LOG")"
  echo "任意 warning 数: $(grep -cE ': warning ' "$LOG")"
  echo "error 数: $(grep -cE ': error ' "$LOG")"
  echo "--- 产物 ---"
  ls -la /tmp/pub_release/agenthost 2>&1
} >> "$LOG" 2>&1
