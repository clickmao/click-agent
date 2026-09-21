# R611 · 铁律 14「任务类型-器件选型」落库证据

轮次：R611（文档落库轮；`src/` 改动 = **0**，产品分支不动）
用户令时间：2026-09-21（CST）
文件性质：把用户钦定的三档器件分工准则写入**主线**与**开发文档铁律**，并标注外部出处与本仓落点。**本文件不宣称任何能力达标。**

## 1 用户令（逐字，不改写）

> 得做到这种程度，请记录在主线和开发文档铁律里：如果你的任务是分类/路由/评分/意图识别 → 直接用Laya或XGBoost，32ms搞定，零API成本
>
> 如果需要文本理解但输出空间有限 → 微调BERT/RoBERTa，精度持平LLM但快50倍
>
> 如果需要生成开放文本 → 传统NLP做不到，必须用LLM或扩散模型 实测效果：延迟降低95%，成本降低85-91%，任务成功率不变。

## 2 落点（四处 + 一处作业面）

| # | 文件 | 位置 | 形态 |
|---|---|---|---|
| 1 | `docs/reports/iteration-master-plan.md` | §0-0 **铁律 14**（宪法条款，与铁律 10–13 并列） | 编号铁律：三档 + 四条选型前提 + 口径出处 + 落地载体指针 |
| 2 | `docs/plans/RF0001-fable-aligned-development-plan.md` | §2.1「器件选型（主线铁律 14）」 | 主线补充：主线不止「怎么对」，还有「用什么器件对」+ 本仓档位现状 |
| 3 | `docs/plans/RF0004-three-capability-development-plan.md` | §0.4「三档任务分工准则」（**唯一权威定义面**） | 三档 × 器件 × 本仓落点 × 现状 的表；口径纪律三条 |
| 4 | `docs/plans/RF0002-nlp-self-improvement.md` | §3 约束条 | 判别器形态约束：按铁律 14 第①/②档选器件，**禁以本地 LLM 当判别位** |
| 5 | cron `b15eb2f40a69` 作业 prompt | 追加「铁律 14」段 | 口径令须改作业 prompt（否则常驻循环不执行该条） |

## 3 三档 × 本仓落点（代码事实）

| 档 | 任务特征 | 器件（用户钦定） | 本仓落点 | 现状 |
|---|---|---|---|---|
| ① 判别/路由 | 分类 · 路由 · 评分 · 意图识别 | Laya / XGBoost（32 ms 级、零 API 成本） | `src/agent.nlp/` 形态/账本规则（10 文件/881 行）+ `TaskRelevanceChecker` + `LocalChannelPolicy` 前置门 | ◐ 规则版在场，**无树模型/编码器判别器** ⇒ RF0002 |
| ② 受限输出理解 | 需文本理解但输出空间有限 | 微调 BERT/RoBERTa（精度持平 LLM、快 50×） | 现由**本地 3B LLM** 承担（`ModelQueueRouter.LocalChannel` → `JudgeTurnAsync`），R609-AB 真机 **17.2 s/例**（2 vCPU / 无 GPU） | ❌ **档位错**（应按本条换器件） |
| ③ 开放生成 | 生成新文本/代码/文件 | LLM 或扩散模型（传统 NLP 做不到） | 远端 LLM = **skill 插件服务**（`ModelQueueRouter` / `agent.skill`）；本地生成端口 `ILocalGenerationPort`；`allow_general: false` ⇒ 主回答永不本地化 | ✅ 形态正确 |

## 4 器件查证（本仓本轮查证结果，供选型时引用）

**Laya**（`github.com/NandhaKishorM/laya`，Apache-2.0，`pip install laya`；发行方 convaiinnovations）
- 形态 = 开源 System1 决策器；原语 `choice` / `score` / `noul`；**单次前向出校准概率**。
- 官方口径 32.8 ms（单 GPU 中位），与用户「32ms」吻合；对照 Jev 官方 236–276 ms。
- 官方自陈四条坑（**必须随条文记录**）：① 开箱 ≈0.35（近随机）⇒ **须域内微调**（微调后 0.995）；② 选项 >20 显著退化（Banking77 0.425 vs Jev 0.870）；③ **非拉丁脚本高置信错判**（Khmer 0% 准确率却报 95.2% 置信度）；④ 仅 Python ⇒ **入 NativeAOT 栈必须先 ONNX 化**（PyPI 件不可直接引用）。

**实测口径出处**：「延迟降低 95%，成本降低 85-91%，任务成功率不变」= **外部出处**（TabAgent，arXiv **2602.16429**，AppWorld / CUGA 设定；摘要逐字 `reducing latency (by ~95%) and inference cost (by 85–91%)`）。TabAgent 把 GPT-4.1 生成式决策头换成 ~50M 分类器（2.682 ms / $2.0e-7 per read vs GPT-4.1 的 7.50 s / $0.052）；同篇把 LLM 当决策头 1B/3B/8B = 100.48/198.12/378.42 s per read ⇒ 方向支持「NLP 当决策主体」，反对「本地 LLM 当决策头」。
**本仓未复现该量级**（本机 3B 判别位 17.2 s/例，差四个数量级）⇒ **方向可搬、量级不可搬**，禁直引为本仓结论。本仓可对照口径：prompt 9,576 vs 12,925（省 26%）· 缓存命中 0.9477 vs 0.9315 · 质量轴 R602–R606 多为未达标。

## 5 四条选型前提（缺一不得宣称达标）

1. **标签可分**：R444 真值 —— 99 次问本地模型里 **71 次（71.7%）本可规则化**，却判 `NOT_SEPARABLE`（4 反例 + 双通道不一致）⇒ 属**前提/数据**问题，**换模型不解决**。
2. **AOT 可用**（铁律 3 优先）：树模型须能导成**纯 C# 打分器**；`pip` 件须先 ONNX 化，否则一票否决。
3. **本机可跑**：3.6 GiB / 2 vCPU / **无 GPU** ⇒ 「32 ms」是单 GPU 读数，**不可直接搬**。
4. **跨语言**：中英混流必须走 multilingual 档；**模型置信度不得单独作自动放行依据**（Khmer 0% 准确率报 95.2% 置信度即反例）。

## 6 机检（本行的 evidence_cmd）

```
python3 -c "import pathlib;p=['docs/reports/iteration-master-plan.md','docs/plans/RF0001-fable-aligned-development-plan.md','docs/plans/RF0004-three-capability-development-plan.md','docs/plans/RF0002-nlp-self-improvement.md'];n=[f for f in p if '铁律 14' in pathlib.Path(f).read_text(encoding='utf-8')];print(len(n),n);assert len(n)==4"
```

**负控（有牙证明）**：把任一文件中的「铁律 14」改一个字 ⇒ 命中数 4→3 ⇒ assert 失败、rc≠0 ⇒ 该行读数由文件内容派生、非恒真。
**诚实的边界**：本行为 **L1 静态检查**（只证「条文已写进指定文件」），**不证任何器件已接入、更不证任何性能/成本达标**；② 档换器件仍是未完成工作（落点 RF0002 / RF0004.1）。

## 7 跳步（各一行原因）

- **AOT / 全量真机跑**：本轮零 `src/` 改动 + 同窗有在飞写者 ⇒ 跑构建会抬高下一主线轮的 `PREV_SWING`。
- **质量对照臂（codex）**：文档落库轮无质量对照项，禁作能力宣称。
- **性能/成本实测**：本机无 GPU，且外部口径不得直引 ⇒ 本文件只登记**待达成的程度**，不登记读数。
