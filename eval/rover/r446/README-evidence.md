# R446 证据 (判官侧: 确定性根因 / 0-token 结算可行性 / 器具面并轨 / prompt 瘦身消融)

轮号 R446 · 计划 `docs/plans/v0.66.0-r446-judge-determinism-and-zero-token-settlement.md`
前置 R445 `4d917b8`（判官侧可分性预检, 零测量轮, 负结论: 消息面不存在廉价必要条件）

## A. 判官路径确定性（真机产品路径探针）

网格 `grid/task-JDET.json`（12 轮**同一消息** `好，按这个来。`）+ `task-JDET24.json`（24 轮）,
臂 = BRJ 同形（relation_judge 开, turn_gate 关）; 偶数轮的 165 字回复是**计划续跑内部回执**,
不触发判官 ⇒ 判官看到的 `上一轮` 恒为桩应答常量。

| 跑次 | local 判官行 | 字母 | `tokens_evaluated/new/gen` | `prompt_len` |
|---|---|---|---|---|
| JDET-s1 | 5 | N N N N N | 215 / 215 / 92 | 284 |
| JDET-s2 | 5 | N N N N N | 215 / 215 / 92 | 284 |
| JDET-s3 | 5 | N N N N N | 215 / 215 / 92 | 284 |
| **聚合** | **15** | **{N}** | **全同** | **全同** |

⇒ **H2（判官路径确定）成立**：同输入 ⇒ 同字母; 归档中「同一消息跨 run 三态并存」由
**`上一轮` 文本差异**（真实回复逐轮不同 ⇒ 160 字截断后不同）解释, **不是**路径非确定性。
形态自证（进程 argv 直取）: `llama-server -m r1-distill... -c 4608 -t 1 -np 1 --cache-type-k f32
--cache-type-v f32 --flash-attn off --jinja`（R430/R407 口径在位）。

### 预注册缺陷（诚实登记）
探针判据 `D2_inputs_identical` 预注册门槛为 `n_local >= 8`, 但 12 轮网格仅产出 5 次判官调用
（其余轮次被 L1 规则层 0-token 结算）⇒ `-s1/-s2/-s3` 判 **INVALID_PREMISE**。
处理：**不事后改阈值**, 改为加长网格（24 轮）重测（`grid/task-JDET24.json`, NS `-s1`）。

## B. 候选②「0-token 结算（判官 L1 扩词）」—— 两版预检 ⇒ 负结论

基线 = R445 归档的 **244 行真机 r1 实答**（`source=local`, 排除 297 行桩回声/兜底）,
其中 **7 条消息跨 run 多态**（占 42% 行）。

| 版本 | 规则 | 结果 | 判定 |
|---|---|---|---|
| v1 | `好，`/`行，`/`可以，` + contains 匹配 | 结算 46/244; 与归档一致仅 14; **误赏 9 行**（Correct→Adopt）、23 行 Neutral→Adopt | **FAIL** |
| v2 | 精确串白名单, 按 **run** 划分拟合/留出 | 留出半: 结算 64 行、误赏 0、精度 0.98 | **方法缺陷 ⇒ 自纠**: 按 run 划分时同消息跨半泄漏（白名单是按消息拟合的）⇒ 该 PASS 不成立 |

**机制**（由 A 节解释）: 判官判决是 `(用户消息, 上一轮回答)` 的函数 —— 归档中 `好，按这个来。`
三态并存来自 **prev 文本差异**; 故「只按消息面结算」在原理上不可能安全。
⇒ 候选② 在**消息面**不可实现（与 R445 负结论同向）; 且预检 v2 的失败给了我一条方法教训:
**按样本划分 ≠ 按拟合单元划分**（拟合单元是消息 ⇒ 必须按消息分组划分）。

附带发现（归档真值本身不可靠）: `换个说法。` 21/21 判 Adopt、`再展开点。` 10/11 判 Adopt
⇒ 1.5B 判官模型对「换说法类」消息存在**系统性误读**; 归档裁决只能作相对判据。

## C. 源码/器具改动 + 回归证据

1. `src/agent.roles/CorrectionDetector.cs`: 判官 prompt 拆为 **单一构造点 + 两形态**
   （`BuildJudgePromptVerbose` 逐字未改 / `BuildJudgePromptCompact` 去 4 行示例）,
   开关 `AGENTFRAMEWORK_JUDGE_PROMPT_COMPACT`（**默认关** ⇒ 生产行为零变化）;
2. `src/agent.tests/RelationJudgeParseTests.cs`: 新增 `K14_紧凑prompt_形状与截断口径一致且更短`
   （断言：截断 120/160 逐字同源 + 尾部两行同源 + 更短）;
3. `eval/rover/r443/channel_marks.py` **与** `eval/rover/r444/channel_marks.py`: 源码结构变动
   导致 `_literals_of("BuildJudgePrompt")` **真红**（`未找到 BuildJudgePrompt 函数体`）⇒
   改为**多形态派生**: 识别标记取各形态首行的**公共前缀**（`判定用户消息相对上一轮回答: `）,
   A2 断言改为**逐形态**校验 C/A/N; 单形态时退化为首行（向后兼容）。

**工具改动零回归证据**（用 R444 归档 calls 复跑 settle, 临时目录已清理）：
`settle BRJ-s4 calls=13(G=13/J=0) tok=32968 acc=1.0` 与 R444 记录**逐位相同**;
`S1 复现档案 ok=True compared=5`（B-p8-b1/BRJ-p8-k1/BP-p8-d1/A-p12-n1/B-p12-o1 全 match）,
rc=0（改动前该脚本在同样输入下因函数体重命名直接抛异常）。

## D. 本轮自伤缺陷登记（全部已修 + 机检）

| # | 缺陷 | 症状 | 修复 | 证据 |
|---|---|---|---|---|
| 1 | 分析器**硬编码**输出名 `verdict-JDET{ns}.json` | JDET24 裁决覆盖了 12 轮 s1 裁决, 本身无独立裁决文件 | 增 `label` 形参（`verdict-{label}{ns}.json`）, 执行器传 `$GRID` | 重生成后 `verdict-JDET24-s1.json` rc=0；`verdict-JDET-s1.json` 如实 INVALID_PREMISE |
| 2 | 臂执行器 settle 路径 `$DIR/settle_r444.py` | A 臂跑完无裁决（`can't open file .../r446/settle_r444.py`） | 改 `$ROOT/eval/rover/r444/settle_r444.py`; A/BRJ 两臂**事后补 settle**（测量数据未受影响） | `[settle ...]` 行 + verdict 文件 |
| 3 | 端口传参 `4831$RANDOM` | >65535 ⇒ 宿主 `frontend-api: 端口非法` | 固定合法端口重跑（执行器 fail-closed 正确拒绝） | 日志 `[致命]`/`端口非法` |
| 4 | 内存起手闸 | dotnet build server 残留 ⇒ MemAvailable 2234MB ⇒ 批次 fail-closed | `dotnet build-server shutdown` + 清 MSBuild 节点 ⇒ 2801MB ⇒ 重跑 | 批次首行 `[致命] 内存起手闸红 (2234MB < 2650MB)` |

**注**: #1/#2 是「**器具自伤**」而非被测对象缺陷 —— 按 R405/R419 纪律全部登记, 不作读数。
探针预注册门槛（`n_local>=8`）的 INVALID_PREMISE 亦按 R判据纪律**不改阈值**, 改加长网格重测。

## E. 候选① 判官 prompt 瘦身消融（同网格 M20 三臂, 预注册判据见计划 §8）

| 臂 | 远端 tok (调用) | 本地真值 tok (门+判官) | 判官行 | 判官 tok (ev+gen) | 成本 | KPI 含本地 |
|---|---|---|---|---|---|---|
| A（分母, 门/J 全关） | 61256 (25) | 0 | 0 | 0 | 61256 | — |
| BRJ（基线） | 32968 (13) | 7841 (3103+4738) | 13 | 4738 (2764+1974) | 40809 | **33.38%** |
| BRJC（紧凑 prompt） | 33231 (16) | 6291 (2957+3334) | 10 | 3334 (1096+2238) | 39522 | **35.48%** |

判据（`analyze_r446.py` 机检, rc=2）：

| 代号 | 判 | 读数 |
|---|---|---|
| D1 字母逐轮一致 | **FAIL** | BRJ `ANCNNANNNNAAN` (13) vs BRJC `NNNCANAAAA` (10) —— 调用次数都不同 |
| D2 判官本地降幅 ≥10% | PASS | 4738 → 3334 = **−29.6%**（`ev` 2764→1096 = **−60%**） |
| D3 生成不升 | **FAIL** | 1974 → 2238 = **+13%** |
| D4 远端零回归 | **FAIL** | 32968 → 33231 = **+263**（BRJC 远端调用 16 vs 13） |
| N1 非空心 | PASS | 13 / 10 条 local 判官行 |

**事后判据（checks_posthoc, 单列）D1b 按 `msg_head` 对齐**：共同 10 条, 一致 **5**（50%）;
差异 = `换个说法。` A→N、`明白，多谢。` A→C、`行，可以，明白。` N→A、`说细一些。` N→A、`重讲一次。` N→A。
（其中 `换个说法。` 的 A→N 方向**修正了 R445 记录的系统性误读**, 但 `明白，多谢。` A→C 与三条 N→A 是反向退化 ⇒ 净效果不可判优。）

### 结论（候选①）
**未通过等价性**: 瘦身让判官 prompt 侧**减半**（−60% ev）却让模型**生成变长**（+13% gen）,
净效应 ≈ −29.6% 本地判官 token（KPI 33.38% → 35.48%）**但判决改变**（D1/D3/D4 FAIL, 事后一致率仅 50%）。
⇒ 开关 `AGENTFRAMEWORK_JUDGE_PROMPT_COMPACT` **保持默认关**（零产品变更）; 该 lever 在取得**判决等价证据**前不可启用。
**机制**（预注册预测被证实）: 判官本地成本由**生成**主导; 砍指令块会诱发更长推理 ⇒ 指令块不是有效杠杆。
