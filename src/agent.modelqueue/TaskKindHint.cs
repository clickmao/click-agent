namespace agent.modelqueue;


/// <summary>任务种类提示 (C.3.4): 调用方标注本次 LLM 调用的用途, 供计价路由/意图选模。</summary>
public enum TaskKindHint
{
    /// <summary>主回答 (默认, 用主模型)</summary>
    General,

    /// <summary>上下文压缩 (性能不敏感 → 便宜模型)</summary>
    ContextCompression,

    /// <summary>关键词标注 (性能不敏感)</summary>
    KeywordTagging,

    /// <summary>倾向分析 (性能不敏感)</summary>
    TendencyAnalysis,

    /// <summary>意图分类 (轻任务)</summary>
    IntentClassification,
}
