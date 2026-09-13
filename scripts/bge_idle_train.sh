#!/usr/bin/env bash
# bge 闲时训练: 本机无任务时 → 采集训练对 → 训练 T1 适配器 → 确定性召回闸门择优 → 版本小报。
# 设计: no_agent cron 直接跑本脚本; 无版本产出则**零输出**(watchdog 形态, 不打扰用户)。
set -uo pipefail
REPO="/home/agentuser/AgentFramework"
cd "$REPO" || exit 0
mkdir -p data/bge data/bge/versions docs/reports/bge/versions
LOG="data/bge/idle.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# 防重入
exec 9>data/bge/.train.lock
flock -n 9 || { log "skip: lock held"; exit 0; }

# ── 闲时判定 (全部满足才跑) ──
read -r l1 _ < /proc/loadavg
memavail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
if awk "BEGIN{exit !($l1 >= 1.0)}"; then log "skip: load=$l1"; exit 0; fi
if [ "${memavail:-0}" -lt 1200 ]; then log "skip: mem=${memavail}MB"; exit 0; fi
busy=$(pgrep -af "run_round|round_autopilot|dotnet build|llama-server|run_recall|gen_queries|train_adapter" 2>/dev/null | wc -l)
if [ "${busy:-0}" -gt 0 ]; then log "skip: busy=$busy"; exit 0; fi
log "idle ok (load=$l1 mem=${memavail}MB)"

export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a

# ── 数据采集 (真实 query 收割 + LLM 出题, 有预算上限) ──
col=$(python3 eval/bge/collect_pairs.py --harvest --gen --budget 240 --max-pairs 120 2>>"$LOG")
log "collect: ${col:-<empty>}"
added=$(printf '%s' "$col" | python3 -c "import sys,json;print(json.load(sys.stdin).get('pairs_added',0))" 2>/dev/null || echo 0)
if [ "${added:-0}" -lt 32 ]; then log "skip train: added=$added < 32"; exit 0; fi

# ── 训练 + 闸门 ──
out=$(python3 eval/bge/train_adapter.py 2>>"$LOG")
log "train: ${out:-<empty>}"
verdict=$(printf '%s' "$out" | python3 -c "import sys,json;print(json.load(sys.stdin)['verdict'])" 2>/dev/null || echo err)
[ "$verdict" = "err" ] && { log "train failed"; exit 0; }
vnum=$(printf '%s' "$out" | python3 -c "import sys,json;print(json.load(sys.stdin)['version'])" 2>/dev/null || echo 0)
report="docs/reports/bge/versions/v${vnum}.md"

# 有版本产出 → 打印小报摘要 (cron 无输出则不推送)
echo "【bge 版本小报 v${vnum}】verdict=${verdict}"
printf '%s' "$out" | python3 -c "
import sys,json
d=json.load(sys.stdin)
b,be=d['base'],d['best'] or {}
print(f\"配置 {d['config']} | 基线 r@1/r@10 = {b['r@1']}/{b['r@10']} → 新版 {be.get('r@1','-')}/{be.get('r@10','-')}\")
print(f\"原因: {d['reason']} | 训练对 {d.get('n_pairs','-')} | 耗时 {d.get('elapsed_s','-')}s\")
" 2>/dev/null
echo "报告: $report"
