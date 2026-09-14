#!/usr/bin/env bash
# 开发侧回流 digest v1 的本地提交器 — 只本地 commit, 绝不 push (推送暂停令 2026-09-13 未解除)
set -eu
cd /home/agentuser/AgentFramework

test -f .git/PUSH_PAUSED || { echo "[FAIL] PUSH_PAUSED 标记不在位, 拒绝继续"; exit 1; }

git add scripts/dev_return_digest.py docs/reports/dev-return-digest.md

git -c user.name=dev -c user.email=dev@local commit -q -m "dev-return: 开发侧回流 digest 机械生成器 + 单页 digest (D状态/探针裁决/轮次提交/台账/口径红线/复验命令)

- 生成器 scripts/dev_return_digest.py: 只汇聚已有外部真值产物与台账, 不产生新读数
- 单页 docs/reports/dev-return-digest.md: 9 个 D 条目(含源行号) + 4 个探针裁决 + 未推提交数 + 台账状态 + 口径红线 7 条
- 如实暴露文档缺口: D6/D9-a 仅正文提及无独立小节 ⇒ 渲染为缺口而非猜状态
- 未标注状态的条目渲染 (未标注), 不推断

验证: DevPlanDocRef/VerificationForm/SkillGeneralization 13/13; 生成器可重入(同输入同产物)"

git --no-pager log --oneline -1
echo "[ok] 已本地提交; 推送三道闸未动"
