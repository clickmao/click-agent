#!/usr/bin/env bash
# R527 AOT 证据落盘
cd /home/agentuser/AgentFramework || exit 1
OUT=eval/rover/r527/evidence/aot-r527.txt
{
  echo "# R527 AOT 重发布证据 (铁律: 改链代码后必 AOT + IL 警告 0)"
  date -Is
  echo
  echo "## 命令"
  echo '$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r527'
  echo
  echo "## 结果"
  grep -E "agent.host ->|RC=" /tmp/r527/aot-r527.log | tail -3
  echo "IL 警告数: $(grep -cE 'warning IL[0-9]{4}' /tmp/r527/aot-r527.log)"
  echo
  echo "## 产物"
  ls -l /tmp/pub_r527/agenthost
  sha256sum /tmp/pub_r527/agenthost
  echo
  echo "## 基线 (R526 AOT)"
  ls -l /tmp/pub_r526/agenthost 2>/dev/null
  sha256sum /tmp/pub_r526/agenthost 2>/dev/null
  echo
  echo "## smoke (-q /help, 冷启动)"
  timeout 120 /tmp/pub_r527/agenthost -q /help 2>&1 | head -4
  echo "smoke_rc=$?"
} > "$OUT" 2>&1
tail -14 "$OUT"
