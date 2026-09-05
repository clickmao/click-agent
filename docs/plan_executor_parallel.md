# 子模块开发计划: 执行器同层并发化 (拓扑图·执行端)

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **修订说明 (v7.14 复核)**: 原计划假设需要"Kahn 分层算法"。复核 `TaskPlanBuilder.ComputeLevelsAndParallelGroups`
> (intent/TaskPlanBuilder.cs 136-165) 确认: **Level 递归计算 + ParallelGroup 赋值已存在且正确**
> (按 DependsOn 递归求 max(上游)+1, 同层节点 ParallelGroup=Level)。
> 真实缺口只在**执行端**: `TaskPlanExecutor.ExecuteAsync` (registry/NodeExecutionResult.cs)
> 按 `OrderBy(Level).ThenBy(indexOf)` 排序后**逐节点串行 await**, 同层并发被放弃
> (源码注释自认: "同层并行留给并发化迭代 (先保正确, 再提速)")。

---

## A.1 需求 (一句话)
`TaskPlanExecutor.ExecuteAsync` 在保持现有依赖正确性的前提下,
把**同 Level 且同 ParallelGroup 的无关节点并发执行**, 跨层仍按 Level 顺序等待上游全部终态。

## A.2 现状 (代码事实)
- `PlanNode.Level` / `ParallelGroup` 字段: **已实现** (TaskPlan.cs 44/57)
- `ComputeLevelsAndParallelGroups`: **已实现** (递归 + 缓存, 拆解链线性无环假设成立)
- `TaskPlanExecutor.ExecuteAsync`: **串行** — foreach (order) 逐节点 `_nodeRunner(node, ct)`
- 现有失败语义 (并发化后必须保留):
  - 依赖失败/跳过 → 连带 Skipped (NodeExecutionResult.cs 121-128)
  - 敏感意图 → 全计划 PausedForApproval (133-144)
  - 问询未答 → AwaitingClarification 不阻断无关节点 (150-163)
  - FailFast: 单节点失败 → SkipRemaining + Finished (172-180)

## A.3 设计
```
foreach (level in plan.Nodes.Select(n=>n.Level).Distinct().OrderBy(l=>l)):
    var batch = 同层节点 (保持 indexOf 序)
    // 层内预检: 依赖全部在前层 (Level 计算保证) → 批内互不依赖, 天然可并发
    if (batch.Count == 1): 走现有串行路径 (零行为变化, 大多数计划命中)
    else:
        var gates = batch.Select(n => RunNodeCoreAsync(n, run, ct));  // 抽方法
        var results = await Task.WhenAll(gates);
        // 失败/取消策略 (保守起步):
        //   任一节点 Failed → 取消同批未完成节点 (CancellationTokenSource 联动),
        //   SkipRemaining 后续层, 语义与 FailFast 一致
        //   敏感节点命中 → 先并发跑完非敏感同批节点, 再暂停等审批 (不丢已完成结果)
```

### 关键约束
1. **_nodeRunner 并发安全是前置验证项**: 检查 V2 注入的 nodeRunner 闭包是否共享可变状态
   (Session 写入/记忆回写)。不安全则并发上限降为 1 并在文档记录 (诚实边界)。
2. **问询节点剔除出并发批**: AwaitingClarification 节点不阻塞同批 (现有 continue 语义),
   并发批构建时先过滤 IsExecutable。
3. **注入指令 (pollInjections) 每层检查一次**, 不在并发内轮询 (保持现有粒度)。
4. **MaxParallelism 上限**: Plan 新增 `MaxParallelism { get; set; } = 4`;
   批内 `Task.WhenAll` 前按上限分片 (防止 LLM 并发配额打爆)。

## A.4 验收标准
- [ ] 同层双节点并发: 执行时间 < 串行和 × 0.8 (时间断言留抖动余量, 参考 SessionPerformanceTests 教训)
- [ ] 依赖正确性回归: 跨层顺序不变, 依赖失败连带 Skipped 语义不变 (现有测试全绿)
- [ ] 敏感暂停: 并发批中敏感节点仍触发 PausedForApproval, 已完成节点结果保留
- [ ] MaxParallelism=1 时行为与当前串行完全一致 (等价性测试)
- [ ] 全量测试绿 + AOT 0 警 (无新反射/动态生成)
