using System.Text.Json.Serialization;

namespace agent;


/// <summary>/rag &lt;path&gt; 切换结果载荷</summary>
public sealed class RagSwitchPayload
{
    public string Path { get; set; } = string.Empty;
    public bool Reloaded { get; set; }
    public string Hint { get; set; } = string.Empty;
}
