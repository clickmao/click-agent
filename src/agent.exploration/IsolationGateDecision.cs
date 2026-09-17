namespace agent.exploration;


/// <summary>微问询预发送判定结果 (闸的单一事实源: 是否发送 / 原因 / 命中的回指标记, 供打点审计)。</summary>
public sealed class IsolationGateDecision
{
    /// <summary>true = 照旧发送到 LLM 通道; false = 本微问题不发送。</summary>
    public bool Send { get; init; }

    /// <summary>拦截原因: "ok"(放行) / "blank"(空问题) / "isolation_invalid_anaphora"(回指在隔离通道内不可解)。</summary>
    public string Reason { get; init; } = "ok";

    /// <summary>命中的回指标记 (放行时为空串) — 只落标记本身, 不落用户正文。</summary>
    public string Marker { get; init; } = string.Empty;
}
