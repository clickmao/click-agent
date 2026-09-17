# DCR 口径对齐 — FAVA 正文取证（2026-09-13，解 dcr-align 阻塞）

> 阻塞项原文：**"dcr-align（pending）: FAVA 的 DCR 公式/分母/弃权处置/aggregate 合并方式不可得 ⇒ 阻塞 ±5pp 成立性；只能双口径并列。"**
> 本轮取到 FAVA **正文**（此前只有新闻稿级摘要），阻塞解除。以下全部为原文取证, 非推断。

## 0. 取证来源（可复算）

| 项 | 值 |
|---|---|
| 论文 | FAVA: Formal Authorization for Verified Agents with Evidence-Backed Permission Graphs |
| arXiv | `2607.27267v1` [cs.CR], 2026-07-29 |
| 抓取 URL | `https://arxiv.org/pdf/2607.27267`（HTML 版 `arxiv.org/html/2607.27267v1` 为动态页, 只回 3.1k 字符, 不可用） |
| 全文缓存 | `/home/agentuser/.hermes/cache/web/arxiv.org-6cb3b928a8.md`（16,134 clean chars） |
| 抓取时间 | 2026-09-13 |

## 1. DCR 的权威定义（原文）

> **Metrics.** Our primary evaluation metric is the Decision Compliance Rate (DCR), which measures the overall accuracy of binary allow/block decisions. … False Negatives (**FN**, unauthorized actions incorrectly allowed, i.e., under-blocking). Based on these components, the DCR is formally defined as:

```
DCR = (TP + TN) / (TP + TN + FP + FN)
```

**四条关键口径（本轮阻塞点的直接答案）**：

| 问题 | 原文口径 |
|---|---|
| **分母是什么** | 全部**二元 allow/block 决策数** = TP+TN+FP+FN。**没有"弃权/不可决断"这一项**。 |
| **弃权怎么处置** | **fail-closed**：*"if the solver finds no explicit forbidden flow but the extracted risk posture remains sensitive, dangerous, or ambiguous, the gateway deliberately fails closed."* ⇒ 不确定 = **拒绝(block)**, 计入分母, 不是排除。 |
| **aggregate 怎么合并** | *"90.5% over the full 801-case binary matrix"* —— **单一二元矩阵**(所有案例混算 TP/TN/FP/FN), **不是**各数据集 DCR 的宏平均。 |
| **trace-conditioned split** | **单独报告**：*"The trace-conditioned split is reported separately because it uses benchmark-provided trace evidence as part of the trace specification"*; 论文自陈这是 *"labeled diagnostic rather than zero-shot discovery"* ⇒ 100.0% 不可与 zero-shot 主表混读。 |

**案例构成**：801 任务 = OpenAgentSafety 359（原 361 去 2 个缺文本目录）+ OctoBench + ActPlane 等；子集读数：OctoBench **90.8%**、OpenAgentSafety **84.4%**、ActPlane Public **100.0%**（0 FP, 0 FN）、trace-conditioned **100.0%**；整体 **90.5%**。论文自陈 *"fully automated setting is intentionally conservative: the benign allow rate is 57.7%"*（宁可拒绝）。

## 2. 与本仓口径的映射（为何此前"合规 100% / 保守 69.66%"两面不矛盾）

本仓现状（R388 真装配 145 题）：**合规 145/145 = 100.00%**、**保守 101/145 = 69.66%**、可决断集覆盖 101/101 = 100.00%、主动误判 unsafe = 0。

| 维度 | FAVA | 本仓 现行"合规" | 本仓 现行"保守" |
|---|---|---|---|
| 弃权/不可决断 (Unknown / Vacuous / Malformed) | **不存在**：一律 fail-closed 记 block | 从分母**排除**（只统计可决断集） | 计入分母, 且按"未阻断即失分"处置 |
| 分母 | TP+TN+FP+FN（全部二元决策） | 101（可决断集） | 145（全部题） |
| 结论 | 单一 DCR 数字 | 100.00% | 69.66% |

⇒ **两个数字的差不是"系统能力差", 而是弃权处置口径不同**。FAVA 的语义 = 把"不确定"并入 **block**；本仓"保守"口径把"不确定"并入 **未阻断**（即失分）。
**对齐动作（下一轮）**：按 FAVA 语义重算本仓单一 DCR = 把 `Vacuous / Unknown / Malformed` 一律记 **block**（fail-closed），`absent` 按 FormAssertionContract 仍放行（"缺失≠错误"），再对 `eval/dcr/{assembly_out,kernel_out}.jsonl` 逐题重算 TP/TN/FP/FN。**在该重算完成前, 不得引用 FAVA 的 90.5% 与本仓数字做直接比较。**

## 3. 对"90.5% ±5pp 可行性"的影响

- 原区间 [85.5%, 95.5%] 来自 90.5% ±5pp。取证后确认：90.5% **是单一二元矩阵的整体准确率**，其成分包含 ActPlane 与 trace-conditioned 两个 **100.0%** 的高分口径（后者论文自陈是 labeled diagnostic）。
- ⇒ 若本仓口径不包含"benchmark 提供的 trace 证据"这一加成，**直接对标 90.5% 会系统性高估难度或低估难度**（取决于题集构成）。因此本仓引用该数字时必须同时声明：**"含 2 个 100% 子口径（其一为 labeled diagnostic）"**。
- ±5pp 的成立性：论文未给置信区间/方差（Table 2 只给点估计与 FP/FN 计数）⇒ **±5pp 仍属本仓自设工程裕度, 不是论文口径** —— 该结论在取证后**更硬**（此前是"不可得故无法判断", 现在是"论文确未提供方差估计"）。

## 4. 诚实边界

1. 本文口径全部转写自 PDF 抽取文本（16,134 字符）；表格数字（如 Table 2 的列含义）在纯文本抽取下有歧义，故本文**只引用论文正文明确陈述的句子**，不从表格数字反推。
2. 论文原文在 FP/FN 表述上有一处术语重叠（把"未授权动作被错误允许"同时写进 FP 与 FN 的括注）—— 本文按标准混淆矩阵语义（FP=误拦, FN=漏拦）与论文 *"0 FP, 0 FN"* 的用法理解, 并在引用处保留原文。
3. 对齐重算（§2 末）**尚未执行**，故本仓仍维持"双口径并列"上报；重算完成前不得把 100.00%/69.66% 与 90.5% 混读。

## 5. 下轮待办

1. 按 FAVA 语义重算本仓 145 题单一 DCR（fail-closed 归并 + `absent` 放行），并与现行双口径并列存档。
2. 若重算值落入 [85.5%, 95.5%]，则 DCR 90.5%±5pp 可行性结论**升级为同为口径可比**；否则必须改写结论为"口径不可比"。
