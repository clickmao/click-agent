#!/usr/bin/env bash
# R376 能力探针回归样本: 同一题(贪吃蛇) 单跑 — 证明 R376(仅前端模式改动) 未回归 CLI 主链;
# 产物自测由聚合脚本独立复核(不信任遥测自报)。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r376/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'

[ -x "$BIN" ] || { echo "BIN 缺失: $BIN (需先 AOT 发布)"; exit 2; }
echo "=== [R376] RUN 1 START $(date '+%H:%M:%S') ==="
before=$(wc -l < "$TEL")
s=$(date +%s)
AGENTFRAMEWORK_PY_RUN=1 timeout 420 "$BIN" -q "$PROMPT" --output-mode text --log "$P/r376_run1.md" > "$P/r376_run1.stdout" 2>&1
echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
sed -n "$((before+1)),\$p" "$TEL" > "$P/r376_run1.telemetry"
echo "NEW_LINES=$(wc -l < "$P/r376_run1.telemetry")"
echo "=== DONE $(date '+%H:%M:%S') ==="
