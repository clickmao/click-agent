namespace agent.exploration;

/// <summary>
/// v0.13.0 T3 M-A — 复杂度门: 判定是否展开思考链+探索 (用户钦定任务3 ①②)。
/// 纯逻辑可打点; 简单题直答省 token, 复杂题才展开。
/// </summary>
public sealed class ComplexityVerdict
{
    public bool IsComplex { get; set; }
    public int Score { get; set; }
    public List<string> Triggers { get; set; } = new();
}

public static class ComplexityGate
{
    /// <summary>
    /// 判据 (各触发 +分): 子任务≥2 (+2) / 研究编码规划意图 (+2) / 含 URL (+2) /
    /// 含目录引用 (+2) / 长度>200ch (+1) / 含比较对比词 (+1)。score ≥ threshold (默认 3) → 复杂。
    /// </summary>
    public static ComplexityVerdict Evaluate(
        string message, string primaryIntent, int subtaskCount, int threshold = 3)
    {
        var v = new ComplexityVerdict();
        var msg = message ?? string.Empty;
        if (subtaskCount >= 2)
        { v.Score += 2; v.Triggers.Add("subtasks>=2"); }
        var intent = primaryIntent ?? "";
        if (intent is "research" or "coding" or "planning" or "search")
        { v.Score += 2; v.Triggers.Add($"intent:{intent}"); }
        if (msg.Contains("http://") || msg.Contains("https://"))
        { v.Score += 2; v.Triggers.Add("has_url"); }
        if (msg.Contains('/') || msg.Contains("\\"))
        { v.Score += 2; v.Triggers.Add("path_like"); }
        if (msg.Length > 200)
        { v.Score += 1; v.Triggers.Add("long_input"); }
        foreach (var w in new[] { "对比", "比较", "哪个更好", "区别", "compare", "versus", " vs " })
            if (msg.Contains(w))
            { v.Score += 1; v.Triggers.Add("comparison"); break; }
        v.IsComplex = v.Score >= threshold;
        return v;
    }
}
