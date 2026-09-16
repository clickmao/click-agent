#!/usr/bin/env bash
# EXP1-Q42 step 1: occupancy gate -> build-server shutdown -> occupancy gate again
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
G=eval/capability/exp1-q38/precheck_occupancy.sh
O1=eval/capability/exp1-q42/occupancy_q42_pre.txt
O2=eval/capability/exp1-q42/occupancy_q42_post.txt

bash "$G" "$O1" 0 >/dev/null 2>&1
rc1=$?
v1=$(grep -m1 '^PRE_GATE_VERDICT=' "$O1" | cut -d= -f2)
echo "PRE verdict=$v1 rc=$rc1"

timeout 90 dotnet build-server shutdown > eval/capability/exp1-q42/build_server_shutdown_q42.txt 2>&1
echo "shutdown_rc=$? out=$(tr '\n' ' ' < eval/capability/exp1-q42/build_server_shutdown_q42.txt | cut -c1-200)"

bash "$G" "$O2" 60 >/dev/null 2>&1
rc2=$?
v2=$(grep -m1 '^PRE_GATE_VERDICT=' "$O2" | cut -d= -f2)
echo "POST verdict=$v2 rc=$rc2"
tail -2 "$O2" | cut -c1-200
awk '/MemAvailable/{printf "MemAvailable_MB=%d\n",$2/1024}' /proc/meminfo
