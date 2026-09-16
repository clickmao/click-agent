#!/usr/bin/env bash
# R371 复跑: 修复后用 AOT 真产物跑游戏任务, 观察 生成→落盘→校验→运行 链
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_aot_r371/agenthost
P=/tmp/gameprobe
TEL=data/telemetry/host.jsonl
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
before=$(wc -l < "$TEL" 2>/dev/null || echo 0)

for mode in default run; do
  if [ "$mode" = run ]; then export AGENTFRAMEWORK_PY_RUN=1; else unset AGENTFRAMEWORK_PY_RUN; fi
  echo "=== MODE=$mode $(date '+%H:%M:%S') PY_RUN=${AGENTFRAMEWORK_PY_RUN:-<unset>} ==="
  timeout 900 "$BIN" -q "$PROMPT" --output-mode text --log "$P/run_$mode.md" > "$P/run_$mode.stdout" 2>&1
  echo "exit=$? stdout_bytes=$(wc -c < "$P/run_$mode.stdout")"
done

echo "=== 遥测增量 (llm_call / script_artifact / loop_turn) ==="
tail -n +$((before + 1)) "$TEL" | python3 -c '
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except Exception: continue
    if r.get("point") in ("llm_call", "llm_call_recover", "script_artifact", "loop_turn"):
        print(r["point"], json.dumps(r["kv"], ensure_ascii=False))
'

echo "=== 最新产物 + 我复跑其自测 ==="
newest=$(ls -t data/artifacts/*.py 2>/dev/null | head -1)
echo "artifact=$newest"
if [ -n "${newest:-}" ]; then
  wc -c "$newest"
  timeout 60 python3 "$newest" --selftest; echo "selftest_exit=$?"
fi
