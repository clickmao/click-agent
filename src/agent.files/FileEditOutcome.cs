namespace agent.files;

/// <summary>
/// 写盘结果分类 — 每类对应一条机检判据；Applied/MergedAuto 之外保证盘上零改动。
/// </summary>
public enum FileEditOutcome
{
    /// <summary>快路径: 期望 sha 与现盘一致 ⇒ 备份后直接写。</summary>
    Applied = 0,

    /// <summary>现盘已被他人改动但改动不重叠 ⇒ 三方合并后写（备份现盘）。</summary>
    MergedAuto = 1,

    /// <summary>现盘已被他人改动且重叠 ⇒ 不写盘，返回冲突块交人裁定。</summary>
    Conflict = 2,

    /// <summary>缺可比对的基线（未给 BaseText 且备份库无该版本）或文件已被删 ⇒ 不写盘。</summary>
    StaleBase = 3,

    /// <summary>前置条件失败（备份失败 / 超合并上限 / 非文本）⇒ 不写盘。</summary>
    Rejected = 4,
}
