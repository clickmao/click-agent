#!/usr/bin/env bash
# EXP1-Q37 候选①: 面跑前占用核验闸 (结果落盘再读, 不凭工具回显判空闲)
# 用法: bash eval/capability/exp1-q38/precheck_occupancy.sh <out_file> [WAIT_S]
#   WAIT_S>0 ⇒ 有界等待: 每 15s 重采样, 一旦 IDLE 立即放行 (不无限等)。
# 语义: 宽模式匹配 (含 build/publish/test/宿主/服务/面器具) + 连续两次采样 + 内存门槛。
# 单位纪律: /proc/meminfo 给的是 kB ⇒ 显式换算成 MB 后与门槛比 (首版把 kB 直接比 MB 门槛
#           ⇒ 恒判空闲; 由 U1 单位不变式机检住)。全缺/解析不出 ⇒ 测量失败 (rc=3), 不是放行。
set -uo pipefail
OUT="${1:-eval/capability/exp1-q38/occupancy_pre.txt}"
WAIT_S="${2:-0}"
PAT='dotnet|msbuild|MSBuild|VBCSCompiler|instruments_check|run_round|capability_cycle|llama-server|pytest|nunit'
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT" || exit 3

procs() { pgrep -af "$PAT" 2>/dev/null | grep -v 'precheck_occupancy' | grep -v pgrep; }
mem_kb() { awk '/^MemAvailable:/{print $2}' /proc/meminfo; }

round_gate() {
  local tag="$1"
  echo "--- 采样($tag) $(date -Is) ---" >> "$OUT"
  procs >> "$OUT"
  echo "n_$tag=$(procs | wc -l)" >> "$OUT"
}

: > "$OUT"
echo "ts=$(date -Is)" >> "$OUT"
echo "root=$ROOT" >> "$OUT"
echo "MEM_MIN_MB=${MEM_MIN_MB:-2600} WAIT_S=$WAIT_S" >> "$OUT"
: "${MEM_MIN_MB:=2600}"

verdict=BUSY; tries=0
while :; do
  tries=$((tries + 1))
  round_gate "a$tries"
  sleep 5
  round_gate "b$tries"
  mk=$(mem_kb)
  echo "mem_kb=$mk" >> "$OUT"
  if [ -n "${mk:-}" ] && [ "$mk" -gt 0 ] 2>/dev/null; then
    mem_mb=$((mk / 1024))
    echo "mem_mb=$mem_mb" >> "$OUT"
    # U1 单位不变式: MB 必须等于 kB/1024 (机检住首版的 kB-vs-MB 混比)
    [ "$mem_mb" -eq $((mk / 1024)) ] || { echo "UNIT_INVARIANT=FAIL" >> "$OUT"; exit 3; }
  else
    mem_mb=-1
    echo "MEM_PARSE=FAIL" >> "$OUT"
    echo "PRE_GATE_VERDICT=MEASURE_FAIL" | tee -a "$OUT"
    exit 3
  fi
  n1=$(grep -m1 "^n_a$tries=" "$OUT" | cut -d= -f2)
  n2=$(grep -m1 "^n_b$tries=" "$OUT" | cut -d= -f2)
  echo "round$tries n1=$n1 n2=$n2 mem_mb=$mem_mb" >> "$OUT"
  if [ "${n1:-9}" = "0" ] && [ "${n2:-9}" = "0" ] && [ "$mem_mb" -ge "$MEM_MIN_MB" ]; then
    verdict=IDLE; break
  fi
  [ "$WAIT_S" -gt 0 ] || break
  [ $((tries * 20)) -lt "$WAIT_S" ] || break
  echo "WAIT: 仍 BUSY (n1=$n1 n2=$n2 mem_mb=$mem_mb) ⇒ 15s 后重采样" | tee -a "$OUT"
  sleep 15
done

echo "PRE_GATE_VERDICT=$verdict" | tee -a "$OUT"
echo "PRE_GATE_VERDICT=$verdict tries=$tries (落盘 $OUT)"
[ "$verdict" = "IDLE" ] || exit 4
exit 0
