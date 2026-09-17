namespace agent.contract;

/// <summary>R1 结构化契约 · 拒答信息（硬闸命中时唯一允许的推进方式）。</summary>
public sealed record RefusalInfo(string Reason, string Category);
