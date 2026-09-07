# 子模块开发计划: 上下文梯度压缩与防漂移子系统

> **[v0.10.0 落地注记]** P1 规则版已落地; P3 向量化仍未接 (计划中, v0.11.0 候选)。BgeEmbedder 已真机可用 (384 维) 并接入 Skill 语义匹配, 压缩模块接入待做。

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **依据**: 《Agent框架 上下文梯度压缩与防漂移子系统 技术设计文档 v1.0》(用户 2026-09-06 提供,
> 21468 字符全文已读, 含 9 个子模块/聚类算法/分级校正/四级降级/性能指标; 本文是工程落地计划,
> 架构与算法以原文为准, 不复制)。
> **配置依赖**: 全部参数走 `base/context_compression.yaml` + `modules/` 同名覆盖
> (plan_yaml_config.md Y.2.1 契约; 规范文档 5.3 节已给出该 yaml 全量参数表)。
> **用户特别点名**: "程序退出时防漂移持久化以便下次程序开启时复用状态" → 见 P.3.4 持久化落盘。

---

## P.1 现状裁定 (2026-09-06 代码核实)
| 现有件 | 位置 | 与本子系统关系 |
|---|---|---|
| SessionMemory 滚动摘要 (≤1000 字符按序裁剪) + GoalProfile (KeyEntities) | src/agent/session/SessionMemory.cs | **雏形**: 只相当于 L1 层的时间裁剪, 无 L0-L3 分级/无锚点/无校验 → 本子系统的被升级对象, 不推倒: SessionMemory 数据结构保留, 压缩引擎旁路接管 |
| pinned 源恒入选 (方向锚不因预算挤掉) | ContextAssembler.cs 749 | 与"P0 锚点永不压缩"同向, 接线时统一到锚点体系 |
| MaxTokenBudget 8000 + 源配额 (Memory 2000/Session 3000/Web 1500) | ContextAssembler 680 | Token 预算的现成入口, 分层管理器以此为约束 |
| **嵌入服务空壳**: EmbeddingConfig 只有配置类, 无真实嵌入调用; bge-small.gguf 在 /home/agentuser/models/ 未接线 | agent.vectormemory/VectorDocument.cs 51 | **关键缺口**: 语义校验/主题聚类的依赖 → P1 先用规则聚类+实体重合度 (算法本就 0.7/0.3 双因子), P3 接 bge 真向量 |
| 意图识别/实体 (规则版) | IntentDecomposer | 锚点提取 P1/P2 级的现成信号源 |

## P.2 模块落点 (`src/agent.context/` 新项目, 命名空间 `agent.context`)
```
ContextFragment.cs   — 信息分片实体 (原文 §8.2, source-gen JSON)
TopicDomain.cs       — 主题域实体 (§8.3): 中心向量/实体集/校正等级/冷却轮次
Anchor.cs            — 分级锚点 (§8.4): P0 强制约束/P1 任务目标/P2 事实实体/P3 逻辑锚
CompressionLevel.cs  — L0 原文/L1 轻摘/L2 结构化索引/L3 归档 枚举 (§8.1)
FragmentStore.cs     — 分片+主题域+锚点索引 内存仓 (lock 保护, 线程安全)
TopicClusterer.cs    — 增量主题聚类: 综合得分=语义相似度×0.7+实体重合率×0.3 (原文 §5.4.2),
                       P1 规则版: 相似度=实体 Jaccard; 每 10 轮巡检合并(≥0.9/实体≥0.7)拆分(<0.7)
AnchorExtractor.cs   — 锚点提取: 规则/关键词→P2/P3, IntentDecomposer→P1, Skill force_use→P0 (§4.2)
LayerManager.cs      — 分层调度: 命中权重分五维加权 (锚点40%/时间20%/引用20%/主题15%/任务5%, §5.3.1)
                       → L0(8轮)/L1(9-20)/L2(20+)/L3(50+无引用) + 预算紧张优先扩 L2/L3
Summarizer.cs        — 梯度摘要: L1 调 LLM 轻摘 (锚点强制注入); L2 结构化索引 [主题|实体|锚级|时间|ID];
                       L3 原文写归档只留 ID; 失败降级实体抽取拼接 (§11.2.2-3)
DriftValidator.cs    — 三重校验: ①P0/P1 锚点召回率必须 100% ②语义余弦≥0.92 (P1 规则版: 实体/数值
                       保持率) ③事实三元组一致性; 不通过→回滚 (§4.5)
RollbackManager.cs   — 版本链 (保留 10 版): 单次失败回退上一版; 连续 2 次降级粒度; 3 次关该层压缩 (§4.8)
ElasticCorrector.cs  — 弹性校正: 四类重复确认信号→定位主题域→轻度(提1级/+0.5权重)/中度(提至L0/
                       锚点升级)/重度(全量解压缩/锚升P0/压缩关5轮) (§5.4.3); 阶梯冷却回落 3/5/8 轮 (§5.4.4)
HitOptimizer.cs      — 预召回 (关联度≥0.8 提层) + 命中埋点 (used/missing) + 权重调优回写 (§4.6)
EssenceStore.cs      — 精要持久化: P0/P1 锚点+核心结论跨会话去重增量写, 新会话加载为初始锚 (§4.9)
CompressionPipeline.cs — 对外门面: CompressAsync/GetCompressedContext/TriggerElasticCorrection/
                       PersistSessionEssence/LoadPersistentEssence (原文 §7.2 五接口) + OnSkillActivated 等回调
```

### P.3.4 跨进程持久化 (用户点名, 退出→重启复用)
原文只写"归档存储", 落地方案定死:
- **落盘物** (`data/context/<sessionId>/`): `fragments.jsonl` (分片: 原文+摘要+锚+层级+权重, source-gen,
  MemorySanitizer 洗敏感串后落盘 — 沿 v7.14 铁律), `topics.json` (主题域), `versions.jsonl` (版本链),
  `essence.json` (永久事实层, 按 userId)
- **触发时机**: 每轮压缩管线完成后异步追加写 (append-only jsonl + 版本链尾部覆写); 进程退出钩子
  (Program.cs 生命周期 / SIGTERM handler) flush 收尾
- **重启复用**: 新会话/进程启动 → 按 sessionId 加载 fragments+topics 重建内存索引 → L0/L1 直接进上下文,
  L2/L3 只载索引 → 加载 essence.json 的 P0/P1 作初始锚 (原文 §6.3 新会话初始化流程)
- **校验**: fragments.jsonl 每行带 checksum (CompressVersion.Checksum, §8.5), 损坏行跳过不中断 (沿
  SessionMemoryStore 容错模式)

### P.3.5 V2 主链接线 (异步非阻塞, 原文 §10.1-5)
```
OnProcessAsync: 每轮回复生成完成 → _ = Task.Run(CompressionPipeline.CompressAsync(...)) 异步执行
AssembleContext 前: GetCompressedContext(sessionId, MaxTokenBudget) 替代现有裸 SessionMemory 拼装
证据门/EvidenceGate 的锚 (GoalProfile.KeyEntities) → 映射为 P1/P2 锚点入库
Skill 联动 (§9): OnSkillActivated → 独立主题域+L0; force_use 口径 → P0 锚 (P3 接 plan_skill_dispatch)
```

## P.4 分期 (风险递进, 每期独立可验)
1. **P1 规则版骨架** (无 LLM/无向量): Fragment/Topic/Anchor 实体 + TopicClusterer(实体 Jaccard 版) +
   AnchorExtractor(规则) + LayerManager(五维权重) + Summarizer(L2 索引/L3 归档, L1 暂实体拼接) +
   DriftValidator(锚点召回+实体保持率) + Rollback + **P.3.4 全量持久化/重启复用** + V2 异步接线
   — 这期做完用户点名的"退出持久化复用"就已可用
2. **P2 弹性校正**: 四类信号检测 + 分级定向校正 + 阶梯冷却回落 + HitOptimizer 埋点回写
3. **P3 语义版**: bge.gguf 嵌入接线 (LLamaSharp Embedder, /home/agentuser/models/ 已有模型) →
   真余弦相似度校验/聚类/预召回; L1 真 LLM 摘要; Skill force_use→P0 联动
⚠ 排除项: 不做全局关闭压缩的触发路径 (§10.1-3 定向原则); 不做永久层级提升 (冷却回落强制);
P1 阶段不引入 LLM 摘要 (可测性优先, L2 索引已能压到 1/5 Token)

## P.5 验收标准
- [ ] 梯度分层: 20 轮对话后 L0=最近 8 轮原文, L1/L2 索引/摘要按权重分层, 全程 P0 锚原样保留
- [ ] 锚点零丢失: 任何压缩路径后 P0/P1 锚点字符串级完整 (召回率校验 100% 强制)
- [ ] 弹性校正定向性: 重复确认仅提升目标主题域, 其他主题层级不变 (§5.4.2 示例场景单测)
- [ ] 冷却回落: 校正后连续 3/5/8 轮无确认 → 逐级回落基线 (单测)
- [ ] **跨进程复用 (用户点名)**: 写入 → 重建 Agent → 加载后 L0/L1 内容与退出前一致, essence 初始锚注入新会话
- [ ] 损坏容错: fragments.jsonl 中间行损坏 → 跳过该行继续, 不崩溃
- [ ] 异步非阻塞: 压缩在回复完成后执行, 主链路耗时无增量 (埋点对比)
- [ ] 四级降级: 嵌入失败→规则聚类; 摘要失败→实体拼接; 连续校验失败→降级→关闭该层 (单测覆盖)
- [ ] 配置契约: 全部阈值从 base/context_compression.yaml 读 (改 yaml 即改行为, 代码零常量)
- [ ] AOT publish 0 警; 全量测试绿; 未开压缩 (enable=false) 时 V2 行为与现状等价
