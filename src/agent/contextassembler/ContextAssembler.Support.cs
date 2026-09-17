using Microsoft.Extensions.Logging;
using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.context;

public partial class ContextAssembler : IContextAssembler
{
    
    /// <summary>
    /// 计算 Token 分配
    /// </summary>
    private Dictionary<DataSourceType, int> CalculateTokenAllocation(
        List<ContextSnippet> snippets,
        ContextAssemblyRequest request)
    {
        var allocation = new Dictionary<DataSourceType, int>();
        var totalQuota = request.SourceTokenQuota.Values.Sum();
        
        foreach (var source in request.EnabledSources)
        {
            var quota = request.SourceTokenQuota.GetValueOrDefault(source, 500);
            allocation[source] = Math.Min(quota, request.MaxTokenBudget);
        }
        
        return allocation;
    }
    
    /// <summary>
    /// 压缩片段
    /// </summary>
    private agent.contextgradient.ContextGradientCompressor _gradientCompressor;
    private readonly agent.contextgradient.CompressionBreaker _compressionBreaker = new(); // v0.13.3 D4

    static ContextAssembler()
    {
    }

    /// <summary>P3: bge 嵌入器注入 (可选) — 语义漂移校验启用; null → 纯锚词模式</summary>
    public agent.contextgradient.ITextEmbedder? Embedder
    {
        set => _gradientCompressor = new agent.contextgradient.ContextGradientCompressor(value);
    }

    private static readonly System.Text.RegularExpressions.Regex EnglishWordRegex = new("[A-Za-z]{3,}");

    /// <summary>锚词提取 (P1 启发式: 取出现 ≥2 次的 2-8 字中英词段, 前 8 个; P3 向量版替换)
    /// v0.16.4 R333 (P10 首段): CJK 2/3/4 字滑窗每位置 Substring → long key 零分配计数。
    /// v0.17.3 R338 (P10 收尾): English 提取 Regex.Matches (每匹配 m.Value+ToLowerInvariant
    /// = 2 短串分配 + MatchCollection) → Regex.EnumerateMatches(span) 零匹配对象 + ≤7 字符词
    /// 8bit/char long 键零分配计数 (ASCII 字母 |0x20 即小写; 8×7=56bit 无歧义), >7 词 string
    /// 兜底; 两路 distinct 首见登记 = match 序 = 内容首见序, 计数毕按登记序解码 count≥2 候选
    /// → 与原实现 (English match 序先、CJK len-major 后) 同插入序, 稳定排序输出全等。</summary>
    private static List<string> ExtractAnchorWords(string content)
    {
        var words = new Dictionary<string, int>(StringComparer.Ordinal);
        // English 词 ≤7 字符 → 8bit/char long 键零分配 (ASCII 字母 |0x20 即小写; 8×7=56bit
        // 无歧义); >7 → string 兜底 (长词稀有)。两路 distinct 首见登记 enOrder (EnumerateMatches
        // 枚举序 = match 序 = 内容首见序), 计数毕按登记序并入 words — count 相同的稳定排序
        // 输出与原实现 (每 match 立即入 string 字典) 完全一致。
        var enLong = new Dictionary<long, int>();
        var enStr = new Dictionary<string, int>(StringComparer.Ordinal);
        var enOrder = new List<(long Key, string? Word)>();
        foreach (var m in EnglishWordRegex.EnumerateMatches(content.AsSpan()))
        {
            if (m.Length <= 7)
            {
                long key = 0;
                for (var j = 0; j < m.Length; j++)
                    key |= (long)(content[m.Index + j] | 0x20) << (8 * j);
                if (!enLong.ContainsKey(key))
                    enOrder.Add((key, null));
                enLong[key] = enLong.GetValueOrDefault(key) + 1;
            }
            else
            {
                var w = content.Substring(m.Index, m.Length).ToLowerInvariant();
                if (!enStr.ContainsKey(w))
                    enOrder.Add((0, w));
                enStr[w] = enStr.GetValueOrDefault(w) + 1;
            }
        }
        Span<char> chars = stackalloc char[7]; // 8bit/char; 移出循环复用同栈槽 (CA2014), new string 即拷贝
        foreach (var (key, word) in enOrder)
        {
            if (word is not null)
            {
                if (enStr[word] >= 2)
                    words[word] = enStr[word];
                continue;
            }
            var count = enLong[key];
            if (count < 2)
                continue;
            var k = key;
            var len = 0;
            while (k != 0 && len < chars.Length)
            {
                chars[len] = (char)(k & 0xFF);
                k >>= 8;
                len++;
            }
            words[new string(chars[..len])] = count;
        }
        // 中文 2-4 字词 (滑动窗, 出现 ≥2 次) — long 编码键零分配。每 len 独立字典:
        // 编码低位=窗首字 (chars[0]), 解码按固定 len 正向移位取回 — 避免歧义与反序。
        var cjkWords2 = new Dictionary<long, int>();
        var cjkWords3 = new Dictionary<long, int>();
        var cjkWords4 = new Dictionary<long, int>();
        for (var i = 0; i + 2 <= content.Length; i++)
        {
            var c0 = content[i];
            if (!char.IsLetter(c0) || c0 < 0x4E00 || c0 > 0x9FFF)
                continue;
            long k2 = content[i] | ((long)content[i + 1] << 16);
            cjkWords2[k2] = cjkWords2.GetValueOrDefault(k2) + 1;
            if (i + 3 <= content.Length)
            {
                long k3 = k2 | ((long)content[i + 2] << 32);
                cjkWords3[k3] = cjkWords3.GetValueOrDefault(k3) + 1;
                if (i + 4 <= content.Length)
                {
                    long k4 = k3 | ((long)content[i + 3] << 48);
                    cjkWords4[k4] = cjkWords4.GetValueOrDefault(k4) + 1;
                }
            }
        }
        AddDecoded(cjkWords2, 2, words);
        AddDecoded(cjkWords3, 3, words);
        AddDecoded(cjkWords4, 4, words);
        return words.Where(kv => kv.Value >= 2)
            .OrderByDescending(kv => kv.Value)
            .Take(8)
            .Select(kv => kv.Key)
            .ToList();
    }

    private static void AddDecoded(Dictionary<long, int> src, int len, Dictionary<string, int> dst)
    {
        foreach (var kv in src)
        {
            if (kv.Value < 2)
                continue;
            var chars = new char[len];
            var k = kv.Key;
            for (var j = 0; j < len; j++)
            {
                chars[j] = (char)(k & 0xFFFF);
                k >>= 16;
            }
            dst[new string(chars)] = kv.Value;
        }
    }
}
