#!/usr/bin/env bash
# R639 起臂包装（keys 载入 + DOTNET + 后台化安全：无 exec、setsid 由脚本内部处理）
set -u
cd /home/agentuser/AgentFramework
set -a
. "$HOME/.agentframework/keys.env" 2>/dev/null || true
set +a
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
echo "KEYSET=$(env | grep -c AGENTFRAMEWORK_KEYS_DEEPSEEK) MEM=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
bash eval/rover/r639/run_r639.sh
echo "RUN_RC=$?"
