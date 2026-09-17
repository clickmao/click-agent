using System.Text.Json.Serialization;

namespace agent.search;


/// <summary>
/// 槽位状态持久化模型 —— 记录主备次序, 下次启动复用
/// </summary>
public class ProviderSlotState
{
    /// <summary>槽位顺序 (index 0 = 主槽)</summary>
    public List<string> SlotOrder { get; set; } = new();

    /// <summary>各插件健康状态</summary>
    public Dictionary<string, ProviderHealthSnapshot> Health { get; set; }
        = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>状态保存时间 (UTC)</summary>
    public DateTime SavedAtUtc { get; set; } = DateTime.UtcNow;

    /// <summary>状态文件格式版本 (向前兼容)</summary>
    public int Version { get; set; } = 1;
}
