#!/usr/bin/env bash
# R374b 真机复测: 修复提示词加"闸门契约 + 未通过用例摘要 + 最小改动"后, 回流臂 3 连跑对照。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r374d/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'

# 环境卫生(R374 实证): 闸门 env 不得导出到测试进程 — 否则 env 敏感用例必红(xUnit 进程继承)。
echo "=== 全量测试 (env 干净) ==="
dotnet test src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | grep -E "\[FAIL\]|Passed!|Failed!|error CS" | head -8
echo "=== AOT 发布 ==="
rm -rf /tmp/pub_r374d
dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r374d > /tmp/pub_r374d.log 2>&1
echo "IL_WARN=$(grep -cE 'IL[0-9]{4}' /tmp/pub_r374d.log)"
ls -l /tmp/pub_r374d/agenthost | awk '{print "BIN_BYTES="$5}'

for i in 1 2 3; do
  echo "=== [D] RUN $i START $(date '+%H:%M:%S') ==="
  before=$(wc -l < "$TEL")
  s=$(date +%s)
  AGENTFRAMEWORK_PY_RUN=1 timeout 300 "$BIN" -q "$PROMPT" --output-mode text --log "$P/D_run$i.md" > "$P/D_run$i.stdout" 2>&1
  echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
  sed -n "$((before+1)),\$p" "$TEL" > "$P/r374d_B_run$i.telemetry"
  echo "NEW_LINES=$(wc -l < "$P/r374d_B_run$i.telemetry")"
  grep -o '"point":"artifact_feedback".*' "$P/r374d_B_run$i.telemetry" | head -c 400; echo
done
echo "=== DONE $(date '+%H:%M:%S') ==="
