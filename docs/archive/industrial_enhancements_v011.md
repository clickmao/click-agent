# click-agent 能力增强计划 (v0.11.0 口径)

> 本文档为活文档: 记录当前项目总体状态、与 Claude Code / Codex 级核心能力的差距、
> 以及差距的收敛路线。每轮迭代后同步更新 (用户钦定)。

## 一、当前项目总体状态 (2026-09-07, R143b 审查校准)

- **版本口径**: v0.11.0 (千轮迭代 R143)
- **质量基线**: 389/389 测试全绿; NativeAOT publish 0 IL 警; 千轮评测 1034/1056 (97.92%, 215 轮); 55 项真缺陷修复 (打点驱动)
- **架构**: 16 个 csproj — agent 主链 22 子模块 + core / config / contextgradient / modelqueue / skills / rag / vectormemory / workspace / io / logging / output / recovery / codegen / host / tests (planner 已并入 agent/intent)
- **v0.11.0 关键能力**:
  1. 5 KPI 全维度可观测 (K1 被提问/K2 token/K3 语义质量/K4 SKILL/K5 基础) + 15 维度测试总账
  2. PGO 式打点 12+ 点位 (含 compression 防漂移指数/intent 指数入报告)
  3. bge 512 维真向量链 (RAG/ContextGradient/语义漂移/reply_rel 全真链)
  4. 22 模型目录 + 3 端点真机余额链 + 阈值切模
  5. Skill 四级触发 (关键词→正则→领域词→bge 语义 cos≥0.45) + executive 脚本真进程
  6. 评测体系: quick-10 扩容口径 + 19 用例全量 + 负面 21% + 防幻觉 must_not_contain

## 二、Claude Code / Codex 级别的核心能力对照

> 语义: ✅ 已达成 / ⚠️ 部分达成 (有真实实现, 覆盖或深度不足) / 🔌 插件接口预留 (框架只定义契约,
> 内部功能由开发者实现注册 — 同 WebSearch 数据源模式) / ❌ 缺失。

| 能力模块 | 当前状态 | 说明 / 收敛路径 | 优先级 |
|----------|----------|------------------------|--------|
| **任务规划** | ✅ 达成 | TaskPlan 拓扑分层 + 同层并发 + 节点重试(瞬态分类) + 影子演练 + 问询/审批语义 | P0 |
| **记忆系统** | ✅ 达成 | RAG + 向量检索 (bge 512 维真机验证) + 会话滚动摘要 + 跨进程持久化 + UserTendency 画像 (R133 断链修复, snip 可执行化) | P0 |
| **模型调度** | ✅ 达成 | 三通道 (本地/官方/远端) 混合调度 + 并发托管 + 主备切换 + 意图/价格/速度综合选模 + 余额查询 | P0 |
| **上下文工程** | ✅ 达成 | 梯度压缩 L0-L3 + DriftGuard 防漂移 + bge 语义相似度回退 | P0 |
| **错误恢复** | ✅ 达成 | FailRetry + 会话中断检查点复原 + /status recovery 面板 | P1 |
| **可观测** | ✅ 达成 | 日志四通道单路径路由 + thinking 流协议 + /log dump + /status /session 全 JSON | P1 |
| **IO 协议** | ✅ 达成 | agent.io 单行事件 + 流式块双态读写 (netstandard2.1, 前端可嵌) | P1 |
| **配置体系** | ✅ 达成 | 四层 YAML 深合并 + ConfigSnapshot/ConfigWriter 读写分离 + 凭据铁律 | P1 |
| **Skill 调度** | ✅ 达成 | 生命周期状态机+沙箱+熔断 (P2); P3 bge 语义匹配已接 (cos≥0.45) + SKILL.md 开放规范包 (v0.10.0) | — |
| **多Agent协作** | ⚠️ 部分达成 | 隔离子任务 (独立会话/并发上限/相关性判定) 已落地; 通信协议/冲突解决未做 | P1 |
| **工作区管理** | 🔌 插件接口预留 | `ICapabilityPlugin` + `CapabilityPluginRegistry` (agent.registry); 文件系统操作、git 集成由开发者实现 (agent.workspace 骨架已有基础类型) | P0 |
| **测试集成** | 🔌 插件接口预留 | 同上契约; 测试生成、运行、覆盖率分析由开发者实现 (框架自身测试基建即参考实现样本) | P1 |
| **代码审查** | 🔌 插件接口预留 | 同上契约; 静态分析、安全扫描、风格检查由开发者实现 | P2 |
| **代码生成** | ⚠️ 基础占位 | 模板引擎+CodeGenerator 存在; 补全/多文件重构未做 | P0 |
| **用户交互** | ⚠️ 部分达成 | 批量问询+偏好库+证据门槛已落地; 多模态/实时可视化未做 (chatbox 传输通道已定案待实现) | P1 |

## 三、插件接口约定 (需求6 定案)

工作区管理、测试集成、代码审查**不再作为框架内置模块排期**, 统一收敛到插件契约:

```csharp
public interface ICapabilityPlugin
{
    string Name { get; }                                  // 注册表唯一键
    string Description { get; }
    IReadOnlyList<string> ProvidedCapabilities { get; }   // 如 workspace.read_file
    Task InitializeAsync(CancellationToken ct = default);
    Task<PluginExecutionResult> ExecuteAsync(string capabilityId, string args, CancellationToken ct = default);
}
```

- 注册: `CapabilityPluginRegistry.Register(plugin)` (同名拒绝, 不覆盖)
- 分发: `ExecuteAsync("插件名.能力id", args)` — 未注册/未提供/插件内异常一律结构化 Fail, 不打断主链
- 参考实现方向: agent.workspace (Workspace/WorkspaceState 基础类型已有) 可演进为首个 workspace 插件
- 与 WebSearch 同模式: 接口与分发在框架, 能力实现在外部/开发者侧

## 四、v0.9.0 总结与工业 1.0 门槛

> v0.10.0 增补: 上表「未达成」项已全部落地 (语义匹配/Token 统计/统一输出/配置代理), 下一版本计划见 readme v0.11.0 节。

**已达成的工业级特征**: 真实编译/测试/AOT 三重验证纪律; 伪实现零容忍 (能力扫描删反射改 PATH 探嗅);
配置分层契约 + 凭据永不落盘; 会话可恢复; 模型调用可观测可审计; IO 协议前端可编程。

**工业 1.0 前必须收敛 (按序)**:
1. chatbox 推送传输实体化 (websocket/面板 — 传输通道接口 IChatboxSink 已定案)
2. ~~Skill P3 语义匹配接 bge 向量~~ ✅ v0.10.0 已落地 (TriggerMatcher 语义层 + SKILL.md 包格式)
3. 多 Agent 通信协议与冲突解决 (隔离任务已落地)
4. 插件生态首批参考实现 (workspace 插件起步)
5. LLM 全链路真实推理验收 (当前部分链路走失败路径兜底)
