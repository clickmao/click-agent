using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.session;

/// <summary>
/// 会话记忆 JSON 落盘 (v7.14): data/sessions/&lt;id&gt;_memory.json。
/// AOT 安全: source-gen (JsonSerializerContext), 不用反射序列化。
/// 存的是"记忆"不是凭据 — MemorySanitizer 已在写入端过滤, 落盘端不再存敏感值。
/// </summary>
public sealed class JsonSessionMemoryStore : ISessionMemoryStore
{
    private readonly string _dir;
    private readonly object _lock = new();

    public JsonSessionMemoryStore(string dataStoragePath = "data")
    {
        // 对齐 AgentRegistry.AgentDir 约定: data/sessions/
        _dir = Path.Combine(dataStoragePath, "sessions");
        Directory.CreateDirectory(_dir);
    }

    public SessionMemory? Load(string sessionId)
    {
        if (string.IsNullOrWhiteSpace(sessionId))
            return null;
        lock (_lock)
        {
            try
            {
                var path = PathFor(sessionId);
                if (!File.Exists(path))
                    return null;
                var dto = System.Text.Json.JsonSerializer.Deserialize(File.ReadAllText(path), SessionMemoryJsonContext.Default.SessionMemoryDto);
                if (dto == null)
                    return null;
                var memory = new SessionMemory(dto.MaxChars > 0 ? dto.MaxChars : SessionMemory.DefaultMaxChars);
                memory.Restore(dto.LongTermMemory ?? string.Empty, dto.ToGoal(), dto.EntryCount);
                return memory;
            }
            catch
            {
                // 损坏文件不阻塞启动 — 空记忆重建 (下次 Save 覆写)
                return null;
            }
        }
    }

    public void Save(string sessionId, SessionMemory memory)
    {
        if (string.IsNullOrWhiteSpace(sessionId) || memory == null)
            return;
        lock (_lock)
        {
            try
            {
                var dto = SessionMemoryDto.From(sessionId, memory);
                File.WriteAllText(PathFor(sessionId),
                    System.Text.Json.JsonSerializer.Serialize(dto, SessionMemoryJsonContext.Default.SessionMemoryDto));
            }
            catch
            {
                // 落盘失败不阻塞会话 — 内存态仍有效
            }
        }
    }

    /// <summary>枚举已落盘的会话 Id (从文件名反解; v7.14 面板 /session 用)</summary>
    public IReadOnlyList<string> EnumerateSessionIds()
    {
        var ids = new List<string>();
        string[] files;
        lock (_lock)
        {
            try
            {
                if (!Directory.Exists(_dir))
                    return ids;
                files = Directory.GetFiles(_dir, "*_memory.json");
            }
            catch
            {
                return ids;
            }
        }
        foreach (var f in files)
        {
            var name = Path.GetFileNameWithoutExtension(f);
            if (name.EndsWith("_memory", StringComparison.Ordinal))
                name = name[..^"_memory".Length];
            if (name.Length > 0)
                ids.Add(name);
        }
        return ids;
    }

    private string PathFor(string sessionId)
    {
        // 文件名消毒: sessionId 可能含路径分隔符
        var safe = string.Create(sessionId.Length, sessionId, (span, s) =>
        {
            for (int i = 0; i < s.Length; i++)
                span[i] = char.IsLetterOrDigit(s[i]) || s[i] == '-' || s[i] == '_' ? s[i] : '_';
        });
        return Path.Combine(_dir, $"{safe}_memory.json");
    }
}

/// <summary>落盘 DTO (与领域类型解耦, source-gen 友好)</summary>
public sealed class SessionMemoryDto
{
    public string SessionId { get; set; } = string.Empty;
    public int MaxChars { get; set; }
    public string LongTermMemory { get; set; } = string.Empty;
    public int EntryCount { get; set; }
    public string? GoalText { get; set; }
    public List<string>? KeyEntities { get; set; }
    public List<string>? Constraints { get; set; }
    public List<string>? Milestones { get; set; }

    public static SessionMemoryDto From(string sessionId, SessionMemory m)
    {
        var goal = m.Goal;
        return new SessionMemoryDto
        {
            SessionId = sessionId,
            MaxChars = m.MaxChars,
            LongTermMemory = m.LongTermMemory,
            EntryCount = m.EntryCount,
            GoalText = goal?.GoalText,
            KeyEntities = goal?.KeyEntities,
            Constraints = goal?.Constraints,
            Milestones = goal?.Milestones,
        };
    }

    public GoalProfile? ToGoal()
    {
        if (string.IsNullOrEmpty(GoalText))
            return null;
        return new GoalProfile
        {
            GoalText = GoalText,
            KeyEntities = KeyEntities ?? new List<string>(),
            Constraints = Constraints ?? new List<string>(),
            Milestones = Milestones ?? new List<string>(),
        };
    }
}

/// <summary>AOT source-gen JSON 上下文</summary>
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    PropertyNameCaseInsensitive = true,
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(SessionMemoryDto))]
internal sealed partial class SessionMemoryJsonContext : JsonSerializerContext;
