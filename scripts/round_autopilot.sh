#!/usr/bin/env bash
# =============================================================================
# round_autopilot.sh — 批测轮次自动巡航（R369 用户 OOB 钦定）
#
# 语义：一轮批测结束后**自动开始下一轮**，无需人工触发。
# 轮次结束判定 = 双判据（必须同时满足，避免"日志像结束但数据没落盘"）：
#   ① 日志出现收尾行 `=== round=<N> passed=`（run_round.py:699 的收尾标记）
#   ② 产物落盘 `eval/results/<N>.json` 存在（run_round.py:714 镜像）
#   并且 run_round.py 进程已退出（否则可能仍是上一轮的中间态）。
#
# 安全设计（对应"轮号占用判定铁律"）：
#   · flock 独占锁 → 同一时刻只有一个巡航实例
#   · 启动前 pgrep run_round.py → 有别的 runner 在跑就诚实退出，绝不并发写
#   · 轮号取 max(现有 results/rounds 轮号) + 1（不取"首个空位"，避免被 sibling 占用）
#   · 目标轮文件已存在且 mtime 距今 >10min 才算 stale；否则视为在写，跳过并等待
#   · 任一环节异常 → 记 FAILED 到状态文件并停止（不盲目续跑）
#
# 用法:
#   scripts/round_autopilot.sh [--max-rounds N] [--start N] [--label-prefix S] [--dry-run]
# 停止:
#   touch /tmp/round_autopilot.stop      # 优雅停在当前轮结束
#   pkill -f round_autopilot.sh          # 立即停（不影响在跑的 run_round.py）
# 状态（监控入口）:
#   /tmp/round_autopilot.status   # JSONL: {ts, round, phase, passed, cases, tokens, wall_ms, log}
#   /tmp/round_autopilot.log      # 巡航自身日志
#   tail -f /tmp/batch<N>.log     # 当前轮 LLM 输出
# =============================================================================
set -uo pipefail

REPO="${ROUND_AUTOPILOT_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOCK="/tmp/round_autopilot.lock"
STOP="/tmp/round_autopilot.stop"
STATUS="/tmp/round_autopilot.status"
SLOG="/tmp/round_autopilot.log"

MAX_ROUNDS=1000; START=""; PREFIX="auto"; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --max-rounds) MAX_ROUNDS="$2"; shift 2;;
    --start)      START="$2"; shift 2;;
    --label-prefix) PREFIX="$2"; shift 2;;
    --dry-run)    DRY=1; shift;;
    *) echo "未知参数: $1" >&2; exit 2;;
  esac
done

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$SLOG" >&2; }
status() { printf '{"ts":"%s","round":%s,"phase":"%s"%s}\n' \
  "$(date '+%F %T')" "${2:-0}" "$1" "${3:-}" >> "$STATUS"; }

# ── 独占锁 ────────────────────────────────────────────────────────────────────
exec 9>"$LOCK" || { echo "无法创建锁 $LOCK" >&2; exit 3; }
if ! flock -n 9; then log "另一个 round_autopilot 实例持有锁 — 本实例退出"; exit 4; fi

cd "$REPO" || { log "REPO 不存在: $REPO"; exit 5; }
log "巡航启动 repo=$REPO max_rounds=$MAX_ROUNDS dry_run=$DRY"

# ── 轮号工具 ──────────────────────────────────────────────────────────────────
next_round() {
  python3 - "$REPO" <<'PY'
import os, re, sys
repo = sys.argv[1]
nums = []
for d in ("eval/results", "rounds"):
    p = os.path.join(repo, d)
    if not os.path.isdir(p):
        continue
    for f in os.listdir(p):
        m = re.fullmatch(r"(?:mass_)?(\d+)\.json", f)
        if m:
            nums.append(int(m.group(1)))
print((max(nums) + 1) if nums else 1)
PY
}

round_artifact_ready() { [ -s "$REPO/eval/results/$1.json" ]; }
round_marker_in_log() { grep -qE "^=== round=$1 |^=== round=$1$" "$2" 2>/dev/null; }
runner_alive() { pgrep -f "run_round\.py" >/dev/null 2>&1; }

# ── 单轮执行 ──────────────────────────────────────────────────────────────────
run_one() {
  local N="$1" LOG="/tmp/batch$1.log"
  if round_artifact_ready "$N"; then
    if [ -n "$(find "$REPO/eval/results/$N.json" -mmin +10 2>/dev/null)" ]; then
      log "轮 $N 已有产物且 >10min（stale）→ 跳过，不覆盖"
      status SKIPPED "$N" ',"reason":"artifact_exists_stale"'
      return 0
    fi
    log "轮 $N 产物正在写入（<10min）→ 视为 sibling 在跑，等待"
    return 1
  fi
  if [ "$DRY" = 1 ]; then log "[dry-run] 将执行: run_round.py --quick $N"; return 0; fi

  log "轮 $N 开始 → $LOG"
  status RUNNING "$N" ''
  (
    cd "$REPO" || exit 1
    export PATH="$HOME/.dotnet:$PATH"
    if [ -f .env.local ]; then set -a; . ./.env.local; set +a; fi
    python3 -u eval/run_round.py --quick "$N" "$PREFIX R$N" >"$LOG" 2>&1
  )
  local rc=$?

  # ── 结尾双判据 ──
  if [ $rc -eq 0 ] && round_marker_in_log "$N" "$LOG" && round_artifact_ready "$N"; then
    local sum
    sum=$(python3 - "$REPO/eval/results/$N.json" <<'PY' 2>/dev/null
import json, sys
d = json.load(open(sys.argv[1]))
print(f'\\"passed\\":{d.get("passed")},"cases":{d.get("cases")},"tokens":{d.get("tokens_total")},"wall_ms":{d.get("wall_total_ms")}')
PY
)
    log "轮 $N 完成 ✅ $(echo "$sum" | tr ',' ' ')"
    status DONE "$N" ",$sum"
    return 0
  fi
  log "轮 $N 异常 ❌ rc=$rc marker=$(round_marker_in_log "$N" "$LOG" && echo ok || echo no) artifact=$(round_artifact_ready "$N" && echo ok || echo no)"
  status FAILED "$N" ",\"rc\":$rc"
  return 2
}

# ── 主循环 ────────────────────────────────────────────────────────────────────
if runner_alive; then
  log "检测到其他 run_round.py 在跑 → 本巡航不介入（轮号分裂防护）"
  pgrep -af "run_round\.py" | head -3 | tee -a "$SLOG" >&2
  status EXTERNAL_RUNNER_RUNNING 0 ''
  exit 6
fi

N="${START:-$(next_round)}"
COUNT=0
while [ "$COUNT" -lt "$MAX_ROUNDS" ]; do
  if [ -f "$STOP" ]; then log "发现停止文件 $STOP → 退出"; status STOPPED "$N" ''; exit 0; fi
  if ! run_one "$N"; then
    # 产物冲突（sibling 在写）或失败：等待/停止
    if runner_alive; then log "有 runner 在跑 → 等 60s 后重试"; sleep 60; continue; fi
    log "轮 $N 失败且无 runner → 停止巡航（不盲目续跑）"; exit 7
  fi
  COUNT=$((COUNT + 1))
  N=$((N + 1))
done
log "达到 max-rounds=$MAX_ROUNDS → 正常退出"
status MAX_ROUNDS_REACHED "$N" ''
