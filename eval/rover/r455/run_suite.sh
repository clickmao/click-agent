#!/usr/bin/env bash
# R455 模块覆盖套件 runner —— 同环境(逐字节同夹具) / 同 6 轮输入 / 两侧同一真实模型(deepseek-flash)
# 我方: 单会话 6 轮(带上下文累积 → 可测缓存命中/闸门/吸收)  codex: 单会话 6 轮(resume)
set -uo pipefail
A=/home/agentuser/AgentFramework
OUT=/tmp/r455_env/logs
mkdir -p "$OUT"
set -a; . "$A/.env.local"; set +a
export PATH=/tmp/codexenv/node_modules/.bin:$PATH
cd "$A"
python3 -c "import json;print('\n'.join(json.load(open('/tmp/r455_env/suite-turns.json',encoding='utf-8'))['turns']))" > "$OUT/turns.txt"
export DSKEY="$AGENTFRAMEWORK_KEYS_DEEPSEEK"
CFG=(-c model_providers.ds.name=ds -c model_providers.ds.base_url=http://127.0.0.1:48615/v1 -c model_providers.ds.env_key=DSKEY -c model_provider=ds -m deepseek-flash)

echo "=== codex 侧(单会话 6 轮) ==="
cd /tmp/r455_env/codex/work   # resume 用「进程 cwd」而非记录 cwd (本轮实测) ⇒ 必须在夹具目录内起
TID=""; i=0
while IFS= read -r T; do
  i=$((i+1))
  if [ -z "$TID" ]; then
    timeout 600 codex exec --skip-git-repo-check --json -C /tmp/r455_env/codex/work \
      --dangerously-bypass-approvals-and-sandbox "${CFG[@]}" "$T" < /dev/null > "$OUT/codex-t$i.jsonl" 2>&1
    rc=$?
    TID=$(python3 -c "
import json
for l in open('$OUT/codex-t$i.jsonl',encoding='utf-8'):
    try: e=json.loads(l)
    except Exception: continue
    if e.get('type')=='thread.started': print(e.get('thread_id')); break" 2>/dev/null)
  else
    timeout 600 codex exec resume "$TID" --json \
      --dangerously-bypass-approvals-and-sandbox "${CFG[@]}" "$T" < /dev/null > "$OUT/codex-t$i.jsonl" 2>&1
    rc=$?
  fi
  echo "[codex t$i] rc=$rc tid=${TID:0:8} :: $T"
done < "$OUT/turns.txt"

echo "=== 我方侧(单会话 6 轮) ==="
cd /tmp/r455_env/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r455-token AGENTFRAMEWORK_CONFIG=/tmp/r455_env/agent/cfg \
  setsid nohup /tmp/pub_r450/agenthost --frontend-api 48616 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r455-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48616 \
  /tmp/r455_env/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
echo "=== 产物 ==="
for side in codex agent; do
  echo "-- $side:"; ls /tmp/r455_env/$side/work | tr '\n' ' '; echo
done
