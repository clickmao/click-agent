#!/usr/bin/env bash
# R596 候选④: 落点谓词分层 —— ① 零回归对照臂（登记窗集 r585..r591, 与 r592 读数逐字段比对）
#                          ② 第三窗集 (r596) 分布单列
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
: "${AGENTFRAMEWORK_KEYS_DEEPSEEK:=}"
if [ -z "$AGENTFRAMEWORK_KEYS_DEEPSEEK" ]; then set -a; . "$HOME/.agentframework/keys.env"; set +a; fi
L=eval/rover/r596/logs
mkdir -p "$L"
echo "[start] $(date +%H:%M:%S)"
timeout 2400 python3 eval/rover/r593/landing_predicate_r593.py \
  --out eval/rover/r596/landing-predicate-r596.json --codex-too > "$L/landing-zero-reg.txt" 2>&1
echo "RUN1_ZERO_REG=$?"
timeout 2400 python3 eval/rover/r593/landing_predicate_r593.py --rounds r596 \
  --out eval/rover/r596/landing-third-r596.json --codex-too > "$L/landing-third.txt" 2>&1
echo "RUN2_THIRD=$?"
echo "[done] $(date +%H:%M:%S)"
