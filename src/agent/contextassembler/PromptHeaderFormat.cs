using agent.core;

namespace agent.context;

/// <summary>
/// Prompt Header 格式选项
/// </summary>
public enum PromptHeaderFormat
{
    /// <summary>简洁模式：仅内容</summary>
    Compact,
    
    /// <summary>标准模式：带标签</summary>
    Standard,
    
    /// <summary>详细模式：带元数据</summary>
    Detailed,
    
    /// <summary>调试模式：含统计</summary>
    Debug
}
