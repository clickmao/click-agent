namespace agent.registry;


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
