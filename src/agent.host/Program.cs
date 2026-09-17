using agent.contextgradient;
using System.Text;
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
///   agenthost --session-id cli-x7 → 显式指定会话 Id (D7b 跨进程续跑/真机复现; 默认每次随机)
///   agenthost --smoke         → AOT 冒烟 (原 Program 行为保留)
/// 返回内容经区段插件处理 (html 标记/代码审查) 后输出; markdown 渲染重点。
/// </summary>
internal class Program
{
    private static string Truncate(string? s, int n) => string.IsNullOrEmpty(s) ? string.Empty : s.Length <= n ? s : s[..n] + "...";

    /// <summary>R371: 运行级验证结论上屏 (闸门未开/未运行时不显示 — 不假装验证过)。</summary>
    private static string RunNote(agent.registry.PythonArtifactReport r)
        => !r.Ran ? string.Empty
           : r.RunTimedOut ? $" · run 超时({r.RunElapsedMs}ms)"
           : $" · run exit={r.RunExitCode} ({r.RunElapsedMs}ms)";

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
        string? roleId = null;   // R363 (用户钦定): --role <file.rbin> 可空 — 缺省无角色 (行为不变); 非明文单文件
        string? sessionIdOverride = null; // R384 (D7b): --session-id <id> 显式指定会话 Id (跨进程续跑/真机复现需要)
        string? formalEvalPath = null; // v0.23.0 exp12 S3/S4: --formal-eval <cases.jsonl> 判定层题集入口 (纯本地零 token)
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--log" && i + 1 < args.Length)
                logPath = args[++i];
            else if (args[i] == "-q" && i + 1 < args.Length)
                oneShot = args[++i];
            else if (args[i] == "--session-id" && i + 1 < args.Length)
                sessionIdOverride = args[++i];
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
            // R363 (用户钦定): --role <file.rbin> 挂载外挂角色 (可空 — 不传即无角色; 非明文单文件)
            else if (args[i] == "--role" && i + 1 < args.Length)
                roleId = args[++i];
            // v0.23.0 exp12 S3/S4 (用户钦定: DCR 必须可证伪): --formal-eval <cases.jsonl> —— 真实装配判定层逐条裁决
            else if (args[i] == "--formal-eval" && i + 1 < args.Length)
                formalEvalPath = args[++i];
        }

        // R408 (用户钦定: 直接改用 llama.cpp): --embed 走 llama-server --embeddings。
        // 旧路径 (RemoteEmbedder / unix-socket daemon) 在 daemon 离线时**抛未处理异常 ⇒ core dump (exit 134)**,
        // 且注释声称的「hash 兜底语义」在实现中并不存在 (本轮 R408 实测) ⇒ 改为显式失败 + 明确退出码。
        if (embedText is not null)
        {
            var opts = agent.llamacpp.LlamaCppEmbedderOptions.FromEnvironment();
            await using var embedder = new agent.llamacpp.LlamaCppTextEmbedder(opts);
            if (!embedder.IsAvailable)
            {
                Console.Error.WriteLine($"embed: provider_unavailable (模型 {opts.ModelPath} 或 llama-server 不可解析;" +
                                        " 设 AGENTFRAMEWORK_LLAMA_BIN / AGENTFRAMEWORK_BGE_MODEL)");
                return 4;
            }
            try
            {
                var vec = await embedder.EmbedAsync(embedText, CancellationToken.None);
                Console.WriteLine("[" + string.Join(",", vec.Select(v => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture))) + "]");
                return 0;
            }
            catch (agent.llamacpp.LlamaCppException ex)
            {
                Console.Error.WriteLine($"embed: {ex.Code}: {ex.Message}");
                return 4;
            }
        }

        // ── v0.23.0 exp12 · S3/S4（用户钦定：决策合规率必须可证伪）─────────────────────────────
        // --formal-eval <cases.jsonl>：判定题集逐条过**真实装配的判定层**（契约层 → 四态处置 → 共享源内核），
        // 零 LLM / 零 daemon / 零 shell；输出 JSONL 交 scripts/kpi_dcr.py 与独立 oracle(z3) 标签对账。
        if (formalEvalPath is not null)
            return agent.host.FormalEvalCommand.Run(formalEvalPath, Console.Out, Console.Error);
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

// v0.30.0 R408 (用户钦定: 本地 GGUF 引擎整线退役 → llama.cpp 进程化接入):
// --llamacpp — 真实 llama-server 进程做一次生成/嵌入并输出读数 JSON (零 P/Invoke; 进程+loopback HTTP; 跨平台)。
// 依据: 进程内 native interop 在 NativeAOT 下 SIGSEGV (R90 实测); --expect-ids 逐位对账, 不一致 exit 3。
if (args.Length >= 1 && args[0] == "--llamacpp")
{
    return await LlamaCppCommand.RunAsync(args, Console.Out, Console.Error);
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

        // R375 (exp2 P0-1): 前端事件出站枢纽 — 进程内唯一出站口 (ask 信封送达面)。
        services.AddSingleton<agent.frontendapi.FrontendEventHub>();
        // v0.22.0 exp9 D5: 计划事件出站 (plan.created/plan.node/plan.finished) —
        // 核心层发 IPlanEventSink, 宿主包前端信封; 无前端连接时 hub 只计数丢弃 (不静默崩)。
        services.AddSingleton<agent.intent.IPlanEventSink>(sp =>
            new agent.host.PlanEventEnvelopeSink(sp.GetRequiredService<agent.frontendapi.FrontendEventHub>()));
        var frontendApiRequested = args.Length >= 2 && args[0] == "--frontend-api";
        if (frontendApiRequested)
        {
            // R375: frontend 模式下问询必须走**前端**通道 —— 后注册覆盖 AddAgentFramework 内的 Console 实现
            // (DI 单服务解析取最后注册者)。不覆盖 = ask 事件无人消费, 兜底行为打到服务端控制台 (接线缺口)。
            services.AddSingleton<agent.userinteraction.IUserPromptService>(sp =>
                new agent.frontendapi.FrontendPromptService(
                    sp.GetRequiredService<agent.frontendapi.FrontendEventHub>().EmitAsync));
        }

// v0.19 P1 后半 (R355): --frontend-api <port> — FrontendApi 统一接口独立挂载。
// 与 REPL/one-shot 并列的第三种运行形态: 常驻服务, 外部前端经 TCP 行 JSON 信封消费完整 agent 管线。
        await using var provider = services.BuildServiceProvider();
        // R363: CLI --role <file.rbin> → env 注入路径 (V2 内部用 data/master.key 解密 — 持久密钥层级)
        if (!string.IsNullOrWhiteSpace(roleId))
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ROLE_FILE", Path.GetFullPath(roleId));
        var entryAgent = provider.GetRequiredService<IAgent>();

// R515: --orchestrate <计划文件> — 长任务编排器 (逐节点真实执行, 每节点独立步数预算)。
// 与 --frontend-api / REPL 并列的第四种形态: 无人值守的**多节点长任务**驱动。
if (args.Length >= 2 && args[0] == "--orchestrate")
    return await OrchestrateCommand.RunAsync(provider, entryAgent, args[1..], Console.Out, Console.Error);

if (args.Length >= 2 && args[0] == "--frontend-api")
{
    if (!int.TryParse(args[1], out var apiPort) || apiPort is < 1 or > 65535)
    {
        Console.Error.WriteLine("frontend-api: 端口非法");
        return 4;
    }
    RedirectDaemonLogIfConfigured();
    var frontendCtx = new AgentContext(provider)
    {
        // R509: 会话 id 可注入 (默认 frontend-main 保持兼容) — 真机探针/多客户端需要独立会话,
        // 否则共享会话会把上一轮的续跑/待答复状态带进本次任务 (实测: 事件面全绿但回复是陈旧续跑)。
        SessionId = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_FRONTEND_SESSION") ?? "frontend-main",
        UserId = "frontend-user",
    };
    await entryAgent.InitializeAsync(frontendCtx);

    // R465: 本地通道预热 (env 开关, 默认关 ⇒ 现有行为逐位不变)。
    // 目的: 把长驻 llama-server 的**权重装载**从「首次门控轮」挪到宿主启动期 ——
    // 冷启动装载是门控轮墙钟的主项 (R464 实测 40~100 s/门控轮), 用户不该为它等待。
    if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LOCAL_WARMUP") == "1")
    {
        var localPort = provider.GetService<agent.modelqueue.ILocalGenerationPort>();
        if (localPort is not null && localPort.IsAvailable)
        {
            var warmSw = System.Diagnostics.Stopwatch.StartNew();
            await localPort.WarmupAsync();
            warmSw.Stop();
            var concrete = localPort as agent.llamacpp.LlamaCppLocalGenerationPort;
            agent.config.AgentTelemetry.Emit("local_channel_warmup", "Program",
                ("ok", localPort.WarmupOk ? "true" : "false"),
                ("warm_ms", localPort.WarmupOk ? (concrete?.WarmupMs ?? warmSw.ElapsedMilliseconds).ToString() : "-1"),
                ("wall_ms", warmSw.ElapsedMilliseconds.ToString()),
                ("error", concrete?.WarmupError ?? ""));
        }
    }

    // v0.21.1 (R367): 版本跟随发布线 (原硬编码 "0.20.5", 与 v0.21.0 实际版本漂移 — 前端无从得知真实版本)
    var metaJson = "{\"version\":\"0.21.0\",\"contract\":1,\"domains\":[\"chat\",\"meta\",\"state\",\"plan\"]}";
    // R375 (exp2 P0-1): 挂接事件出站 + ask 应答面 (hub 为唯一出站口; 未挂接时事件丢弃并计数)
    var eventHub = provider.GetRequiredService<agent.frontendapi.FrontendEventHub>();
    if (provider.GetRequiredService<agent.userinteraction.IUserPromptService>() is agent.frontendapi.IAskReplySink askSink)
        eventHub.AttachAsk(askSink);
    // R510: 审批应答面同源挂接 (同一 PromptService; 未挂接 ⇒ approval.respond 回 channel_unavailable, 不伪造批准)
    if (provider.GetRequiredService<agent.userinteraction.IUserPromptService>() is agent.frontendapi.IApprovalReplySink approvalSink)
        eventHub.AttachApproval(approvalSink);
    // R509: 任务生命周期登记 (chat.send → task.started/completed 事件 + state.snapshot.tasks)
    var taskRegistry = new agent.frontendapi.FrontendTaskRegistry();
    var chatRouter = new agent.frontendapi.FrontendApiChatRouter(entryAgent,
        askSink: eventHub.AskSink, tasks: taskRegistry, hub: eventHub, approvalSink: eventHub.ApprovalSink);
    var v2 = entryAgent as IndustrialAgentV2;
    var server = new agent.frontendapi.FrontendApiServer(async (api, payloadJson) =>
    {
        // chat 域 (异步直通 V2)
        var chatResp = await chatRouter.HandleAsync(api, payloadJson);
        if (chatResp is not null) return chatResp;
        // 状态域: R356-c 真实快照 (V2.GetSnapshot 实时聚合 — 手写序列化零反射)
        if (api == "state.snapshot")
        {
            if (v2 is null)
                return "{\"error\":\"snapshot_unavailable\"}";
            var snap = v2.GetSnapshot();
            using var ms = new MemoryStream();
            using (var w = new Utf8JsonWriter(ms))
            {
                w.WriteStartObject();
                w.WriteString("session_id", snap.SessionId);
                w.WriteStartObject("model");
                w.WriteString("id", snap.ModelId ?? "(none)");
                w.WriteString("provider", snap.ModelProvider ?? "(none)");
                w.WriteString("selection", snap.SelectionBasis);
                w.WriteString("mode", snap.SelectionMode);
                w.WriteNumber("switches", snap.ModelSwitches);
                w.WriteEndObject();
                w.WriteNumber("uptime_ms", snap.UptimeMs);
                w.WriteBoolean("ready", true);
                // R509: 任务面 (断线重连可读在飞/最近任务; 空数组 = 无任务, 非缺字段)
                w.WritePropertyName("tasks");
                w.WriteRawValue(taskRegistry.SnapshotJson(), skipInputValidation: true);
                w.WriteEndObject();
            }
            return Encoding.UTF8.GetString(ms.ToArray());
        }
        // 元域 (同步)
        return api switch
        {
            "state.hello" => "{\"hello\":true}",
            "meta.info" => metaJson,
            _ => null,
        };
    }, msg => Console.WriteLine($"[frontend-api] {msg}"), apiPort);

    try
    {
        // R375: 上电前挂接出站面 — ask 信封经 hub → 所有在线客户端 (挂接前的事件计入 Dropped, 不伪装送达)
    eventHub.AttachServer(line => server.EmitEventAsync(line));
    server.Start();
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"frontend-api: 启动失败 — {ex.Message}");
        return 4;
    }
    Console.WriteLine($"frontend-api: READY :{apiPort} (chat.send 直通 V2 管线; Ctrl+C 退出)");
    Console.WriteLine($"frontend-api: AUTH token = {server.TokenHex} (客户端首行 {{\"type\":\"auth\",\"token\":\"...\"}}; env AGENTFRAMEWORK_FRONTEND_TOKEN 可注入)");
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
            return await RunCliAsync(provider, entryAgent, sink, oneShot, logPath, outputMode, imageArgs, sessionIdOverride);
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
        List<string>? imageAttachments = null, string? sessionId = null)
    {
        var sessionMgr = provider.GetRequiredService<ISessionManager>();
        var session = new CliSession(sink, "./data", sessionId: sessionId);
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

                var pyLedger = provider.GetService<agent.registry.PythonArtifactLedger>();
                var pyVersion0 = pyLedger?.Version ?? 0;
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
                        sink.Step(step, "返回区段标记", string.Join(", ", codeLangs));
                    }
                }

                // 步骤明细④ (R368): PY 段机器校验台账 — 落盘 + py_compile 真实结论。
                // 旧文案 "(已路由插件)" 只是显示, 无法证明 python 产出可运行; 这里读真台账。
                var pyReports = pyLedger?.Snapshot().Skip((int)pyVersion0).ToList();
                if (pyReports is { Count: > 0 })
                {
                    var pass = pyReports.Count(r => r.CompileValid);
                    step++;
                    session.RecordStep($"PY 机器校验: {pass}/{pyReports.Count} 通过");
                    sink.Step(step, "PY 落盘 + py_compile", $"{pass}/{pyReports.Count} 通过");
                    foreach (var r in pyReports)
                        sink.Write(CliRenderer.Dim(r.CompileValid
                            ? $"    · {r.Path} ({r.Bytes}B) ✓ py_compile" + RunNote(r)
                            : $"    · {r.Path} ({r.Bytes}B) ✗ exit={r.ExitCode} {Truncate(r.Detail, 120)}"));
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
