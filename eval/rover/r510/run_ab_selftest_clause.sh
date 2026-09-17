#!/usr/bin/env bash
# R510 A/B: 「自检契约泛化」(SessionBaseline 二.3 加非功能语义必测) 对 p3(hidden case restart_drops_expired) 的效果。
#   臂 before = 旧 AOT (R509 发布物 /tmp/pub_r509), 臂 after = 新 AOT (/tmp/pub_r510)
#   同窗·同题集·同模型·同夹具; 每跑次独立 session (--arm 带 -r<N>), 否则首跑继承前窗失败态 = 假失败。
# 用法: bash run_ab_selftest_clause.sh   (环境: REPO/.env.local 存在; adapter 走 r455 转发)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
BIN_BEFORE=${BIN_BEFORE:-/tmp/pub_r509/agenthost}
BIN_AFTER=${BIN_AFTER:-/tmp/pub_r510/agenthost}
D=${D:-/tmp/r510/ab}
PORT=${PORT:-48679}
REPS=${REPS:-3}
TASKS=${TASKS:-p3}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$D"/{agent,adapter,evidence,logs}
[ -d "$D/agent/cfg" ] || cp -r /tmp/r455_env/agent/cfg "$D/agent/cfg"
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态 (base/models.yaml 缺)"; exit 3; }
grep -rl "486[0-9][0-9]" "$D/agent/cfg" | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
for b in "$BIN_BEFORE" "$BIN_AFTER"; do [ -x "$b" ] || { log "[致命] 缺 bin $b"; exit 3; }; done
for i in 1 2; do
  python3 "$R/r483/preflight_gate.py" --round R510 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json'))['verdict'])" 2>/dev/null)
  log "闸$i: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过 (单采样不可信, 连续 2 PASS 才起臂)"; exit 2; }
done
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
DEMO_OUT="$D/adapter" setsid nohup python3 "$R/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 & APID=$!
ok=0; for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 1; done
[ "$ok" = 1 ] || { log "[致命] adapter 未就绪"; kill $APID 2>/dev/null; exit 3; }
log "adapter up port=$PORT sha_before=$(sha256sum "$BIN_BEFORE" | cut -c1-12) sha_after=$(sha256sum "$BIN_AFTER" | cut -c1-12)"
python3 - "$D" "$BIN_BEFORE" "$BIN_AFTER" > "$D/hosts.json" <<'PY'
import json,sys,hashlib,os
d,bb,ba=sys.argv[1],sys.argv[2],sys.argv[3]
def h(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()[:12] if os.path.isfile(p) else None
json.dump({"before":{"bin":bb,"host_sha12":h(bb)},"after":{"bin":ba,"host_sha12":h(ba)}},sys.stdout,indent=1)
PY
sleep 8
cd "$REPO"
run_one(){ local arm="$1" rep="$2" bin="$3" out="$D/$1/rep$2"
  log "  臂 $arm rep$rep bin=$bin"
  python3 "$R/r508/proj_run_side.py" --side agent --tasks "$TASKS" --out "$out" \
    --agent-bin "$bin" --cwd "$REPO" --arm "$arm-r$rep" --timeout 600 --adapter-dir "$D/adapter" 2>&1 | tail -1
}
for i in $(seq 1 "$REPS"); do run_one agentBefore "$i" "$BIN_BEFORE"; done
for i in $(seq 1 "$REPS"); do run_one agentAfter  "$i" "$BIN_AFTER";  done
kill $APID 2>/dev/null; sleep 1
log "== 聚合 (同窗同题集; 逐用例通过率 + 逐用例失败点名) =="
python3 "$R/r509/aggregate_repeats_r509.py" --run-dir "$D" --tasks "$TASKS" --reps "$REPS" --json "$D/ab-report.json" | tail -25
log "DONE ab-report=$D/ab-report.json"
