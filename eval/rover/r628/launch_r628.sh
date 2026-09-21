#!/usr/bin/env bash
# R628 起手器（派生自 launch_r596.sh，结构逐字节复用；唯一差异 = 轮号命名空间）:
#   先按血统收口本会话的按需工具子进程（LSP, RSS ~140MB），再立即起手跑轮。
#   依据: 用户既立纪律「起手前清场并记前后差」（own-tool 子进程不在闸血统、可吃 ~150MB）。
#   注意: 本脚本禁 exec（会替换被跟踪 shell ⇒ 进程被回收，unattended-job-reliability §7）。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
mkdir -p "$HOME/.agentframework/harness/runs/r628/logs"
B=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
REAPED=""
for p in $(pgrep -f '\.hermes/lsp/bin/' 2>/dev/null); do
  [ -r "/proc/$p/cmdline" ] || continue
  cmd=$(tr '\0' ' ' < "/proc/$p/cmdline")
  case "$cmd" in *"pgrep -f"*) continue ;; esac
  ppid=$(awk '{print $4}' "/proc/$p/stat" 2>/dev/null)
  # 只收口: PPid 首跳即本会话 gateway 的 LSP 工具子进程
  if [ "$ppid" = "1145246" ] && [ "${cmd#*\.hermes/lsp/bin/}" != "$cmd" ]; then
    rss=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
    kill "$p" 2>/dev/null && REAPED="$REAPED $p:${cmd%% *}:${rss}kB"
  fi
done
sleep 3
A=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
printf '[%s] own-tool reap:%s mem_before=%sMB mem_after=%sMB delta=%sMB\n' \
  "$(date +%H:%M:%S)" "${REAPED:- none}" "$B" "$A" "$((A-B))" | tee -a "$HOME/.agentframework/harness/runs/r628/logs/reap.txt"
echo "$REAPED" > "$HOME/.agentframework/harness/runs/r628/logs/reaped-tools.txt"
# 立即起手（同一 shell 内，样本窗最小化）
bash eval/rover/r628/run_r628.sh
