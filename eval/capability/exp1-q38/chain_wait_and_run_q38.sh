#!/usr/bin/env bash
# EXP1-Q38: 有界等待对侧在飞作业 → 占用闸放行后跑干净三面 (混合注入 / 只信息项注入 / 修复后全量面)。
# 纪律: 每一轮等待都落盘 (occupancy_wait<N>.txt); 闸不放行 ⇒ 绝不启动真机面 (闸不是装饰)。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
: > /tmp/q38_chain.log
for k in 1 2 3 4; do
  bash eval/capability/exp1-q38/precheck_occupancy.sh eval/capability/exp1-q38/occupancy_wait$k.txt 300 \
      > /tmp/gate_wait$k.log 2>&1
  rc=$?
  echo "gate round=$k rc=$rc $(tail -2 /tmp/gate_wait$k.log | head -1)" >> /tmp/q38_chain.log
  if [ $rc -eq 0 ]; then
    echo "GATE_IDLE at round=$k ⇒ 启动三面 $(date -Is)" >> /tmp/q38_chain.log
    bash eval/capability/exp1-q38/run_face_nc_q38.sh --class-mixed-inject t12b > /tmp/q38_t12b.stdout 2>&1
    bash eval/capability/exp1-q38/run_face_nc_q38.sh --class-info-only-inject t13b > /tmp/q38_t13b.stdout 2>&1
    bash eval/capability/exp1-q38/run_face_q38.sh t14 > /tmp/q38_t14.stdout 2>&1
    cp /tmp/q38_face_t14.json eval/capability/exp1-q38/face_q38_t14.json 2>/dev/null
    cp /tmp/q38_face_t14.out eval/capability/exp1-q38/logs/face_t14.out.txt 2>/dev/null
    cp /tmp/q38_t12b.stdout eval/capability/exp1-q38/logs/nc_t12b_runner.txt 2>/dev/null
    cp /tmp/q38_t13b.stdout eval/capability/exp1-q38/logs/nc_t13b_runner.txt 2>/dev/null
    cp /tmp/q38_t12.out eval/capability/exp1-q38/logs/nc_t12b_face.txt 2>/dev/null
    cp /tmp/q38_t13.out eval/capability/exp1-q38/logs/nc_t13b_face.txt 2>/dev/null
    echo "TRIO_DONE $(date -Is)" > /tmp/q38_all_done
    break
  fi
done
echo "CHAIN_END $(date -Is)" >> /tmp/q38_chain.log
