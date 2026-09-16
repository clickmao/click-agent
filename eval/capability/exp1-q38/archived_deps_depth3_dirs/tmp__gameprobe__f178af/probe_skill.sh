#!/usr/bin/env bash
# R373 技能侧真机: 新增 delivery-selfcheck 后, agent 自检 skill 是否被真实加载/命中
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r373b/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
export AGENTFRAMEWORK_PY_RUN=1
before=$(wc -l < "$TEL")
echo "=== SKILL PROBE START $(date '+%H:%M:%S') ==="
timeout 300 "$BIN" -q "$PROMPT" --output-mode text --log "$P/r373b_skill.md" > "$P/r373b_skill.stdout" 2>&1
echo "EXIT=$?"
sed -n "$((before+1)),\$p" "$TEL" > "$P/r373b_skill.telemetry"
grep -o '"point":"skill_load".*' "$P/r373b_skill.telemetry" | head -2
grep -o '"point":"skill_scan".*' "$P/r373b_skill.telemetry" | head -2
grep -o '"point":"skill_match".*' "$P/r373b_skill.telemetry" | head -2
grep -o '"point":"skill".*' "$P/r373b_skill.telemetry" | head -2
grep -o '"point":"script_artifact".*' "$P/r373b_skill.telemetry" | tail -1 | head -c 200
echo; echo "=== DONE $(date '+%H:%M:%S') ==="
