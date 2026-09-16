#!/usr/bin/env bash
# R500 · 续跑 P 臂 (C 臂已于 01:44–01:57 以 rc=0 完成, 不重跑)
#
# 自伤登记 (本回合真实根因):
#   eval/rover/r499/run_rest_r499.sh 第 10–12 行给执行器传了 **5 个实参**
#   (`P 1 r499 49920 49922`), 而执行器形参是 `<ARM> [tag] [relay_port] [api_port]` (4 个)
#   ⇒ "r499" 落到 RELAY_PORT ⇒ relay_real_r475.py:29 int('r499') ValueError
#   ⇒ `[致命] 中继未启动` ⇒ rc=4 ⇒ 矩阵在 P1 起手处中止 (C 臂读数不受影响)。
#   R499 冻结清单 (prereg_r500.json) 逐字节不动; 修正版放在本文件 (r500 命名空间)。
set -u
cd /home/agentuser/AgentFramework
DIR=/home/agentuser/AgentFramework/eval/rover/r499
LOG=/tmp/r500_p_arms.log
: > "$LOG"
ok=0
for i in 1 2; do
  python3 eval/rover/r483/preflight_gate.py --round R500 --out /tmp/pf_r500_p$i.json >>"$LOG" 2>&1
  v=$(python3 -c "import io,json,sys;d=json.load(io.open('/tmp/pf_r500_p$i.json',encoding='utf-8-sig'));print('%s mem=%s src=%s'%(d['verdict'],d['mem_available_mb'],d['recent_src_writes_120s']))")
  echo "闸采样 $i: $v" | tee -a "$LOG"
  case "$v" in PASS*) ok=$((ok+1));; *) ok=0;; esac
  sleep 20
done
[ "$ok" -ge 2 ] || { echo "[致命] 闸未连续 2 次通过 ⇒ 让行" | tee -a "$LOG"; exit 3; }
echo "闸通过 ⇒ 续跑 P1/P2/P3" | tee -a "$LOG"
rc_all=0
for spec in "1 49920 49922" "2 49930 49932" "3 49940 49942"; do
  set -- $spec
  echo "=== $(date '+%T') P$1 (relay=$2 api=$3) ===" >>"$LOG"
  bash "$DIR/run_arm_real_r499.sh" P "$1" "$2" "$3" >>"$LOG" 2>&1
  rc=$?
  echo "--- rc=$rc P$1 ---" >>"$LOG"
  [ $rc -ne 0 ] && { echo "[致命] P$1 rc=$rc ⇒ 中止" | tee -a "$LOG"; rc_all=1; break; }
done
echo "P_ARMS_RC=$rc_all" | tee -a "$LOG"
exit $rc_all
