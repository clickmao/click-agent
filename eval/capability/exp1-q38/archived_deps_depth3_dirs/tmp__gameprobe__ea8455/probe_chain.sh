#!/usr/bin/env bash
# R371 链式验证: 重发 AOT(r373, 含 D2 config 自包含) → 三模式跑游戏任务
#   ① default  : 仓库 cwd, 运行级验证关
#   ② run      : 仓库 cwd, AGENTFRAMEWORK_PY_RUN=1
#   ③ outside  : 仓库外 cwd (/tmp/gameprobe/work) + PY_RUN=1  ← 同时验证 D2 自包含
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"

out=/tmp/gameprobe/probe_chain.log
: > "$out"
{
  echo "=== PUBLISH $(date '+%H:%M:%S') ==="
  dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_aot_r373 --nologo > /tmp/aot_r373.log 2>&1
  echo "PUBLISH_EXIT=$?"
  echo "IL_WARN=$(grep -c 'warning IL' /tmp/aot_r373.log)"
  echo "CONFIG_SHIPPED=$(ls -d /tmp/pub_aot_r373/config/base 2>/dev/null || echo MISSING)"
  ls -l /tmp/pub_aot_r373/agenthost | awk '{print "BIN_BYTES="$5}'
} >> "$out" 2>&1

set -a; [ -f .env.local ] && . ./.env.local; set +a
BIN=/tmp/pub_aot_r373/agenthost
TEL=/home/agentuser/AgentFramework/data/telemetry/host.jsonl
OUTSIDE=/tmp/gameprobe/work
mkdir -p "$OUTSIDE"
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'

run_one() {   # $1=mode  $2=cwd
  local mode="$1" cwd="$2"
  echo "=== MODE=$mode cwd=$cwd $(date '+%H:%M:%S') PY_RUN=${AGENTFRAMEWORK_PY_RUN:-<unset>} ===" >> "$out"
  ( cd "$cwd" && timeout 900 "$BIN" -q "$PROMPT" --output-mode text --log "/tmp/gameprobe/reply_$mode.md" > "/tmp/gameprobe/reply_$mode.stdout" 2>&1 )
  echo "exit=$? stdout_bytes=$(wc -c < "/tmp/gameprobe/reply_$mode.stdout")" >> "$out"
  echo "围栏数=$(grep -c '```' "/tmp/gameprobe/reply_$mode.stdout" || true)" >> "$out"
}

before=$(wc -l < "$TEL" 2>/dev/null || echo 0)
unset AGENTFRAMEWORK_PY_RUN; run_one default /home/agentuser/AgentFramework
export AGENTFRAMEWORK_PY_RUN=1;  run_one run /home/agentuser/AgentFramework
run_one outside "$OUTSIDE"

{
  echo "=== 遥测增量 (llm_call / recover / script_artifact / loop_turn) ==="
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
  echo "=== 新产物 (仓库 data/artifacts 与 外部 cwd data/artifacts) ==="
  ls -lt /home/agentuser/AgentFramework/data/artifacts/*.py 2>/dev/null | head -3
  ls -lt /tmp/gameprobe/work/data/artifacts/*.py 2>/dev/null | head -3
  echo "=== 我复跑 agent 产物自测 (最新一个) ==="
  newest=$(ls -t /home/agentuser/AgentFramework/data/artifacts/*.py /tmp/gameprobe/work/data/artifacts/*.py 2>/dev/null | head -1)
  echo "artifact=$newest"
  if [ -n "${newest:-}" ]; then
    timeout 60 python3 "$newest" --selftest; echo "selftest_exit=$?"
  fi
} >> "$out" 2>&1
echo "=== CHAIN DONE $(date '+%H:%M:%S') ===" >> "$out"
