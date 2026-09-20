#!/usr/bin/env bash
# R599 起手包装: 环境前置(keys/DOTNET_ROOT) + 调起手器（禁 exec）。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
set -a
[ -f "$HOME/.agentframework/keys.env" ] && . "$HOME/.agentframework/keys.env"
set +a
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
n=$(env | grep -c '^AGENTFRAMEWORK_KEYS_DEEPSEEK=' || true)
echo "key_env_count=$n"
[ "$n" -ge 1 ] || { echo "[致命] 缺 AGENTFRAMEWORK_KEYS_DEEPSEEK ⇒ 远端臂会全 VOID"; exit 3; }
bash eval/rover/r599/launch_r599.sh
