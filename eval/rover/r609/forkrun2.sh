#!/usr/bin/env bash
# RF0006 QR1c-v2：P2_0 件 × 厂商 fork(prism-b10709, CPU) 速度/上下文标度
# v2 修正（R609 事故）：
#  (a) 每档输出物理上限 head -c 4MiB（v1 stage[2] 无上限 ⇒ REPL 空转写盘 1,741,793,711 B / 581,597,563 行）
#  (b) 全档补 -st（v1 stage[2]/[3] 缺 -st ⇒ 交互 REPL，stdin EOF 后空转刷 '> '）
#  (c) 起手 / 逐步 df 前置闸（磁盘 <2GB 即 ABORT_DISK）
#  (d) 模式检测：命中 'available commands:' 判定 ARM_INVALID（不进对账）
#  (e) RSS 峰值采样（被测进程自落 pid → 按 pid 采样，不用 pkill -f）
set -u
OUT=/tmp/forkr2; mkdir -p "$OUT"
FORK=/tmp/tb2fork/llama-prism-b10709-9a9394a/llama-cli
M=/tmp/llamatq/out/Ternary-Bonsai-4B-PQ2_0.gguf
CAP=$((4*1024*1024))
df -m "$OUT" | tail -1 | awk '{print "df_free_mb="$4}'

run_stage() {  # $1=name $2=extra args...
  local name="$1"; shift
  local log="$OUT/$name.txt"
  [ "$(df -m "$OUT" | tail -1 | awk '{print $4}')" -lt 2000 ] && { echo "$name ABORT_DISK"; return 9; }
  local t0=$(date +%s)
  # RSS 采样器：被测进程 pid 由包装脚本落盘
  ( timeout 900 "$FORK" "$@" -st --no-display-prompt 2>&1 | head -c $CAP > "$log" ) &
  local wp=$!
  local peak=0
  while kill -0 $wp 2>/dev/null; do
    local r=$(pgrep -f '[l]lama-prism' | while read p; do ps -o rss= -p $p; done | sort -n | tail -1)
    [ -n "${r:-}" ] && [ "$r" -gt "$peak" ] && peak=$r
    sleep 2
  done
  wait $wp; local rc=$?
  local t1=$(date +%s)
  local mode=ok; grep -q 'available commands:' "$log" && mode=REPL_INVALID
  local perf=$(tr -d '\r' < "$log" | grep -o '\[ Prompt: [0-9.]* t/s | Generation: [0-9.]* t/s \]' | tail -1)
  echo "$name rc=$rc wall=$((t1-t0))s mode=$mode peak_rss_mb=$((peak/1024)) bytes=$(stat -c%s "$log") $perf"
}

echo "== QR1c-v2 fork=$(basename $FORK) model_bytes=$(stat -c%s $M) start=$(date +%H:%M:%S) =="
run_stage tg128 -m "$M" -p 'The capital of France is' -n 128 --temp 0 -c 512 -t 2
for N in 256 512 1024 2048; do
  F='The quick brown fox jumps over the lazy dog and then walks along the river bank. '
  python3 -c "open('/tmp/forkr2/prompt_$N.txt','w').write('$F'*(($N//18)+1))"
  run_stage pp_$N -m "$M" -f "/tmp/forkr2/prompt_$N.txt" -n 1 --temp 0 -c $((N+256)) -t 2
done
echo "== QR1c-v2 DONE $(date +%H:%M:%S) =="
