using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;

public partial class IndustrialAgentV2 : AgentBase
{

    private AgentResponse? HandleModelCommand(string input, long elapsedMs)
    {
        var parts = input.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var head = parts[0].ToLowerInvariant();

        // R351: /official-key 指令移除 (官方通道已废弃 — 用户钦定全 API 化)

        if (head == "/model")
        {
            if (_modelRouter is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model", Ok = false, Error = "model_queue_not_configured",
                }, elapsedMs);
            }
            if (parts.Length == 1)
            {
                var active = _modelRouter.ActiveModel;
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model",
                    Ok = true,
                    Active = active?.Id ?? "(empty)",
                    Provider = active?.Provider,
                    ReasoningScore = active?.ReasoningScore ?? 0,
                    CodingScore = active?.CodingScore ?? 0,
                    LastSelection = _modelRouter.LastSelectionBasis,
                    Switches = _modelRouter.Switches.Count,
                    Mode = _modelRouter.ManualOverride is null ? "auto" : "manual",
                }, elapsedMs);
            }

            // /model list: 可用模型列表 (序号 1-N — 序号可直接用于 /model <序号>)
            if (parts[1].Equals("list", StringComparison.OrdinalIgnoreCase))
            {
                var activeNow = _modelRouter.ActiveModel;
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model_list",
                    Ok = true,
                    Active = activeNow?.Id ?? "(empty)",
                    Mode = _modelRouter.ManualOverride is null ? "auto" : "manual",
                    Models = _modelRouter.Catalog.Models.Select((m, i) => new ModelListItem
                    {
                        Index = i + 1,
                        Id = m.Id,
                        Description = m.Description,
                        Provider = m.Provider,
                        PriceInPerM = m.PriceInPerM,
                        PriceOutPerM = m.PriceOutPerM,
                        ReasoningScore = m.ReasoningScore,
                        CodingScore = m.CodingScore,
                        ContextWindow = m.ContextWindow,
                        IsActive = m.Id == activeNow?.Id,
                    }).ToList(),
                }, elapsedMs);
            }

            // /model <序号>: 按列表序号指定模型 (1-N; 序号即 /model list 的 Index)
            if (int.TryParse(parts[1], System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture, out var idx) && idx >= 1)
            {
                var list = _modelRouter.Catalog.Models;
                if (idx <= list.Count)
                {
                    var chosen = list[idx - 1];
                    var okIdx = _modelRouter.SetManualOverride(chosen.Id);
                    if (okIdx)
                    {
                        return MakeJsonResponse(new ModelCommandPayload
                        {
                            Command = "model",
                            Ok = true,
                            Target = chosen.Id,
                            Active = chosen.Id,
                            Provider = chosen.Provider,
                            Mode = "manual",
                            Note = $"selected_by_index:{idx}",
                        }, elapsedMs);
                    }
                }
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model",
                    Ok = false,
                    Target = parts[1],
                    Error = $"index_out_of_range (1-{list.Count}, 见 /model list)",
                }, elapsedMs);
            }
            if (parts[1].Equals("verify", StringComparison.OrdinalIgnoreCase) && parts.Length >= 3)
            {
                var v = _verifyService?.VerifyAsync(parts[2]).GetAwaiter().GetResult();
                // v0.11.0: 命令执行恒成功 (Success=true) — 校验结论在 Ok/Verdict 字段,
                // 不可达端点也如实输出 JSON (Ok:false + UNREACHABLE) 而非吞进失败渲染
                var payload = new ModelCommandPayload
                {
                    Command = "model_verify",
                    Ok = v?.Ok ?? false,
                    Active = v?.Model ?? parts[2],
                    HttpStatusCode = v?.HttpStatusCode ?? 0,
                    Verdict = NonEmpty(v?.Verdict, v?.Error, "verify_service_unavailable"),
                };
                var json = System.Text.Json.JsonSerializer.Serialize(
                    payload, ModelCommandJsonContext.Default.ModelCommandPayload);
                return new AgentResponse
                {
                    Success = true,
                    Content = json,
                    ExecutionTimeMs = elapsedMs,
                };
            }
            // R349: /model verify-all — 全目录并发校验 (免费池 52 条目真机探针; 汇总渲染)
            if (parts[1].Equals("verify-all", StringComparison.OrdinalIgnoreCase))
            {
                if (_verifyService is null)
                {
                    return MakeJsonResponse(new ModelCommandPayload
                    {
                        Command = "model_verify_all", Ok = false, Error = "verify_service_unavailable",
                    }, elapsedMs);
                }
                var all = _verifyService.VerifyAllAsync().GetAwaiter().GetResult();
                var okCount = all.Count(v => v.Ok);
                var sb = new System.Text.StringBuilder();
                sb.Append($"模型目录全量校验: {okCount}/{all.Count} 合法 (假 key 探针, HTTP 401/403/429=地址真实)\n");
                foreach (var g in all.GroupBy(v => v.Ok ? "ok" : "bad"))
                {
                    if (g.Key == "ok")
                    {
                        sb.Append($"  ✓ 合法 {okCount}: ");
                        sb.Append(string.Join(", ", g.Select(v => v.Model)));
                        sb.Append('\n');
                    }
                }
                var bad = all.Where(v => !v.Ok).ToList();
                if (bad.Count > 0)
                {
                    sb.Append("  ✗ 异常 (人工复核):\n");
                    foreach (var v in bad)
                        sb.Append($"    {v.Model}: {NonEmpty(v.Verdict, v.Error, "unknown")}\n");
                }
                return new AgentResponse
                {
                    Success = true,
                    Content = sb.ToString(),
                    ExecutionTimeMs = elapsedMs + (long)(DateTime.UtcNow - DateTime.UtcNow).TotalMilliseconds,
                };
            }
            var target = parts[1];
            var okSet = _modelRouter.SetManualOverride(target);
            if (okSet)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model", Ok = true, Target = target, Active = target,
                }, elapsedMs);
            }
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "model",
                Ok = false,
                Target = target,
                Active = _modelRouter.ActiveModel?.Id ?? "(empty)",
                Error = "unknown_model_id (见 config/base/models.yaml)",
            }, elapsedMs);
        }

        // v0.10.0: /token stats — 用量统计 (总 token/按模型/按 provider/预估成本/余额快照)
        if (head == "/token" && parts.Length >= 2 && parts[1].Equals("stats", StringComparison.OrdinalIgnoreCase))
        {
            if (_tokenUsageService is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "token_stats", Ok = false, Error = "token_usage_not_configured",
                }, elapsedMs);
            }
            var st = _tokenUsageService.GetStats();
            return MakeJsonResponse(new TokenStatsPayload
            {
                Command = "token_stats",
                Ok = true,
                TotalTokens = st.TotalTokens,
                TokensByModel = st.TokensByModel,
                TokensByProvider = st.TokensByProvider,
                EstimatedCostUsd = Math.Round(st.EstimatedCostUsd, 4),
                Balances = st.Balances.ToDictionary(
                    kv => kv.Key,
                    kv => new BalanceEntryPayload
                    {
                        Provider = kv.Value.Provider,
                        Remaining = kv.Value.TotalRemaining,
                        At = kv.Value.At,
                        FromApi = kv.Value.FromApi,
                    }),
                BalanceFlag = _modelRouter?.LastBalanceFlag,
            }, elapsedMs);
        }

        if (head == "/balance")
        {
            if (_balanceService is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "balance", Ok = false, Error = "model_queue_not_configured",
                }, elapsedMs);
            }
            // v0.11.0 R89b (真缺陷 36 关联): /balance 无参应查当前实际活跃模型 —
            // 原传 null 落目录首项 (gpt-4o, 无 key), 与 auto 实际调用模型脱节。
            var balTarget = parts.Length >= 2 ? parts[1] : _modelRouter?.ActiveModel?.Id;
            var b = _balanceService.QueryAsync(balTarget)
                .GetAwaiter().GetResult();
            // v0.11.0: 命令执行恒 Success=true — 余额结论在 Ok/TotalRemaining/Error 字段,
            // 查询失败 (无 scheme/无 key/网络) 也如实 JSON 输出而非吞进失败渲染
            var json = System.Text.Json.JsonSerializer.Serialize(new ModelCommandPayload
            {
                Command = "balance",
                Ok = b.Ok,
                Active = b.Model,
                Provider = b.Provider,
                TotalGranted = b.TotalGranted,
                TotalUsed = b.TotalUsed,
                TotalRemaining = b.TotalRemaining,
                Error = b.Error,
                Note = b.Note,
            }, ModelCommandJsonContext.Default.ModelCommandPayload);
            return new AgentResponse
            {
                Success = true,
                Content = json,
                ExecutionTimeMs = elapsedMs,
            };
        }

        return null;
    }

    /// <summary>
    /// /log 指令 (v7.15 L.2.1): /log dump → MemoryLogBuffer 快照存档 JSON 行文件 (data/logs/log-{ts}.jsonl)。
    /// </summary>
    private AgentResponse? HandleLogCommand(string input, string sessionId, long elapsedMs)
    {
        var parts = input.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 2 || !parts[1].Equals("dump", StringComparison.OrdinalIgnoreCase))
        {
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "log", Ok = false,
                Error = "用法: /log dump (子命令: dump)",
            }, elapsedMs);
        }
        if (_logRouter is null)
        {
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "log", Ok = false, Error = "log_router_not_configured",
            }, elapsedMs);
        }
        var entries = _logRouter.SnapshotEntries();
        var dir = System.IO.Path.Combine(_dataStoragePath, "logs");
        System.IO.Directory.CreateDirectory(dir);
        var file = System.IO.Path.Combine(dir,
            $"log-{DateTime.UtcNow:yyyyMMdd-HHmmss}.jsonl");
        using (var writer = new System.IO.StreamWriter(file, append: false))
        {
            foreach (var e in entries)
            {
                writer.WriteLine(System.Text.Json.JsonSerializer.Serialize(
                    e, agent.logging.LogJsonContext.Default.LogEntry));
            }
        }
        return MakeJsonResponse(new ModelCommandPayload
        {
            Command = "log", Ok = true, Active = file,
            Switches = entries.Count,
        }, elapsedMs);
    }

    /// <summary>模型队列指令统一响应 (强类型 payload — source-gen 序列化, AOT 铁律)</summary>
    /// <summary>首个非空字符串 (verify 判定展示: Verdict 优先, Error 兜底)</summary>
    private static string NonEmpty(params string?[] values)
    {
        foreach (var v in values)
        {
            if (!string.IsNullOrWhiteSpace(v))
                return v;
        }
        return string.Empty;
    }

    private AgentResponse MakeJsonResponse(ModelCommandPayload payload, long elapsedMs)
    {
        var json = System.Text.Json.JsonSerializer.Serialize(
            payload, ModelCommandJsonContext.Default.ModelCommandPayload);
        return new AgentResponse
        {
            Success = payload.Ok,
            Content = json,
            ExecutionTimeMs = elapsedMs,
        };
    }

    /// <summary>v0.10.0: /token stats 专用 JSON 出口 (TokenStatsPayload 上下文)</summary>
    private AgentResponse MakeJsonResponse(TokenStatsPayload payload, long elapsedMs)
    {
        var json = System.Text.Json.JsonSerializer.Serialize(
            payload, ModelCommandJsonContext.Default.TokenStatsPayload);
        return new AgentResponse
        {
            Success = payload.Ok,
            Content = json,
            ExecutionTimeMs = elapsedMs,
        };
    }

    /// <summary>
    /// 计划构建 + 确定性路由 (v0.22.0 exp9 D1+D2): 拆解 → TaskPlan → 节点位置判定 → 追加本地验证节点。
    /// 只构建不执行 —— 本地节点的执行在产物就绪后 (RunPlanAsync), 避免"无对象空跑"。
    /// </summary>
    private TaskPlan BuildRoutedPlan(string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks)
    {
        var plan = RoutedPlanBuilder.Build(sourceText, subTasks);
        var local = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Local);
        var hybrid = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Hybrid);
        var remote = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Remote);
        _logger.LogInformation(
            "Plan {PlanId}: {Nodes} nodes → local={Local} hybrid={Hybrid} remote={Remote}",
            plan.PlanId, plan.Nodes.Count, local, hybrid, remote);
        agent.config.AgentTelemetry.Emit("plan_route", "IndustrialAgentV2",
            ("plan_id", plan.PlanId),
            ("nodes", plan.Nodes.Count),
            ("local", local),
            ("hybrid", hybrid),
            ("remote", remote));
        return plan;
    }

    /// <summary>
    /// 计划真执行 (v0.22.0 exp9 D3): 产物就绪后跑本地节点 (真子进程/真统计, 零 LLM 调用),
    /// 并把主链已生成的正文登记为远程节点产物 (**不二次调用模型**)。
    /// 失败只记录不阻断主链; 结论写 run.Outcomes + telemetry plan_node/plan。
    /// </summary>
    private async Task<TaskPlanRun?> RunPlanAsync(TaskPlan plan, string? remoteText, CancellationToken ct,
        LocalFirstRun? localFirst = null)
    {
        try
        {
            _planRunner ??= new agent.intent.PlanRunner();
            // 同一个 ctx 对象贯穿两阶段: 本地先行阶段的节点输出不能丢 (否则下游依赖取不到)
            var ctx = _planCtx ?? agent.intent.PlanRunner.NewContext();
            _planRunner.FillFromLedger(ctx);
            ctx.RemoteText = remoteText;
            var window = _planRemoteStartUs > 0
                ? new RemoteWindow(_planRemoteStartUs, _planRemoteReadyUs)
                : (RemoteWindow?)null;
            var run = await _planRunner.RunAsync(plan, ctx, ct, localFirst, window);

            // D7b: 计划停在"等用户 / 等产出" → 落续跑三件套 (蓝图 + 运行态 + 已完成节点真产出)。
            //     没有这一步, 用户下一轮的答复就没有消费方 —— 计划的 Waiting 会永远挂着 (结构缺口)。
            var store = _planCheckpoints ??= new agent.recovery.CheckpointStore(_dataStoragePath);
            if (agent.intent.PlanResumeService.Capture(
                    store, ctx.SessionId ?? "", plan, run, ctx.NodeOutputs, plan.SourceText))
            {
                agent.config.AgentTelemetry.Emit("plan_resume_capture", "IndustrialAgentV2",
                    ("plan_id", plan.PlanId),
                    ("state", run.State.ToString()),
                    ("awaiting", agent.intent.PlanResumeService.AwaitingNodeIdOf(run, plan) ?? ""),
                    ("outputs", ctx.NodeOutputs.Count),
                    ("waits", run.Waits.Count));
            }
            var localOk = run.Outcomes.Count(o =>
                o.Location is "local" or "hybrid" && o.State == PlanNodeState.Completed);
            var failed = run.Outcomes.Count(o => o.State == PlanNodeState.Failed);
            var skipped = run.Outcomes.Count(o => o.State == PlanNodeState.Skipped);
            _logger.LogInformation(
                "Plan {PlanId} executed: local_ok={LocalOk} failed={Failed} skipped={Skipped} (executors: {Executors})",
                plan.PlanId, localOk, failed, skipped, string.Join(",", _planRunner.WiredExecutors));
            return run;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // 计划失败不影响主链 (审计性质) — 但不静默: 告警 + 遥测
            _logger.LogWarning(ex, "Plan execution failed (non-fatal)");
            agent.config.AgentTelemetry.Emit("plan_exec_failed", "IndustrialAgentV2",
                ("plan_id", plan.PlanId), ("error", ex.GetType().Name));
            return null;
        }
    }

    /// <summary>最近一次路由后的计划 (D1+D2 产物; /plan 与前端事件读这里)</summary>
    private TaskPlan? _lastPlan;

    /// <summary>最近一次计划真执行记录 (D3 产物)</summary>
    private TaskPlanRun? _lastPlanRun;

    /// <summary>D4: 本地先行批次句柄 (无依赖本地节点, 计划构建时即启动)</summary>
    private LocalFirstRun? _localFirst;

    /// <summary>出站文本扣减结果 (v0.22.0 exp9 D4b): 已判本地执行的子请求片段 + 扣减后的出站正文。</summary>
    private agent.intent.AblationResult? _planAblation;

    /// <summary>D4: 贯穿两阶段的执行上下文 (本地先行 + 产物就绪后回填)</summary>
    private LocalNodeContext? _planCtx;

    /// <summary>D7b: 计划检查点仓库 (懒建) —— 暂停时写它, 下一轮装载入口读它</summary>
    private agent.recovery.CheckpointStore? _planCheckpoints;

    /// <summary>R457: 续跑答复落不到槽位时的前台提示 (转正常路径后前置到回复, 不吞掉这一轮)。</summary>
    private string? _resumeVoidNotice;
}
