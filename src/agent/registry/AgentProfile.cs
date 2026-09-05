namespace agent.registry;

/// <summary>
/// Agent 画像 (v7.14): 该 agent 处理任务时的倾向 — 决策风格/工具偏好/输出风格/任务类别胜任度。
/// 与 TendencyProfile (用户级) 互补: 用户画像调"用户要什么", AgentProfile 调"这个 agent 怎么干"。
/// 双通道: 静态声明 (注册时定, 如"代码类任务用保守策略") + 动态学习 (执行结果回写胜率)。
/// 铁律对齐: 画像只存模式与统计, 绝不存凭据/用户输入原值。
/// </summary>
public sealed class AgentProfile
{
    /// <summary>所属 agent (AgentIdentity.Uid)</summary>
    public string AgentUid { get; set; } = string.Empty;

    /// <summary>决策风格: conservative(保守求稳) / balanced(默认) / aggressive(激进求快)</summary>
    public string DecisionStyle { get; set; } = "balanced";

    /// <summary>任务类别胜任度 (intent → 成功次数) — 动态学习主通道</summary>
    public Dictionary<string, int> TaskSuccess { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>任务类别失败次数 (intent → 失败次数)</summary>
    public Dictionary<string, int> TaskFailure { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>工具/能力偏好 (toolName → 使用次数) — 越用越顺手的能力排前</summary>
    public Dictionary<string, int> ToolAffinity { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>输出风格: markdown / plain / json (该 agent 默认产出形态)</summary>
    public string OutputStyle { get; set; } = "markdown";

    /// <summary>是否偏好先澄清再执行 (低置信任务先问而非猜, 与 EvidenceGate 联动)</summary>
    public bool PreferClarifyFirst { get; set; } = true;

    /// <summary>单任务最大重试次数 (conservative=2, balanced=1, aggressive=0 之类按风格推导)</summary>
    public int MaxRetries { get; set; } = 1;

    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>记录一次任务执行结果 (动态学习入口; 线程安全)</summary>
    private readonly object _lock = new();

    public void RecordTaskOutcome(string intent, bool success, string? toolUsed = null)
    {
        if (string.IsNullOrWhiteSpace(intent))
            return;
        lock (_lock)
        {
            var dict = success ? TaskSuccess : TaskFailure;
            dict[intent] = dict.TryGetValue(intent, out var n) ? n + 1 : 1;
            if (!string.IsNullOrWhiteSpace(toolUsed))
                ToolAffinity[toolUsed] = ToolAffinity.TryGetValue(toolUsed, out var t) ? t + 1 : 1;
            UpdatedAt = DateTime.UtcNow;
        }
    }

    /// <summary>某任务类别的胜任率 (无样本返回 null, 由调用方决定兜底)</summary>
    public double? SuccessRateFor(string intent)
    {
        lock (_lock)
        {
            var s = TaskSuccess.TryGetValue(intent, out var su) ? su : 0;
            var f = TaskFailure.TryGetValue(intent, out var fa) ? fa : 0;
            return s + f == 0 ? null : (double)s / (s + f);
        }
    }

    /// <summary>渲染注入 prompt 的画像块 (④核心输出: 让 LLM 知道自己该用什么风格干)</summary>
    public string RenderForPrompt()
    {
        lock (_lock)
        {
            var sb = new System.Text.StringBuilder();
            sb.Append("【Agent 画像】风格=").Append(DecisionStyle)
              .Append(", 输出=").Append(OutputStyle)
              .Append(", 重试=").Append(MaxRetries)
              .Append(", 先澄清=").Append(PreferClarifyFirst ? "是" : "否");
            // 擅长领域: 胜任率最高的前 3 类 (样本≥1)
            var best = TaskSuccess.Keys
                .Where(k => TaskSuccess[k] + (TaskFailure.TryGetValue(k, out var f) ? f : 0) >= 1)
                .Select(k => (k, Rate: SuccessRateFor(k) ?? 0))
                .OrderByDescending(x => x.Rate)
                .Take(3)
                .ToList();
            if (best.Count > 0)
                sb.Append(", 擅长=").Append(string.Join("/", best.Select(b => b.k)));
            // 顺手工具: 使用次数前 3
            var tools = ToolAffinity.OrderByDescending(kv => kv.Value).Take(3).ToList();
            if (tools.Count > 0)
                sb.Append(", 常用工具=").Append(string.Join("/", tools.Select(t => t.Key)));
            return sb.ToString();
        }
    }
}

/// <summary>
/// Agent 画像注册表: uid → 画像; 落盘 {DataStoragePath}/agent_profiles.json (随 AgentRegistry 同目录)。
/// </summary>
public sealed class AgentProfileStore
{
    private readonly string _filePath;
    private readonly object _lock = new();
    private Dictionary<string, AgentProfile> _profiles = new(StringComparer.Ordinal);

    public AgentProfileStore(string dataStoragePath = "data")
    {
        _filePath = Path.Combine(dataStoragePath, "agent_profiles.json");
        Directory.CreateDirectory(dataStoragePath); // 对齐 JsonSessionMemoryStore: 目录不静默失败
        Load();
    }

    public AgentProfile GetOrCreate(string agentUid)
    {
        lock (_lock)
        {
            if (!_profiles.TryGetValue(agentUid, out var p))
                _profiles[agentUid] = p = new AgentProfile { AgentUid = agentUid };
            return p;
        }
    }

    public void Save()
    {
        lock (_lock)
        {
            try
            {
                File.WriteAllText(_filePath, System.Text.Json.JsonSerializer.Serialize(
                    new AgentProfileFile { Profiles = _profiles.Values.ToList() },
                    AgentProfileJsonContext.Default.AgentProfileFile));
            }
            catch
            {
                // 落盘失败不阻塞 — 内存态仍有效
            }
        }
    }

    private void Load()
    {
        try
        {
            if (!File.Exists(_filePath))
                return;
            var file = System.Text.Json.JsonSerializer.Deserialize(
                File.ReadAllText(_filePath), AgentProfileJsonContext.Default.AgentProfileFile);
            if (file?.Profiles == null)
                return;
            _profiles = file.Profiles
                .Where(p => !string.IsNullOrEmpty(p.AgentUid))
                .ToDictionary(p => p.AgentUid, StringComparer.Ordinal);
        }
        catch
        {
            // 损坏文件 → 空库重建
        }
    }
}

public sealed class AgentProfileFile
{
    public List<AgentProfile> Profiles { get; set; } = new();
}

[System.Text.Json.Serialization.JsonSerializable(typeof(AgentProfileFile))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(WriteIndented = true, PropertyNameCaseInsensitive = true)]
internal sealed partial class AgentProfileJsonContext : System.Text.Json.Serialization.JsonSerializerContext;
