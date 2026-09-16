#!/usr/bin/env bash
# R377 真机样本: 同一题(贪吃蛇) 连跑 2 次 —— (a) 能力探针回归证据 (b) prompt 缓存命中率实测
# (第二次请求与第一次前缀相同 → 期望 DS 上下文缓存命中 > 0)
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r377/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'

[ -x "$BIN" ] || { echo "BIN 缺失: $BIN (需先 AOT 发布)"; exit 2; }
for i in 1 2; do
  echo "=== [R377] RUN $i START $(date '+%H:%M:%S') ==="
  before=$(wc -l < "$TEL")
  s=$(date +%s)
  AGENTFRAMEWORK_PY_RUN=1 timeout 420 "$BIN" -q "$PROMPT" --output-mode text --log "$P/r377_run$i.md" > "$P/r377_run$i.stdout" 2>&1
  echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
  sed -n "$((before+1)),\$p" "$TEL" > "$P/r377_run$i.telemetry"
  echo "NEW_LINES=$(wc -l < "$P/r377_run$i.telemetry")"
done
echo "=== DONE $(date '+%H:%M:%S') ==="
