namespace agent.contextgradient;

/// <summary>
/// 向量嵌入抽象 (P3): 由宿主项目注入实现 (agent.llamalocal 的 BgeEmbedder — LLamaSharp+bge.gguf);
/// 本模块零 LLamaSharp 依赖, AOT 友好。不可用时宿主不注入 → DriftGuard 退纯锚词模式。
/// </summary>
public interface ITextEmbedder
{
    /// <summary>模型就绪? (文件缺失/后端失败 → false, 调用方走锚词回退)</summary>
    bool IsAvailable { get; }

    /// <summary>嵌入 (失败抛异常 — 调用方兜底)</summary>
    Task<float[]> EmbedAsync(string text, CancellationToken ct = default);
}

/// <summary>向量工具 (cosine 相似度)</summary>
public static class VectorMath
{
    public static double Cosine(float[] a, float[] b)
    {
        if (a.Length == 0 || a.Length != b.Length)
            return 0;
        double dot = 0, na = 0, nb = 0;
        for (var i = 0; i < a.Length; i++)
        {
            dot += (double)a[i] * b[i];
            na += (double)a[i] * a[i];
            nb += (double)b[i] * b[i];
        }
        var denom = Math.Sqrt(na) * Math.Sqrt(nb);
        return denom <= 0 ? 0 : dot / denom;
    }
}
