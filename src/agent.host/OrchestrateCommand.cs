using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.core;
using agent.intent;
using agent.registry;

namespace agent.host;

/// <summary>
/// R515 长任务编排器宿主入口: `--orchestrate &lt;计划文件&gt; [选项]`
///
/// 语义: 计划文件里每个**远端节点 = 一次真实 agent 轮次** (各自独立步数预算), 本地节点 = 零 LLM 子进程;
/// 逐节点落盘「本节点改了哪些文件」(工作区快照差), 上游产出注入下游节点提示; 收尾写 orchestrate-report.json。
///
/// 退出码: 0 = 全部节点 Completed; 1 = 有节点失败; 2 = 计划/参数非法 (fail-closed)。
/// 诚实边界: 本命令**不判断产物逻辑正确性** —— 正确性判据由外部夹具负责 (铁律 11)。
/// </summary>
public static class OrchestrateCommand
{
    private const int DefaultNodeSteps = 6;
    private const int MaxNodeSteps = 32;
    private const int UpstreamCharsDefault = 4000;

    public static async Task<int> RunAsync(IServiceProvider provider, IAgent agent, string[] args, TextWriter outp, TextWriter errp)
    {
        var planPath = "";
        var workspace = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE") ?? "";
        var session = "orchestrator";
        var nodeSteps = DefaultNodeSteps;
        var maxNodes = 24;
        var reportPath = "";
        var upstreamChars = UpstreamCharsDefault;
        var scopePath = "";
        var supplementsPath = "";   // R580: 用户补充投递文件 (一行一条; 运行中追加即投递)
        var nodeEscalations = 1;   // R518: 零产物 ⇒ 升预算重试次数上限 (默认开 1; 0 = 关)

        for (var i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--node-escalations":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], NumberStyles.Integer, CultureInfo.InvariantCulture, out nodeEscalations))
                    { errp.WriteLine("orchestrate: --node-escalations 需整数 (0..3)"); return 2; }
                    break;
                case "--scope":
                    if (i + 1 >= args.Length) { errp.WriteLine("orchestrate: --scope 缺参"); return 2; }
                    scopePath = args[++i];
                    break;
                case "--node-steps":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], NumberStyles.Integer, CultureInfo.InvariantCulture, out nodeSteps))
                    { errp.WriteLine("orchestrate: --node-steps 需整数"); return 2; }
                    break;
                case "--max-nodes":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], NumberStyles.Integer, CultureInfo.InvariantCulture, out maxNodes))
                    { errp.WriteLine("orchestrate: --max-nodes 需整数"); return 2; }
                    break;
                case "--workspace":
                    if (i + 1 >= args.Length) { errp.WriteLine("orchestrate: --workspace 缺参"); return 2; }
                    workspace = args[++i];
                    break;
                case "--session":
                    if (i + 1 >= args.Length) { errp.WriteLine("orchestrate: --session 缺参"); return 2; }
                    session = args[++i];
                    break;
                case "--report":
                    if (i + 1 >= args.Length) { errp.WriteLine("orchestrate: --report 缺参"); return 2; }
                    reportPath = args[++i];
                    break;
                case "--upstream-chars":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], NumberStyles.Integer, CultureInfo.InvariantCulture, out upstreamChars))
                    { errp.WriteLine("orchestrate: --upstream-chars 需整数"); return 2; }
                    break;
                case "--supplements":
                    if (i + 1 >= args.Length) { errp.WriteLine("orchestrate: --supplements 缺参"); return 2; }
                    supplementsPath = args[++i];
                    break;
                default:
                    if (planPath.Length == 0 && !args[i].StartsWith("--", StringComparison.Ordinal)) planPath = args[i];
                    else { errp.WriteLine($"orchestrate: 未知参数 {args[i]}"); return 2; }
                    break;
            }
        }

        if (planPath.Length == 0) { errp.WriteLine("用法: --orchestrate <计划文件> [--scope <范围文件>] [--workspace DIR] [--node-steps N] [--max-nodes N] [--supplements <投递文件>]"); return 2; }
        if (nodeSteps < 1 || nodeSteps > MaxNodeSteps) { errp.WriteLine($"orchestrate: --node-steps 越界 1..{MaxNodeSteps}"); return 2; }

        var (plan, problems) = TaskPlanFile.Load(planPath);
        if (plan is null)
        {
            errp.WriteLine("orchestrate: 计划非法 (fail-closed):");
            foreach (var p in problems) errp.WriteLine("  · " + p);
            return 2;
        }
        problems = TaskPlanFile.Validate(plan, maxNodes);
        if (problems.Count > 0)
        {
            errp.WriteLine("orchestrate: 计划校验失败:");
            foreach (var p in problems) errp.WriteLine("  · " + p);
            return 2;
        }

        // ── R516 范围契约 (起臂前, 零 LLM 成本): 未知节点 / 同层写范围重叠 ⇒ 拒收 rc=2 ──
        Dictionary<string, IReadOnlyList<string>>? scopes = null;
        if (scopePath.Length > 0)
        {
            var (parsed, scopeProblems) = NodeScopeFile.Load(scopePath);
            if (parsed is null)
            {
                errp.WriteLine($"orchestrate: 范围文件非法 (fail-closed): {scopePath}");
                foreach (var p in scopeProblems) errp.WriteLine("  · " + p);
                return 2;
            }
            var scopePlanProblems = TaskOrchestrator.ValidateScopes(plan, parsed);
            if (scopePlanProblems.Count > 0)
            {
                errp.WriteLine("orchestrate: 范围契约校验失败 (未发起任何 LLM 调用):");
                foreach (var p in scopePlanProblems) errp.WriteLine("  · " + p);
                return 2;
            }
            scopes = parsed;
            outp.WriteLine($"范围契约: {Path.GetFileName(scopePath)} 已声明 {scopes.Count}/{plan.Nodes.Count} 节点");
        }

        if (workspace.Length == 0) { errp.WriteLine("orchestrate: 缺工作区 (--workspace 或 AGENTFRAMEWORK_WORKSPACE)"); return 2; }
        if (!Directory.Exists(workspace)) { errp.WriteLine($"orchestrate: 工作区不存在 {workspace}"); return 2; }
        workspace = Path.GetFullPath(workspace);
        var nodeDir = Path.Combine(workspace, ".orchestrator");
        if (supplementsPath.Length == 0) supplementsPath = planPath + ".supplements.txt";
        var suppInbox = new global::agent.r1.SupplementInbox(
            new global::agent.rag.LexicalRerankScorer(0.0),
            global::agent.r1.SupplementInbox.ThresholdFromEnvironment("AGENTFRAMEWORK_ORCH_SUPPLEMENT_MIN_SCORE", 0.05),
            global::agent.r1.SupplementInbox.DropFileSource(supplementsPath));
        var supplementPlacements = new List<string>();
        outp.WriteLine("[orchestrate] 用户补充投递文件: " + supplementsPath + " (运行中追加一行即投递; 在下一个节点边界插入, 尾部可变区不破前缀缓存)");
        Directory.CreateDirectory(nodeDir);
        if (reportPath.Length == 0) reportPath = Path.Combine(nodeDir, "orchestrate-report.json");

        outp.WriteLine($"编排开始: 计划={Path.GetFileName(planPath)} 节点={plan.Nodes.Count} 单节点预算={nodeSteps} 工作区={workspace}");

        // R515 铁律: 与 CLI/one-shot 同源 —— 必须先 InitializeAsync 才能 ProcessAsync,
        // 否则远端节点一律 Failed ("Agent is not in ready state. Current state: Initial")。
        var agentCtx = new AgentContext(provider) { SessionId = session, UserId = "orchestrator" };
        await agent.InitializeAsync(agentCtx).ConfigureAwait(false);
        outp.WriteLine($"编排: agent 已初始化 (session={session})");

        var localExecutors = new ILocalNodeExecutor[]
        {
            new PythonSelfTestExecutor(),
            new TextProcessExecutor(),
        };

        var orchestrator = new TaskOrchestrator(
            localExecutors,
            events: null,
            checkpointStore: null,
            sessionId: session,
            options: new TaskOrchestrator.Options
            {
                NodeMaxSteps = nodeSteps,
                MaxNodes = maxNodes,
                MaxBudgetEscalations = nodeEscalations,
                ConcurrentLocalFirst = true,
                WorkspaceRoot = workspace,
                NodeScopes = scopes,
                LocalContextFactory = node =>
                {
                    var artifact = node.LocalHint ?? node.Text;
                    if (artifact.Length > 0 && !Path.IsPathRooted(artifact)) artifact = Path.Combine(workspace, artifact);
                    var python = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_PYTHON") ?? "python3";
                    return new LocalNodeContext
                    {
                        SessionId = session,
                        ArtifactPath = artifact,
                        PythonPath = python,
                        PythonRunGate = () => Environment.GetEnvironmentVariable("AGENTFRAMEWORK_PY_RUN") == "1",
                        SourceText = plan.SourceText,
                    };
                },
            });

        Task<NodeExecutionResult> Remote(PlanNode node, IReadOnlyDictionary<string, string> upstream, int steps, CancellationToken ct)
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_MAX_STEPS", steps.ToString(CultureInfo.InvariantCulture));
            // 时机锚: 上一个节点返回之后(此刻)收割投递的补充, 按本节点文本打分后插到提示**尾部**(可变区)。
            suppInbox.Harvest();
            var injectedSupplements = suppInbox.SelectFor(node.Text);
            if (injectedSupplements.Count > 0)
            {
                suppInbox.MarkConsumed(injectedSupplements);
                lock (supplementPlacements)
                {
                    supplementPlacements.Add(node.Id + " | injected=" + injectedSupplements.Count.ToString(CultureInfo.InvariantCulture));
                }
            }

            var prompt = BuildNodePrompt(plan, node, upstream, upstreamChars, workspace, steps, injectedSupplements);
            var msg = new Message
            {
                Role = MessageRole.User,
                Content = prompt,
                SessionId = session,
                SenderId = "orchestrator",
            };
            return RunRemoteAsync(agent, msg, node, nodeDir, ct);
        }

        TaskPlanRun run;
        try
        {
            run = await orchestrator.RunAsync(plan, Remote, pollInjections: null, ct: CancellationToken.None).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            errp.WriteLine($"orchestrate: 编排异常 {ex.GetType().Name}: {ex.Message}");
            return 1;
        }

        var failed = run.NodeStates.Count(kv => kv.Value == PlanNodeState.Failed);
        var completed = run.NodeStates.Count(kv => kv.Value == PlanNodeState.Completed);

        // R516: 逐节点产物清单由编排器 (单一权威快照持有者) 落盘, 不再由宿主节点执行体各自快照。
        foreach (var pair in orchestrator.NodeArtifacts)
        {
            try
            {
                File.WriteAllText(Path.Combine(nodeDir, pair.Key + ".files.txt"), string.Join('\n', pair.Value), new UTF8Encoding(false));
            }
            catch (IOException)
            {
                Console.Error.WriteLine($"orchestrate: 节点产物清单落盘失败 {pair.Key}");
            }
        }

        outp.WriteLine("── 节点表 ──");
        outp.Write(TaskPlanFile.Summary(plan, orchestrator.Telemetry));
        outp.WriteLine($"汇总: 完成 {completed}/{plan.Nodes.Count} · 失败 {failed} · 墙钟重叠 {orchestrator.OverlapMs} ms · 预算上界 {orchestrator.BudgetCeiling} 步");
        if (orchestrator.ScopeViolations.Count > 0)
        {
            outp.WriteLine($"范围机检: {orchestrator.ScopeViolations.Count} 条违规 (节点已判 Failed)");
            foreach (var v in orchestrator.ScopeViolations) outp.WriteLine($"  · {v.NodeId} [{v.Kind}] {(v.Path.Length == 0 ? "(零产物)" : v.Path)}");
        }
        if (supplementPlacements.Count > 0)
        {
            File.WriteAllLines(Path.Combine(nodeDir, "orchestrate-supplements.csv"), supplementPlacements, new UTF8Encoding(false));
        }


        WriteReport(reportPath, plan, orchestrator, run, scopes, scopePath, workspace, nodeSteps);
        outp.WriteLine($"报告: {reportPath}");

        return failed == 0 && completed == plan.Nodes.Count ? 0 : 1;
    }

    private static async Task<NodeExecutionResult> RunRemoteAsync(
        IAgent agent,
        Message msg,
        PlanNode node,
        string nodeDir,
        CancellationToken ct)
    {
        AgentResponse reply;
        try
        {
            reply = await agent.ProcessAsync(msg, ct).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            return new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = PlanNodeState.Failed,
                Error = $"远端节点执行异常 {ex.GetType().Name}",
                FailureKind = NodeFailureKind.Permanent,
            };
        }

        // R516: 产物清单不在此处快照 (快照权威 = 编排器, 修 R515 的「同层写者互相覆盖」归属错乱)。
        var content = reply.Content ?? string.Empty;
        try
        {
            File.WriteAllText(Path.Combine(nodeDir, node.Id + ".md"), content, new UTF8Encoding(false));
        }
        catch (IOException)
        {
            // IO 异常留告警, 不掩盖节点结论
            Console.Error.WriteLine($"orchestrate: 节点产物落盘失败 {node.Id}");
        }

        return new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = reply.Success ? PlanNodeState.Completed : PlanNodeState.Failed,
            Output = content,
            Error = reply.Success ? null : (reply.Error ?? "回复失败"),
            FailureKind = reply.Success ? NodeFailureKind.None : NodeFailureKind.Transient,
        };
    }

    /// <summary>节点提示: 长任务切片 + 上游产出 + 落盘纪律。</summary>
    private static string BuildNodePrompt(
        TaskPlan plan,
        PlanNode node,
        IReadOnlyDictionary<string, string> upstream,
        int upstreamChars,
        string workspace,
        int steps,
        IReadOnlyList<string> supplements)
    {
        var sb = new StringBuilder(1024);
        sb.Append("你是长任务编排器驱动的一次**节点执行体**。整条长任务被切成 ")
          .Append(plan.Nodes.Count.ToString(CultureInfo.InvariantCulture))
          .Append(" 个节点, 你只负责当前节点 ").Append(node.Id)
          .Append(" (第 L").Append(node.Level.ToString(CultureInfo.InvariantCulture)).Append(" 层)。\n\n");
        sb.Append("【全计划】\n").Append(TaskPlanFile.Render(plan)).Append('\n');
        sb.Append("【当前节点 ").Append(node.Id).Append(" 的任务】\n").Append(node.Text).Append("\n\n");
        if (upstream.Count > 0)
        {
            sb.Append("【上游节点产出】\n");
            foreach (var pair in upstream)
            {
                sb.Append("--- ").Append(pair.Key).Append(" ---\n");
                var text = pair.Value;
                sb.Append(text.Length > upstreamChars ? text[..upstreamChars] + "\n…(截断)" : text).Append('\n');
            }
            sb.Append('\n');
        }
        sb.Append("【纪律】\n")
          .Append("1) 用工具**真实落盘**文件到工作区 ").Append(workspace).Append(" (写在回复正文里的代码不算完成)。\n")
          .Append("2) 只做本节点这一段; 不要替后序节点做, 也不要重复上游已完成的工作。\n")
          .Append("3) 本节点动作步数预算 = ").Append(steps.ToString(CultureInfo.InvariantCulture)).Append(" 步, 先落盘再补充说明。\n")
          .Append("4) 结束前用工具核对文件确实存在。\n")
          .Append("5) 工具 path 一律写**工作区相对**路径 (如 games/life.py); **禁止**把工作区绝对路径裁成仓根相对路径")
          .Append(" —— 那会在工作区内生成影子副本 (被边界闸拒绝), 且你读回的会是另一份文件。\n");
        sb.Append(global::agent.r1.SupplementBlock.Render(supplements));

        return sb.ToString();
    }

    private static void WriteReport(
        string reportPath,
        TaskPlan plan,
        TaskOrchestrator orchestrator,
        TaskPlanRun run,
        IReadOnlyDictionary<string, IReadOnlyList<string>>? scopes,
        string scopePath,
        string workspace,
        int nodeSteps)
    {
        var sb = new StringBuilder(2048);
        sb.Append("{\n  \"plan_id\": \"").Append(plan.PlanId).Append("\",\n");
        sb.Append("  \"run_id\": \"").Append(run.RunId).Append("\",\n");
        sb.Append("  \"state\": \"").Append(run.State.ToString()).Append("\",\n");
        sb.Append("  \"workspace\": \"").Append(Escape(workspace)).Append("\",\n");
        sb.Append("  \"node_steps\": ").Append(nodeSteps.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"budget_ceiling\": ").Append(orchestrator.BudgetCeiling.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"budget_ceiling_effective\": ").Append(orchestrator.BudgetCeilingEffective.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"node_escalations_max\": ").Append(orchestrator.Opt.MaxBudgetEscalations.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"escalations_total\": ").Append(orchestrator.EscalationCount.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"overlap_ms\": ").Append(orchestrator.OverlapMs.ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"scope_file\": \"").Append(Escape(scopePath)).Append("\",\n");
        sb.Append("  \"scope_declared\": ").Append((scopes?.Count ?? 0).ToString(CultureInfo.InvariantCulture)).Append(",\n");
        sb.Append("  \"scope_undeclared\": [")
          .Append(string.Join(", ", plan.Nodes.Where(n => scopes is null || !scopes.ContainsKey(n.Id)).Select(n => "\"" + Escape(n.Id) + "\"")))
          .Append("],\n");
        sb.Append("  \"requires_scoped_artifact\": true,\n");
        sb.Append("  \"scope_violations\": [")
          .Append(string.Join(", ", orchestrator.ScopeViolations.Select(v => "{\"node_id\": \"" + Escape(v.NodeId) + "\", \"path\": \"" + Escape(v.Path) + "\", \"kind\": \"" + v.Kind + "\"}")))
          .Append("],\n");
        sb.Append("  \"nodes\": [\n");
        var telemetry = orchestrator.Telemetry;
        for (var i = 0; i < telemetry.Count; i++)
        {
            var t = telemetry[i];
            var node = plan.Nodes.First(n => n.Id == t.NodeId);
            sb.Append("    {\"node_id\": \"").Append(Escape(t.NodeId))
              .Append("\", \"level\": ").Append(t.Level.ToString(CultureInfo.InvariantCulture))
              .Append(", \"location\": \"").Append(t.Location)
              .Append("\", \"executor\": \"").Append(Escape(t.Executor))
              .Append("\", \"state\": \"").Append(t.State)
              .Append("\", \"elapsed_ms\": ").Append(t.ElapsedMs.ToString(CultureInfo.InvariantCulture))
              .Append(", \"output_chars\": ").Append(t.OutputChars.ToString(CultureInfo.InvariantCulture))
              .Append(", \"deps\": [").Append(string.Join(", ", node.DependsOn.Select(d => "\"" + Escape(d) + "\""))).Append(']')
              .Append(", \"scope\": [").Append(string.Join(", ", t.Scope.Select(s => "\"" + Escape(s) + "\""))).Append(']')
              .Append(", \"files\": [").Append(string.Join(", ", Files(orchestrator.NodeArtifacts, t.NodeId).Select(f => "\"" + Escape(f) + "\""))).Append(']')
              .Append(", \"budget_steps\": ").Append(t.BudgetSteps.ToString(CultureInfo.InvariantCulture))
              .Append(", \"escalations\": ").Append(t.Escalations.ToString(CultureInfo.InvariantCulture))
              .Append(", \"attempts\": [").Append(string.Join(", ", t.Attempts.Select(a => "\"" + Escape(a) + "\""))).Append(']')
              .Append(", \"error\": \"").Append(Escape(t.Error)).Append("\"}");
            sb.Append(i + 1 < telemetry.Count ? ",\n" : "\n");
        }
        sb.Append("  ],\n");
        sb.Append("  \"node_states\": {");
        sb.Append(string.Join(", ", run.NodeStates.Select(kv => "\"" + Escape(kv.Key) + "\": \"" + kv.Value + "\"")));
        sb.Append("}\n}\n");
        try
        {
            File.WriteAllText(reportPath, sb.ToString(), new UTF8Encoding(false));
        }
        catch (IOException) { }
    }

    private static IReadOnlyList<string> Files(IReadOnlyDictionary<string, IReadOnlyList<string>> map, string nodeId)
        => map.TryGetValue(nodeId, out var list) ? list : Array.Empty<string>();

    private static string Escape(string? s)
    {
        if (string.IsNullOrEmpty(s)) return string.Empty;
        var sb = new StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}
