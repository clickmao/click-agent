# skill 抽离评估 (R326-f, 版本A 后)

> 用户钦定: 整理当前功能模块哪些可以抽离成 skills (非机器限制隔断) 范畴, 生成 skill 主文档 +
> 可链接详尽附件文档 + config, 放 skills/ 内; 与定版A 方案/KPI 对比迭代。

## 判定原则: "可抽离" = 知识/规则/流程侧可外置, 且外置后 LLM 可消费而不依赖机器内部状态/调用链

| 判定 | 含义 | 归属 |
|---|---|---|
| 可抽离 (知识侧) | 触发词表 / 规则清单 / 反模式知识 / 流程步骤 / 检查项 — 以文档+config 表达, LLM 读入后行为等价 | skill |
| 不可抽离 (机器限制) | 判定器算法 / 执行器 / 存储引擎 / 状态机 / 并发 / 打点 — 依赖代码内部分支与数据, 外置即断 | 留代码 |

## 模块扫描结论

| 模块 | 知识侧 (可抽) | 机器侧 (留) | 判定 |
|---|---|---|---|
| 意图识别 S3 | 连接词/意图词表 (19 连接词)、子任务拆解规则 | IntentDecomposer 分解算法/聚合 | 部分可抽: 词表外置, 算法留 |
| 输出自审 v0.14 | R01-R08 反模式描述/修法知识 (OutputCritic 规则文案) | 静态扫描引擎/CriticPipeline 三级过滤 | **知识侧天然可抽**: 规则清单已 config 化最适合 |
| 修法记忆 FixMemory | 修法条目 (反模式→修法) | 存储/Recall/来源秩 | 数据已外置 (json), 已是 skill 形态 |
| GuardrailMemory | 铁律三元组条目 | 存储/域匹配/注入 | 数据已外置 (json) |
| 压缩防护 | 健康线阈值/audit 清单 | ContextGradientCompressor | 阈值可 config, 机制留 |
| 主题牵引 | L1/L3 提示文案 | drift 判定/状态机 | 文案可抽 (提示话术 skill) |
| 探索链 | 夹具页面/探索策略 | 执行器/预算 | 策略提示可抽 |
| RAG 召回 | 三口径健康线 (0.40/0.65/0.70/0.95) | RAGRecall 算法 | 阈值 config 化 |

## 首批抽离候选 (高价值低风险)

1. **critic-rules** skill: OutputCritic R01-R08 反模式清单 → SKILL.md (每条: 模式/机制/修法/示例), 触发词
   让 LLM 在代码输出前自查。config = rules.yaml。
2. **guardrail 铁律库** skill: 从 guardrails.json 的可移植条目 (域/三元组) → SKILL.md 人类可读版本。
3. **pivot 词表** skill: R-1 收敛后的 PivotMarkers → 文档化 (触发词知识侧)。
4. **压缩审计** skill: audit 流程/健康线 (104 篇/keys≥95%) → SKILL.md。

## 判断铁律
- 抽离 = 增加 LLM 可消费的知识入口, **不删除任何机器代码** (双轨共存: 机器判定保持, skill 供 LLM 预判)。
- 不做"功能搬家"(把代码改文档) — 只做"知识侧镜像"。
- 每抽离一个做 A/B (原机器侧 vs +skill 侧) 对比, 数据说话, 不强推。


---

# skill 版式分类定稿 (R326-g)

| 版式 | 语义 | 命中行为 | 适用 |
|---|---|---|---|
| executive | 脚本执行 | 脚本输出直出 | unit-convert/wordcount |
| normative | 口径/清单交付 | SKILL.md body 直出 | code-review-checklist/git-commit-helper |
| knowledge_hint ★新增 | 知识前置 | body 注入 systemPrompt, 回复走 LLM | critic-rules (R01-R08 生成前自查) |

版本A→skill 版迁移矩阵 (按功能模块):
- ✅ 已迁: 输出自审知识 (critic-rules)
- ➖ 不迁 (机器限制/已有活通道): 判定器/执行器/存储引擎/FixMemory/Guardrail (已有注入链)/主题牵引判定
- ➖ 不迁 (normative 已正确): 清单交付类 (code-review-checklist 等)
- ⏳ 待迁候选: 压缩健康线知识 (audit 流程) / RAG 三口径知识 (召回校准) — 需触发场景评估

KPI 对比结论 (critic-rules 模块):
- 反模式规避: skill 版 (生成前预防, 含例外理解) > 定版A (生成后检测) — C33/C34/C35 三案实证
- token: skill 版 +~2KB/命中 (命中才注入); 定版A 0 增量 (后扫) — 预防价值 vs 成本, 命中率随域收窄
- 用户体验: skill 版无额外提问 (注入无感); force 直出型 (错位形态) 才产生打扰 — 已由 KnowledgeHint 消除
