# R614 · DAG（意图 → 子任务：节点 / 依赖边 / 可并行面 / 收尾重启判据）

- 轮次：**R614**（2026-09-21 · cron 60min tick）｜ 类型：**重启边轮（零新增单变量）**
- 意图：**把 R610 顺延的 `N8→N9` 这条边跑完** —— R610 已把 M3 第一刀（动作候选进 R1 契约 + 本地机械裁选器）落到 `src/` 并提交，
  但真机臂因①同仓在飞写者②内存闸红③共享编译节点在飞而顺延 ⇒ 本轮**只重启该边**（同 `prereg-r610.json` 起臂，禁调闸值）。
- 上位判据：RF0004 §4 M3 出口闸（调用数 ≤ 旧臂 50% ∧ 质量 ≥ 旧臂 ∧ 恒前缀命中 ≥97%）中**本轮只判机制面 + 收集面**
  （执行接线属 M3 第二刀）；RF0005 §1 七硬约束 + 铁律 11 `rc=0` 才可验收。

```
意图：R610 N8→N9 边重启（取得 M3 第一刀真机读数）
  │
  ├─ N1 起手闸（roundcheck preflight R614 + 清 build server + 记 MemAvailable）
  │      └─ 实测 rc=0（FAIL=0/WARN=0；R614 空闲；无在飞执行体）
  │
  ├─ N2 AOT 重发布 `$HOME/.agentframework/artifacts/pub_r610/agenthost`（src/tools 与 R610 零 diff）
  │      └─ 判据：PUBLISH_RC=0 ∧ IL_WARNINGS=0 ∧ ERRORS=0 ∧ ELF 字节数落盘
  │
  ├─ N3 R614 轮面落盘：dag-r614.md + prereg-r614.json（**引用件**，阈值/判据一字不改，权威 prereg = r610 件）
  │      └─ 依赖：无（与 N2 并行：N3 只写 docs/eval 纯文本，不触构建面）
  │
  ├─ N4 真机臂（**唯一真机面**）：`bash eval/rover/r610/run_r610.sh`
  │      ├─ 窗集 = **第十三窗集 w199..w201**（与历史轮不相交；prereg-r610.json 声明）
  │      ├─ 臂表 = T(产品默认档 ×3) / C(`AGENTFRAMEWORK_R1_ACTION_CANDIDATES=0` ×3) / C1(codex 真值 ×1) = 21 跑次
  │      ├─ 同输入硬门：taskset sha `e0c667c2a313c04b`（与 R585–R608 冻结件 `cmp` 零差异）
  │      └─ 依赖：N2（被测件身份）∧ N3（先写后跑闸）
  │
  ├─ N5 文献小步（arXiv ≤3 query / 全文 ≤2 篇；**只读网络**）—— 与 N4 **并行面**
  │      └─ 台账追加在 N4 落盘**之后**做（共享文件写者纪律：面在飞时不写被面调用的文件）
  │
  ├─ N6 判决（runner 尾段自动）：`judge_r610.py` → verdict-r610.json（J1 机制 / J2b 守恒 / J2 收敛 / J3v2 成本 / J4 能力 / J5 同向 + v3 配对）
  │      └─ + 铁律 11 前置器 `exec_precondition.py --round r610`
  │
  └─ N7 收口（依赖 N6 ∧ N5）：报告 / kpi.jsonl 行（带 baselines）/ registry 行 / §7 状态块一行 / `status_gen --check` PASS / 形式门禁 / 逐名列名提交

并行面（可开子 agent 的节点）：仅 N5（只读网络）；N2/N4 写同仓与内存 ⇒ **串行**，禁并行。
收尾重启判据（按 DAG 判「重启哪条边」，不重跑全轮）：
  · bin sha 运行前后不一致 ⇒ 臂身份不成立 ⇒ 重启 **N2→N4**；
  · 起手闸 fail-closed（窗口不可开）⇒ 重启 **N1**（清场重取 ceiling），不降闸值；
  · 某窗 codex rc≠0 / 真值自败 ⇒ 该窗标 `unreliable` 剔除配对并**单列我方读数**（R4），不重启全轮；
  · 判据器/器具缺陷 ⇒ 只重启 **N6**（后处理幂等重算），**禁重测**。
```
