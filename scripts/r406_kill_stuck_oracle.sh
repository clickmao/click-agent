#!/bin/sh
# R406: 收尾卡住的 oracle 运行 (按 pid / 括号技巧杀, 避免 pkill -f 匹配自身命令行导致自杀)
set -u

for p in $(pgrep -f 'r403_oracle_compare' 2>/dev/null || true); do
  echo "kill oracle-script pid=$p"
  kill "$p" 2>/dev/null || true
done

for p in $(pgrep -f '[l]lama-cli' 2>/dev/null || true); do
  echo "kill llama-cli pid=$p"
  kill "$p" 2>/dev/null || true
done

sleep 3

echo "--- 残留检查 ---"
pgrep -af '[l]lama-cli' 2>/dev/null || echo "无 llama-cli 残留"
pgrep -af 'r403_oracle_compare' 2>/dev/null || echo "无对账脚本残留"
echo "--- 磁盘 ---"
df -h / | tail -1
echo "--- oracle 日志 ---"
ls -la /home/agentuser/AgentFramework/eval/rover/r403/oracle/
