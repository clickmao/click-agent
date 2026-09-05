using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.userinteraction;

/// <summary>
/// 凭据/审批的本地持久化存储 —— 凭据只落本地加密目录权限文件, 绝不进日志/上下文。
/// </summary>
public static class PromptPersistence
{
    /// <summary>凭据文件路径: {dataDir}/credentials.json (用户主动提供的 Key 存这里, 下次启动复用)</summary>
    public static string CredentialsPath(string dataDir) =>
        Path.Combine(string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "credentials.json");

    /// <summary>审批策略缓存路径</summary>
    public static string ApprovalCachePath(string dataDir) =>
        Path.Combine(string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "approval_cache.json");

    public static Dictionary<string, string> LoadCredentials(string dataDir)
    {
        var path = CredentialsPath(dataDir);
        if (!File.Exists(path))
            return new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        try
        {
            var json = File.ReadAllText(path);
            var loaded = JsonSerializer.Deserialize(json, PromptJsonContext.Default.DictionaryStringString);
            return loaded is null
                ? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                : new Dictionary<string, string>(loaded, StringComparer.OrdinalIgnoreCase);
        }
        catch
        {
            // 凭据文件损坏 → 视为无凭据, 让问询流程重新要走 (绝不抛异常阻断启动)
            return new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        }
    }

    public static void SaveCredentials(string dataDir, Dictionary<string, string> credentials)
    {
        var path = CredentialsPath(dataDir);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        File.WriteAllText(path, JsonSerializer.Serialize(credentials, PromptJsonContext.Default.DictionaryStringString));

        // 尽力收紧文件权限 (Unix); Windows 上 ACL 收紧交给用户/部署脚本
        if (!OperatingSystem.IsWindows())
        {
            try
            {
                File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            }
            catch (PlatformNotSupportedException)
            {
            }
        }
    }

    /// <summary>审计日志: 每次问询/代答/自动批准都追加一行 (JSONL), 供事后追责</summary>
    public static void AppendAudit(string dataDir, PromptAuditEntry entry)
    {
        try
        {
            var path = Path.Combine(
                string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "prompt_audit.jsonl");
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);
            File.AppendAllText(path, JsonSerializer.Serialize(entry, PromptJsonContext.Default.PromptAuditEntry) + Environment.NewLine);
        }
        catch
        {
            // 审计失败不阻断主流程
        }
    }
}

/// <summary>
/// 控制台问询服务实现 —— 等待真实用户输入; subagent 发起的问题按权威模型路由。
/// 凭据类 (RealUserOnly) 永远阻塞等真实用户, 主 agent 绝不能代答;
/// 敏感操作类按托管级别 + Origin.Authority 决定: 自动批准 / 主 agent 代答 / 问真实用户。
/// </summary>
public sealed class ConsoleUserPromptService : IUserPromptService
{
    private readonly ILogger<ConsoleUserPromptService> _logger;
    private readonly string _dataDir;
    private readonly Dictionary<string, string> _credentials;

    public SupervisionLevel Supervision { get; }

    /// <summary>agent 间问询静默 (v7.13, 用户钦定): 开启后 MainAgentAllowed 的问询不打印到控制台,
    /// 由主 agent 静默代答并审计 — 面向 subagent 编排场景, 用户界面零打扰。凭据类仍强制问真人。</summary>
    public bool SilentInterAgent { get; set; }

    public ConsoleUserPromptService(
        ILogger<ConsoleUserPromptService> logger,
        string dataDir,
        SupervisionLevel supervision)
    {
        _logger = logger;
        _dataDir = dataDir;
        Supervision = supervision;
        _credentials = PromptPersistence.LoadCredentials(dataDir);
    }

    /// <summary>已保存的凭据 (供插件启动时快速读取, 避免重复问询)</summary>
    public IReadOnlyDictionary<string, string> Credentials => _credentials;

    // ── IUserPromptService ──

    public Task<Dictionary<string, string>?> RequestCredentialsAsync(
        CredentialRequest request, CancellationToken ct = default)
    {
        // 权威检查: 凭据永远 RealUserOnly —— 主 agent 代答在这里被物理阻断。
        // subagent 发起的凭据问询也直接问真实用户 (这正是"回答者可能是主 agent 而非真实用户"
        // 陷阱的防御: 宁可多问真人, 不可让 agent 编造 Key)。
        if (request.Origin.Authority != AnswerAuthority.RealUserOnly)
            request.Origin.Authority = AnswerAuthority.RealUserOnly;

        // v7.13 静默代答: agent 间问询 (非敏感项) 不打扰用户 — 主 agent 给占位确认并审计。
        // 含敏感项 (Sensitive) 时静默不可用, 必须真人。
        if (SilentInterAgent && !request.Items.Any(it => it.Sensitive))
        {
            var silentAnswers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var item in request.Items)
                silentAnswers[item.Key] = string.Empty; // 空串=主 agent 无依据, 不编造值 (走缺参降级, 不伪造)
            PromptPersistence.AppendAudit(_dataDir, new PromptAuditEntry
            {
                Kind = $"credential:{request.Kind}",
                Service = request.ServiceName,
                AnsweredBy = "MainAgentSilent",
                Approved = true,
                Detail = $"agent 间静默问询: {silentAnswers.Count} 项置空 (不编造, 走降级)",
            });
            return Task.FromResult<Dictionary<string, string>?>(silentAnswers);
        }

        Console.WriteLine();
        Console.WriteLine("┌── 需要你的输入 ──────────────────────────────");
        Console.WriteLine($"│ 服务: {request.ServiceName}  [类型: {request.Kind}]");
        Console.WriteLine($"│ 作用: {request.Purpose}");
        if (!string.IsNullOrEmpty(request.FallbackNote))
            Console.WriteLine($"│ 不提供时: {request.FallbackNote}");

        var answers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var item in request.Items)
        {
            Console.Write($"│ {item.DisplayName}" +
                (item.Required ? " (必填)" : " (可留空跳过)") + ": ");
            if (item.Sensitive)
            {
                var value = ReadMasked();
                if (string.IsNullOrWhiteSpace(value))
                {
                    if (item.Required)
                    {
                        Console.WriteLine("│ 已取消 —— 走降级路径");
                        PromptPersistence.AppendAudit(_dataDir, new PromptAuditEntry
                        {
                            Kind = $"credential:{request.Kind}",
                            Service = request.ServiceName,
                            AnsweredBy = "RealUser",
                            Approved = false,
                            Detail = "用户未提供必填凭据",
                        });
                        return Task.FromResult<Dictionary<string, string>?>(null);
                    }
                    continue;
                }
                answers[item.Key] = value.Trim();
            }
            else
            {
                var input = Console.ReadLine();
                if (string.IsNullOrWhiteSpace(input))
                {
                    if (item.Required)
                        return Task.FromResult<Dictionary<string, string>?>(null);
                    continue;
                }
                answers[item.Key] = input.Trim();
            }
        }

        Console.WriteLine("└──────────────────────────────────────────────");
        Console.WriteLine();

        // 持久化到本地凭据文件, 下次启动不再重复问
        foreach (var kv in answers)
            _credentials[$"{request.ServiceName}:{kv.Key}"] = kv.Value;
        PromptPersistence.SaveCredentials(_dataDir, _credentials);

        PromptPersistence.AppendAudit(_dataDir, new PromptAuditEntry
        {
            Kind = $"credential:{request.Kind}",
            Service = request.ServiceName,
            AnsweredBy = "RealUser",
            Approved = true,
            Detail = $"{answers.Count} 项已提供并保存到 credentials.json",
        });

        return Task.FromResult<Dictionary<string, string>?>(answers);
    }

    public Task<OperationApprovalResult> RequestOperationApprovalAsync(
        SensitiveOperationRequest request, CancellationToken ct = default)
    {
        // 路由决策:
        // 1) Full 托管 + MainAgentAllowed → 自动批准
        // 2) MainAgentAllowed + 主 agent 自己发起 (depth=0) 且操作策略允许 → 主 agent 代答
        // 3) 其余 (RealUserOnly / subagent 深度超限 / Strict 模式) → 问真实用户
        var decision = DecideRoute(request);

        switch (decision.answeredBy)
        {
            case PromptAnswerSource.AutoApproved:
                _logger.LogInformation(
                    "敏感操作自动批准 (Full 托管): {Summary} by {Initiator}",
                    request.Summary, request.Initiator);
                Audit(request, decision.answeredBy, true);
                return Task.FromResult(new OperationApprovalResult
                {
                    Approved = true,
                    AnsweredBy = decision.answeredBy,
                    Reason = decision.reason,
                });

            case PromptAnswerSource.MainAgentDelegate:
                _logger.LogInformation(
                    "敏感操作由主 agent 代答批准: {Summary} (发起方: {Agent}, 策略: {Policy})",
                    request.Summary, request.Origin.AskedByAgentId, decision.reason);
                Audit(request, decision.answeredBy, true);
                return Task.FromResult(new OperationApprovalResult
                {
                    Approved = true,
                    AnsweredBy = decision.answeredBy,
                    Reason = decision.reason,
                });

            default:
                return Task.FromResult(PromptRealUser(request));
        }
    }

    // ── 路由决策引擎 ──

    private (PromptAnswerSource answeredBy, string reason) DecideRoute(
        SensitiveOperationRequest request)
    {
        // 规则 1: RealUserOnly 权威 → 必须问真人 (不可逆操作如删除)
        if (request.Origin.Authority == AnswerAuthority.RealUserOnly)
            return (PromptAnswerSource.RealUser, "权威模型要求真实用户审批");

        // 规则 2: subagent 深度超限 → 升级真人 (防 agent 层级间代答闭环)
        if (request.Origin.AskingDepth > PromptOrigin.MaxDelegationDepth)
            return (PromptAnswerSource.RealUser,
                $"嵌套深度 {request.Origin.AskingDepth} 超过代答上限 {PromptOrigin.MaxDelegationDepth}");

        // 规则 3: Full 托管 → 自动批准 (不可逆操作仍问真人)
        if (Supervision == SupervisionLevel.Full &&
            !IsIrreversible(request.Kind))
            return (PromptAnswerSource.AutoApproved, "Full 托管策略");

        // 规则 4: Standard 托管下的低风险操作 → 主 agent 代答
        if (Supervision == SupervisionLevel.Standard && IsLowRisk(request.Kind))
            return (PromptAnswerSource.MainAgentDelegate, $"Standard 托管: {request.Kind} 属低风险");

        // 其余 → 真实用户
        return (PromptAnswerSource.RealUser, $"默认策略 ({Supervision})");
    }

    /// <summary>不可逆操作 —— 任何托管级别都必须真人批准</summary>
    private static bool IsIrreversible(SensitiveOperationKind kind) =>
        kind == SensitiveOperationKind.DeleteFile ||
        kind == SensitiveOperationKind.SystemConfig;

    /// <summary>低风险操作 —— Standard 模式下主 agent 可代答</summary>
    private static bool IsLowRisk(SensitiveOperationKind kind) =>
        kind == SensitiveOperationKind.CreateFile ||
        kind == SensitiveOperationKind.ModifyFile;

    private OperationApprovalResult PromptRealUser(SensitiveOperationRequest request)
    {
        Console.WriteLine();
        Console.WriteLine("┌── 需要你的批准 ──────────────────────────────");
        Console.WriteLine($"│ 操作类型: {request.Kind}  [发起方: {request.Initiator}]");
        if (request.Origin.AskedByAgentId != "main")
            Console.WriteLine($"│ 注意: 此请求来自 subagent '{request.Origin.AskedByAgentId}' (深度 {request.Origin.AskingDepth})");
        Console.WriteLine($"│ 摘要: {request.Summary}");
        Console.WriteLine($"│ 细节: {request.Details}");
        Console.Write("│ 批准? [y/N]: ");

        var input = Console.ReadLine();
        var approved = input is not null &&
            (input.Trim().Equals("y", StringComparison.OrdinalIgnoreCase) ||
             input.Trim().Equals("yes", StringComparison.OrdinalIgnoreCase));

        Console.WriteLine("└──────────────────────────────────────────────");
        Console.WriteLine();

        Audit(request, PromptAnswerSource.RealUser, approved);
        return new OperationApprovalResult
        {
            Approved = approved,
            AnsweredBy = PromptAnswerSource.RealUser,
            Reason = approved ? "用户批准" : "用户拒绝",
        };
    }

    private void Audit(SensitiveOperationRequest request, PromptAnswerSource by, bool approved) =>
        PromptPersistence.AppendAudit(_dataDir, new PromptAuditEntry
        {
            Kind = $"operation:{request.Kind}",
            Service = request.Initiator,
            AnsweredBy = by.ToString(),
            Approved = approved,
            Detail = request.Summary,
        });

    // ── 敏感输入 (不回显) ──

    private static string ReadMasked()
    {
        // 非交互环境 (管道/CI/无 TTY) 无法 ReadKey — 诚实返回空, 走调用方的跳过/降级路径
        if (Console.IsInputRedirected || !Environment.UserInteractive)
            return string.Empty;
        var buf = new System.Text.StringBuilder();
        while (true)
        {
            var key = Console.ReadKey(intercept: true);
            if (key.Key == ConsoleKey.Enter)
            {
                Console.WriteLine();
                return buf.ToString();
            }
            if (key.Key == ConsoleKey.Backspace)
            {
                if (buf.Length > 0)
                {
                    buf.Length--;
                    Console.Write("\b \b");
                }
                continue;
            }
            if (!char.IsControl(key.KeyChar))
            {
                buf.Append(key.KeyChar);
                Console.Write('*');
            }
        }
    }
}
