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
