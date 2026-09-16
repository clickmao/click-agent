#!/usr/bin/env bash
# R492 AOT 重发布 + IL 警告机检 + 闸字样机检 + 冷启冒烟 (禁 push 环境, 只本地)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
OUT=/tmp/pub_r492
$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o "$OUT" > /tmp/pub_r492_il.log 2>&1
RC=$?
echo "publish_rc=$RC"
echo "IL_warnings=$(grep -c 'warning IL' /tmp/pub_r492_il.log)"
echo "all_warnings=$(grep -c 'warning' /tmp/pub_r492_il.log)"
echo "errors=$(grep -c ' error ' /tmp/pub_r492_il.log)"
[ -x "$OUT/agenthost" ] || { echo "[致命] 未产出 agenthost"; exit 5; }
echo "size_r492=$(stat -c %s "$OUT/agenthost")"
sha256sum "$OUT/agenthost" | cut -c1-24
# 闸字样机检: 新码必须编进产物, 否则臂里 export 无效 (= 静默假阴性)
echo "gate_str_tooldecl=$(grep -ac AGENTFRAMEWORK_TOOL_DECL_GATE "$OUT/agenthost" || true)"
echo "gate_str_pairtrim=$(grep -ac AGENTFRAMEWORK_REPLAY_PAIR_TRIM "$OUT/agenthost" || true)"
# 冷启冒烟 (env -i 原生, /exit 退出)
printf '/exit\n' | timeout 30 env -i HOME="$HOME" DOTNET_ROOT="$HOME/.dotnet" AGENTFRAMEWORK_KEYS_DEEPSEEK=dummy "$OUT/agenthost" --version
echo "smoke_rc=$?"
tail -3 /tmp/pub_r492_il.log
