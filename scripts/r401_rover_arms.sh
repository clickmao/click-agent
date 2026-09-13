#!/usr/bin/env bash
# R401 解法级对比: rover 臂两次真机跑 (非 dotnet 构建, 只跑已发布 CLI)。
#   A 模板对等臂: prompt 取自目标 GGUF 自身 chat_template (jinja2 渲染) ⇒ 与远端 API 臂同 prompt 语义
#   B 归因对照臂: 引擎内建 --chat (硬编码 DeepSeek 版式) ⇒ 实测标签不在 qwen 词表, 用于归因「输出异常」的成因
# 每题落 data/probe/r401/raw-*/rover-gen-<tid>.json (含 prompt_sha256/prompt_tokens/ms_per_token)
set -u
cd "$(dirname "$0")/.."
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
M=${R401_MODEL:-/tmp/models/qwen25-math-1.5b-i1-q4km.gguf}
TS=data/probe/r401/taskset-r401.json
if [ ! -f "$M" ]; then echo "FAILED: 模型不存在 $M"; exit 3; fi
echo "[$(date +%T)] model=$(basename "$M") bytes=$(stat -c%s "$M")"

export AGENTFRAMEWORK_ROVER_MODEL="$M"
export PROBE_ROVER_JSON_DIR=data/probe/r401/raw-template
export PROBE_ROVER_PROMPT_MODE=template
export PROBE_ROVER_MAX_TOKENS=${R401_MAX_TOKENS:-128}
echo "[$(date +%T)] A) template-parity arm max_tokens=$PROBE_ROVER_MAX_TOKENS"
python3 eval/probe/run_probe.py --solver rover --tasks "$TS" --tag r401-template \
    --solve-timeout 1800 --out data/probe/r401/probe-rover-template.json 2>&1 | tail -8
echo "[$(date +%T)] A done rc=$?"

export PROBE_ROVER_JSON_DIR=data/probe/r401/raw-enginechat
export PROBE_ROVER_PROMPT_MODE=engine-chat
export PROBE_ROVER_MAX_TOKENS=${R401_CHAT_MAX_TOKENS:-64}
echo "[$(date +%T)] B) engine-chat(硬编码版式) arm max_tokens=$PROBE_ROVER_MAX_TOKENS (m001 only)"
python3 eval/probe/run_probe.py --solver rover --tasks "$TS" --limit 1 --tag r401-enginechat \
    --solve-timeout 1800 --out data/probe/r401/probe-rover-enginechat.json 2>&1 | tail -8
echo "[$(date +%T)] B done rc=$?"
echo "[$(date +%T)] ALL DONE"
