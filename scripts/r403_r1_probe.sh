#!/usr/bin/env bash
# R403 · DeepSeek-R1-Distill-Qwen-1.5B 真机探针
# 目的双关: ① 用户问"更小/同尺寸更强"的候选是否可用; ② 诊断探针 —— 它是 qwen2 架构但
#           **untied**(有 output.weight), 而 qwen2.5-math-1.5B 是 tied ⇒ 可判别 tied 词表路径是否就是乱码根因。
# 串行: 等主作业 (pid 63874) 退出后再跑, 避免 CPU/磁盘争用污染读数。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"
BIN=src/agent.rover/bin/Release/net10.0/agent.rover.dll
M=/tmp/models/r1-distill-qwen-1.5b-q4km.gguf
L=eval/rover/r403/raw
mkdir -p "$L"

while kill -0 63874 2>/dev/null; do sleep 10; done
echo "##### 主作业已退出, 开始 R1 探针 #####"

# 0) 登记表 sha256/size 对账 (tree API)
curl -s -m 60 "https://hf-mirror.com/api/models/bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/tree/main?recursive=true" > "$L/r1-registry.json" 2>&1
python3 - <<'PY'
import json,os,hashlib
p="eval/rover/r403/raw/r1-registry.json"
try:
    d=json.load(open(p))
    for it in d:
        if it.get("path","").endswith("Q4_K_M.gguf"):
            size=it.get("size"); lfs=(it.get("lfs") or {}).get("oid")
            local="/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
            ls=os.path.getsize(local)
            print(f"registry{{path={it['path']} size={size} lfs_oid={lfs} local_size={ls} size_match={size==ls}}}")
except Exception as e:
    print("registry_check_error", e)
PY

# 1) 元数据 + 分词
dotnet $BIN meta $M > "$L/meta-r1.log" 2>&1
grep -E "^cfg\{|arch=" "$L/meta-r1.log" | head -4
dotnet $BIN tokenize $M --text "1, 2, 3, 4, 5," > "$L/tok-r1.log" 2>&1
grep -E "^(tokenset|ids)\{" "$L/tok-r1.log" | head -2

# 2) 生成: 平凡续写 + 直答数学题 (与 1.5B-Math 同条件)
while IFS='|' read -r P TAG N; do
  dotnet $BIN generate $M --prompt "$P" --max-tokens "$N" --temperature 0 \
    --json "$L/gen-r1-$TAG.json" > "$L/gen-r1-$TAG.log" 2>&1
  echo "--- gen $TAG (prompt=$P) ---"
  grep -E "^(gen_text|gen_text_raw|gen_done)" "$L/gen-r1-$TAG.log" | head -3
done <<'SPECS'
1, 2, 3, 4, 5,|trivial|4
What is 12*12? Answer with the number.|math|8
SPECS

echo "##### R1 探针完成 #####"
