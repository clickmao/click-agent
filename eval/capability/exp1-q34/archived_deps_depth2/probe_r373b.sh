#!/usr/bin/env bash
# R373 真机 A/B: **首轮预算策略** — 同题(贪吃蛇) 3 连跑, 看是否需要恢复链
# 对照 R372: 3/3 轮都触发恢复 (2 轮空正文恢复 first_reasoning_len 26752~28306 / 1 轮截断续写)
# 判据: 每轮 llm_call 次数(期望 1) · recover/continue 次数(期望 0) · tokens · 耗时 · 产物有效
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r373b/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
export AGENTFRAMEWORK_PY_RUN=1
for i in 1 2 3; do
  echo "=== RUN $i START $(date '+%H:%M:%S') ==="
  before=$(wc -l < "$TEL")
  s=$(date +%s)
  timeout 300 "$BIN" -q "$PROMPT" --output-mode text --log "$P/r373b_run$i.md" > "$P/r373b_run$i.stdout" 2>&1
  echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
  sed -n "$((before+1)),\$p" "$TEL" > "$P/r373b_run$i.telemetry"
  echo "NEW_LINES=$(wc -l < "$P/r373b_run$i.telemetry")"
  grep -o '"point":"script_artifact".*' "$P/r373b_run$i.telemetry" | tail -1 | head -c 220
  echo
done
echo "=== DONE $(date '+%H:%M:%S') ==="
