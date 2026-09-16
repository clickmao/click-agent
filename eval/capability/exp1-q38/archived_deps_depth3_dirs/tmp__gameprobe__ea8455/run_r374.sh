#!/usr/bin/env bash
# R374 真机 A/B: **运行结果回流 (D3)** — 同 prompt 两臂对照, 同一二进制, 仅环境变量开合
#   A 臂 (AGENTFRAMEWORK_ARTIFACT_REPAIR=0): 校验失败即终局 (当前交付形态的对照)
#   B 臂 (默认开)                        : 失败输出回流 → 有界修复一次 → 复检
# 判据: 有效产物率(编译+实跑) · llm 调用次数 · artifact_feedback(fixed) · tokens · 耗时
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_r374/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'

run_arm () {
  local arm=$1 val=$2
  for i in 1 2 3; do
    echo "=== [$arm] RUN $i START $(date '+%H:%M:%S') ==="
    local before=$(wc -l < "$TEL")
    local s=$(date +%s)
    AGENTFRAMEWORK_PY_RUN=1 AGENTFRAMEWORK_ARTIFACT_REPAIR=$val timeout 300 "$BIN" -q "$PROMPT" --output-mode text \
      --log "$P/r374_${arm}_run$i.md" > "$P/r374_${arm}_run$i.stdout" 2>&1
    echo "EXIT=$? ELAPSED=$(( $(date +%s) - s ))s"
    sed -n "$((before+1)),\$p" "$TEL" > "$P/r374_${arm}_run$i.telemetry"
    echo "NEW_LINES=$(wc -l < "$P/r374_${arm}_run$i.telemetry")"
    grep -o '"point":"script_artifact".*' "$P/r374_${arm}_run$i.telemetry" | tail -1 | head -c 280; echo
    grep -o '"point":"artifact_feedback".*' "$P/r374_${arm}_run$i.telemetry" | head -c 280; echo
  done
}

# 环境卫生(R374 实证): 闸门 env 不得导出到测试进程 — 否则 env 敏感用例必红(xUnit 进程继承)。
echo "=== 全量测试 (env 干净) ==="
dotnet test src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | grep -E "Passed!|Failed!|error CS" | tail -3
echo "=== AOT 发布 ==="
rm -rf /tmp/pub_r374
dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r374 > /tmp/pub_r374.log 2>&1
echo "IL_WARN=$(grep -cE 'IL[0-9]{4}' /tmp/pub_r374.log)"
ls -l /tmp/pub_r374/agenthost | awk '{print "BIN_BYTES="$5}'
echo "=== A 臂 (回流关) ==="; run_arm A 0
echo "=== B 臂 (回流开) ==="; run_arm B 1
echo "=== DONE $(date '+%H:%M:%S') ==="
