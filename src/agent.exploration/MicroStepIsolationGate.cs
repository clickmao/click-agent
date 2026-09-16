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

/// <summary>
/// R485 微问询形态分流闸 — 隔离微通道的**原理性**约束:
/// 微 prompt = system(隔离声明, 声明不引用任何外部会话历史) + user(微问题原文 + "只回答本微问题"),
/// **不携带任何前文**。因此凡以回指代词指代前文者, 在通道内**不可解** (原理性, 非统计启发式):
/// 模型只能复述/样板化, 其答复对回注摘要零信息量。
/// R484 真机读数佐证: 隔离微问询本地化判否 (H3 3/4), 远端答复样板化或直接指出「隔离执行未携带前文」。
/// R482 真机读数: Arole 21 次远端调用中 7 次 (33.3%) 为该形态, 占 token 8.30% — 全属可省调用。
///
/// 风险取向 (预注册声明): **宁漏勿伤**。词面过泛的「继续 / 接着」刻意**不上**标记表 —
/// 误伤 (把自足问题拦掉) 会丢信息, 漏网只是少省一次调用 ⇒ 漏网记为 known_miss, 不记为缺陷。
///
/// AOT 安全: 纯 Ordinal 字符串包含判定, 零反射, 零正则。
/// </summary>
public static class MicroStepIsolationGate
{
    /// <summary>
    /// 回指标记表 (窄口径, 由 R482/R484 已录制真机流量归纳; 器具侧由本数组源码派生, fail-closed)。
    /// </summary>
    public static readonly IReadOnlyList<string> AnaphoraMarkers = new string[]
    {
        "上一条", "上一句", "上句", "刚才", "前面说", "之前说", "此前说",
        "换个说法", "换一种说法", "从头", "再说", "重新说", "重新确认", "不对，你",
    };

    public static IsolationGateDecision Decide(string? question)
    {
        var q = question ?? string.Empty;
        if (q.Trim().Length == 0)
            return new IsolationGateDecision { Send = false, Reason = "blank" };

        for (var i = 0; i < AnaphoraMarkers.Count; i++)
        {
            var m = AnaphoraMarkers[i];
            if (m.Length > 0 && q.Contains(m, System.StringComparison.Ordinal))
                return new IsolationGateDecision { Send = false, Reason = "isolation_invalid_anaphora", Marker = m };
        }

        return new IsolationGateDecision { Send = true, Reason = "ok" };
    }
}
