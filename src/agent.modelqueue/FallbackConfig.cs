namespace agent.modelqueue;

/// <summary>
/// v0.13.1 F1 (用户钦定) — 兜底服务配置 (models.yaml fallback 段)。
/// 总开关 / 性价比序 (=auto 同序) / 单请求兜底上限 / 兜底回复校验。
/// </summary>
public sealed class FallbackConfig
{
    public bool Enabled { get; set; } = true;
    /// <summary>cost_quality = 与 auto 选择同序 (RankCandidates); catalog = 目录序 (旧行为)</summary>
    public string Order { get; set; } = "cost_quality";
    /// <summary>单请求最多切几个备选 (含首个; 1=旧行为)</summary>
    public int PerRequestMaxFallbacks { get; set; } = 2;
    /// <summary>兜底回复校验 (非空/非错误模板/最短长度)</summary>
    public bool VerifyFallbackReply { get; set; } = true;
    /// <summary>校验最小回复长度</summary>
    public int MinReplyChars { get; set; } = 2; // 'ok' 类短合法回复放行; 校验主目标=空/错误模板 (C07 400 模板实证)
    /// <summary>错误模板特征 (命中=校验失败)</summary>
    public string[] ErrorMarkers { get; set; } = { "API Error", "HTTP 4", "HTTP 5", "未正常接收", "model cannot" };

    /// <summary>兜底回复校验 (用户钦定"启用兜底校验"): 非空 + 长度 + 错误模板。</summary>
    public bool VerifyReply(QueueResponse resp)
    {
        if (!VerifyFallbackReply) return resp.Success;
        if (!resp.Success) return false;
        var content = resp.Content ?? string.Empty;
        if (content.Trim().Length < MinReplyChars) return false;
        foreach (var mk in ErrorMarkers)
            if (content.Contains(mk, StringComparison.OrdinalIgnoreCase)) return false;
        return true;
    }
}
