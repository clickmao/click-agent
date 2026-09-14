#!/usr/bin/env bash
# R419 多轮探针驱动 (计划 §5 复验命令): 真机 agent n=3 × 2 轮 + 成对控制 (正控/负控)
#
# 命名空间隔离 (R419 实测事故): 同仓另一执行体也在写 `r419ctlpos/r419a1` 同名档 ⇒
#   本驱动所有臂带**唯一批次后缀** (默认 `b$(date +%m%d%H%M)`), 检查器断言三臂同后缀。
# 设计纪律 (unattended-job-reliability §3):
#   * 前置资产检查 (AOT 二进制 / 磁盘 / 内存), 缺失即秒退并列出检查过的路径
#   * 每步退出码**当场记录**为 STEP_EXIT_*, 批结论只读这些记录, 不由末条命令决定
#   * 结论标记 = R419_EXIT=<码>; 0 全过 / 2 断言失败 / 3 测量或环境失败 (分类不同码)
#   * 不 push / 不调 gh (推送暂停令生效)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$REPO" || exit 3
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"
LOG_DIR="$HERE/logs"
mkdir -p "$LOG_DIR"
NS="${R419_NS:-b$(date +%m%d%H%M)}"
BIN="src/agent.host/bin/Release/net10.0/linux-x64/native/agenthost"

echo "=== 批次后缀 NS=$NS ==="
echo "=== 前置检查 ==="
if [ ! -x "$BIN" ]; then
  echo "ABORT_ASSET_MISSING: $BIN 不存在/不可执行 (检查路径: $BIN)"; echo "R419_EXIT=3"; exit 3
fi
FREE_MB=$(df -Pm . | awk 'NR==2{print $4}')
AVAIL_MB=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "disk_free_mb=$FREE_MB mem_available_mb=$AVAIL_MB"
if [ "${FREE_MB:-0}" -lt 2048 ]; then echo "ABORT_DISK_FREE (需 ≥2048MB)"; echo "R419_EXIT=3"; exit 3; fi
if [ "${AVAIL_MB:-0}" -lt 700 ]; then echo "ABORT_MEM_LOW (需 ≥700MB, 子进程内存计入预算)"; echo "R419_EXIT=3"; exit 3; fi

run_arm () {  # $1=臂前缀 $2=solver
  TAG="$1-$NS"
  echo "--- 臂 $TAG ($2) ---"
  python3 -u eval/probe/run_probe.py --kind program --families json_mini --n 3 --seed 419 \
      --turns 2 --solver "$2" --tag "$TAG" > "$LOG_DIR/$TAG.log" 2>&1
  local rc=$?
  echo "STEP_EXIT_$1=$rc"
  tail -3 "$LOG_DIR/$TAG.log"
  return $rc
}

run_arm r419bctlpos "mutation:delayfix"; pos_rc=$?
run_arm r419bctlneg "mutation:nofix";    neg_rc=$?
run_arm r419bagent  "agent";             ag_rc=$?

echo "=== 多轮表 ==="
python3 eval/probe/process_metrics.py --multiturn --report > "$LOG_DIR/process_metrics-$NS.out" 2>&1
echo "STEP_EXIT_metrics=$?"
cat "$LOG_DIR/process_metrics-$NS.out"

echo "=== 判据检查 (预注册) ==="
python3 eval/rover/r419/check_multiturn.py --ns "$NS" | tee "$LOG_DIR/check-$NS.out"
chk_rc=${PIPESTATUS[0]}

# 批结论: 任一臂执行失败 ⇒ 测量失败(3); 判据红 ⇒ 断言失败(2); 全绿 ⇒ 0
if [ "$pos_rc" -ne 0 ] || [ "$neg_rc" -ne 0 ] || [ "$ag_rc" -ne 0 ]; then
  echo "ARM_RUN_FAILED pos=$pos_rc neg=$neg_rc agent=$ag_rc ⇒ 测量失败"
  echo "R419_EXIT=3"; exit 3
fi
echo "R419_EXIT=$chk_rc"
exit "$chk_rc"
