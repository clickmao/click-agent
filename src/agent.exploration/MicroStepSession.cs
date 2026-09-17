namespace agent.exploration;

/// <summary>
/// 微步骤会话 (v0.13.3 B2): 阈值门触发后, 当前步骤 → 微问题序列 → 隔离执行 → 结果回注主上下文。
/// 微问题执行由宿主委托隔离 subagent (独立 session, 主记忆零污染, 完成即销毁 — A5 语义复用);
/// 本类管编排/回注预算/失败升级联动。
/// </summary>
public sealed class MicroStepSession
{
    private readonly ContextGateConfig _gateConfig;
    private readonly int _maxRestoreTokensPerMicro;
    private readonly List<MicroStepResult> _results = new();

    public MicroStepSession(ContextGateConfig? gateConfig = null, int maxRestoreTokensPerMicro = 200)
    {
        _gateConfig = gateConfig ?? new ContextGateConfig();
        _maxRestoreTokensPerMicro = maxRestoreTokensPerMicro;
    }

    public IReadOnlyList<MicroStepResult> Results => _results;

    /// <summary>
    /// 结果回注主上下文的摘要预算 (用户钦定: ≤200 tok/条, 防止微执行结果反把主上下文撑爆)。
    /// </summary>
    public string BuildRestoreSummary(MicroStepResult r)
    {
        var a = (r.Answer ?? string.Empty).Trim();
        if (a.Length == 0) return string.Empty;
        var maxChars = _maxRestoreTokensPerMicro * 2; // 1 token ≈ 2 chars 粗算 (批测同口径)
        if (a.Length > maxChars) a = a[..maxChars] + "…";
        return $"[{r.MicroId}] {a}";
    }

    /// <summary>连续失败计数 (FailureEscalation 联动: ≥N 次 → 宿主插入升级)。</summary>
    public int ConsecutiveFailures { get; private set; }

    public void Record(MicroStepResult r)
    {
        _results.Add(r);
        ConsecutiveFailures = r.Ok ? 0 : ConsecutiveFailures + 1;
    }
}
