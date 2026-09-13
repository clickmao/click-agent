#!/usr/bin/env bash
# R403 · RoPE 配对修复的"改后"证据采集 (生成质量 A/B + 全量回归)
# 串行执行: 生成先跑 (独占机器, 保证 ms/token 读数不被争用污染), 回归后跑。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
BIN=src/agent.rover/bin/Release/net10.0/agent.rover.dll
M=/tmp/models/prover7b-q4km.gguf
OUT=eval/rover/r403/raw
mkdir -p "$OUT"

run_gen () {  # $1=prompt $2=max_tokens $3=tag
  local p="$1" n="$2" tag="$3"
  echo "##### gen-after tag=$tag prompt=[$p] max_tokens=$n #####"
  dotnet "$BIN" generate "$M" --prompt "$p" --max-tokens "$n" --temperature 0 \
      --json "$OUT/gen-after-$tag.json" 2>&1 | grep -E "prompt\{|ids\{|gen_text|gen_done|step" | head -6
}

run_gen "1, 2, 3, 4, 5," 4 trivial
run_gen "2, 4, 6, 8," 4 even
run_gen "What is 12*12?" 8 math

echo "##### 全量回归 #####"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test -c Release src/agent.tests/agentframework.tests.csproj --no-build 2>&1 | tail -4
echo "##### DONE #####"
