#!/bin/sh
# R406: 探清 llama-cli 的「会话模式能否关闭」。事实链:
#   1) -no-cnv 短别名: 无效 (仍 auto 进入会话模式, 空转刷 '> ')
#   2) --no-conversation 长别名: 待验
#   3) --no-jinja 组合: 待验
#   4) /exit 经 stdin: 强制 REPL 退出 (与模式无关的兜底)
set -u
CLI=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-cli
M=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
O=/tmp/probe-r406
mkdir -p "$O"

probe() { # $1=tag  $2..=cli args
  tag=$1; shift
  echo "--- [$tag] $* + stdin '/exit' ---"
  printf '/exit\n' | timeout 240 "$CLI" -m "$M" "$@" 2>&1 | head -c 200000 > "$O/$tag.log"
  echo "bytes=$(stat -c %s "$O/$tag.log") repl_marker=$(grep -acE '^> $|available commands:' "$O/$tag.log")"
  grep -av '^$' "$O/$tag.log" | grep -avE '^\s*[▄█]' | tail -6
}

probe nocnv_nojinja -p "1, 2, 3, 4, 5," -n 3 --temp 0 -s 0 --no-conversation --no-jinja --no-warmup -t 2
probe nocnv_jinja   -p "1, 2, 3, 4, 5," -n 3 --temp 0 -s 0 --no-conversation --no-warmup -t 2
probe st_jinja      -st --jinja -p "1, 2, 3, 4, 5," -n 3 --temp 0 -s 0 --no-warmup -t 2

echo "=== 结论判据: repl_marker=0 且 bytes 小 ⇒ 该组合可用于裸补全 ==="
