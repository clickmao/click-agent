# R631 DAG（起手先出图：意图 → 子任务 / 依赖 / 并行面 / 重启判据）

意图 = 在**与历史窗集不相交**的新窗集上复现 `AGENTFRAMEWORK_R1_ACTION_EXEC` 质量效应，并让铁律 11 验收面**可归属**（named 阻塞，替代 DISCONNECT_FAIL）。

```
N0 起手闸 (roundcheck preflight R631)                      [已完成 rc=0]
      │
      ├─► N1 主线提醒（读 §7 最新块 + RF0004 + 上轮 verdict）   [1 行]
      │
      ├─► N2 契约落地（零产品改动，器具面）
      │      N2a taskset-r631.json（tasks 逐字节复制件）
      │      N2b cases/run_cases_r521.py（逐字节复制）
      │      N2c prereg-r631.json（先写后跑：evidence_scope=臂级验收面）
      │      └─► 依赖：N2c 必须先于 N3 落盘（先写后跑闸）
      │
      ├─► N3 真机臂（唯一变量：窗集；轴 = R1_ACTION_EXEC，held-constant = legacy）
      │      N3a 前提闸（1 跑次，不计入臂表）── 未过 ⇒ rc=5 零臂起跑
      │      N3b 逐窗：codex 真值 ×1 → T ×3 → C ×3（w223/w224）
      │      N3c 逐窗判分 + 快照冻结 + evidence/windows 落盘
      │      └─► 依赖：N2c ∧ adapter 就绪 ∧ 起手闸 A1/A2 连续 PASS
      │
      ├─► N4 判决（judge_r631.py：J0/J1/J3/J4a/J4b/J6/W_floor）
      ├─► N5 铁律 11 前置器（exec_precondition --round r631）
      └─► N6 收口（轮志 + registry 行 + kpi 行带 baselines + status_gen --check + 形式门禁 14/14 + 逐名列名 commit）
```

## 并行面

- **无真并行节点**：全部节点写同一工作树（`eval/rover/r631/**`），且真机臂必须串行（2 vCPU / 3.6 GB / 单适配器端口）。
- 只读并行（可与 N3 同窗）：文献小步（arXiv 检索，**不写仓**，只追加台账）；主线提醒文档读取。
- 子 agent 禁开：同仓在飞写者 = 本侧自身（N3 正在写 `eval/rover/r631/**` 与 `$HOME/.agentframework/harness/runs/r631/**`）。

## 重启判据（收尾按图判「重启哪条边」，不重跑全轮）

| 失败边 | 判据 | 重启边 |
|---|---|---|
| N3a 前提闸 | 非 0（candidates 到达 / 前缀 ≠ legacy 锚） | 回 N2c 复核 prereg 的 held-constant 声明；**禁**改阈值 |
| N3b 跑次 VOID（`stage=llm_transport`） | 判据器 VOID 闸（`calls<1 ∨ stage=llm_transport`） | 只重启该窗该臂（补 adapter 就绪闸），**不重跑全轮**（R630 教训） |
| N4 J0 | 两臂不可区分 / 前缀不同源 | rc=2 整轮 VOID，回 N3b 复核臂环境注入 |
| N4 J4a | Δ 中位 ≤ 0 | **不重启**：按 R2/R5 记「非承重、定案关闭」，换杠杆 |
| N5 P11 | DISCOVER_FAIL | 回 N2a/N2c（契约件缺失/命名不符）重落盘，**重跑前置器**（不重测） |
| 起手闸 A1/A2 | 未 PASS | 清 LSP（VBCSCompiler/MSBuild/pyright）后**重采样**，禁降标准强开 |
