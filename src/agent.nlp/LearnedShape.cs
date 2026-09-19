namespace agent.nlp;

/// <summary>
/// 远端返回蒸馏出的**可泛化形状** — 用户令 2026-09-19「加入远端返回后可以优化 nlp 能力的机制」。
/// 与逐字补丁 (face + 精确签名) 的区别: 本形状只保留 面 / 语言 / 长度带 / 显著 token 集,
/// 使**同面不同措辞**的下一句也能本地命中 ⇒ 学到的是能力 (形状), 不是字符串。
/// </summary>
/// <param name="Face">判定面 (如 repeat / paraphrase); 不同面互不命中。</param>
/// <param name="Language">语言标签 (fastText lid); 跨语言不命中 (fail-safe)。</param>
/// <param name="Band">长度带 = token 数 / 4 (粗粒度, 容措辞增减)。</param>
/// <param name="Tokens">显著 token 集 (去重后按序数排序, 与签名同口径)。</param>
/// <param name="Score">评分: 命中且有用 +1 (上限 +4); 一次无用即剔除 ⇒ 只留"下次真有用"的形状。</param>
public readonly record struct LearnedShape(string Face, string Language, int Band, string[] Tokens, int Score = 0);
