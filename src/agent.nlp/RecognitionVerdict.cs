namespace agent.nlp;

/// <summary>
/// 开放域识别出口 (RF0004.1 · M1): 输入任意域文本 ⇒ `{标签 | abstain, 依据}`。
/// 标签集**不固定** (由机制面产出: 面标 + 判定依据), 不新增本体, 不新增词表;
/// abstain = 本层无本地消化依据 ⇒ 交远端 (远端回执经既有形状通道回补 ⇒ 下次可命中)。
/// 本结构是**只读出口**: 判定链一字不改, 出口只做渲染 (渲染器见 <see cref="RecognitionOutlet"/>)。
/// </summary>
public readonly record struct RecognitionVerdict(bool Abstain, string Label, string Evidence)
{
    /// <summary>abstain 面标签常量 (标签位写它, 原因进依据)。</summary>
    public const string AbstainLabel = "abstain";

    /// <summary>识别命中 (有本地消化依据)。</summary>
    public static RecognitionVerdict Recognized(string label, string evidence) => new(false, label, evidence);

    /// <summary>识别弃权 (无本地消化依据 ⇒ 交远端)。</summary>
    public static RecognitionVerdict Abstained(string evidence) => new(true, AbstainLabel, evidence);

    /// <summary>单行渲染 `标签|依据` (abstain ⇒ `abstain|依据`); 打点与机检共用同一形态 (单一渲染点)。</summary>
    public string Render() => (Abstain ? AbstainLabel : Label) + "|" + Evidence;
}
