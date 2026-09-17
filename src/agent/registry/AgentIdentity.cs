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
