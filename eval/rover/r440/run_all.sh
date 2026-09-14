#!/usr/bin/env bash
# R440 全臂执行（顺序，避免 llama-server 端口竞争）
#   分档梯: V1(N=1 单次真诉求) → V2(N=3 短, 可跳1/3) → V4(N=20 长, 可跳35% 晚簇) → V5(N=20 零可跳)
#   V4 另加 BP 无设备负控（增益须归零 ⇒ 归因到真实本地设备而非口径）
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r440
cd /home/agentuser/AgentFramework || exit 1
echo "[$(date -Iseconds)] R440 run_all start  launcher_pid=$$"
for spec in "A V1 48010 48012" "BRJ V1 48014 48016" \
            "A V2 48018 48020" "BRJ V2 48022 48024" \
            "A V4 48026 48028" "BRJ V4 48030 48032" "BP V4 48034 48036" \
            "A V5 48038 48040" "BRJ V5 48042 48044"; do
  set -- $spec
  echo "[$(date -Iseconds)] >>> arm=$1 grid=$2 stub=$3 api=$4"
  R440_GRID=$2 bash "$DIR/run_arm.sh" "$1" "$3" "$4"
  echo "[$(date -Iseconds)] <<< arm=$1 grid=$2 rc=$?"
done
echo "[$(date -Iseconds)] R440 run_all done"
