#!/usr/bin/env bash
# 起手窗口体检 (共享机): 重进程清单 + 内存余量 + 兄弟作业产物新鲜度
cd /home/agentuser/AgentFramework || exit 3
echo "TS=$(date '+%Y-%m-%d %H:%M:%S %z')"
echo "---- heavy procs ----"
ps -eo pid,etime,args | grep -E 'dotnet|MSBuild|VBCSCompiler|run_r5|agenthost|waiter|preflight' | grep -v grep | head -12
echo "PROC_COUNT=$(ps -eo args | grep -cE 'dotnet|MSBuild|VBCSCompiler')"
echo "---- mem ----"
free -m | sed -n '2p'
echo "MEM_AVAIL_MB=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
echo "---- sibling artifacts (last 6 by mtime) ----"
ls -t /tmp/r519/ 2>/dev/null | head -5
ls -t /tmp/*.log 2>/dev/null | head -4
echo "---- git ----"
git log -1 --format='HEAD=%h %ad %s' --date=format:'%H:%M'
git status --porcelain | head -12
