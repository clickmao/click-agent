#!/usr/bin/env bash
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
"$DOTNET_ROOT/dotnet" build-server shutdown >/dev/null 2>&1 || true
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || echo "drop_caches 失败"
sleep 20
grep -E "MemAvailable" /proc/meminfo
for i in 1 2 3; do
  python3 eval/rover/r483/preflight_gate.py --round R499 --out /tmp/pf_r499_c$i.json >/tmp/pf_r499_c$i.txt 2>&1
  v=$(python3 -c "import io,json;d=json.load(io.open('/tmp/pf_r499_c$i.json',encoding='utf-8-sig'));print(d['verdict'],d['mem_available_mb'],d['blocker_cause'])" 2>&1 | head -1)
  echo "试 $i: $v"
  case "$v" in GATE_PASS*|PASS*) echo "PASS ⇒ 可起真机测量"; exit 0;; esac
  sleep 60
done
echo "三次均未通过 ⇒ 本轮真机让行"
exit 3
