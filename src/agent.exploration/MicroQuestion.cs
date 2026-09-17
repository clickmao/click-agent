namespace agent.exploration;


/// <summary>微问题 (当前步骤细分产物 — 用户钦定: 细分的是步骤, 不是任务)。</summary>
public sealed class MicroQuestion
{
    public string Id { get; set; } = "mq" + Guid.NewGuid().ToString("N")[..6];
    public string Question { get; set; } = string.Empty;
    /// <summary>数据依赖: 关键字 → 正向链接 (snippet/文档/URL) — v0.13.0 探索复用</summary>
    public List<string> ForwardRefs { get; set; } = new();
    /// <summary>反向链接 (哪些历史片段引用了本依赖) — 探索基建复用</summary>
    public List<string> BackwardRefs { get; set; } = new();
    /// <summary>归纳进微上下文的有效信息 (主上下文不复制全量)</summary>
    public string InjectedContext { get; set; } = string.Empty;
    public int InjectedTokens { get; set; }
}
