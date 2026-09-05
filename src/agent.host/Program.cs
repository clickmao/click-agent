using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using agent.core;
using agent.intent;
using agent.registry;
using agent.session;

namespace agent.host;

/// <summary>
/// AgentFramework CLI (v7.12):
///   agenthost                 → 交互 REPL (任务执行步骤明细, /status /plan /stop 可查询/控制)
///   agenthost -q "问题"       → 单条问答
///   agenthost --log run.log   → 任务输出日志保存为 markdown 文件
///   agenthost --smoke         → AOT 冒烟 (原 Program 行为保留)
/// 返回内容经区段插件处理 (html 标记/代码审查) 后输出; markdown 渲染重点。
/// </summary>
internal class Program
{
    private static string Truncate(string? s, int n) => string.IsNullOrEmpty(s) ? string.Empty : s.Length <= n ? s : s[..n] + "...";

    private static async Task<int> Main(string[] args)
    {
        // ── 参数解析 ──
        string? logPath = null;
        string? oneShot = null;
        var smoke = args.Length == 0 || args.Contains("--smoke");
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--log" && i + 1 < args.Length)
                logPath = args[++i];
            else if (args[i] == "-q" && i + 1 < args.Length)
                oneShot = args[++i];
        }

        var services = new ServiceCollection();
        services.AddLogging(b => b.AddSimpleConsole().SetMinimumLevel(LogLevel.Warning));
        services.AddAgentFramework(o => { o.DataStoragePath = "./data"; });

        await using var provider = services.BuildServiceProvider();
        var entryAgent = provider.GetRequiredService<IAgent>();

        IOutputSink sink = logPath != null
            ? new TeeOutputSink(new ConsoleOutputSink(), new FileOutputSink(logPath))
            : new ConsoleOutputSink();

        var agentCtx = new AgentContext(provider) { SessionId = "cli-main", UserId = "cli-user" };
        await entryAgent.InitializeAsync(agentCtx);

        if (smoke && oneShot == null)
            return await RunSmokeAsync(provider, entryAgent);

        return await RunCliAsync(provider, entryAgent, sink, oneShot, logPath);
    }

    // ─────────────────────────── CLI REPL ───────────────────────────

    private static async Task<int> RunCliAsync(
        ServiceProvider provider, IAgent agent, IOutputSink sink, string? oneShot, string? logPath)
    {
        var sessionMgr = provider.GetRequiredService<ISessionManager>();
        var session = new CliSession(sink, "./data");
        var turnCount = 0;
        string? lastIntent = null, lastTendency = null;

        sink.Write(CliRenderer.Bold("AgentFramework CLI"));
        sink.Write(CliRenderer.Dim("  /status 状态查询  /plan 计划 JSON  /stop 停止  /reset 重置  /exit 退出" +
                                   (logPath != null ? $"  [log → {logPath}]" : "")));

        // 单条模式或 REPL
        while (true)
        {
            string? input;
            if (oneShot != null)
            {
                input = oneShot;
            }
            else
            {
                sink.Write("");
                sink.Write(CliRenderer.Green("❯ ") + CliRenderer.Bold("(输入任务, /exit 退出)"));
                sink.Write("  ");
                input = Console.ReadLine();
                if (input == null || input.Trim() is "/exit" or "exit" or "quit")
                    break;
            }

            if (string.IsNullOrWhiteSpace(input))
            {
                if (oneShot != null) return 2;
                continue;
            }

            // CLI 本地命令 (非 LLM 强制指令的路由分流: /status /plan 由 CLI 消费, 其余进 V2 拦截层)
            var trimmed = input.Trim();
            if (trimmed == "/status")
            {
                session.RenderStatus(turnCount, lastIntent, lastTendency);
                if (oneShot != null) return 0;
                continue;
            }
            if (trimmed == "/reset")
            {
                turnCount = 0;
                lastIntent = null;
                sink.Write(CliRenderer.Yellow("🔄 会话已重置"));
                if (oneShot != null) return 0;
                continue;
            }

            try
            {
                var step = 0;
                sink.Write(CliRenderer.Dim($"── 执行中 (turn {++turnCount}) " + new string('─', 30)));

                var msg = new Message
                {
                    Role = MessageRole.User,
                    Content = input,
                    SessionId = session.SessionId,
                    SenderId = "cli-user",
                };

                // 步骤明细①: 意图/拆解预览 (快速标记给用户看, 与 V2 内部一致)
                step++;
                var subTasks = IntentDecomposer.Decompose(input);
                var intent = IntentDecomposer.PrimaryIntent(subTasks);
                lastIntent = intent;
                session.RecordStep($"意图={intent} 子任务={subTasks.Count}");
                sink.Step(step, $"意图分析: {CliRenderer.Cyan(intent)}",
                    subTasks.Count > 1 ? $"拆解 {subTasks.Count} 个子任务: {string.Join(" → ", subTasks.Select(t => t.Intent))}" : "");

                foreach (var st in subTasks)
                {
                    step++;
                    sink.Step(step, $"子任务: {Truncate(st.Text, 36)}",
                        st.DependsOnPrevious ? "[依赖前序]" : "");
                }

                // 步骤明细②: 管线执行
                step++;
                session.RecordStep($"LLM 处理 ({intent})");
                sink.Step(step, "管线执行 (上下文装配 → LLM → 后处理)…");

                var reply = await agent.ProcessAsync(msg, CancellationToken.None);
                session.RecordStep(reply.Success ? "完成" : $"失败: {Truncate(reply.Error, 50)}");

                // 步骤明细③: 返回后处理标记 (区段插件已路由)
                if (reply.Success && reply.Content.Contains("```"))
                {
                    var segs = ResponseSegmenter.Segment(reply.Content);
                    var codeLangs = segs.Where(s => s.Kind == SegmentKind.Code)
                        .Select(s => s.Language ?? "code").ToList();
                    if (codeLangs.Count > 0)
                    {
                        step++;
                        session.RecordStep($"区段标记: {string.Join(",", codeLangs)}");
                        sink.Step(step, "返回区段标记", $"{string.Join(", ", codeLangs)} (已路由插件)");
                    }
                }

                session.RenderResponse(reply, intent);

                if (reply.Success)
                {
                    var forecast = NextTurnForecast.Load("./data", "main");
                    lastTendency = forecast?.Tendency;
                    if (forecast?.LikelyContinues == true)
                        sink.Write(CliRenderer.Dim($"  ↳ 下轮预估: {forecast.Tendency}"));
                }
            }
            catch (Exception ex)
            {
                sink.Write(CliRenderer.Red("✗ 执行异常: " + ex.Message));
                if (oneShot != null) return 1;
            }

            if (oneShot != null)
                return 0;
        }

        return 0;
    }

    // ─────────────────────── AOT 冒烟 (回归闸门) ───────────────────────

    private static async Task<int> RunSmokeAsync(ServiceProvider provider, IAgent entryAgent)
    {
        Console.WriteLine("AgentFramework host (NativeAOT) starting...");
        var logger = provider.GetRequiredService<ILogger<Program>>();
        var probeTypes = new Type[]
        {
            typeof(agent.IndustrialAgentV2),
            typeof(agent.context.IContextAssembler),
            typeof(agent.search.ISearchService),
            typeof(agent.session.ISessionManager),
            typeof(agent.memory.IAgentMemoryStore),
            typeof(agent.rag.IRAGRecall),
            typeof(agent.workspace.IWorkspace),
            typeof(agent.planner.ITaskPlanner),
            typeof(agent.recovery.IRecoverySystem),
            typeof(agent.vectormemory.IVectorMemoryRecall),
            typeof(agent.templates.ITemplateStore),
        };
        int ok = 0;
        foreach (var t in probeTypes)
        {
            provider.GetRequiredService(t);
            ok++;
        }
        Console.WriteLine($"DI graph: {ok}/{probeTypes.Length} resolved");

        var agentCtx = new AgentContext(provider) { SessionId = "aot-smoke", UserId = "host" };
        await entryAgent.InitializeAsync(agentCtx);
        Console.WriteLine($"Agent state after init: {entryAgent.State}");

        var msg = new Message
        {
            Role = MessageRole.User,
            Content = "ping: AOT 宿主端到端冒烟",
            SessionId = "aot-smoke"
        };
        var reply = await entryAgent.ProcessAsync(msg, CancellationToken.None);
        Console.WriteLine($"E2E: Success={reply.Success} Content={Truncate(reply.Content, 80)} Error={Truncate(reply.Error, 60)}");
        if (reply.Success)
            Console.WriteLine("WARN: Success=true without API key — check ILLMCaller registration");

        var sessionMgr = provider.GetRequiredService<agent.session.ISessionManager>();
        var round2 = await entryAgent.ProcessAsync(new Message
        {
            Role = MessageRole.User,
            Content = "第二轮: 记得上一条说了什么吗",
            SessionId = "aot-smoke"
        }, CancellationToken.None);
        var session = await sessionMgr.GetSessionAsync("aot-smoke");
        var userMsgs = session?.Messages.Count(m => m.Role == MessageRole.User) ?? 0;
        Console.WriteLine($"Multi-turn: session={session?.Id ?? "NULL"} userMsgs={userMsgs} round2Success={round2.Success}");
        if (session == null || userMsgs != 2)
        {
            Console.Error.WriteLine($"FATAL: multi-turn session broken (expected session with 2 user messages, got {session?.Id ?? "NULL"} / {userMsgs})");
            return 1;
        }

        Console.WriteLine("AgentFramework host: OK (full-graph AOT smoke passed)");
        return 0;
    }
}
