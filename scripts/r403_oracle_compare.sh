#!/usr/bin/env bash
# R403 独立 oracle 对账: 分离「引擎 qwen2 路径缺陷」与「prompt 形式 OOD」
#
# 起因(诚实记录): 自研引擎在 qwen2 家族(R1-Distill-1.5B untied / qwen2.5-math-1.5b tied)
# 上对同一批 prompt 输出异常("11 ," / "UNThis0one kil girlsforth0")。此前我把 i1 的
# `gen_text=6622` 当作"qwen2 路径正常"的证据 —— 该判断已作废(6622 不是 "1,2,3,4,5," 的合法续写)。
# tied 假说已被否(R1-Distill 是 untied, 照样异常)。
#
# ===== 判据(预注册, 跑之前写死) =====
# ① 分词与 prompt 逐 id 对账: llama.cpp --verbose-prompt 打印的 prompt token id 必须与
#    自研引擎 ev.../tok 一致; 不一致 ⇒ 先修分词, 后续对比无意义(判 ORACLE_TOKEN_MISMATCH)。
# ② 原始续写臂(双臂同 prompt/同采样/同 n/贪心):
#      B 乱 && A 乱  ⇒ 引擎无罪, 异常来自 prompt 形式(缺 chat template / OOD 输入)
#      B 通顺 && A 乱 ⇒ 引擎 qwen2 路径有 bug ⇒ 转 --dump 逐层对账(embedding→attn→ffn→norm→logits)
# ③ 负控: 同命令重跑一次必须逐字节一致(否则读的是抖动, 不可判定); 另跑 chat-template 臂
#    (-st --jinja) 确认"模型本身在这条题上是否会答" ⇒ 用于区分"模型不会"与"引擎不对"。
# ④ 只认落盘原文; 不得以"看起来差不多"代替逐字对比。
#
# ===== 机制修订 (2026-09-14, R405; 判据①②③④ 一字未动) =====
# 实测事故: 上一版直接把交互式 llama-cli 的 stdout/stderr 重定向到文件, 该 CLI 在 stdin 触 EOF 后
# 空转刷 "> " 提示符 + 载入进度条(\b 序列) ⇒ oracle-trivial.log 30 min 涨到 6.7 GB(2,232 万行),
# 把 50 GB 根盘写满 100%。修订: ① 输出经 head -c 硬截断(文件由 head 独占写, 物理不可能超限);
# ② 运行前后查可用空间, <2 GB 直接 ABORT; ③ 日志超限 ⇒ 该臂判 LOG_OVERFLOW 不参与对账;
# ④ 不再对可能超限的日志做无界 grep。
set -u
ROOT=/home/agentuser/AgentFramework
CLI=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-cli
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
OUT=$ROOT/eval/rover/r403/oracle
LOG_MAX_MB=${LOG_MAX_MB:-4}          # 单臂日志硬上限
MIN_FREE_MB=${MIN_FREE_MB:-2048}     # 可用空间下限
mkdir -p "$OUT"

guard_disk() {
  local free; free=$(df -Pm / | awk 'NR==2{print $4}')
  if [ "$free" -lt "$MIN_FREE_MB" ]; then echo "ABORT_DISK_FREE=${free}MB (<${MIN_FREE_MB}MB)"; exit 9; fi
}
log_ok() { # 超限返回 1, 并把判定写进调用方可见的输出
  local f=$1 sz; sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
  if [ "$sz" -ge $((LOG_MAX_MB*1048576)) ]; then
    echo "LOG_OVERFLOW $(basename "$f") ${sz}B >= ${LOG_MAX_MB}MB ⇒ 输出失控, 该臂不可用"; return 1
  fi; return 0
}

echo "##### 等 oracle 编译完成 (最多 40 min) #####"
for _ in $(seq 1 480); do [ -x "$CLI" ] && break; sleep 5; done
if [ ! -x "$CLI" ]; then echo "ORACLE_CLI_MISSING $CLI"; exit 2; fi
echo "ORACLE_CLI_OK $(stat -c %s "$CLI") bytes  LOG_MAX_MB=$LOG_MAX_MB"
"$CLI" --version 2>&1 | head -3
guard_disk

repl_marker() { # 会话 REPL 标志: '> ' 空提示符 行 或 'available commands:' 或生成标签
  grep -aqE "^> $|^available commands:|^\[Start thinking\]" "$1"
}

run() { # $1=tag $2=prompt $3=n $4..=extra  —— 会话首轮臂 (本 build 关不掉 conv, 见下)
  local tag=$1 p=$2 n=$3 rc; shift 3
  echo "--- [$tag] prompt='$p' n=$n $* ---"
  guard_disk
  # R406 实测 (scripts/r406_oracle_cli_mode_probe.sh, 两臂独立复现):
  #   a) `-no-cnv` 与 `--no-conversation` 在本 build **均未能关闭会话模式** (仍打印 '> ' 与 REPL 回显);
  #   b) 生成结束后 stdin 触 EOF ⇒ 空转刷 '> ' (4 MB 上限 / 千万行);
  #   c) 兜底 = 从 stdin 送 '/exit' ⇒ REPL 立即退出 (2589 B 而非 4 MB);
  #   d) 因此本脚本把 -p 当**会话首轮**使用 (与引擎 --chat 路径同模态), 不再声称是裸补全。
  printf '/exit\n' | timeout 600 "$CLI" -m "$MODEL" -p "$p" -n "$n" --temp 0 -s 0 --no-conversation --no-warmup -t 2 --verbose-prompt "$@" \
      2>&1 | head -c $((LOG_MAX_MB*1048576)) > "$OUT/$tag.log"
  rc=$?
  echo "exit=$rc -> $OUT/$tag.log ($(stat -c %s "$OUT/$tag.log")B)"
  if ! log_ok "$OUT/$tag.log"; then return 7; fi
  if repl_marker "$OUT/$tag.log"; then echo "MODE=auto-chat (conv 无法关闭 ⇒ 按会话首轮解读)"; else echo "MODE=completion"; fi
  grep -aE "^(llama_perf|\[end of text\])" "$OUT/$tag.log" | head -3
  echo "--- 原文(去掉前导空行后 20 行) ---"
  grep -av "^$" "$OUT/$tag.log" | tail -20
}

run_chat() { # $1=tag $2=prompt $3=n —— 会话单轮臂 (-st: 生成完即退, 无 REPL 空转)
  local tag=$1 p=$2 n=$3
  echo "--- [chat:$tag] prompt='$p' n=$n ---"
  guard_disk
  timeout 600 "$CLI" -m "$MODEL" -st --jinja -p "$p" -n "$n" --temp 0 -s 0 --no-warmup -t 2 \
      </dev/null 2>&1 | head -c $((LOG_MAX_MB*1048576)) > "$OUT/$tag.log"
  echo "exit=${PIPESTATUS[0]} -> $OUT/$tag.log ($(stat -c %s "$OUT/$tag.log")B)"
  log_ok "$OUT/$tag.log" || return 7
  grep -av "^$" "$OUT/$tag.log" | tail -12
  grep -aE "^\[ Prompt:" "$OUT/$tag.log" | tail -1
}

run oracle-trivial "1, 2, 3, 4, 5," 4
run oracle-trivial.repeat "1, 2, 3, 4, 5," 4
if cmp -s "$OUT/oracle-trivial.log" "$OUT/oracle-trivial.repeat.log"; then
  echo "NEGCONTROL_DETERMINISM=OK (逐字节一致)"
else
  echo "NEGCONTROL_DETERMINISM=FAIL (同一命令两次输出不同 ⇒ 本轮对比不可判定)"
  diff <(grep -av "^$" "$OUT/oracle-trivial.log") <(grep -av "^$" "$OUT/oracle-trivial.repeat.log") | head -10
fi
run oracle-math "What is 12*12? Answer with the number." 8

echo "##### chat-template 臂 (模型自身模板, 由 llama.cpp 的 jinja 引擎渲染 —— 引擎无关参照) #####"
run_chat oracle-trivial.template "1, 2, 3, 4, 5," 4
run_chat oracle-math.template "What is 12*12? Answer with the number." 64

echo "##### 分词 id 对照 (自研 token 记录 vs oracle --verbose-prompt) #####"
log_ok "$OUT/oracle-trivial.log" && grep -aiE "token|piece" "$OUT/oracle-trivial.log" | head -12
echo "##### 完成 #####"
