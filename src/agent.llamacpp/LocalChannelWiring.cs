namespace agent.llamacpp;

/// <summary>
/// R464: 本地通道权重路径的**来源判定** —— 三态分离（配置未声明 / 配置可用 / 配置错配）。
///
/// 立规背景（R463 现场）: 原接线 `lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` 把三态压成两态，
/// 于是「配置指向不存在的文件」时产品**静默改用宿主默认权重**，既不告警也不留痕 ⇒ 任何以权重档位为
/// 单变量的测量在该配置下读数是错的且看不出来（R463 负控 BP 因此 VOID）。
/// 本类的唯一纪律: <b>Declared == true 时绝不把 fallback 写进 ModelPath</b>；错配 ⇒ 通道不可用
/// （门走既有 fail-open Pass，远端兜底），但配置意图不被改写，且告警必落。
/// </summary>
public enum LocalModelPathSource
{
    /// <summary>配置未声明 local 段 ⇒ 合法使用宿主默认（env / 内置权重）。</summary>
    Unconfigured = 0,

    /// <summary>配置声明的路径存在 ⇒ 按配置使用。</summary>
    Configured = 1,

    /// <summary>配置声明的路径缺失/为空 ⇒ **按配置意图置为不可用**，不替换、不静默兜底。</summary>
    ConfiguredMissing = 2,
}

/// <summary>R464: 解析输入（**纯数据** —— 文件存在性由调用方探测，便于单测与确定性）。</summary>
public readonly record struct LocalChannelWiringInput(
    bool Declared,
    string? ConfiguredPath,
    string FallbackPath,
    bool ConfiguredFileExists,
    bool FallbackFileExists);

/// <summary>R464: 解析结论（生效路径 + 来源 + 告警文本 null=无告警）。</summary>
public sealed record LocalModelPathResolution(string ModelPath, LocalModelPathSource Source, string? Warning)
{
    /// <summary>错配（声明了配置但不可用）—— 调用方据此**不得**认为配置生效。</summary>
    public bool ConfigMismatch => Source == LocalModelPathSource.ConfiguredMissing;

    /// <summary>配置宽度参数（ctx/parallel）是否应当生效。</summary>
    public bool UseConfiguredWidths => Source == LocalModelPathSource.Configured;
}

/// <summary>R464: 本地通道接线解析（纯函数；告警串以 ASCII 标记开头以便机检 grep）。</summary>
public static class LocalChannelWiring
{
    public const string MismatchMarker = "R464 config_mismatch:";
    public const string DefaultMissingMarker = "R464 config_default_missing:";

    /// <summary>纯解析（零 I/O）。</summary>
    public static LocalModelPathResolution Resolve(in LocalChannelWiringInput input)
    {
        if (!input.Declared)
        {
            // 未声明 = 合法走默认；但默认权重缺失同样是「静默不可用」，必须留告警（仪器异常必留痕）。
            return input.FallbackFileExists
                ? new LocalModelPathResolution(input.FallbackPath, LocalModelPathSource.Unconfigured, null)
                : new LocalModelPathResolution(input.FallbackPath, LocalModelPathSource.Unconfigured,
                    $"{DefaultMissingMarker} 未声明 local 段且默认权重不存在 {input.FallbackPath}" +
                    " ⇒ 本地通道不可用 (门 fail-open Pass, 远端兜底; 修正 config local.model_path 或 env AGENTFRAMEWORK_LLM_MODEL)");
        }

        if (string.IsNullOrWhiteSpace(input.ConfiguredPath))
        {
            // 声明了 local 段却没有 model_path = 配置不完整。返回空路径 ⇒ 端口 IsAvailable=false。
            // 纪律: 不回退 fallback（回退即静默替换意图）。
            return new LocalModelPathResolution(string.Empty, LocalModelPathSource.ConfiguredMissing,
                $"{MismatchMarker} local 段已声明但缺 model_path ⇒ 本地通道置为不可用" +
                $" (未回退默认权重 {input.FallbackPath})");
        }

        if (!input.ConfiguredFileExists)
        {
            return new LocalModelPathResolution(input.ConfiguredPath!, LocalModelPathSource.ConfiguredMissing,
                $"{MismatchMarker} local.model_path 不存在 {input.ConfiguredPath}" +
                $" ⇒ 本地通道置为不可用 (未回退默认权重 {input.FallbackPath})");
        }

        return new LocalModelPathResolution(input.ConfiguredPath!, LocalModelPathSource.Configured, null);
    }

    /// <summary>宿主接线薄壳: 由 primitives 探测文件存在性后调用 <see cref="Resolve(in LocalChannelWiringInput)"/>。</summary>
    public static LocalModelPathResolution ResolveForHost(bool declared, string? configuredPath, string fallbackPath)
    {
        var cfgExists = !string.IsNullOrWhiteSpace(configuredPath) && SafeExists(configuredPath!);
        var fbExists = !string.IsNullOrWhiteSpace(fallbackPath) && SafeExists(fallbackPath);
        return Resolve(new LocalChannelWiringInput(declared, configuredPath, fallbackPath, cfgExists, fbExists));
    }

    private static bool SafeExists(string path)
    {
        // 探测本身不得让宿主启动失败（非法字符/超长路径/权限异常 ⇒ 视为不存在 + 由告警可见）
        try
        {
            return File.Exists(path);
        }
        catch (Exception)
        {
            return false;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // R465: 嵌入 (bge) 通道 —— 与生成通道**同一三态纪律**, 但通道独立、标记独立
    // ─────────────────────────────────────────────────────────────────────────
    /// <summary>R465: 嵌入通道的环境变量名 (声明 = 用户意图)。</summary>
    public const string EmbedderEnvVar = "AGENTFRAMEWORK_BGE_MODEL";

    /// <summary>R465: 嵌入通道错配标记 (ASCII, 便于机检 grep)。</summary>
    public const string EmbedderMismatchMarker = "R465 embedder_config_mismatch:";

    /// <summary>R465: 嵌入通道「未声明且内置默认权重不存在」标记。</summary>
    public const string EmbedderDefaultMissingMarker = "R465 embedder_default_missing:";

    /// <summary>
    /// R465: 嵌入通道接线解析 (纯函数, 零 I/O 之外的 File.Exists 探测)。
    ///
    /// 立规背景: 原接线 `embedder.IsAvailable ? embedder : new NullTextEmbedder()` 把
    /// 「env 声明了 bge 权重但文件不存在」与「未声明」塌成同一态 ⇒ 静默降级为**空心向量**
    /// (锚词回退), 用户看不出 bge 通道没生效, 测量也区分不了 —— 与 R463/R464 生成通道同一类缺陷
    /// (声明即意图; 错配必须留痕, 不得静默替换)。
    /// 返回: 未声明且默认缺失 / 声明却缺失 ⇒ Warning 非空; 声明且存在 ⇒ Configured, 无告警。
    /// </summary>
    public static LocalModelPathResolution ResolveEmbedder(bool declared, string? configuredPath, string fallbackPath)
    {
        var r = ResolveForHost(declared, configuredPath, fallbackPath);
        if (r.Source == LocalModelPathSource.ConfiguredMissing)
            return new LocalModelPathResolution(string.Empty, r.Source,
                EmbedderMismatchMarker + " " + (r.Warning ?? string.Empty).Trim());
        if (r.Source == LocalModelPathSource.Unconfigured && r.Warning is not null)
            return new LocalModelPathResolution(r.ModelPath, r.Source,
                EmbedderDefaultMissingMarker + " " + r.Warning.Trim());
        return r;
    }
}
