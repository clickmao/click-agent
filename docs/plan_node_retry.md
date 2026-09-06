# 子模块开发计划: 节点级重试策略 (FailFast → FailRetry)

> **[落地注记]** 本模块已落地 (MaxRetries + 指数退避 + 瞬态/永久分类)。

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **来源**: `TaskPlanExecutor.ExecuteAsync` 失败分支源码注释自认:
> "FailFast: 单节点失败停止计划 (**重试策略后续迭代**)" (registry/NodeExecutionResult.cs 178)。
> 本文档把该欠账落成可执行计划。

---

## B.1 需求 (一句话)
单节点执行失败时不再立即放弃整个计划: 按**可配置重试策略** (次数/退避) 重试,
重试耗尽才按现有 FailFast 语义收敛 (下游 Skipped + 计划 Finished)。

## B.2 现状 (代码事实)
- 失败路径: `result.FinalState == Failed` → `SkipRemaining` → `run.State = Finished` (172-180)
- 节点结果载体: `NodeExecutionResult` (FinalState + Error)
- 重试不能伪造成功: **重试后仍失败必须保持 Failed 终态**, Error 追加重试历史

## B.3 设计
```csharp
// PlanNode 新增 (AOT 纯数据):
public int MaxRetries { get; set; } = 0;            // 默认 0 = 现状 (不重试)
public static int DefaultMaxRetries { get; set; } = 1;   // 计划级默认可覆盖

// TaskPlanRun 新增审计:
public List<NodeRetryRecord> Retries { get; set; } = new();
// NodeRetryRecord { NodeId, Attempt, Error, WaitedMs, At }

// 执行端 (伪代码):
for attempt in 0..=node.MaxRetries:
    result = await _nodeRunner(node, ct)
    if result.FinalState != Failed: break
    if attempt < node.MaxRetries:
        delay = ExponentialBackoff(attempt)   // 500ms * 2^attempt, 上限 4s, ct 可中断
        run.Retries.Add(...);                 // 审计落 TaskPlanRun → /plan 面板可见
```

### 关键约束
1. **只对瞬态失败重试**: `NodeExecutionResult` 增 `FailureKind` (Transient/Permanent)。
   参数校验失败/敏感拒绝 = Permanent 不重试; 网络/超时/LLM 5xx = Transient 重试。
   nodeRunner 实现方负责分类, 默认 Unknown 按 Transient (保守可重试)。
2. **CancellationToken 优先**: 取消 (OperationCanceledException) 永不重试 — 保持现有语义。
3. **重试不重新问询**: 重试沿用已答参数; 期间新 Clarifications 不叠加 (问询协议不重复打扰)。
4. **敏感节点 + 审批暂停点不参与重试** (审批是人工决策, 无瞬态一说)。
5. **重试计数进 TaskPlanRun 落盘**, /plan 面板 JSON 输出 retries 数组 (程序可解析)。

## B.4 验收标准
- [ ] MaxRetries=2 且持续失败: 恰好 3 次调用, 终态 Failed, 下游 Skipped (语义不变)
- [ ] 第 2 次成功: 终态 Completed, Retries 含 1 条记录, 下游正常执行
- [ ] Permanent 失败: 0 重试直接收敛
- [ ] 取消: 重试等待中 ct 触发 → 立即返回 Cancelled
- [ ] 默认 MaxRetries=0: 全部现有测试不变绿→绿 (零行为变化证明)
- [ ] 全量测试绿 + AOT 0 警
