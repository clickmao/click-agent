namespace agent.llamacpp;


/// <summary>R464: 解析结论（生效路径 + 来源 + 告警文本 null=无告警）。</summary>
public sealed record LocalModelPathResolution(string ModelPath, LocalModelPathSource Source, string? Warning)
{
    /// <summary>错配（声明了配置但不可用）—— 调用方据此**不得**认为配置生效。</summary>
    public bool ConfigMismatch => Source == LocalModelPathSource.ConfiguredMissing;

    /// <summary>配置宽度参数（ctx/parallel）是否应当生效。</summary>
    public bool UseConfiguredWidths => Source == LocalModelPathSource.Configured;
}
