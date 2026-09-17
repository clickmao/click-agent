namespace agent.core;


/// <summary>
/// 任务类型
/// </summary>
public enum TaskType
{
    /// <summary>代码生成</summary>
    CodeGeneration,
    
    /// <summary>代码审查</summary>
    CodeReview,
    
    /// <summary>文档生成</summary>
    Documentation,
    
    /// <summary>搜索</summary>
    Search,
    
    /// <summary>分析</summary>
    Analysis,
    
    /// <summary>测试</summary>
    Testing,
    
    /// <summary>重构</summary>
    Refactoring,
    
    /// <summary>通用任务</summary>
    General
}
