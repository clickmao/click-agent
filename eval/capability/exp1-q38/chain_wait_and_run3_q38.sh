#!/usr/bin/env bash
# EXP1-Q38 · 末轮: 修复 (第三条声明 + 输入规范形) 后重跑**只信息项红面**与**修复后全量面**。
# 预注册判据 J3 (rc=0 ∧ 可判据红 0 ∧ 信息项红 1) / J4 (rc=0 ∧ 25/25 ∧ 2/2 ∧ side_effects []), 见 assert_face_q38.py。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
: > /tmp/q38_chain3.log
for k in 1 2 3 4 5 6; do
  bash eval/capability/exp1-q38/precheck_occupancy.sh eval/capability/exp1-q38/occupancy_wait3_$k.txt 300 \
      > /tmp/gate3_wait$k.log 2>&1
  rc=$?
  echo "gate round=$k rc=$rc $(tail -2 /tmp/gate3_wait$k.log | head -1) $(date -Is)" >> /tmp/q38_chain3.log
  if [ $rc -eq 0 ]; then
    echo "GATE_IDLE at round=$k ⇒ 重跑 T13b + T14 $(date -Is)" >> /tmp/q38_chain3.log
    bash eval/capability/exp1-q38/run_face_nc_q38.sh --class-info-only-inject t13b > /tmp/q38_t13b.stdout 2>&1
    bash eval/capability/exp1-q38/run_face_q38.sh t14 > /tmp/q38_t14.stdout 2>&1
    cp /tmp/q38_face_t14.json eval/capability/exp1-q38/face_q38_t14.json 2>/dev/null
    cp /tmp/q38_face_t14.out eval/capability/exp1-q38/logs/face_t14_face.txt 2>/dev/null
    cp /tmp/q38_t13b.stdout eval/capability/exp1-q38/logs/nc_t13b_runner.txt 2>/dev/null
    cp /tmp/q38_t13b.out eval/capability/exp1-q38/logs/nc_t13b_face.txt 2>/dev/null
    python3 eval/capability/exp1-q38/assert_face_q38.py > eval/capability/exp1-q38/assert_face_q38.after_trio.txt 2>&1
    echo "RERUN_DONE $(date -Is)" > /tmp/q38_rerun_done
    break
  fi
done
echo "CHAIN3_END $(date -Is)" >> /tmp/q38_chain3.log
