#!/usr/bin/env bash
# R371 D4-b 真机 A/B: 模型**不给围栏**时, 无围栏启发式是否也能让产物入链 (artifact 命中率 1/3 → ?)
# 判据: 每次运行后 repo 遥测里 script_artifact 的增量 (>0 即入链成功)
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
PROBE=/tmp/gameprobe
BIN=/tmp/pub_r372/agenthost
TEL=/home/agentuser/AgentFramework/data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
export AGENTFRAMEWORK_PY_RUN=1
CNT_BEFORE=$(grep -c '"point":"script_artifact"' "$TEL" 2>/dev/null || true)
echo "=== BASELINE script_artifact 累计=${CNT_BEFORE:-0} ==="
for i in 1 2 3; do
  before=$(grep -c '"point":"script_artifact"' "$TEL" 2>/dev/null || true)
  echo "=== RUN $i START $(date '+%H:%M:%S') ==="
  timeout 300 "$BIN" -q "$PROMPT" --output-mode text --log "$PROBE/d4b_run$i.md" > "$PROBE/d4b_run$i.stdout" 2>&1
  echo "EXIT=$?"
  after=$(grep -c '"point":"script_artifact"' "$TEL" 2>/dev/null || true)
  echo "ARTIFACT_DELTA=$((after-before))"
  grep -o '"point":"script_artifact"[^}]*' "$TEL" | tail -1
  grep -o '"point":"llm_call_recover"[^}]*' "$TEL" | tail -1
done
echo "=== DONE $(date '+%H:%M:%S') ==="
