using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>
/// 会话配置
/// </summary>
public class SessionConfig
{
    /// <summary>
    /// 最大Token数
    /// </summary>
    public long MaxTokens { get; set; } = 100000;
    
    /// <summary>
    /// 超时时间
    /// </summary>
    public TimeSpan Timeout { get; set; } = TimeSpan.FromHours(1);
    
    /// <summary>
    /// 会话长期记忆上限字符数 (v7.14): 默认 1000, 可配置 (100..10000)
    /// </summary>
    public int MaxMemoryChars { get; set; } = SessionMemory.DefaultMaxChars;

    /// <summary>
    /// 是否自动保存
    /// </summary>
    public bool AutoSave { get; set; } = true;
    
    /// <summary>
    /// 保存间隔
    /// </summary>
    public TimeSpan SaveInterval { get; set; } = TimeSpan.FromMinutes(1);
}
