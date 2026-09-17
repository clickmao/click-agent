#!/usr/bin/env bash
# R520: 编排臂复跑 —— R519 的 plan/scope/判据器**逐字节复用** (md5 同源), 唯一变量 =
#   ① 影子路径闸 (WorkspaceActionPort.ShadowPath) ② 节点提示词第 5 条纪律。
# 判据形态: (a) 5 节点是否 Completed (R519: 1 失败 + 4 未执行)
#           (b) 落盘产物里是否还有影子树 (工作区内重复自身位置)
#           (c) 58 用例整题全对率 (同判据器)
set -u
REPO=/home/agentuser/AgentFramework; R=$REPO/eval/rover/r520
D=$R/run-$(date +%m%d-%H%M%S); mkdir -p "$D"/{logs,adapter} "$D/orch/ws"
BIN=${R520_AGENT_BIN:-/tmp/pub_r520/agenthost}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
[ -f "$REPO/.env.local" ] || { log "[致命] 缺 $REPO/.env.local (模型 Key 来源)"; exit 3; }
grep -q "AGENTFRAMEWORK_KEYS_DEEPSEEK" "$REPO/.env.local" || { log "[致命] .env.local 未含 AGENTFRAMEWORK_KEYS_DEEPSEEK"; exit 3; }
set -a; . "$REPO/.env.local"; set +a   # 凭据只经环境注入, 不落盘不回显
log "== 臂 O 复跑: 5 节点 × 8 步 + --scope (R519 同题面) =="
AGENTFRAMEWORK_WORKSPACE="$D/orch/ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
  timeout 3000 "$BIN" --orchestrate "$R/plan-games-longtask.txt" --scope "$R/scope-games-longtask.txt" \
  --node-steps 8 --workspace "$D/orch/ws" --session "r520-orch" --report "$D/orch/report.json" \
  > "$D/logs/arm-O.txt" 2>&1
log "ARM_O_RC=$?"
log "== 影子路径落盘机检 (工作区内不得出现自身位置的副本) =="
python3 "$R/shadow_check_r520.py" --root "$D/orch/ws" 2>&1 | tee "$D/logs/shadow-check.txt"
log "SHADOW_CHECK_RC=$?"
log "== 58 用例评分 (与 R519 同判据器, md5 同源) =="
python3 "$R/grade_r520.py" --dir "$D/orch/ws" --out "$D/grade-orch.json" > "$D/logs/grade-orch.txt" 2>&1
echo "GRADE_orch_RC=$?" >> "$D/logs/grade-orch.txt"
log "DONE RUN_DIR=$D"
