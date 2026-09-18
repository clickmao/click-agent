#!/usr/bin/env bash
# R561 本地提交 (推送暂停令在效: 只 commit, 不 push / 不 gh api 写)
set -uo pipefail
cd /home/agentuser/AgentFramework
MSG=${MSG:-"R561: 判据口径修订(质量判据 v2: 逐窗并列+真值崩窗 unreliable+VOID 臂窗单列, 影子自检 6 夹具) + 剂量轴收口(封存前提被自身机检证伪 ⇒ 不封存为「已证无增益」, 停用实验轴/产品默认不改/写死重开条件) —— 9 窗 x 3 臂离线复算 (零远端/零产品改动/零新臂), 复算一致性 27/27; 铁律11 rc=1"}
PATHS=(
  "docs/improvements.md"
  "docs/reports/iteration-master-plan.md"
  "docs/reports/r561-judge-v2-and-dose-axis-closure.md"
  "eval/capability/kpi.jsonl"
  "eval/rover/r561/"
)
# 逐字取自 git status --porcelain, 并核对每条确实存在
for p in "${PATHS[@]}"; do
  if ! git status --porcelain -- "$p" | grep -q .; then
    echo "[致命] 路径无改动/不存在: $p"; exit 3
  fi
done
git add -- "${PATHS[@]}"
git status --porcelain | grep -E "^[AM]" | sed 's/^/STAGED: /'
git commit -q -m "$MSG" || { echo "[致命] commit 失败"; exit 4; }
echo "--- 回读 HEAD ---"
git log --oneline -1
git show --stat --oneline HEAD | tail -12
