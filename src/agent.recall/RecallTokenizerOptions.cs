// R480: 独立文本召回模块 —— 分词面。
// 【语言无关令】这里没有任何文件后缀/语言标签分支: 字符类 → 切分规则全部来自
// RecallTokenizerOptions(可配置数据), 默认值只是一组「常见表意文字区间」。
using System.Text;

namespace agent.recall;


public sealed class RecallTokenizerOptions
{
    /// <summary>表意文字(逐字无空格分隔)区间: 命中后按 n-gram 切分。</summary>
    public IReadOnlyList<CodepointRange> IdeographicRanges { get; init; } = DefaultIdeographicRanges;

    /// <summary>表意文字的 n-gram 阶数(默认 2 = bigram)。1 表示逐字。</summary>
    public int IdeographicNgram { get; init; } = 2;

    /// <summary>是否把 ASCII 字母折成小写(仅影响 ASCII 段, 表意文字不受影响)。</summary>
    public bool LowercaseAscii { get; init; } = true;

    public int MinTokenBytes { get; init; } = 1;
    public int MaxTokenBytes { get; init; } = 96;
    public int MaxTokensPerDoc { get; init; } = 8192;

    /// <summary>算作词内字符的符号。点号被排除: R481-B 统计判定 (n=300 真实查询, hit@5 差异 +0.67pt / p=0.856 不显著,
    /// 而查询词数 -16.05%、postings -0.254% 更低) ⇒ 质量无显著差异时取成本更低者。语言无关: 该集合是配置数据, 不含任何后缀语义。</summary>
    public string WordSymbols { get; init; } = "_/+#";

    /// <summary>n-gram 环形缓冲的最大阶数(超过的阶数一律按此上限截断)。</summary>
    internal const int MaxNgramOrder = 4;

    public static readonly IReadOnlyList<CodepointRange> DefaultIdeographicRanges = new[]
    {
        new CodepointRange(0x3040, 0x30FF),   // 假名
        new CodepointRange(0x3400, 0x4DBF),   // 扩展 A
        new CodepointRange(0x4E00, 0x9FFF),   // 基本区
        new CodepointRange(0xAC00, 0xD7AF),   // 谚文音节
        new CodepointRange(0xF900, 0xFAFF),   // 兼容表意
        new CodepointRange(0x20000, 0x2FA1F), // 扩展 B..F (代理对)
    };

    public static RecallTokenizerOptions Default { get; } = new();

    internal bool IsIdeographic(int cp)
    {
        for (int i = 0; i < IdeographicRanges.Count; i++)
        {
            if (IdeographicRanges[i].Contains(cp))
            {
                return true;
            }
        }
        return false;
    }

    internal bool IsWordSymbol(char c)
    {
        for (int i = 0; i < WordSymbols.Length; i++)
        {
            if (WordSymbols[i] == c)
            {
                return true;
            }
        }
        return false;
    }
}
