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

## 7. v3 硬化 (R428-hold · 2026-09-14 18:19 · 活跃窗口内零冲突推进)

窗口: 30 分钟节拍作业 (9a97763d5fcd) 正在同一工作树内实现 **R428**（未提交 `src/agent/session/SessionHistorySearch.cs` +
`src/agent.tests/SessionHistorySearchTests.cs`，mtime 18:14:17/18:14:30；18:15:06 时其 `dotnet test --filter SessionHistorySearchTests` 在跑）
⇒ 本 tick **不碰产品源码 / 不跑 dotnet / 不占轮号**，只硬化循环自身的检测机制。

### 7.1 因果链

`capability_cycle.py status` 是每 tick 的分支开关（tasks vs selfcheck）。v2 实测输出 `open_items=[R371, R370]` ——
两条都是**轮历史沉积行**（R371 各断链点已在 R374/R414/R416 修复并留证；R370 的 L1/L2/L3e/L5 全 ✅、L4 转持续线），
而用户钦定「之前的 5 个开发计划的实施」所在 L3 表的 6 行（exp1/exp2/exp3/exp4/exp8/exp5）**0 行入账**。
根因是行键硬编码 `^R\d+`：轮次看板行是「轮历史」，不是「计划项」⇒ **「最前的未完成计划项」在该机制下不可能被列出**
（每 tick 只能看到沉积行，或据此误判 mode）。

### 7.2 修改点

| # | 缺陷 | 修法 |
|---|---|---|
| D5 | 计划项行 (expN) 结构性漏读 | 行键 `^(?:R\d+|exp\d+)`；旧键保留 `ROW_KEY_LEGACY`（负控 A/B 必须跑旧键，否则负控失去判别力） |
| D6 | 「核心已交付 + 自陈欠项」判 closed（exp5 行） | `欠` 入 `OPEN_MARKERS`，并配**反面对照**用例（已交付且无欠项 ⇒ 必须仍 closed） |
| D7 | 沉积行无法识别 | 每条 open 项随附 `kind`(round/plan-item) + **其余格原文** `other_cells`；**不做机械裁定**（反例：R370 行产出格全 ✅ 但其 L4 是真实持续线，机械判沉积会误杀） |
| D8 | 自检未覆盖新判据 | `--selftest` 7 判定 + 2 负控 → **11 判定 + 4 负控**（新增 T7 exp 行入账 / T8 kind 判别 / T9 欠项判 open / T10 反面对照 / T11 沉积透明；负控 N3 旧行键必漏 exp1、N4 旧分类必把 exp3 判 closed） |

### 7.3 读数（真机）

- 探针 sha256: pre `d7428582ebc8022f…`（git HEAD 版本，从 `git show` 取回重跑）→ post `e52ebb61ee472da4…`。
- `open_count` **2 → 8**（新增 6 条计划项），`mode` 恒为 `tasks`，open 集合 pre ⊂ post（只增不漏）。
- `--selftest` **15/15 passed, rc=0**；负控臂 legacy_open 仅 `[R902]`（旧逻辑在夹具上漏 R901/R910/exp1/exp3）。
- legacy（v1 逻辑）跑真机看板: `mode=selfcheck, open_count=0` —— v1 连 R371/R370 都读不到（读错列 + 完成标记先过滤），
  说明「mode 判定」在 v1 下会直接翻转为「无任务」。
- 证据: `eval/capability/r428-hold/README-evidence.md`（由 `hold-r428.json` 机检渲染）+ `hold-r428.json`（判据 H1–H5 全 PASS）。

### 7.4 基线 / 判据

- 判据 H1–H5 预注册于 `run_hold.py` 头部与本节; 结果 **PASS**（H1 计划项入账 ∧ H2 不回退 ∧ H3 自检全绿 ∧ H4 前态可由
  git HEAD 复现 ∧ H5 沉积透明）。
- 台账: `eval/capability/kpi.jsonl` 追加 1 行（tag `R428-hold:loop-detection-probe-v3`，幂等，回读 22 行 1 命中）。

### 7.5 诚实边界

1. `open_count=8` 是**判定口径扩张**（计划项行首次入账），不是待办变多；沉积行 R371/R370 未做归档判断。
2. 探针不判「沉积」——`other_cells` 只提供原文，最终定性由读者按对应计划文档做（防机械裁定误杀持续线）。
3. 未登记 `docs/verification-registry.json`（需当轮 dotnet 形式校验，与活跃构建窗口冲突）⇒ 顺延。
4. 首次跑出现假 FAIL（H2/H4 红）：pre 副本落在 `/tmp` 致其自算 ROOT 退化为 `/` 读不到文档 —— 属**采集侧假失败**，
   显式传 `--backlog/--master` 后复跑 PASS；已在 `run_hold.py` 注释与本节留档，避免被误读为被测缺陷。

### 7.6 下轮候选（等活跃体释放后）

1. 复用本 tick 的 `kind`/`other_cells`: 把 L7 缺口清单（G1–G9，无「状态」列、判据词在「判定」列）接入探针 —— 需按表适配
   + 正反对照（G8「不修」⇒ closed、G2「宣称≠实现」⇒ open）。
2. `exp1` 是否仍受阻于用户裁决（其计划文档 §8 Q1–Q5）——若受阻，循环应把它标为 `blocked-on-user` 而非普通未开始。
3. 活跃体释放后补 `docs/verification-registry.json` 探针 v3 登记行 + 当轮跑形式校验（`VerificationForm|SkillGeneralization|DevPlanDocRef`）。
4. 来源②（主报告 §7 正则）仍是残的：`master_open=0` 已知不可作「主报告无未完成事项」的证据。
