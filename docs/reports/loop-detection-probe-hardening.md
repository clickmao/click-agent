# 循环入口自检 · 状态探针 v2 硬化 (2026-09-14, 循环第 2 tick)

> 归属: cron `10f9d6454575` 能力自检循环 · **分支 A 前置**（检测机制本身）。不是 R402 步2 的重复工作。
> 证据: `scripts/capability_cycle_status.py`（v2 + `--selftest`/`--legacy`）/ `eval/capability/kpi.jsonl`（本轮读数行）。

## 1. 因果链（为什么要修这一步）

- 循环的**每一步路线都由 `scripts/capability_cycle_status.py` 决定**（`mode=tasks|selfcheck` + `open_items[0]` = 最前未完成项）。
- 本 tick 检测结果与账本自身矛盾: 探针报 **open_count=1（R403「未开始」）**，而 L8 表中 **R401「…对比进行中」** 与 **R402「进行中」** 两行仍在账。
- 根因（读码 + A/B 双跑定位）: v1 先按 `DONE_MARKERS`(已交付/已完成…) **过滤整行**，再看开放标记 ⇒ 状态格写成「接线已交付(R400)；解法级对比**进行中**」的行被判为已完成丢弃。
- **后果量化（真机 A/B, 同一二进制 `--legacy` 开关）**: `legacy open_items=[R403]` vs `v2 open_items=[R401,R402,R403,R371,R370]` ⇒ v1 会把循环指向**最后一行**，与计划文档自身路线（R400→R401→R402→R403）相反——无人值守下这是静默误路由，永远不会报错。

## 2. 修改点（4 处缺陷 + 1 处自捕）

| # | 缺陷 | 修法 | 反证据 |
|---|---|---|---|
| D1 | 完成标记覆盖进行中标记 ⇒ R401/R402 被吞 | 开放标记**优先**（同格并存 ⇒ open） | 负控 N1: v1 逻辑漏 R901 |
| D2 | 状态列硬编码 `cells[2]` ⇒ 「轮次看板」状态列在第 4 格的行永不入账 | 由**表头**定位状态列（`状态|进度`），无表头退回 `cells[2]` 并在 `sources.state_col` 标注 | 负控 N2: v1 逻辑漏 R910；真机 `state_col` R371/R370 由 2→3 |
| D3 | 来源②（主报告 §7 正则）当前版式 **0 命中却静默** ⇒ 读者误读为「主报告无未完成事项」 | 输出 `sources.master.format_matched=false` + note（**缺失≠为空**） | 真机 `master_open=0, format_matched=false` |
| D4 | 判定器无自检 ⇒ 判定力未量化 | `--selftest`: 6 例判定 + 2 例负控（v1 逻辑必须判错，否则用例无判别力） | 8/8 PASS, exit 0 |
| D5 | **自捕**: 自检用例 T1 用**子串包含**判「R900 已关闭」，被另一行状态文本里引用的 `已交付(R900)` 误命中 ⇒ 假 FAIL | 断言改结构化键前缀匹配（`item.startswith`） | 首跑 7/8 → 修后 8/8；词面启发式当判定器 = 已知反模式（kpi skill「行为类 KPI 禁用文本形状启发式」同源） |

## 3. 读数（真机）

| 项 | 读数 |
|---|---|
| 判定器自检 | **8/8 PASS**, exit 0（含 2 例负控证明判别力） |
| 真机 A/B（同码开关） | v1: `open_count=1` `[R403]` ／ v2: `open_count=5` `[R401,R402,R403,R371,R370]` |
| 最前未完成项 | v1 = R403（**错**，最后一行）／ v2 = **R401**（与文档路线一致） |
| 来源②可见性 | `hits=0, format_matched=false`（v1 静默） |
| 状态列定位 | 表头驱动: L8 表 col=2, 轮次看板 col=3（v1 恒 col=2） |
| 契约兼容 | `capability_cycle.py status` 输出字段向后兼容（`mode/open_count/open_items` 原样），新增 `open_items_detail/sources` |
| 代价 | 纯 stdlib，秒级；**零 dotnet build** ⇒ 不与活跃 7B 生成链争二进制（真实缺陷 71/测旧二进制形态） |

## 4. 基线

- 本 tick 之前（生产基线）: `open_count=1`, 最前项 R403, 来源②静默, 判定器 0 自检。
- 本 tick 之后: `open_count=5`, 最前项 **R401**, 来源②显式标注缺失, 自检 8/8。
- 行为变更**有意为之**且经用户路线校验: 下一步循环 tick 将指向 **R401**（而非 R403）。

## 5. 诚实边界

1. **本轮未与活跃会话抢写共享文档**: pid 55444 是**交互 QQ 会话**（`HERMES_SESSION_ID=20260906_070359_b183e6e4`, `HERMES_CRON_SESSION` 空），正在推进 **R402 步2**（compute bench + 批预填），其未提交改动含 `ComputeBenchCli.cs` / `eval/rover/r402/*`。故本轮**不碰** L8 表、主报告 §7、`docs/verification-registry.json`（后者改动强制立刻跑 `VerificationForm|SkillGeneralization|DevPlanDocRef` 形式校验 = 需要 dotnet build，会覆盖活跃运行中的二进制）。登记行挂载与形式校验**顺延到活跃会话结束**。
2. **来源②仍是残的**: 只做了「静默→可见」，正则未适配当前报告版式（「最新状态」块无 `**下轮候选**` 字面形式）。即 `master_open=0` 现在**已知不可作「主报告无未完成事项」的证据**。
3. `open_count` 由 1→5 是**判定修正**，不是计划项变多；历史轮（R371/R370「进行中」）入账属判定口径扩张，未做历史轮归档判断。
4. 本轮未跑 dotnet 测试（非零风险: 与活跃生成链撞车）；Python 侧改动以 `--selftest` + 真机 A/B 为证。

## 6. 下轮候选

1. **R401 口径重锚**（v2 判定的最前项）: R401 剩余「解法级 KPI 对比」在本机物理不可行（R402 步1 实测计算 9.2–17.0 s/pass ⇒ 0.06–0.11 tok/s vs 远端 470.2 ⇒ 单题 31.4h）；按 v0.26.0 §9.4 ③ 改为「离线/验证用引擎的正确性与可对账性」口径 + 写进 backlog/主报告（**须等活跃会话释放共享文档**）。
2. 来源②正则适配（或改为读结构化状态源），把「缺失≠为空」升级为「真能读」。
3. `docs/verification-registry.json` 补探针 v2 登记行（L3: `--selftest` 8/8 + 真机 A/B）+ **当轮立即**跑形式校验。
4. 通用化 skill: 「判定器/测试禁用词面子串断言（结构化键优先）」+「开放标记优先于完成标记」两条已抽象为语言无关判据，待写入 `skills/`（受 `SkillGeneralizationTests` 机检，需 dotnet 构建 ⇒ 顺延）。
