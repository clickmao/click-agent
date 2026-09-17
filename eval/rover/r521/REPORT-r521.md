# REPORT R521 — 游戏类多文件长任务: 三臂同窗对照 + 器具两缺陷自查 (2026-09-17)

**窗口**: `w2` = `run-0917-154115` · 题面 `games-longtask-v1` (pins: taskset sha12 `d9b373d87e7e`, plan `2e498d04…`, scope `43edb66e…`, prereg `8bc0e2dc…`) · 二进制 `/tmp/pub_r520/agenthost` sha256 `a0ac9695b214f0f8…` (本轮**零产品源码改动** ⇒ 未重发布) · 模型双侧 `deepseek-chat`。
**臂**: A = 本侧单轮 (`--max-steps 32`) · C = codex-cli 外部真值 · O = 本侧编排器 5 节点 × 8 步 + `--scope`。

## 1 因果链
R520 修掉影子路径闸后编排臂 9/58 的读数仍不可比 (异窗) ⇒ 本轮把三臂塞进**同一 adapter 窗口**取可比读数, 并先过两道硬前门 (契约机检 `clean=True` rc=0 · 起手闸 ×2 PASS)。

## 2 读数 (全部机检, 判分权威 = 仓内不可变快照)

| 臂 | 用例 | 上游调用 | prompt | cached | completion | total tok | 墙钟 | 工具步 |
|---|---|---|---|---|---|---|---|---|
| **A 单轮** | **58/58** ✅ | 19 | 288,640 | 270,208 | 14,169 | **302,809** | 66.1 s | 17 |
| **C codex** | **58/58** ✅ | 5 | 43,309 | 39,552 | 3,063 | **46,372** | 25.1 s | — |
| O 编排 | 31/58 ❌ | 30 | 410,612 | 375,808 | 19,296 | 429,908 | 117.8 s | — |

- **质量面**: A = C = **58/58 打平** ⇒ 「回复质量不降」成立 (同环境/同输入/同模型/同窗)。
- **效率面 (方向读数, 非同源实现)**: 本侧 A 的 token = codex 的 **6.53×**、调用数 19 vs 5 ⇒ 本侧**不比**外部真值省。
- **R413 判据 (token ↓≥30%)**: 本轮**无「关闸」同窗消融臂** ⇒ **未测、不宣称降幅**。
- **铁律 11 前置器**: `exec_precondition.py --round r521` ⇒ **rc=1** (`ACCEPTABLE_SCOPED=False`, `SELF_REPORT_AGREES=True`) ⇒ 以上读数一律标**「参考 (未可验收)」**。

## 3 器具两缺陷 (本轮自查发现, 均已修 + 机检)

| # | 缺陷 | 后果 | 修复 | 机检 |
|---|---|---|---|---|
| 1 | `run_r521.sh` 臂 A 走 `proj_run_side --side agent` **未传 `--max-steps`** (默认 0) | 工具面关闭 ⇒ CLI 退回纯对话: 1 调用, 代码只进回复文本, `work/` 空 ⇒ 0/58 | 传 `--max-steps 32` + 起臂后**产物非空断言** | w1: 1 调用/5.4 s/0 字节 ⇒ w2: 19 调用/66 s/58-58 |
| 2 | `freeze_r521.py` 对**空产物树静默跳过** | `snapshots/<win>/agentA` 不生成 ⇒ 前置器只遍历已存在目录 ⇒ **rc=0 假绿** | `emit()` 先 `makedirs` ⇒ 空臂也落盘 (`snapshot_empty: true`) | `eval/rover/r521nc` 负控: 空 `agentA` + 自报 `all_pass=true` ⇒ **rc=1** · `BLOCKED w1/agentA/g1 0/58` · `SELF_REPORT_AGREES=False` |

w1 (`run-0917-153525`) 因缺陷 1 **作废为验收窗**, 证据整体归档至 `eval/rover/r521/nc/w1-armA-no-steps/` (含 README 与仍有效读数: C 58/58 · O 9/58)。

## 4 候选② · 编排臂逐用例定因 (`eval/rover/r521/diag-orch-r521.md`)
5 模块**都在盘上** ⇒ 不是缺产物。life **输出字母表错** (`1/0` 而非 `#/.`, 演化逻辑逐位正确) 0/14 · sub **首行未跳过 ⇒ IndexError** 0/14 · nim **取法非规范最小解** 5/15 · wythoff **`WIN` 后丢两整数** 4/15。⇒ 失败面主要是**接口契约**, 非算法。
**摆动**: 同器具同题面 O 在 w1 = 9/58、w2 = 31/58 ⇒ 单次读数不可作能力结论 (承 R489)。

## 5 候选④ · 轮节台账
`eval/capability/r518/scan_round_sections.py` ⇒ `C1 MISSING n=0 · C2 ZONE_ORDER_VIOLATIONS n=0 · SCAN_EXIT=0` (R402–R407 缺口已由 R518 器具闭合并机检) ⇒ 本候选**已闭合**; R517 轮节 = `docs/reports/r517-mainline-contrast-orchestrator-vs-codex.md` 在位。**R521 轮节本轮补入** `docs/improvements.md` + master plan。

## 6 诚实边界
1. 前置器 rc=1: 预注册 `evidence_scope` 用 `w1/*` 窗口名, 该窗被缺陷 1 作废 ⇒ 验收窗 `w2/agentO` **未声明** ⇒ fail-closed。事后重钉件 `scope-posthoc-r521.json` 明标 `SCOPE_POSTHOC=1` ⇒ 前置器仍 **rc=1**、`ACCEPTABLE_SCOPED=True` **不得当验收依据**。⇒ 本轮**未达可验收**。
2. R413 30% 降幅**未测** (无同窗关闸臂); 「本侧 6.53× codex」只是**跨实现方向读数**, 非同源消融。
3. 编排臂 31/58 为**单次读数** (w1 9/58 ⇒ 摆动), 不作能力结论。
4. 未跑单测/未重发布 AOT (本轮零产品源码改动, 只改 eval 器具)。
5. w1 作废是**器具**缺陷, 非产品缺陷; 产品面 (工具面/落盘) 在 w2 按预期工作。

## 7 下轮候选 (R522)
1. **(主线/R413) 同窗关闸消融臂**: 同二进制 + 关闸 (单变量) 与 A 同窗 ⇒ 才可宣称 token 降幅 ≥30%。
2. **编排臂契约面**: 把逐模块 I/O 契约自测写进节点 (承候选②定因), 目标把 31/58 抬到算法面水位。
3. **编排臂摆动量化**: 同窗 n≥3 重复跑, 出区间 (承 R489)。
4. **器具**: 给 `exec_precondition` 的 `evidence_scope` 加**窗口无关**模式 (如 `*/agentO`), 免器具改版后重复踩预注册窗口名错配。
5. **回执回显落点** (承 R520 候选⑤, 待 token 数据裁定)。
