#!/usr/bin/env bash
# R371 能力差异探针: 让项目 agent 用 Python 写一个可自测的贪吃蛇游戏
# 目的: 观察 "生成代码 → 落盘 → 校验 → 运行 → 迭代" 哪一环断链 (与宿主侧能力对比)
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 1
export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a
PROBE=/tmp/gameprobe
mkdir -p "$PROBE/work"
# 探针A(已完成): 从 /tmp 运行 → 失败 "模型目录为空" (配置解析绑死 cwd, 属能力差异证据 A)
# 探针B: 从仓库根运行 (config 可见)
BIN=/tmp/pub_aot_r370/agenthost
PROMPT='用 Python 写一个贪吃蛇游戏(终端文本渲染)。要求: (1) 单文件 game.py; (2) 核心逻辑与渲染分离, 逻辑可用 python3 game.py --selftest 无头自测并打印 PASS 或 FAIL; (3) 附运行说明。'
echo "=== PROBE START $(date '+%H:%M:%S') ==="
echo "=== ENV: PY_RUN=${AGENTFRAMEWORK_PY_RUN:-<unset>} PY_ARTIFACT=${AGENTFRAMEWORK_PY_ARTIFACT:-<unset>} ==="
timeout 600 "$BIN" -q "$PROMPT" --output-mode text --log "$PROBE/run_root.md" > "$PROBE/run_root.stdout" 2>&1
echo "EXIT=$?"
echo "=== PROBE END $(date '+%H:%M:%S') ==="
