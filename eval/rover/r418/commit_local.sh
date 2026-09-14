#!/usr/bin/env bash
# R418 本地提交（推送暂停令生效：只本地，不 push）
set -u
cd /home/agentuser/AgentFramework
git add -A docs/improvements.md docs/plans/v0.39.0-r418-process-kpi.md docs/plans/v715_dev_plan.taskplan.json \
  docs/reports/dev-return-digest.md docs/verification-registry.json eval/probe/README.md \
  eval/probe/run_probe.py eval/probe/process_metrics.py eval/rover/r418 scripts/dev_return_digest.py
git -c user.name=agentframework -c user.email=agentframework@local commit -q -F - <<'MSG'
R418 探针「过程/成本」维度 KPI: 归属铁律 + 真机成本读数 + 成对负控

- 新 process_metrics.py(349 行): 质量=判定器产物 / 成本=归档回复原文; 归属三级
  (reply_ns 精确名 → 时间窗[ts-elapsed-5s, ts+60s] → n/a); 窗内多候选判歧义不猜;
  n/a≠0 且剔除均值分母; 首次通过率只数 ok∧turn==1(turn 未知单列 first_try_unknown)
- run_probe.py: 归档名加 seed 命名空间(agents<seed>-pNNN.txt) + 摘要记 reply_ns
  (旧缺陷: --tag 默认空 ⇒ 同 solver 不同臂写同一路径 ⇒ 下游必张冠李戴)
- 真机 AOT json_mini n=3 seed=20260916: 整题全对 2/3=0.6667, 用例级 52/53=0.9811,
  tokens/题 9151(prompt 侧), 墙钟均 77.7s/题, turn≤1, n/a 0, 畸形 0
- 成对负控 mutation:json_loose n=4: 整题全对 0/4, 用例级 0.7324, 成本记 4×n/a
- 失分用例双路径核对(活跑+离线复判逐位一致): p002 case#3 got '["a\tb"]' want 'ERR'
- digest §3 拼质量与成本同行; improvements/registry(L4)/TaskPlan(21 节点) 回填
- 门: 45/29/18/14/PASS selftest + 形式 6/6 + 全量 1164/0/0(前两次假红已分诊为同机争用)
- 未推: 推送暂停令生效
MSG
git log --oneline -1
git status --porcelain
echo "COMMITS_UNPUSHED=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo n/a)"
