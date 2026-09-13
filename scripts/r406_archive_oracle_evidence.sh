#!/bin/sh
# R406: 归档「llama-cli 在 -no-cnv 下仍进会话 REPL」这一失控臂里的**有效证据**(生成结果),
# 防止重跑覆盖日志后丢失。抽取非 '> ' 行 (REPL 空转提示符)。
set -u
cd /home/agentuser/AgentFramework
SRC=eval/rover/r403/oracle/oracle-trivial.log
DST=eval/rover/r405/oracle-chat-mode-leak-trivial-2026-09-14.txt

{
  echo "# R406 证据: llama-cli (-no-cnv) 仍自动进会话模式 (help: 有 chat template 时默认 auto), 生成本身正常,"
  echo "#            生成结束后 stdin EOF ⇒ 空转刷 '> ' 提示符 (本次 1,397,341 行 / 4MB 硬上限截断)。"
  echo "# 源: $SRC"
  echo "# 抽取: grep -v '^> \$'"
  echo "---"
  grep -v '^> $' "$SRC"
} > "$DST"

echo "归档 -> $DST"
wc -l "$DST"
ls -la "$DST"
