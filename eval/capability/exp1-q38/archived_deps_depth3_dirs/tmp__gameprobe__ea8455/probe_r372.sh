#!/usr/bin/env bash
# R372 真机 A/B: ① 产物命中率 (D4-b v1: 2/3) ② 产物来路归因 origin ③ 截断检测/续写
# 判据: 每轮 artifact 增量 + script_artifact 的 origin + llm_reply_truncated / llm_call_continue
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
PROBE=/tmp/gameprobe
BIN=/tmp/pub_r373/agenthost
TEL=/home/agentuser/AgentFramework/data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
export AGENTFRAMEWORK_PY_RUN=1
cnt() { grep -c "$1" "$TEL" 2>/dev/null | tr -d '\n'; }
a0=$(cnt '"point":"script_artifact"'); t0=$(cnt '"point":"llm_reply_truncated"'); c0=$(cnt '"point":"llm_call_continue"')
echo "BASELINE artifact=$a0 truncated=$t0 continue=$c0"
for i in 1 2 3; do
  echo "=== RUN $i $(date '+%H:%M:%S') ==="
  timeout 300 "$BIN" -q "$PROMPT" > "$PROBE/r372_run$i.stdout" 2>&1
  echo "EXIT=$?"
  sleep 1
  echo "ARTIFACT_NEW: $(tail -n +$(( $(cnt '"point":"script_artifact"') - (a0 + i - 1) + 1 )) "$TEL" 2>/dev/null | grep '"point":"script_artifact"' | tail -1 | cut -c1-260)"
done
echo "=== 汇总 ==="
echo "artifact: $a0 -> $(cnt '"point":"script_artifact"')"
echo "truncated: $t0 -> $(cnt '"point":"llm_reply_truncated"')"
echo "continue: $c0 -> $(cnt '"point":"llm_call_continue"')"
echo "--- 续写事件明细"
grep '"point":"llm_call_continue"' "$TEL" 2>/dev/null | tail -3 | cut -c1-300
echo "=== DONE $(date '+%H:%M:%S') ==="
