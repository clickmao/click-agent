namespace agent.exploration;


/// <summary>
/// v0.13.0 渐进式探索 (用户钦定 2026-09-08) — 探索源类型。
/// </summary>
public enum ExploreSourceKind
{
    /// <summary>上下文区/RAG snippet 扩展</summary>
    ContextBlock = 0,

    /// <summary>文本片段 (上下文/文件内的引文)</summary>
    Text = 1,

    /// <summary>网页链接 (HTTP GET, 只读)</summary>
    Url = 2,

    /// <summary>目录 (Workspace root 内)</summary>
    Directory = 3,

    /// <summary>文件 (Workspace root 内)</summary>
    File = 4,
}
