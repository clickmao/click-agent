using System.Text;

namespace agent.rover.token;

/// <summary>
/// 预分词器: 与 HF tokenizers 的 Sequence([Split]×5, Digits, ByteLevel) 逐语义等价。
/// 不使用 .NET Regex —— 常量来自 TokenizerAssets 的机器派生区间表 (标量语义),
/// .NET 按 UTF-16 码元解析字符类, 对增补平面区间会静默过量匹配 (实测)。
/// Isolated 语义: 命中片段与间隙都产出片段, 空间隙丢弃。
/// </summary>
public static class Pretokenizer
{
    /// <summary>流水线阶段数 (Split×5 + Digits + ByteLevel)。</summary>
    public const int SplitStageCount = 5;

    /// <summary>区间表 + 正则 sha256 自校验 (防手改常量)。</summary>
    public static bool SelfCheck(out string detail)
    {
        if (TokenizerAssets.Splits.Length != SplitStageCount)
        {
            detail = $"Split 数不符: {TokenizerAssets.Splits.Length}";
            return false;
        }

        for (int i = 0; i < TokenizerAssets.Splits.Length; i++)
        {
            string got = Sha256Hex(System.Text.Encoding.UTF8.GetBytes(TokenizerAssets.Splits[i]));
            if (got != TokenizerAssets.SplitSha256[i])
            {
                detail = $"Split[{i}] sha256 不符: {got[..16]} != {TokenizerAssets.SplitSha256[i][..16]}";
                return false;
            }
        }

        string digest = RangesDigest();
        if (digest != TokenizerAssets.RangesDigest)
        {
            detail = $"区间表摘要不符: {digest[..16]} != {TokenizerAssets.RangesDigest[..16]}";
            return false;
        }

        // 归一化前提机检: 二分查找要求区间严格升序且互不重叠 (R400 实测抓到过非升序表 ⇒ 静默漏判)
        (string name, int[] table)[] tables =
        [
            ("letter", TokenizerAssets.LetterRanges),
            ("punct", TokenizerAssets.PunctRanges),
            ("cjk", TokenizerAssets.CjkRanges),
            ("space", TokenizerAssets.SpaceRanges),
            ("digit", TokenizerAssets.DigitRanges),
        ];
        foreach ((string name, int[] table) in tables)
        {
            if (table.Length == 0 || table.Length % 2 != 0)
            {
                detail = $"{name} 区间表长度非法: {table.Length}";
                return false;
            }

            for (int i = 2; i < table.Length; i += 2)
            {
                if (table[i] <= table[i - 1])
                {
                    detail = $"{name} 区间未归一化: [{i / 2}]lo={table[i]} <= [{i / 2 - 1}]hi={table[i - 1]}";
                    return false;
                }
            }
        }

        detail = $"5 条 Split sha256 全等, 5 张区间表升序互斥, 摘要 {digest[..16]}";
        return true;
    }

    /// <summary>区间表规范化摘要 (与生成器 ranges_digest 同构: "lo-hi" 以 ',' 连接, 表间以 '|' 连接)。</summary>
    public static string RangesDigest()
    {
        string[] parts =
        [
            Canon(TokenizerAssets.LetterRanges),
            Canon(TokenizerAssets.PunctRanges),
            Canon(TokenizerAssets.CjkRanges),
            Canon(TokenizerAssets.SpaceRanges),
            Canon(TokenizerAssets.DigitRanges),
        ];
        return Sha256Hex(System.Text.Encoding.UTF8.GetBytes(string.Join("|", parts)));
    }

    /// <summary>完整预分词: 返回字节级编码后的片段 (与 oracle pre_tokenize_str 逐条可比)。</summary>
    public static List<string> Split(string text)
    {
        List<string> pieces = SplitStages(text);

        List<string> digits = new(pieces.Count + 8);
        foreach (string p in pieces)
        {
            SplitDigits(p, digits);
        }

        List<string> outp = new(digits.Count);
        foreach (string p in digits)
        {
            outp.Add(ByteUnicode.Encode(p));
        }

        return outp;
    }

    /// <summary>仅 5 条 Split (未做数字个体化与字节映射), 供诊断输出。</summary>
    public static List<string> SplitStages(string text)
    {
        List<string> cur = [text];

        // 阶段 0: [\r\n] 隔离
        cur = SplitIsolated(cur, (s, i) => i < s.Length && (s[i] == '\r' || s[i] == '\n') ? i + 1 : -1);

        // 阶段 1/2: \s?[字母集]+ 与 \s?[标点集]+
        cur = SplitIsolated(cur, (s, i) => MatchClassRun(s, i, TokenizerAssets.LetterRanges, true));
        cur = SplitIsolated(cur, (s, i) => MatchClassRun(s, i, TokenizerAssets.PunctRanges, true));

        // 阶段 3: \s+$ (尾部空白整体一片)
        cur = SplitIsolated(cur, MatchTrailingSpaces);

        // 阶段 4: [CJK]+ (无空白前缀)
        cur = SplitIsolated(cur, (s, i) => MatchClassRun(s, i, TokenizerAssets.CjkRanges, false));

        return cur;
    }

    /// <summary>数字个体化 (Digits individual_digits=true)。</summary>
    public static void SplitDigits(string piece, List<string> dst)
    {
        int i = 0;
        int last = 0;
        while (i < piece.Length)
        {
            int len = RuneLen(piece, i);
            if (InRanges(RuneAt(piece, i), TokenizerAssets.DigitRanges))
            {
                if (i > last)
                {
                    dst.Add(piece[last..i]);
                }

                dst.Add(piece[i..(i + len)]);
                i += len;
                last = i;
            }
            else
            {
                i += len;
            }
        }

        if (last < piece.Length)
        {
            dst.Add(piece[last..]);
        }
    }

    /// <summary>区间命中 (二分, 区间按 lo 升序且互不重叠)。</summary>
    public static bool InRanges(int cp, int[] ranges)
    {
        int lo = 0;
        int hi = (ranges.Length / 2) - 1;
        while (lo <= hi)
        {
            int mid = (lo + hi) >> 1;
            int rl = ranges[mid * 2];
            int rh = ranges[(mid * 2) + 1];
            if (cp < rl)
            {
                hi = mid - 1;
            }
            else if (cp > rh)
            {
                lo = mid + 1;
            }
            else
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>标量判定: 光标处的码点 (代理对合成)。</summary>
    public static int RuneAt(string s, int i)
    {
        char c = s[i];
        if (char.IsHighSurrogate(c) && i + 1 < s.Length && char.IsLowSurrogate(s[i + 1]))
        {
            return char.ConvertToUtf32(c, s[i + 1]);
        }

        return c;
    }

    /// <summary>标量长度 (UTF-16 码元数)。</summary>
    public static int RuneLen(string s, int i)
        => char.IsHighSurrogate(s[i]) && i + 1 < s.Length && char.IsLowSurrogate(s[i + 1]) ? 2 : 1;

    private static List<string> SplitIsolated(List<string> pieces, Func<string, int, int> matchAt)
    {
        List<string> outp = new(pieces.Count + 4);
        foreach (string piece in pieces)
        {
            int i = 0;
            int last = 0;
            while (i < piece.Length)
            {
                int m = matchAt(piece, i);
                if (m < 0)
                {
                    i += RuneLen(piece, i);
                    continue;
                }

                if (i > last)
                {
                    outp.Add(piece[last..i]);
                }

                outp.Add(piece[i..m]);
                last = m;
                i = m;
            }

            if (last < piece.Length)
            {
                outp.Add(piece[last..]);
            }
        }

        return outp;
    }

    private static int MatchClassRun(string s, int i, int[] ranges, bool spacePrefix)
    {
        int j = i;
        if (spacePrefix)
        {
            int cp0 = RuneAt(s, j);
            if (InRanges(cp0, TokenizerAssets.SpaceRanges))
            {
                int k = j + RuneLen(s, j);
                if (k < s.Length && InRanges(RuneAt(s, k), ranges))
                {
                    j = k; // 贪婪: 吞掉一个空白且其后紧跟类字符
                }
                else if (!InRanges(cp0, ranges))
                {
                    return -1; // 回溯: 既不吞空白也无类字符匹配 ⇒ 该起点无匹配
                }

                // else: 回溯为"不吞空白", 由下方从 i 起把该空白字符本身当类成员匹配
            }
        }

        if (j >= s.Length || !InRanges(RuneAt(s, j), ranges))
        {
            return -1;
        }

        while (j < s.Length)
        {
            int cp = RuneAt(s, j);
            if (!InRanges(cp, ranges))
            {
                break;
            }

            j += RuneLen(s, j);
        }

        return j;
    }

    private static int MatchTrailingSpaces(string s, int i)
    {
        // \s+$ : 只可能命中从某处开始、直到串尾全为空白的最长后缀; 且必须以 i 为起点。
        if (i >= s.Length || !InRanges(RuneAt(s, i), TokenizerAssets.SpaceRanges))
        {
            return -1;
        }

        int j = i;
        while (j < s.Length && InRanges(RuneAt(s, j), TokenizerAssets.SpaceRanges))
        {
            j += RuneLen(s, j);
        }

        return j == s.Length ? j : -1;
    }

    private static string Canon(int[] ranges)
    {
        StringBuilder sb = new(ranges.Length * 6);
        for (int i = 0; i < ranges.Length; i += 2)
        {
            if (i > 0)
            {
                sb.Append(',');
            }

            sb.Append(ranges[i]).Append('-').Append(ranges[i + 1]);
        }

        return sb.ToString();
    }

    private static string Sha256Hex(byte[] data)
        => Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(data));
}
