namespace agent.contextgradient;

/// <summary>
/// 空实现 (DI 兜底): 无 bge 模型时注册, IsAvailable=false → CompressCore 走纯锚词模式 (P1 行为兼容)。
/// </summary>
public sealed class NullTextEmbedder : ITextEmbedder
{
    public bool IsAvailable => false;

    public Task<float[]> EmbedAsync(string text, CancellationToken ct = default) =>
        throw new NotSupportedException("嵌入器不可用 (bge 模型未配置) — 调用方应先查 IsAvailable");
}
