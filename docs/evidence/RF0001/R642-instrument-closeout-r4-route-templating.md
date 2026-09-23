# R642 · 器具面收口轮：R4 活行分支修复 ＋ route 多源择块（轮志小节源）＋ 三件器具模板化与 nim·sub 只读实验

- 轮号/日期：R642 / 2026-09-23 → 2026-09-24 收口
- 性质：**器具面轮**。零产品源码改动（`src/` 净）· 零真机臂 · 零远端 · 零新增夹具语义。
- 判据预注册：`eval/rover/r642/prereg-r642.json`（`declared_before_any_reading=true`）；DAG `eval/rover/r642/dag-r642.md`。
- 放行面说明：用户 2026-09-24 放行产品侧修复（wythoff 5 处行级），本轮按 DAG 先收口器具面（N3–N9），产品侧修复轮（R643）单列。

## §1 判据与读数（全部真实输出）

### D1 · roundcheck R4 活行/None 分支（候选④）

- 缺陷：`str(eg.get("artifact_sha12"))` 把 `None` 变字面量 `"None"` ⇒ 未记 pin 的 live 行恒判红（R639 起实测）。
- 修法：**语义三分** —— `pin_status ∈ {live, worktree-only}` 或 sha 为空 ⇒ 无物可比 ⇒ 进 `R4a_unpinned_or_live_skipped` 可见计数（禁静默跳过，也禁「无声明即绿」）。
- 两侧样例（合成最小仓，`out/n3-samples-r642.json`）：

| 样例 | 期望 | 实测 |
|---|---|---|
| neg_1 冻结行错 pin | R4 红 | **R4_pin_matches FAIL** ✓ |
| neg_2 未声明 pin 行 | 不参与红绿 + R4a 计数可见 | **R4a live=1 单列 + R4 PASS** ✓ |
| pos_1 live+null | 不红 | **R4 PASS** ✓ |
| pos_2 冻结行正确 pin | 绿 | **R4 PASS** ✓ |

- 历史回放（R637–R641 新旧双器具逐条比对，`out/n3-replay-r642.json`）：**五轮 diffs 全空**，rc 全不变 ⇒ 判决中性。器具自检 `--selftest` 23/23 PASS。

### D2 · route 最新块解析（候选⑤）

- 缺陷根因（比预注册更深一层）：旧解析只认 `>` 引用块；主报告 §7 后 6 个 `>` 块**全是注释性引文**（fields=0），轮次状态实际在 `## R6xx` 轮志小节的裸列表字段里 ⇒ v6 的「多源取轮号最大」在真仓空转，route.first 落回旧拼接源（R596 文本）。
- 修法（v6b）：`_iter_status_blocks` 增产**轮志小节源**（`## R6xx` 节内 `- **…**` 字段），与 `>` 块源并列，调用方按轮号最大择源。
- 真仓读数（`out/n4-route-r642.json`）：选块 = **R642 候选块**（源 `round-section`，section_round=R641，字段 12，含「下轮候选 (R642)」），块总数 53。
- 负控：NC1 无块文档不崩、block_found=False ✓；NC2 高轮号节无候选词面 ⇒ `has_next_candidate=False`、first 记缺失不编造 ✓；NC3 两次全量输出逐字节相同 ✓；NC4 空心闸有牙（首块轮号 438 vs 最大 642，旧行为可复现旧读数）✓。

### D3 · 三件器具模板化 + nim/sub 同形态只读实验（候选②③）

- `out/attrib-r642.json`：wythoff 面复算 **12/12 跑次逐值一致**（Z1 零回归，frame_transpose 4=4）；nim 族：单点变异 15→5、联合修复回 15/15、空重写负控逐位相同；sub 族：14→0→9→修复回 14/14、空重写逐位相同 ⇒ 模板在异族成立。
- 分辨率条款（③）：nim 采样面 15 / 规格面 1,939（稀疏比 0.0077）；sub 14/891（0.0157）——**采样面是规格面的稀疏子集 ⇒ 采样通过率不得单独作验收**，已登记。

## §2 工程面

- 形式门禁读数：形式门禁 14/14（`dotnet test` 过滤集 `VerificationForm|SkillGeneralization|DevPlanDocRef`，`Failed: 0, Passed: 14`，本轮实跑）；build 复核（收口前实跑）⇒ **0 Error(s)**（38.1 s；`src/` 零改动 ⇒ 与 HEAD 构建态一致）；器具自检 **23/23**（`SELFTEST PASS`）；`decl_sweep --apply` ⇒ `checked=30 drifted=0`；`status_gen --check` ⇒ **PASS（违规 0 / 基准漂移 0 / 缺源 0）**；`bind_evidence --check` ⇒ `R2E_R2F_EXIT=0`（r582/r587/r616 三行随器具字节变化已批量重审到现盘）。
- 文献小步（N6）：出口探针 200 后 1 式检索，2 件逐条读摘要 ⇒ 台账 §16（采信 1 / 候选 1 / 证伪 0 / 顺延 0）。
- 外部参照面：`docs/external-reference/DEEPSEEK-HARNESS-MECHANISMS.md`（本轮窗口内用户令产出，只读采编，未提交件随本轮入库）。

## §3 诚实边界

1. **预注册与实现的偏差（amendment）**：D2 原判据「真仓 route.source_round=R641」假设了轮志在 `>` 块内；实测根因是**版式形态错配**（轮志在 `## R6xx` 小节）⇒ 修法从「换择块策略」扩为「增补轮志小节源」。判据精神（取最新轮志块）不变，实现面扩了一层；本节即为 amendment 留档（声明后于 N4 首跑、先于收口判决）。
2. NC2 探针的轮志节头未带 `**` 字段时产出 0 块 ⇒ 该形态（无字段节）视为缺失源，不判红；暴露的边界是「节头存在但全节无字段」与「节不存在」不可区分——现口径都记缺失。
3. D3 的 nim/sub 实验为**合成变异**（器具侧造缺陷），非真机产物缺陷 ⇒ 只证模板机械成立，不证族内真缺陷分布。
4. 零真机臂 ⇒ 质量与成本面本轮无读数（不标参考值）。
5. 收口时工作区残留兄弟轮先期件（`scripts/capability_cycle_status.py` / `tools/roundcheck/roundcheck.py` 的未提交改动）经核对**正是本轮 N3/N4 的对象件**，随本轮一并入库；`__pycache__` 不入库。
