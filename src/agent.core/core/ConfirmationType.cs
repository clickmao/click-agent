namespace agent.core;


/// <summary>
/// 确认类型
/// </summary>
public enum ConfirmationType
{
    /// <summary>保存模板</summary>
    SaveTemplate,
    
    /// <summary>保存示例</summary>
    SaveExample,
    
    /// <summary>确认操作</summary>
    ConfirmAction,
    
    /// <summary>选择选项</summary>
    SelectOption,
    
    /// <summary>批准变更</summary>
    ApproveChange,
    
    /// <summary>拒绝变更</summary>
    RejectChange,
    
    /// <summary>自定义</summary>
    Custom
}
