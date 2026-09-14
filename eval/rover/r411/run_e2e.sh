#!/usr/bin/env bash
# R411 E2E: 长驻多轮会话（正例: 长前缀应达 K2b；负例: 短前缀必越线 ⇒ exit 7）
set -u
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r411
HOST=$ROOT/src/agent.host/bin/Release/net10.0/agenthost
MODEL=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
echo "df: $(df -h / | tail -1)"
for arm in badjson positive negative; do
  echo "=== arm=$arm start $(date -u +%H:%M:%S) ==="
  if [ "$arm" = badjson ]; then
    # 用法错负控: 无 turns 必须 exit 2（且不是 core dump）
    "$HOST" --llamacpp --model "$MODEL" --session-json "$DIR/session-$arm.json" --context 6144 \
        --json "$DIR/session-$arm.out.json" > "$DIR/session-$arm.log" 2>&1
    echo "arm=$arm exit=$? (期望 2)"
    continue
  fi
  "$HOST" --llamacpp --model "$MODEL" --session-json "$DIR/session-$arm.json" --context 6144 \
      --json "$DIR/session-$arm.out.json" > "$DIR/session-$arm.log" 2>&1
  echo "arm=$arm exit=$?"
  echo "=== arm=$arm end $(date -u +%H:%M:%S) ==="
done
echo ALL_DONE
