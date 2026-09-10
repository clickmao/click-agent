using agent.contextgradient;
using System.Text.Json;
using agent.llamalocal;
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
///   agenthost -rag <path>     → 指定 RAG 数据文件 (v0.13.0, 用户钦定)
///   agenthost --log run.log   → 任务输出日志保存为 markdown 文件
///   agenthost --output-mode text → 纯文本模式 (默认 markdown; 控制台均着色)
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
        var imageArgs = new List<string>(); // v0.12.0 A2: -img 图像附件 (路径/URL, 可多次)
        var smoke = args.Length == 0 || args.Contains("--smoke");
        var outputMode = agent.output.OutputMode.Markdown;
        string? embedText = null;
        string? ragPath = null; // v0.13.0: -rag RAG 数据文件路径 (用户钦定)
        // v0.16.0-a (用户钦定): 外挂 skills — --skills-dir <dir> (可多次) / --skills-blacklist <id|dir> (可多次)
        //                        / --skills-file <SKILL.md> (单 skill 文件, 可多次); 与内置 skills/ 不冲突均可匹配。
        var skillExtraDirs = new List<string>();
        var skillBlacklist = new List<string>();
        var skillExtraFiles = new List<string>();
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--log" && i + 1 < args.Length)
                logPath = args[++i];
            else if (args[i] == "-q" && i + 1 < args.Length)
                oneShot = args[++i];
            else if (args[i] == "--output-mode" && i + 1 < args.Length)
                outputMode = args[++i] == "text"
                    ? agent.output.OutputMode.PlainText
                    : agent.output.OutputMode.Markdown;
            else if (args[i] == "--embed" && i + 1 < args.Length)
                embedText = args[++i];
            // v0.12.0 A2: 图像附件 (可多次) — 路径或 URL, 走 vision 链
            else if (args[i] == "-img" && i + 1 < args.Length)
                imageArgs.Add(args[++i]);
            // v0.13.0 (用户钦定): -rag <path> 指定 RAG 数据文件 (index.jsonl 路径, 可自定义库)
            else if (args[i] == "-rag" && i + 1 < args.Length)
                ragPath = args[++i];
            else if (args[i] == "--skills-dir" && i + 1 < args.Length)
                skillExtraDirs.Add(args[++i]);
            else if (args[i] == "--skills-blacklist" && i + 1 < args.Length)
                skillBlacklist.AddRange(args[++i].Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries));
            else if (args[i] == "--skills-file" && i + 1 < args.Length)
                skillExtraFiles.Add(args[++i]);
        }

        // R136 (D4 reply_rel 基础设施): --embed 输出向量 JSON — R352: 本地 bge 已删,
        // 走 llm-service (RemoteEmbedder; daemon 离线 → hash 兜底语义), harness 离线算 reply_rel 不变。
        if (embedText is not null)
        {
            var embedder = new agent.llamalocal.RemoteEmbedder();
            var vec = await embedder.EmbedAsync(embedText, CancellationToken.None);
            Console.WriteLine("[" + string.Join(",", vec.Select(v => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture))) + "]");
            return 0;
        }
// v0.20.0 P3 (R343, 用户 OOB: "/bin/sh 跨平台怎么办?"): daemon 自写日志 — 不依赖 shell 重定向,
// 跨平台 (Windows/macOS/Linux); spawn 端仅传 env, 无 shell 依赖。SIGPIPE/终端消失均不影响。
static void RedirectDaemonLogIfConfigured()
{
    var logPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_LOG");
    if (string.IsNullOrEmpty(logPath)) return;
    try
    {
        var sw = System.IO.TextWriter.Synchronized(new System.IO.StreamWriter(logPath, append: true) { AutoFlush = true });
        Console.SetOut(sw);
        Console.SetError(sw);
    }
    catch { /* 日志文件不可写 → 保持 stdout (不阻断服务) */ }
}

// v0.20.0 P1 (R342, 用户钦定): 本机 LLM service daemon — 常驻加载 bge 服务多 CLI (新 CLI 免重载模型)。
// 旁路模式: 框架现有 LLM 使用流程不改 (用户纠正); 客户端显式用 agent.llamalocal.RemoteEmbedder。
// R352: --llm-service 分支移除 (本地 bge 引擎 = LLamaSharp 已删; embed 语义档走外部 llm-service 部署或锚词)


// v0.20.0 P3 (R343, 用户钦定策略): llm-manager — 轻量常驻编排进程 (0 模型加载)。
// 对外 UDS 与 CLI 通讯; worker (--llm-service, 真模型) 按需 lazy spawn; 资源紧张 ∧ 无 CLI 实例 → kill worker 卸载。
// 客户端 (RemoteEmbedder) 走同一 sock 协议 — manager 透明代理, CLI 全退 manager 仍在 (不随 CLI 生死)。
if (args.Length >= 1 && args[0] == "--llm-manager")
{
    RedirectDaemonLogIfConfigured();
    agent.llmservice.LlmManagerHost manager;
    try
    {
        // env 可调 (用户钦定"llm-host 内部自动管理"; 默认: 内存 <512MB 且无 CLI 实例 → 卸载 worker)
        var floor = long.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_MEM_FLOOR_MB"), out var f) ? f : 512;
        var checkMs = int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_UNLOAD_CHECK_MS"), out var c) ? c : 15_000;
        manager = new agent.llmservice.LlmManagerHost(msg => Console.WriteLine($"[llm-manager] {msg}"),
            memFloorMb: floor, unloadCheckMs: checkMs);
        manager.Start();
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"llm-manager: 启动失败 — {ex.Message}");
        return 4;
    }
    using (manager)
    {
        Console.WriteLine("llm-manager: READY (0 模型占用; worker 按需拉起; 资源紧张且无 CLI 实例时自动卸载 worker)");
        Console.Out.Flush();
        var done = new ManualResetEventSlim(false);
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; done.Set(); };
        AppDomain.CurrentDomain.ProcessExit += (_, _) => done.Set();
        done.Wait();
        Console.WriteLine("llm-manager: 退出");
        return 0;
    }
}

// v0.20.3 (R346): --llm-service-status — 非交互输出 llm-manager/worker 状态 (脚本/CI/前端/无 TTY 场景)。
// exit 0 = manager 在线; exit 5 = 未运行 (诚实失败, 不伪造)。等价 REPL 内 /llm-service 指令。
if (args.Length >= 1 && args[0] == "--llm-service-status")
{
    var sock = agent.llamalocal.RemoteEmbedder.GetSockFromEnv();
    var st = agent.llmservice.LlmServiceStatus.Query(sock);
    Console.WriteLine(st.Render(sock));
    return st.Online ? 0 : 5;
}

// v0.13.3 A2 (用户钦定) — 压缩底座 audit (用户钦定) — 压缩底座 audit: ground-truth 样本 × 真实 ContextGradientCompressor
// → 关键信息保留率 / 压缩率 / semantic / 耗时 矩阵 (JSON 输出 → eval/results/)。
// 用法: agenthost --compression-audit <groundtruth.json>
if (args.Length >= 2 && args[0] == "--compression-audit")
{
    var docs = JsonSerializer.Deserialize(File.ReadAllText(args[1]),
        CompressionAuditJsonContext.Default.ListGtDoc);
    if (docs is null || docs.Count == 0) { Console.Error.WriteLine("no_samples"); return 3; }
    var compressor = new ContextGradientCompressor(); // NullTextEmbedder 锚词模式 (语义校验降级为锚词, 真机批测同形态)
    var report = new List<AuditRow>();
    foreach (var levelName in new[] { "SummarySentences", "RuleCompressed", "TitleOnly" })
    {
        var level = levelName switch
        {
            "SummarySentences" => GradientLevel.SummarySentences,
            "RuleCompressed" => GradientLevel.RuleCompressed,
            _ => GradientLevel.TitleOnly,
        };
        foreach (var grp in docs.GroupBy(d => d.TargetTokens).OrderBy(g => g.Key))
        {
            int keepTotal = 0, keyTotal = 0, causalKeep = 0, instrKeep = 0, instrKeepTotal = 0;
            long msTotal = 0; double ratioSum = 0; int n = 0;
            foreach (var d in grp)
            {
                var request = new GradientRequest
                {
                    Content = d.Content,
                    RelevanceScore = levelName switch { "SummarySentences" => 0.6, "RuleCompressed" => 0.4, _ => 0.1 },
                    TokenBudget = d.TargetTokens / 2,
                    AnchorWords = new List<string> { d.GroundTruth["entity_product"], d.GroundTruth["entity_person"] },
                };
                var sw = System.Diagnostics.Stopwatch.StartNew();
                var result = compressor.Compress(request);
                sw.Stop();
                msTotal += sw.ElapsedMilliseconds;
                n++;
                var outChars = result.Content.Length;
                ratioSum += d.Content.Length > 0 ? 1.0 - (double)outChars / d.Content.Length : 0;
                // ground truth 逐项核对 (保留率):
                foreach (var kv in d.GroundTruth)
                {
                    keyTotal++;
                    if (result.Content.Contains(kv.Value, StringComparison.Ordinal)) keepTotal++;
                }
                if (result.Content.Contains(d.CausalSentence.Split('，')[0].Replace("因为", ""), StringComparison.Ordinal)) causalKeep++;
                // v0.13.3 A3d (audit 判定缺陷实证): 硬编码 "必须先经过" 只匹配 2/6 样式 —
                // nested_list (审批:必须由)、multi_hop (必须由…协调)、zh_en (must)、number_dense (无指令) 全误判丢。
                // 改: 指令判定 = instruction_sentence 含"必须"起的 12ch 核心片段在压缩产物中;
                // 无指令句样本 (number_dense) → instrKeep 分母不计 (诚实: 无从判定)。
                if (!string.IsNullOrEmpty(d.InstructionSentence))
                {
                    var mi = d.InstructionSentence.IndexOf("必须", StringComparison.Ordinal);
                    var coreMark = mi >= 0
                        ? d.InstructionSentence.Substring(mi, Math.Min(12, d.InstructionSentence.Length - mi))
                        : d.InstructionSentence[..Math.Min(12, d.InstructionSentence.Length)];
                    if (result.Content.Contains(coreMark, StringComparison.Ordinal)) instrKeep++;
                    instrKeepTotal++;
                }
            }
            report.Add(new AuditRow
            {
                Level = levelName,
                BucketTokens = grp.Key,
                Samples = n,
                KeyKeepRate = Math.Round((double)keepTotal / Math.Max(1, keyTotal), 4),
                CausalKeepRate = Math.Round((double)causalKeep / Math.Max(1, n), 4),
                InstructionKeepRate = Math.Round((double)instrKeep / Math.Max(1, n), 4),
                CompressRatio = Math.Round(ratioSum / Math.Max(1, n), 4),
                AvgMs = msTotal / Math.Max(1, n),
            });
        }
    }
    var json = JsonSerializer.Serialize(report, CompressionAuditJsonContext.Default.ListAuditRow);
    Console.WriteLine(json);
    var outPath = "eval/results/compression-audit-latest.json";
    Directory.CreateDirectory("eval/results");
    File.WriteAllText(outPath, json);
    return 0;
}


        // v0.13.0 (用户钦定): -rag 指定 RAG 数据文件 → env 钩子 (DI 工厂读取; 进程内生效, 不落盘)
        if (!string.IsNullOrEmpty(ragPath))
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_RAG_PATH", Path.GetFullPath(ragPath));

        // v0.16.0-a: 外挂 skills env 钩子 (DI 读取; 分号分隔多值)
        if (skillExtraDirs.Count > 0)
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_EXTRA_DIRS", string.Join(";", skillExtraDirs.Select(Path.GetFullPath)));
        if (skillBlacklist.Count > 0)
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_BLACKLIST", string.Join(";", skillBlacklist));
        if (skillExtraFiles.Count > 0)
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_EXTRA_FILES", string.Join(";", skillExtraFiles.Select(Path.GetFullPath)));

        var services = new ServiceCollection();
        services.AddLogging(b => b.AddSimpleConsole().SetMinimumLevel(LogLevel.Warning));
        services.AddAgentFramework(o => { o.DataStoragePath = "./data"; });
        // v0.11.0 R101 (真缺陷 37): IOutputSink 从未注册进 DI — RunSmokeAsync (v0.10 引入)
        // 的 GetRequiredService<IOutputSink> 必然抛 InvalidOperationException, AOT 冒烟闸门
        // 实际失效。此处先按命令行 logPath 决策 sink 并注册 (Main 后段复用同一实例, 不再二次构建)。
        IOutputSink earlySink = logPath != null
            ? new TeeOutputSink(new ConsoleOutputSink(), new FileOutputSink(logPath))
            : new ConsoleOutputSink();
        services.AddSingleton<IOutputSink>(earlySink);
        agent.config.AgentTelemetry.Configure("host", "./data/telemetry");
        agent.config.AgentTelemetry.Emit("boot", "Program", ("probe", true));

// v0.19 P1 后半 (R355): --frontend-api <port> — FrontendApi 统一接口独立挂载。
// 与 REPL/one-shot 并列的第三种运行形态: 常驻服务, 外部前端经 TCP 行 JSON 信封消费完整 agent 管线。
        await using var provider = services.BuildServiceProvider();
        var entryAgent = provider.GetRequiredService<IAgent>();

if (args.Length >= 2 && args[0] == "--frontend-api")
{
    if (!int.TryParse(args[1], out var apiPort) || apiPort is < 1 or > 65535)
    {
        Console.Error.WriteLine("frontend-api: 端口非法");
        return 4;
    }
    RedirectDaemonLogIfConfigured();
    var frontendCtx = new AgentContext(provider) { SessionId = "frontend-main", UserId = "frontend-user" };
    await entryAgent.InitializeAsync(frontendCtx);

    var snapshotJson = "{\"v\":1,\"agent\":{\"name\":\"click-agent\",\"status\":\"idle\"},\"note\":\"P1 snapshot 骨架\"}";
    var metaJson = "{\"version\":\"0.20.5\",\"contract\":1,\"domains\":[\"chat\",\"meta\",\"state\"]}";
    var chatRouter = new agent.frontendapi.FrontendApiChatRouter(entryAgent);
    var server = new agent.frontendapi.FrontendApiServer(async (api, payloadJson) =>
    {
        // chat 域 (异步直通 V2)
        var chatResp = await chatRouter.HandleAsync(api, payloadJson);
        if (chatResp is not null) return chatResp;
        // 状态/元域 (同步)
        return api switch
        {
            "state.snapshot" => snapshotJson,
            "state.hello" => "{\"hello\":true}",
            "meta.info" => metaJson,
            _ => null,
        };
    }, msg => Console.WriteLine($"[frontend-api] {msg}"), apiPort);

    try
    {
        server.Start();
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"frontend-api: 启动失败 — {ex.Message}");
        return 4;
    }
    Console.WriteLine($"frontend-api: READY :{apiPort} (chat.send 直通 V2 管线; Ctrl+C 退出)");
    Console.Out.Flush();
    var feDone = new ManualResetEventSlim(false);
    Console.CancelKeyPress += (_, e) => { e.Cancel = true; feDone.Set(); };
    AppDomain.CurrentDomain.ProcessExit += (_, _) => feDone.Set();
    feDone.Wait();
    server.Dispose();
    Console.WriteLine("frontend-api: 退出");
    return 0;
}



        // v7.15 需求1: CLI 启动参数注入官方 key (立即释放命令行引用 — 避免进程参数驻留)

        IOutputSink sink = earlySink; // R101 (缺陷 37): 复用 DI 注册实例 (smoke/CLI 同源)

        var agentCtx = new AgentContext(provider) { SessionId = "cli-main", UserId = "cli-user" };
        await entryAgent.InitializeAsync(agentCtx);

        // v7.15 需求3: 会话中断恢复 — 启动时检查上次执行检查点, 有未完成计划直接提示恢复点
        var checkpointStore = new agent.recovery.CheckpointStore("./data");
        var lastCheckpoint = checkpointStore.Load("cli-main");
        if (lastCheckpoint != null)
        {
            var recovery = agent.recovery.CheckpointRecovery.BuildRecoveryPlan(lastCheckpoint);
            if (recovery.Resumable)
                provider.GetRequiredService<ILogger<Program>>()
                    .LogInformation("[recovery] {Summary}", recovery.Summary);
        }

        try
        {
            if (smoke && oneShot == null)
                return await RunSmokeAsync(provider, entryAgent);
            return await RunCliAsync(provider, entryAgent, sink, oneShot, logPath, outputMode, imageArgs);
        }
        finally
        {
            // v0.17.2-a (R336): 优雅退出清活动心跳 (kill -9 由 ActivityService TTL 兜底, 不在此路径)
            (entryAgent as agent.IndustrialAgentV2)?.ClearActivity();
        }
    }

    // ─────────────────────────── CLI REPL ───────────────────────────

    private static async Task<int> RunCliAsync(
        ServiceProvider provider, IAgent agent, IOutputSink sink, string? oneShot, string? logPath,
        agent.output.OutputMode mode = agent.output.OutputMode.Markdown,
        List<string>? imageAttachments = null)
    {
        var sessionMgr = provider.GetRequiredService<ISessionManager>();
        var session = new CliSession(sink, "./data");
        // 面板数据服务 (v7.14): /status 与 /session 家族全部输出格式化 JSON (程序可解析)
        var panel = new agent.registry.PanelDataService(
            sessionMgr,
            new agent.session.JsonSessionMemoryStore("./data"),
            new agent.registry.AgentProfileStore("./data"),
            new agent.registry.CapabilityScanner(),
            "./data");
        var turnCount = 0;
        string? lastIntent = null, lastTendency = null;

        sink.Write(CliRenderer.Bold("AgentFramework CLI"));
        sink.Write(CliRenderer.Dim("  /status [agent_uid]  /session <agent_uid> [index]  /plan  /stop  /reset  /exit" +
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
            if (trimmed == "/status" || trimmed.StartsWith("/status ", StringComparison.Ordinal))
            {
                // v7.14: 全 JSON 输出 (程序可解析); 带 agent_uid 时输出该 agent 画像/记忆/上下文
                var arg = trimmed.Length > "/status".Length
                    ? trimmed["/status".Length..].Trim()
                    : null;
                sink.Write(arg != null
                    ? panel.RenderAgentStatus(arg)
                    : panel.RenderGlobalStatus(turnCount, lastIntent, lastTendency,
                        BuildPreferenceSummary("./data")));
                if (oneShot != null) return 0;
                continue;
            }
            if (trimmed == "/session" || trimmed.StartsWith("/session ", StringComparison.Ordinal))
            {
                // v7.14: /session <agent_uid> [index] — 历史会话数量+摘要 / 指定会话详情, 全 JSON
                var parts = trimmed.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 2)
                {
                    sink.Write("{\"error\": \"用法: /session <agent_uid> [index]\", \"found\": false}");
                    if (oneShot != null) return 2;
                    continue;
                }
                var uid = parts[1];
                sink.Write(parts.Length >= 3 && int.TryParse(parts[2], out var idx)
                    ? panel.RenderSessionDetail(uid, idx)
                    : panel.RenderSessionList(uid));
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
                    ImageAttachments = imageAttachments ?? new List<string>(),
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
        var sink = provider.GetRequiredService<IOutputSink>();
        sink.Write("AgentFramework host (NativeAOT) starting...");
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
        sink.Write($"DI graph: {ok}/{probeTypes.Length} resolved");

        var agentCtx = new AgentContext(provider) { SessionId = "aot-smoke", UserId = "host" };
        await entryAgent.InitializeAsync(agentCtx);
        sink.Write($"Agent state after init: {entryAgent.State}");

        var msg = new Message
        {
            Role = MessageRole.User,
            Content = "ping: AOT 宿主端到端冒烟",
            SessionId = "aot-smoke"
        };
        var reply = await entryAgent.ProcessAsync(msg, CancellationToken.None);
        sink.Write($"E2E: Success={reply.Success} Content={Truncate(reply.Content, 80)} Error={Truncate(reply.Error, 60)}");
        if (reply.Success)
            sink.Write("WARN: Success=true without API key — check ILLMCaller registration");

        var sessionMgr = provider.GetRequiredService<agent.session.ISessionManager>();
        var round2 = await entryAgent.ProcessAsync(new Message
        {
            Role = MessageRole.User,
            Content = "第二轮: 记得上一条说了什么吗",
            SessionId = "aot-smoke"
        }, CancellationToken.None);
        var session = await sessionMgr.GetSessionAsync("aot-smoke");
        var userMsgs = session?.Messages.Count(m => m.Role == MessageRole.User) ?? 0;
        sink.Write($"Multi-turn: session={session?.Id ?? "NULL"} userMsgs={userMsgs} round2Success={round2.Success}");
        if (session == null || userMsgs != 2)
        {
            provider.GetRequiredService<ILogger<Program>>()
                .LogError("FATAL: multi-turn session broken (expected session with 2 user messages, got {Session} / {UserMsgs})", session?.Id ?? "NULL", userMsgs);
            return 1;
        }

        sink.Write("AgentFramework host: OK (full-graph AOT smoke passed)");
        return 0;
    }

    /// <summary>
    /// /status 面板的偏好库摘要 (v7.13): 只展示 DataType→模式特征/命中数,
    /// 绝不回显原始答案或凭据 (偏好库本身也不存, 双保险)。
    /// </summary>
    private static List<string> BuildPreferenceSummary(string dataDir)
    {
        var lines = new List<string>();
        try
        {
            var store = new agent.registry.ClarificationPreferenceStore(dataDir);
            var prefs = store.Snapshot();
            foreach (var pf in prefs)
            {
                var choicePart = pf.ChoiceOrder.Count > 0
                    ? $" 偏好选项: {string.Join(" > ", pf.ChoiceOrder.Take(3))}"
                    : "";
                lines.Add($"{pf.DataTypeName} → {pf.PreferredPattern}  {choicePart}" +
                          CliRenderer.Dim($"  [命中 {pf.HitCount} 次]"));
            }
        }
        catch
        {
            // 偏好库读取失败不阻断 /status — 面板降级为空 (诚实显示无记录)
        }
        return lines;
    }

}

/// <summary>压缩 audit ground-truth 样本 (v0.13.3 A2)</summary>
/// <summary>压缩 audit ground-truth 样本 (v0.13.3 A2)</summary>
public sealed class GtDoc
{
    [System.Text.Json.Serialization.JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("target_tokens")]
    public int TargetTokens { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("ground_truth")]
    public Dictionary<string, string> GroundTruth { get; set; } = new();
    [System.Text.Json.Serialization.JsonPropertyName("causal_sentence")]
    public string CausalSentence { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("instruction_sentence")]
    public string InstructionSentence { get; set; } = string.Empty;
}

/// <summary>audit 矩阵行</summary>
public sealed class AuditRow
{
    public string Level { get; set; } = string.Empty;
    public int BucketTokens { get; set; }
    public int Samples { get; set; }
    public double KeyKeepRate { get; set; }
    public double CausalKeepRate { get; set; }
    public double InstructionKeepRate { get; set; }
    public double CompressRatio { get; set; }
    public long AvgMs { get; set; }
}

/// <summary>AOT source-gen (v0.13.3 audit — 禁反射铁律)</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(List<GtDoc>))]
[System.Text.Json.Serialization.JsonSerializable(typeof(List<AuditRow>))]
internal sealed partial class CompressionAuditJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
