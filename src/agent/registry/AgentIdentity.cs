using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.registry;

/// <summary>
/// Agent 持久化身份 (v7.11): 主 agent 与所有 subagent 的稳定 UID + 从属关系。
/// UID 落盘跨进程复用 — 下轮预估/记忆/审计都按 UID 隔离, 不随进程重启漂移。
/// </summary>
public class AgentIdentity
{
    /// <summary>持久化 UID (注册时生成, 之后不变)</summary>
    public string Uid { get; set; } = string.Empty;

    /// <summary>显示名 ("main" = 主 agent)</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>父 agent UID (null = 主 agent)</summary>
    public string? ParentUid { get; set; }

    /// <summary>从属深度 (0 = 主 agent)</summary>
    public int Depth => ParentUid == null ? 0 : 1 + (Registry?.Get(ParentUid)?.Depth ?? 0);

    /// <summary>注册时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>注册表引用 (运行时注入, 不序列化)</summary>
    [JsonIgnore]
    public AgentRegistry? Registry { get; set; }
}

/// <summary>registry.json 持久化模型</summary>
public class AgentRegistryFile
{
    public List<AgentIdentity> Agents { get; set; } = new();
}

/// <summary>
/// Agent 注册表: UID 唯一性 + 从属关系持久化 ({DataStoragePath}/agent_registry.json)。
/// 同名 agent 重启后复用既有 UID (按 Name 键控), 保证预估文件跨会话命中。
/// </summary>
public class AgentRegistry
{
    private readonly object _lock = new();
    private readonly string _filePath;
    private readonly Dictionary<string, AgentIdentity> _byUid = new(StringComparer.Ordinal);
    private readonly Dictionary<string, AgentIdentity> _byName = new(StringComparer.Ordinal);

    public AgentRegistry(string dataStoragePath)
    {
        _filePath = Path.Combine(dataStoragePath, "agent_registry.json");
        Load();
    }

    /// <summary>主 agent 身份 (恒定 UID "main")</summary>
    public AgentIdentity Main { get; private set; } = new()
    {
        Uid = "main",
        Name = "main",
        ParentUid = null,
    };

    /// <summary>注册 (或复用) 一个 agent: 同名复用 UID, 新名生成 UID 并落盘</summary>
    public AgentIdentity Register(string name, string? parentUid)
    {
        lock (_lock)
        {
            if (_byName.TryGetValue(name, out var existing))
                return existing;

            var identity = new AgentIdentity
            {
                Uid = name == "main" ? "main" : "a" + Guid.NewGuid().ToString("N")[..10],
                Name = name,
                ParentUid = parentUid,
                Registry = this,
            };
            _byUid[identity.Uid] = identity;
            _byName[name] = identity;
            Save();
            return identity;
        }
    }

    public AgentIdentity? Get(string uid)
    {
        lock (_lock)
        {
            return _byUid.TryGetValue(uid, out var v) ? v : null;
        }
    }

    /// <summary>某 agent 的全部直接子 agent</summary>
    public List<AgentIdentity> ChildrenOf(string uid)
    {
        lock (_lock)
        {
            return _byUid.Values.Where(a => a.ParentUid == uid).ToList();
        }
    }

    /// <summary>agent 状态目录: {root}/agents/{uid}/ — 预估等按 agent 隔离的文件落这里</summary>
    public static string AgentDir(string dataStoragePath, string uid) =>
        Path.Combine(dataStoragePath, "agents", uid);

    private void Load()
    {
        try
        {
            if (!File.Exists(_filePath))
            {
                Main.Registry = this;
                _byUid[Main.Uid] = Main;
                _byName[Main.Name] = Main;
                return;
            }

            using var fs = File.OpenRead(_filePath);
            var file = JsonSerializer.Deserialize<AgentRegistryFile>(fs, RegistryJsonContext.Default.AgentRegistryFile);
            if (file == null)
                return;

            Main.Registry = this;
            _byUid[Main.Uid] = Main;
            _byName[Main.Name] = Main;
            foreach (var a in file.Agents)
            {
                a.Registry = this;
                _byUid[a.Uid] = a;
                _byName[a.Name] = a;
            }
        }
        catch
        {
            // 注册表损坏不应阻断启动 — 按"无历史"处理, 注册时重写
            Main.Registry = this;
            _byUid[Main.Uid] = Main;
            _byName[Main.Name] = Main;
        }
    }

    private void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(_filePath);
            if (dir != null)
                Directory.CreateDirectory(dir);

            var file = new AgentRegistryFile
            {
                Agents = _byUid.Values.Where(a => a.Uid != "main").ToList(),
            };
            using var fs = File.Create(_filePath);
            JsonSerializer.Serialize(fs, file, RegistryJsonContext.Default.AgentRegistryFile);
        }
        catch
        {
            // 落盘失败不阻断注册 — 内存身份仍有效, 下次注册重试
        }
    }
}

/// <summary>AOT source-gen: 注册表 + 预估共用 (禁反射序列化)</summary>
[JsonSourceGenerationOptions(WriteIndented = true)]
[JsonSerializable(typeof(AgentRegistryFile))]
[JsonSerializable(typeof(ForecastRecord))]
internal partial class RegistryJsonContext : JsonSerializerContext
{
}
