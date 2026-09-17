#!/usr/bin/env bash
# EXP1-Q46 提交 (显式路径, staged==清单 机检, 提交后回读)
set -u
cd /home/agentuser/AgentFramework || exit 3
OUT=eval/capability/exp1-q46/commit_q46.txt
exec > >(tee "$OUT") 2>&1

D=eval/capability/exp1-q46
DOC=docs/reports/dynamic-telemetry-eval-rollback-strategy.md
KPI=eval/capability/kpi.jsonl

echo "---- 待提交清单 (git status --porcelain, 逐字取) ----"
git status --porcelain -- "$DOC" "$KPI" "$D" | sed 's/^/RAW /'

# 显式路径 add (目录展开由 git 处理; 不使用 -A / .)
git add -- "$DOC" "$KPI" "$D" || { echo "ADD_EXIT=2"; exit 2; }

echo "---- staged (name-only) ----"
git diff --cached --name-only | sed 's/^/STAGED /'
N_STAGED=$(git diff --cached --name-only | wc -l)
N_EXPECT=$(( $(git status --porcelain -- "$DOC" "$KPI" "$D" | wc -l) ))
echo "STAGED_COUNT=$N_STAGED EXPECT_COUNT=$N_EXPECT"

echo "---- numstat (doc 应为 1 1) ----"
git diff --cached --numstat -- "$DOC"

MSG="EXP1-Q46: 记录面假开放项闭合 (route.first 指向的 improvements.md 轮节项已由 EXP1-Q45 =1ef590a 闭合, 机检 rc=0) + 时效字段登记; 自捕两处器具假红(旧键与新文本重叠⇒读回恒假) + 路径引用写显式(v2); 预注册 14/14 PASS; 探针自检 34/34; 形式门禁 SKIPPED(对侧 R519 起臂窗口占用, 零 dotnet 替代机检 rc=0)"
git commit -q -m "$MSG" || { echo "COMMIT_EXIT=2 (可能被钩子拒; index 仍 staged ⇒ 修后重跑)"; git diff --cached --name-only | wc -l; exit 2; }

echo "---- 回读 HEAD ----"
git log -1 --format='HEAD=%h %ad %s' --date=format:'%H:%M' | cut -c1-160
git show --stat --oneline HEAD | tail -20
echo "WORKTREE_DOC_CLEAN=$(git status --porcelain -- "$DOC" | wc -l)"
echo "COMMIT_EXIT=0"
