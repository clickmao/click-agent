#!/usr/bin/env bash
# R518 编排臂重跑 (修正: 运行期缓存排除 = 链代码改动后 AOT 重发布) + 窗口 w2 全臂重冻结 + 铁律 11 收口。
# 前置: A/C 臂已在 run2 (R518_WINDOW=w2 的首次执行) 跑完且**计量正确** ⇒ 本脚本只重跑 O 臂。
# 禁 push; 单作业 (起手前查占用)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r518
PORT=${R518_PORT:-48695}
DS=$(date +%m%d-%H%M%S)
D=${R518_RUN_DIR:-/tmp/r518/orch-$DS}
AC_RUN=${R518_AC_RUN:-/tmp/r518/run-0917-131155}      # A/C 臂所属 run (留痕可查)
WIN=${R518_WINDOW:-w2}
AGENT_BIN=${R518_AGENT_BIN:-/tmp/pub_r518b/agenthost}
CFGSRC=/tmp/r455_env/agent/cfg
TASKS=p3,p4
NODE_STEPS=${R518_NODE_STEPS:-6}
NODE_ESC=${R518_NODE_ESCALATIONS:-1}
log(){ echo "[$(date +%H:%M:%S)] $*"; }

[ -e "$D" ] && { log "[致命] $D 已存在"; exit 4; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺 AOT $AGENT_BIN"; exit 3; }
[ -d "$AC_RUN" ] || { log "[致命] 缺 A/C 臂 run 目录 $AC_RUN"; exit 3; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent" "$D/orch"
cp -r "$CFGSRC" "$D/agent/cfg" || exit 3
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }

python3 "$R/gen_plan_r518.py" --check > "$D/logs/plan-check.txt" 2>&1 || { log "[致命] 盘上契约机检未过"; exit 3; }
[ -f "$R/prereg-r518.json" ] || { log "[致命] 缺预注册"; exit 3; }

for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R518 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
done

set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
sleep 3
maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }

export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
export AGENTFRAMEWORK_PY_RUN=1
W="$D/orch/ws"; mkdir -p "$W"
I0=$(maxidx)
cd "$REPO" || exit 3     # cwd=仓库根 (宿主自写 data/** 不得落进节点工作区)
AGENTFRAMEWORK_WORKSPACE="$W" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
"$AGENT_BIN" --orchestrate "$R/plan-p3p4-r518.txt" --scope "$R/scope-p3p4-r518.txt" \
  --node-steps "$NODE_STEPS" --node-escalations "$NODE_ESC" --max-nodes 12 \
  --workspace "$W" --report "$D/orch/report.json" --session "r518o-orch-$DS" \
  > "$D/logs/arm-O.txt" 2>&1
orc=$?
I1=$(maxidx)
echo "$I0 $I1" > "$D/orch/idx-range.txt"
log "臂 O-r1 rc=$orc range=[$((I0+1)),$I1]"

# ── 窗口 $WIN 全臂重冻结 (旧窗作废: 首跑 O 臂因缓存缺陷 fail-closed) ──────────
rm -rf "$R/evidence/windows/$WIN" "$R/snapshots/$WIN"
python3 "$R/freeze_snapshot_r518.py" --run-dir "$AC_RUN" --window "$WIN" --write \
  --json "$AC_RUN/report.json" --map A-r1=agentA --map C-r1=codex > "$D/logs/freeze-ac.txt" 2>&1
log "冻结($WIN A/C) rc=$? :: $(tail -1 "$D/logs/freeze-ac.txt")"
python3 "$R/freeze_orch_r518.py" --run-dir "$AC_RUN" --orch-dir "$D/orch" --window "$WIN" \
  --snapshot-dir agentO --tag O --arm O-r1 --tasks "$TASKS" \
  --idx-before "$I0" --idx-after "$I1" --adapter-dir "$D/adapter" --write --append \
  > "$D/logs/freeze-orch.txt" 2>&1
log "冻结($WIN O) rc=$? :: $(tail -1 "$D/logs/freeze-orch.txt")"

python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round R518 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -20 "$D/logs/precond.txt"
log "PRECOND_RC=$prc"
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口未释放" || log "端口已释放"
{ echo "R518 编排臂重跑 $(date -Is)"; echo "run=$D ac_run=$AC_RUN window=$WIN bin=$AGENT_BIN bin_sha=$(sha256sum "$AGENT_BIN" | cut -c1-16)";
  echo "orchestrate_rc=$orc precond_rc=$prc idx=$I0,$I1"; } > "$D/SUMMARY-r518-orch.txt"
exit 0
