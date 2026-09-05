# 子模块开发计划: Skill 调度模块 (领域技能封装与口径管控)

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **依据**: 《Agent 框架 Skill 模块技术设计文档 v1.0》(用户 2026-09-06 提供, 7723 字符全文已读;
> 本文是其**工程落地计划**, 架构与概念以原文为准, 本文不复制只收敛落点/顺序/验收)。
> **配置依赖**: 本模块全部阈值/开关按《全模块 YAML 配置开发规范》从 `base/skill.yaml` +
> `modules/skill.yaml` 同名覆盖读取 (见 plan_yaml_config.md Y.2.1 契约) — 原设计文档 7.1 的
> Skill 元数据 YAML 示例属**技能定义文件**, 走注册中心加载, 不与框架配置分层混淆。

---

## S.1 现状裁定 (2026-09-06 代码核实)
- **无任何 Skill 现有实现** (无 skills 目录; 仅 CapabilityScanner 的"能力探嗅"在语义上相邻但职责不同:
  它发现的是环境工具 (PATH 可执行文件), Skill 是领域级能力封装 — 不合并, 保持独立)
- 插入点已核实: V2 主链 `IndustrialAgentV2.OnProcessAsync` —
  `IntentDecomposer.Decompose` (151) → `RunEvidenceGateAsync` (162) → `AssembleContextAsync` (170) → LLM。
  **Skill 调度层插在 151 之前** (原文"前置触发原则": 所有激活判定必须在推理生成前完成)
- 与既有件的关系裁定:
  - EvidenceGate/ClarificationBatch (v7.13/7.14): Skill 执行中的参数问询**复用**它, 不另造问询
  - TaskPlan/TaskPlanExecutor: Skill 编排 (原文 8.2 工作流) 映射为 TaskPlan 图 — Skill 多步编排
    = PlanNode 序列, **不新建第二套执行引擎** (v7.15 归拢计划正在消灭双体系, 不许再添)
  - SessionMemory.GoalProfile: Skill 上下文隔离层的"受控共享"白名单与它互补, 不冲突

## S.2 模块落点 (`src/agent.skills/` 新项目, 命名空间 `agent.skills`)
```
SkillDefinition.cs     — Skill 元数据 (skill_id/name/version/domain/type/priority/exclusive/
                         timeout/trigger/permissions/entry/output_constraints) — 对应原文 §3.2/§7.1
SkillRegistry.cs       — 注册中心: 静态扫描 skills/ 目录 yaml 定义 + 动态注册 API; 领域分类索引
TriggerMatcher.cs      — 三级匹配: 预匹配 (关键词前缀树) → 精匹配 (意图/正则/语义阈值) →
                         上下文匹配 (会话历史/激活状态); 匹配裁决 (排他>优先级>上下文度>精确度)
SkillLifecycle.cs      — 状态机: Unloaded→Loaded→Active→Suspended→Unloaded; 会话级缓存;
                         话题切换检测 (连续两轮脱域自动卸载); 挂起/恢复; 闲置超时回收
SkillContextScope.cs   — 上下文隔离沙箱: 白名单读全局字段 / 写回卷校验 / 中间数据不入历史
SkillExecutor.cs       — 执行调度: 同步/异步、超时中断、重试 (幂等才重试)、熔断 (连续失败阈值)
SkillResult.cs         — 标准化输出 (原文 §4.6 结构): skill_id/success/content/constraints
                         (force_use/forbidden_words/template)/context_update; source-gen JSON
SkillDispatcher.cs     — 对外唯一入口: DispatchAsync(input, context) → 命中列表 → 执行 → 合并策略
                         (force_use=true 强制口径 / 补充模式); 异常自动降级普通推理
```
技能定义文件目录: `skills/` (仓库根, 每技能一个 yaml, 格式=原文 §7.1); 口径型 Skill (normative)
只含模板与禁语; 执行型 (executive) entry 指向注册的工具/内部委托。

## S.3 V2 主链接线 (两阶段, 对应原文 §5.1 严格两阶段)
```
阶段一 (主触发, 推理前): OnProcessAsync 最前插
    var skillHit = await _skillDispatcher.MatchAsync(message.Content, sessionCtx, ct);
    if (skillHit.Activated) → 走 Skill 执行流程 (原文 §6.1), force_use 结果直接承载回复口径,
       模型只做合规润色; 执行失败 → 降级继续原链路 (不阻塞主流程)
阶段二 (推理校验, 兜底): LLM 流式输出过程中检测回复是否落入未激活 Skill 领域 →
    中断重走 Skill 流程 — 限制为仅校验不新增激活, 常态不允许触发
```
- 疑似命中原则: 匹配阈值取 `base/skill.yaml` 的 `similarity_threshold` (默认 0.85, @dynamic next-turn),
  宁可误触发不可漏触发
- 全部参数 (三级匹配权重/熔断/缓存上限/超时) 从 plan_yaml_config.md 的分层配置读, **零硬编码** —
  这也是两模块的联动验收点

## S.4 分期 (一次全做风险大, 按原文模块依赖排序)
1. **P1 骨架**: SkillDefinition/Registry(静态加载)/TriggerMatcher(一二级匹配)/SkillResult/
   Dispatcher(单命中+强制口径) — 能跑通一个口径型示例 (原文 §11 身份说明型)
2. **P2 生命周期+执行**: Lifecycle(缓存/挂起/话题切换)/ContextScope(白名单/回卷)/Executor(超时/熔断)
3. **P3 增强**: 语义相似度匹配 (依赖向量服务, bge 已在库)、多 Skill 编排 (映射 TaskPlan)、
   动态注册/灰度/热加载、推理校验兜底 (阶段二)
⚠ 每期完成标准见 S.5; P1 不引语义匹配 (纯规则可测), P3 才接向量

## S.5 验收标准
- [ ] 口径型 Skill 命中: 输入命中关键词 → force_use 模板原样承载, 禁语校验生效 (改模板词 → 校验拦截)
- [ ] 前置性: 激活判定发生在 AssembleContextAsync/LLM 之前 (埋点断言顺序)
- [ ] 疑似命中: 表述模糊但含领域词 → 仍激活 (enable_suspected_trigger)
- [ ] 冲突裁决: 双命中时排他优先/优先级排序, 单测覆盖四种组合
- [ ] 话题切换: 连续两轮脱域 → Skill 自动卸载, 第三轮同域重新加载
- [ ] 隔离: Skill 中间数据不出现在对话历史; 白名单外字段读不到 (越权测试)
- [ ] 熔断: 连续 N 败 (配置) → 临时禁用 + 降级普通推理, 主流程零异常
- [ ] 降级: Skill 入口抛异常 → 自动回普通推理, 用户无感 (错误只进日志)
- [ ] 配置契约: 全部阈值来自 base/skill.yaml + modules 覆盖 (改配置即改行为, 代码零常量)
- [ ] AOT publish 0 警; 全量测试绿; V2 未命中 Skill 时行为与现状逐字节等价 (回归保护)

## S.6 明确排除 (不做)
- 不做 Skill 数据库表 (原文结尾开放问题"数据库表设计" — 当前无持久化多版本需求, yaml 文件即存储; 需要时再立项)
- 不做跨 Skill 直接调用 (原文 §12-4 禁止, 一律经 Dispatcher 编排)
- 不做 Skill 内执行系统命令/本地文件访问 (原文 §9.2 沙箱红线; 最小权限白名单)
- 不做模型修改强制口径 (原文 §12-3, force_use 模板仅合规润色)
