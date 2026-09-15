using System.Text;

namespace agent.core;

/// <summary>
/// R462 召回-现实一致性闸 (链机制, 非提示词补丁)。
///
/// 依据 (R460/R461 实发证据): 召回块/记忆块里的**机器可检事实** (文件名 + 声明的内容/体量) 被当成本轮真值 ——
///   模型据此宣称「stats.txt 已写入 chars=15」而当前工作区根本没有该文件 (磁盘 0 B) ⇒ 产物 3/4 + 编造。
/// 用户令 (承重): 「利用 r1 对真假信息判别」——本闸是**该判别的外部真值面**: 真假不由模型自判,
///   由**当前工作区文件系统**裁决 (可复算、可机检、零模型成本)。
///
/// 判据形 (机检可断言):
///   ① 凡含「路径样 token」的子句, 输出必带核验标签 (核验✓ 现存 N B / 核验✗ 当前不存在);
///   ② 路径判定 = **结构判定** (含 '.' 且非纯数字的 token), 零后缀白名单 —— 承 R447 语言无关令;
///   ③ 无 workspace root / 异常 / 超界 ⇒ fail-safe 原样返回 (绝不因闸失败而丢事实或造事实);
///   ④ 幂等: 已带标签的块二次通过不重复追加。
///
/// 纪律: 零反射 / 零 shell / 零正则; 探测次数与子句数有界; 越界路径 (..) 一律判 ✗ 且不探测。
/// </summary>
public static class RecallRealityGate
{
    /// <summary>核验通过标签前缀 (机检锚点)。</summary>
    public const string OkTag = "[核验✓ ";

    /// <summary>核验失败标签前缀 (机检锚点)。</summary>
    public const string BadTag = "[核验✗ ";

    /// <summary>单次 Verify 处理的子句上限 (有界; 超出部分原样透传)。</summary>
    public const int MaxClauses = 128;

    /// <summary>单次 Verify 的文件系统探测次数上限 (有界; 超出部分原样透传)。</summary>
    public const int MaxProbes = 128;

    /// <summary>候选路径 token 的字符上限 (超过视为自然语言长词, 不探测)。</summary>
    public const int MaxTokenChars = 120;

    /// <summary>子句分隔符 (任一出现即断句; 不消费字符)。</summary>
    private static readonly char[] ClauseSeparators = [';', '；', '、', '|'];

    /// <summary>token 分隔符: 落在这些字符上的片段不与路径拼接。</summary>
    private static readonly char[] TokenSeparators =
        [' ', '\t', '=', ':', '：', ',', '，', '(', ')', '（', '）', '[', ']', '【', '】', '"', '\'', '“', '”', '「', '」', '…', '→', '⇒'];

    /// <summary>
    /// 对整块文本做召回-现实一致性核验。
    /// <paramref name="workspaceRoot"/> 为空或不存在 ⇒ 原样返回 (fail-safe)。
    /// <paramref name="failOnly"/> = true ⇒ **只打假** (与现实不一致才追加 ✗ 标签;
    ///   一致时零字节注入 —— 用于每轮都进 prompt 的召回片段, 守住 token 预算)。
    /// </summary>
    public static string Verify(string? block, string? workspaceRoot, bool failOnly = false)
    {
        if (string.IsNullOrEmpty(block)) return block ?? string.Empty;

        var root = NormalizeRoot(workspaceRoot);
        if (root is null) return block;

        // 幂等: 已核验过的块不再二次加工 (块可能被多条路径复用)。
        if (block.Contains(OkTag, StringComparison.Ordinal) || block.Contains(BadTag, StringComparison.Ordinal))
            return block;

        var sb = new StringBuilder(block.Length + 64);
        var clauseNo = 0;
        var probeNo = 0;

        var start = 0;
        for (var i = 0; i <= block.Length; i++)
        {
            var isEnd = i == block.Length;
            var isSep = !isEnd && (block[i] == '\n' || Array.IndexOf(ClauseSeparators, block[i]) >= 0);
            if (!isEnd && !isSep) continue;

            var clause = block[start..i];
            start = i + 1;
            sb.Append(clause);
            if (isSep) sb.Append(block[i]);

            if (string.IsNullOrWhiteSpace(clause)) continue;
            if (clauseNo++ >= MaxClauses) continue;

            var token = FindPathToken(clause);
            if (token is null) continue;

            if (probeNo++ >= MaxProbes)
            {
                sb.Append(BadTag).Append("未核验(超探测上限)]");
                continue;
            }

            var (exists, bytes, outside) = Probe(root, token);
            if (outside) sb.Append(BadTag).Append("越界路径, 已拒绝)]");
            else if (exists && !failOnly) sb.Append(OkTag).Append("现存 ").Append(bytes).Append("B]");
            else if (!exists) sb.Append(BadTag).Append("当前工作区不存在该文件]");
        }

        return sb.ToString();
    }

    /// <summary>
    /// 结构判定一个「路径样 token」(**无后缀白名单**, 承 R447 语言无关令):
    /// 含 '.' 或 '/' + 非纯数字 + 无 '..' + ≤ <see cref="MaxTokenChars"/> + 至少一个字母或数字。
    /// </summary>
    public static string? FindPathToken(string clause)
    {
        string? best = null;
        var cur = new StringBuilder(64);
        void Flush()
        {
            if (cur.Length > 0)
            {
                var t = cur.ToString();
                if ((IsPathLike(t) || IsTraversalLike(t)) && (best is null || t.Length > best.Length)) best = t;
                cur.Clear();
            }
        }
        foreach (var ch in clause)
        {
            if (Array.IndexOf(TokenSeparators, ch) >= 0) Flush();
            else cur.Append(ch);
        }
        Flush();
        return best;
    }

    /// <summary>结构判定 (不依赖任何语言/后缀清单)。</summary>
    public static bool IsPathLike(string token)
    {
        if (token.Length == 0 || token.Length > MaxTokenChars) return false;
        // ASCII-only: 非 ASCII 文本 (如「提升3.2倍」) 不作事实锚 —— 边界见计划文档。
        var letter = false;
        foreach (var ch in token)
        {
            if (ch > 0x7F) return false;
            if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z')) letter = true;
        }
        if (!letter) return false;                 // 纯数字/小数 (1.5) 不算路径
        var hasDotOrSlash = token.IndexOf('.') >= 0 || token.IndexOf('/') >= 0 || token.IndexOf('\\') >= 0;
        if (!hasDotOrSlash) return false;
        var dot = token.IndexOf('.');
        if (dot == 0) return false;                // 隐藏文件/纯后缀, 不作为事实锚
        var lastDot = token.LastIndexOf('.');
        if (lastDot == token.Length - 1) return false;
        for (var i = lastDot + 1; i < token.Length; i++)
        {
            var ch = token[i];
            if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9'))) return false;
        }
        if (token.Length - lastDot - 1 > 12) return false;
        return true;
    }

    /// <summary>越界候选 (含 '..') —— 结构判定用, 调用方一律判 ✗ 且不探测。</summary>
    public static bool IsTraversalLike(string token)
        => token.Contains("..", StringComparison.Ordinal)
           && (token.IndexOf('/') >= 0 || token.IndexOf('\\') >= 0 || token.IndexOf('.') >= 0);

    /// <summary>
    /// 在工作区探测 (有界: 直接相对路径 + 一层子目录同名)。
    /// 返回 (是否存在, 字节数, 是否越界)。任何异常 ⇒ 视为不存在 (不抛)。
    /// </summary>
    public static (bool Exists, long Bytes, bool Outside) Probe(string root, string token)
    {
        try
        {
            var sep = Path.DirectorySeparatorChar;
            var rel = token.Replace('/', sep).Replace('\\', sep);
            var full = Path.GetFullPath(Path.Combine(root, rel));
            if (!full.StartsWith(root, StringComparison.Ordinal)) return (false, 0, true);
            if (File.Exists(full)) return (true, new FileInfo(full).Length, false);

            var name = Path.GetFileName(rel);
            if (name.Length == 0) return (false, 0, false);
            var n = 0;
            foreach (var dir in Directory.EnumerateDirectories(root))
            {
                if (n++ >= 32) break;
                var cand = Path.Combine(dir, name);
                if (File.Exists(cand)) return (true, new FileInfo(cand).Length, false);
            }
            return (false, 0, false);
        }
        catch
        {
            return (false, 0, false);
        }
    }

    /// <summary>规范化工作区根 (必须存在且非空; 否则返回 null ⇒ 调用方 fail-safe)。</summary>
    private static string? NormalizeRoot(string? workspaceRoot)
    {
        if (string.IsNullOrWhiteSpace(workspaceRoot)) return null;
        try
        {
            var full = Path.GetFullPath(workspaceRoot);
            if (!Directory.Exists(full)) return null;
            var sep = Path.DirectorySeparatorChar;
            return full.EndsWith(sep) ? full : full + sep;
        }
        catch
        {
            return null;
        }
    }
}
