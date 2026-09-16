#!/usr/bin/env bash
# EXP1-Q38 · 干净三面的**脱离会话**等待执行体 (Q38 收尾): 有界等待占用闸 → 放行后跑三面。
# 纪律: 每轮等待落盘; 闸不放行绝不启动真机面; 产物落固定命名空间 + done 标记 (供后续轮次接管)。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
: > /tmp/q38_chain2.log
for k in 1 2 3 4 5 6 7 8; do
  bash eval/capability/exp1-q38/precheck_occupancy.sh eval/capability/exp1-q38/occupancy_wait2_$k.txt 300 \
      > /tmp/gate2_wait$k.log 2>&1
  rc=$?
  echo "gate round=$k rc=$rc $(tail -2 /tmp/gate2_wait$k.log | head -1) $(date -Is)" >> /tmp/q38_chain2.log
  if [ $rc -eq 0 ]; then
    echo "GATE_IDLE at round=$k ⇒ 启动三面 $(date -Is)" >> /tmp/q38_chain2.log
    bash eval/capability/exp1-q38/run_face_nc_q38.sh --class-mixed-inject t12b > /tmp/q38_t12b.stdout 2>&1
    bash eval/capability/exp1-q38/run_face_nc_q38.sh --class-info-only-inject t13b > /tmp/q38_t13b.stdout 2>&1
    bash eval/capability/exp1-q38/run_face_q38.sh t14 > /tmp/q38_t14.stdout 2>&1
    cp /tmp/q38_face_t14.json eval/capability/exp1-q38/face_q38_t14.json 2>/dev/null
    cp /tmp/q38_face_t14.out eval/capability/exp1-q38/logs/face_t14_face.txt 2>/dev/null
    cp /tmp/q38_t12b.stdout eval/capability/exp1-q38/logs/nc_t12b_runner.txt 2>/dev/null
    cp /tmp/q38_t13b.stdout eval/capability/exp1-q38/logs/nc_t13b_runner.txt 2>/dev/null
    cp /tmp/q38_t12.out eval/capability/exp1-q38/logs/nc_t12b_face.txt 2>/dev/null
    cp /tmp/q38_t13.out eval/capability/exp1-q38/logs/nc_t13b_face.txt 2>/dev/null
    python3 eval/capability/exp1-q38/assert_face_q38.py > eval/capability/exp1-q38/assert_face_q38.after_trio.txt 2>&1
    echo "TRIO_DONE $(date -Is)" > /tmp/q38_all_done
    break
  fi
done
echo "CHAIN2_END $(date -Is)" >> /tmp/q38_chain2.log
