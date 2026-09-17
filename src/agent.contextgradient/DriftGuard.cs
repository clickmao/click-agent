namespace agent.contextgradient;


/// <summary>
/// 防漂移校验 (三重规则的 P1 简化 — 锚词保持):
/// 压缩产物必须保留 ≥1 锚词 (锚词为空 = 无锚需求, 恒过)。
/// </summary>
public static class DriftGuard
{
    public static bool Check(string compressed, List<string> anchorWords)
    {
        if (anchorWords.Count == 0)
            return true;
        return anchorWords.Any(w =>
            w.Length > 0 && compressed.Contains(w, StringComparison.OrdinalIgnoreCase));
    }
}
