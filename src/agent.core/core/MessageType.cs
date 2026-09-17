namespace agent.core;

/// <summary>
/// 消息类型
/// </summary>
public enum MessageType
{
    /// <summary>文本消息</summary>
    Text,
    
    /// <summary>代码消息</summary>
    Code,
    
    /// <summary>命令消息</summary>
    Command,
    
    /// <summary>确认请求</summary>
    ConfirmationRequest,
    
    /// <summary>确认响应</summary>
    ConfirmationResponse,
    
    /// <summary>错误消息</summary>
    Error,
    
    /// <summary>状态消息</summary>
    Status,
    
    /// <summary>搜索结果</summary>
    SearchResult,
    
    /// <summary>文件内容</summary>
    File
}


