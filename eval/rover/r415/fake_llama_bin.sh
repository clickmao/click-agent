#!/bin/sh
# R415 假 llama-server 可执行壳: 真链只认「二进制 + --port N」, 壳把端口转交给 python 假后端。
# 位置无关: 配置里 AGENTFRAMEWORK_LLAMA_BIN 指向本文件。
PORT=0
MODEL=unknown
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    -m|--model) MODEL="$2"; shift 2 ;;
    *) shift ;;
  esac
done
# 长驻: 与真 llama-server 同为「进程 + HTTP」形态 (零 P/Invoke)
exec python3 "$(dirname "$0")/fake_llama.py" --port "$PORT" --model "$MODEL"
