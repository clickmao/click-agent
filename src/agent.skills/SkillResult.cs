namespace agent.skills;


/// <summary>标准化输出 (原文 §4.6)</summary>
public sealed class SkillResult
{
    public string SkillId { get; set; } = string.Empty;
    public bool Success { get; set; }
    public string Content { get; set; } = string.Empty;

    /// <summary>强制口径 (true = 内容直接承载回复口径, 模型只做合规润色)</summary>
    public bool ForceUse { get; set; }

    /// <summary>R326-f: 知识提示命中 (true = Content 是知识参考, 调用方注入系统侧, 回复仍走主链)</summary>
    public bool IsKnowledgeHint { get; set; }

    /// <summary>禁语命中 (校验拦截时 false)</summary>
    public string? ForbiddenHit { get; set; }

    /// <summary>执行耗时 ms</summary>
    public long ElapsedMs { get; set; }
}
