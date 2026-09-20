namespace agent.nlp;

/// <summary>
/// 识别出口渲染器 (RF0004.1 · M1): 既有判定面事实 ⇒ <see cref="RecognitionVerdict"/>。
/// 输入 = 是否本地消化 / 判定依据 / 面标 / 输入字符数 / 输入指纹 —— 全部是**调用方已算好的事实**。
/// 纪律 (零回归的机理): 本类**只读** —— 不调 Decide/Extract/Observe (不递增任何计数、不写库、不触发分词),
/// 故开关开/关对判定链逐位等价; 「出口落地」与「行为改动」两件事在机理上分开。
/// 单变量轴 <see cref="EnvKey"/>: 缺省 on (出口打点落地) / 显式 off|0 ⇒ 该面打点不发 (旧行为)。
/// </summary>
public static class RecognitionOutlet
{
    /// <summary>单变量轴名 (缺省 on; 显式 off/0 关闭出口打点)。</summary>
    public const string EnvKey = "AGENTFRAMEWORK_RECOGNITION_VERDICT";

    /// <summary>面标缺省 (无具体族面时): 闸面通用。</summary>
    public const string DefaultFace = "gate";

    public static bool IsEnabled() => IsEnabled(Environment.GetEnvironmentVariable(EnvKey));

    /// <summary>轴判定 (纯函数: 只有显式 off/0 才关; 其余含未设 ⇒ 开)。</summary>
    public static bool IsEnabled(string? raw)
    {
        if (string.Equals(raw, "off", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        return !string.Equals(raw, "0", StringComparison.Ordinal);
    }

    /// <summary>
    /// 渲染出口判定 (纯函数; 相同输入 ⇒ 逐位相同输出)。
    /// <paramref name="localConsumed"/>=true ⇒ 识别命中 (标签 = 面标); false ⇒ abstain (依据里带机制面原因)。
    /// </summary>
    public static RecognitionVerdict Render(
        bool localConsumed, string? basis, string? face, int inputChars, string? inputSha16)
    {
        var f = string.IsNullOrEmpty(face) ? DefaultFace : face;
        var evidence = "basis=" + (basis ?? string.Empty)
            + ";face=" + f
            + ";len=" + inputChars.ToString(System.Globalization.CultureInfo.InvariantCulture)
            + ";sha16=" + (inputSha16 ?? string.Empty);
        return localConsumed ? RecognitionVerdict.Recognized(f, evidence) : RecognitionVerdict.Abstained(evidence);
    }
}
