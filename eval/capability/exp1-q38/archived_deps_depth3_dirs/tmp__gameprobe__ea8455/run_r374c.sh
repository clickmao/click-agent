#!/usr/bin/env bash
# R374 真机 A/B ②: **确定性失败场景** — 交互式脚本在无 stdin 下必抛 EOFError
#   A2 臂 (AGENTFRAMEWORK_ARTIFACT_REPAIR=0): 运行失败即终局 → 交付一个跑不起来的脚本
#   B2 臂 (默认开)                          : 失败 traceback 回流 → 有界修复一次 → 复检
# 目的: 证明 D3 的因果链 (失败事实可达 → 修复行动发生 → 复检通过), 并量化代价。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r374/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个猜数字游戏(命令行交互)：运行后提示玩家输入 1-100 的整数，循环提示"猜大了/猜小了"，猜中打印用了多少次；单文件 guess.py，附运行说明。'

run_arm () {
  local arm=$1 val=$2 i before s
  for i in 1 2 3; do
    echo "=== [$arm] RUN $i START $(date '+%H:%M:%S') ==="
    before=$(wc -l < "$TEL")
    s=$(date +%s)
    AGENTFRAMEWORK_PY_RUN=1 AGENTFRAMEWORK_ARTIFACT_REPAIR=$val timeout 300 "$BIN" -q "$PROMPT" --output-mode text --log "$P/${arm}_run$i.md" > "$P/${arm}_run$i.stdout" 2>&1
    echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
    sed -n "$((before+1)),\$p" "$TEL" > "$P/${arm}_run$i.telemetry"
    echo "NEW_LINES=$(wc -l < "$P/${arm}_run$i.telemetry")"
    grep -o '"point":"script_run"[^}]*}' "$P/${arm}_run$i.telemetry" | tail -2
    grep -o '"point":"artifact_feedback".*' "$P/${arm}_run$i.telemetry" | head -c 300; echo
    grep -o '"point":"script_artifact".*' "$P/${arm}_run$i.telemetry" | tail -1 | head -c 220; echo
  done
}

echo "=== A2 臂 (回流关) ==="; run_arm A2 0
echo "=== B2 臂 (回流开) ==="; run_arm B2 1
echo "=== DONE $(date '+%H:%M:%S') ==="
