#!/usr/bin/env bash
# R508 项目级对照跑器: 同环境·同输入·同模型; 三臂串行 (A 本侧默认 / B 本侧步数上限 / C codex 真值)
# 铁律: 起手闸连续 2 PASS; 起手前沉降; 单变量; 判分只吃产物真实行为; 端口/目录守卫 fail-closed。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r508
PORT=${R508_ADAPTER_PORT:-48660}
TS=${R508_TS:-$(date +%m%d-%H%M%S)}
D=${R508_RUN_DIR:-/tmp/r508/run-$TS}
AGENT_BIN=${R508_AGENT_BIN:-/tmp/pub_r504/agenthost/agenthost}
CODEX_BIN=${R508_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
CFGSRC=${R508_CFG_SEED:-/tmp/r455_env/agent/cfg}
MAXSTEP_B=${R508_MAXSTEP_B:-24}
TASKS=${R508_TASKS:-p1,p2}
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex $CODEX_BIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{agentA,agentB,codex,adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl 48615 "$D/agent/cfg" 2>/dev/null | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
echo "run=$D port=$PORT tasks=$TASKS ts=$(date -Is)" > "$D/.owner-r508"

# --- 1 预注册 (机检, fail-closed) ------------------------------------------
python3 "$R/make_prereg_r508.py" --write --out "$R/prereg-r508.json" > "$D/logs/prereg.txt" 2>&1
prc=$?; tail -2 "$D/logs/prereg.txt"
[ "$prc" -eq 0 ] || { log "[致命] 预注册自检失败 rc=$prc"; exit 3; }

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R508 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 3 adapter (起手后沉降) -----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do
  curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5

# --- 4 三臂串行 (内存硬约束: 禁并发) ---------------------------------------
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
run_arm() { # tag side out extra...
  local tag=$1 side=$2 out=$3; shift 3
  log "== 臂 $tag ($side) =="
  python3 "$R/proj_run_side.py" --side "$side" --arm "$tag" --out "$out" --adapter-dir "$D/adapter" \
    --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --codex-bin "$CODEX_BIN" --tasks "$TASKS" \
    "$@" 2>&1 | tee "$D/logs/arm-$tag.txt"
  echo "arm=$tag rc=${PIPESTATUS[0]}" >> "$D/logs/arm-$tag.txt"
}
run_arm A agent "$D/agentA"
run_arm B agent "$D/agentB" --max-steps "$MAXSTEP_B"
run_arm C codex "$D/codex"

# --- 5 汇总判分 (铁律11: 独立物化 + 逐条用例) -----------------------------
python3 "$R/aggregate_r508.py" --run-dir "$D" --json "$D/report.json" 2>&1 | tee "$D/logs/report.txt"
echo "REPORT_RC=${PIPESTATUS[0]}" >> "$D/logs/report.txt"

# --- 6 teardown ------------------------------------------------------------
kill "$APID" 2>/dev/null
sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
log "DONE RUN_DIR=$D"
