#!/usr/bin/env bash
# RF0006 判别位 A/B 运轮器（夹具 = eval/rover/r462 · 28 例 · ctx 1024 · 无 GPU · 同机同窗）
#
# 用法（每条 = 一个臂；同一时刻只允许一个 llama-server）：
#   TAG=lfm3b-main  BIN=/tmp/llamatq/llama-b11065/llama-server                  \
#   MODEL=$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf      \
#   PORT=48791 bash run-ab.sh
#
#   TAG=lfm3b-fork  BIN=/tmp/tb2fork/llama-prism-b10709-9a9394a/llama-server   \
#   MODEL=$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf      \
#   PORT=48792 bash run-ab.sh
#
#   TAG=bonsai8b-fork … MODEL=/tmp/llamatq/out/Ternary-Bonsai-8B-PQ2_0.gguf  PORT=48793 bash run-ab.sh
#   TAG=bonsai4b-fork … MODEL=/tmp/llamatq/out/Ternary-Bonsai-4B-PQ2_0.gguf  PORT=48794 bash run-ab.sh
#
# 产物：/tmp/r462_out_<TAG>.json（acc / false_skip_n / miss_skip_n / undecided_n / gen_truth_sum / elapsed_s / rows[]）
set -eu
TAG=${TAG:?TAG required}; BIN=${BIN:?BIN required}; MODEL=${MODEL:?MODEL required}
PORT=${PORT:-48791}; CTX=${CTX:-1024}; TIMEOUT=${TIMEOUT:-10800}
R=$(cd "$(dirname "$0")/../../rover/r462" && pwd)     # 夹具目录（本脚本不复制、不修改夹具）
if [ ! -f "$R/bench_r462_w.py" ]; then echo "[致命] 夹具缺失: $R/bench_r462_w.py" >&2; exit 2; fi
if [ ! -f "$MODEL" ]; then echo "[致命] 模型缺失: $MODEL" >&2; exit 2; fi

# bench_r462_w.py 从 /tmp 读取题集（历史约定），此处只做只读拷贝
cp -f "$R/corpus-r462-w.json" /tmp/r462_corpus.json
mkdir -p /tmp/llama-full/build/bin
ln -sf "$BIN" /tmp/llama-full/build/bin/llama-server
echo "=== ARM $TAG bin=$BIN model=$(basename "$MODEL") bytes=$(stat -c%s "$MODEL") ctx=$CTX start=$(date +%H:%M:%S) ==="
timeout "$TIMEOUT" python3 "$R/bench_r462_w.py" --model "$MODEL" --tag "$TAG" --port "$PORT" --ctx "$CTX" \
        --out "${OUT:-/tmp/r462_out_$TAG.json}"
rc=$?
echo "=== ARM $TAG rc=$rc end=$(date +%H:%M:%S) ==="
exit $rc
