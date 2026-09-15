using System.Text;

namespace agent.context;

/// <summary>
/// R458 承接轮 (degenerate / continuation turn) 的**人性化接地**机制。
///
/// 用户令 (2026-09-15): 「一个人对另一个人突然说一句"继续"，另一个人不明所以，肯定就会反问"继续什么"」
///   ⇒ 机器味问句 ("意图不明确，你想让 agent 做什么? (如: 搜索/写文档/…)") 换成**先承接真实状态, 再反问**。
///
/// 链机制 (非关键字补丁):
///   ① 判定面: 复用**既有**意图置信度分支 (WeakIntent/TooVague 且无更具体缺口) —— 不新立关键词表;
///   ② 接地面: 只在承接轮注入本块, 内容 = **工作区真实产物** (名字/字节/首行), 逐项可机检;
///   ③ 收口面: 模型若没接地 (回复既无问句又不含任何真实产物名) ⇒ 链自身用同一批事实组装反问 (fail-closed)。
///
/// 纪律: 零反射 / 零 shell / 零正则; 只读首行; 块内出现的每个文件名必须来自扫描结果 —— 负控保证:
///   扫描为空 ⇒ 块内不得出现任何文件名, 也从不得出现未扫描到的名字。
/// </summary>
public readonly record struct ArtifactFact(string Name, long Bytes, string FirstLine);

public static class ContinuationBrief
{
    public const string BlockTitle = "[承接状态 v1]";

    /// <summary>注入块里最多列几项 (长工作区不刷屏, 且控制本轮 token 增量)。</summary>
    public const int MaxArtifacts = 8;

    /// <summary>
    /// 承接轮置信下限 —— 与 <see cref="agent.registry.EvidenceGate"/> 默认阈值同源。
    /// R458 实测教训: 只看 flags 会误判 (问句「当前目录下一共有几个 .py 文件？」置信 0.8,
    /// 意图层标了弱意图但**门并未发问**) ⇒ 判定必须与门**同一判据**: flags 弱且置信度低于门限。
    /// </summary>
    public const double ConfidenceFloor = 0.60;

    /// <summary>产物首行的字符上限 (超长行截断; 只用于让模型"认得出这是什么")。</summary>
    public const int MaxFirstLineChars = 40;

    /// <summary>目录扫描条目上限 (有界: 不因工作区膨胀而变慢)。</summary>
    public const int MaxScanEntries = 512;

    /// <summary>读首行时的字节上限 (只读文件头, 不整文件载入)。</summary>
    private const int HeadBytes = 256;

    /// <summary>工作区自身的运行时目录/文件, 不算"用户产物" (不计入承接事实)。</summary>
    private static readonly string[] NoiseNames =
    [
        "data", "logs", "log", "bin", "obj", ".git", ".hermes", "node_modules", ".vs", "artifacts", "out", "publish"
    ];

    /// <summary>
    /// 承接轮判定: **复用 EvidenceGate 的同一条分支判据** (子句意图弱/过短, 置信度低于门限,
    /// 且没有更具体的缺口: 缺参数 / 指代不明 / 疑似省略依赖)。判据是意图层的既有结论, 不是新加的关键词表。
    /// </summary>
    public static bool IsContinuationTurn(IReadOnlyList<agent.intent.IntentDecomposer.SubTask>? subTasks)
    {
        if (subTasks is null || subTasks.Count == 0) return false;
        foreach (var t in subTasks)
        {
            if (t.Confidence >= ConfidenceFloor) return false;
            var f = t.Flags;
            var weak = (f & agent.intent.IntentDecomposer.ConfidenceFlags.WeakIntent) != 0
                    || (f & agent.intent.IntentDecomposer.ConfidenceFlags.TooVague) != 0;
            if (!weak) return false;
            var concrete = (f & agent.intent.IntentDecomposer.ConfidenceFlags.MissingParameter) != 0
                        || (f & agent.intent.IntentDecomposer.ConfidenceFlags.AmbiguousReference) != 0
                        || (f & agent.intent.IntentDecomposer.ConfidenceFlags.SuspiciousDependency) != 0;
            if (concrete) return false;
        }
        return true;
    }

    /// <summary>
    /// 扫描工作区产物 (真实磁盘事实; 异常一律降级为空表, 绝不抛出/绝不编造)。
    /// <paramref name="total"/> 返回**扫描到的总项数** —— 块里必须如实标注"只列最近 N 项/共 M 项",
    /// 否则模型会自己发现清单被截断并写进回复 (R458 run1 实测: 它质疑"承接状态里只列了 c.py、d.py")。
    /// </summary>
    public static IReadOnlyList<ArtifactFact> ScanArtifacts(string? root, int max, out int total)
    {
        total = 0;
        var list = new List<ArtifactFact>();
        if (string.IsNullOrWhiteSpace(root) || max <= 0) return list;

        string full;
        try { full = Path.GetFullPath(root); } catch { return list; }
        if (!Directory.Exists(full)) return list;

        var cands = new List<(DateTime Ts, string Rel)>();
        var scanned = 0;
        try
        {
            foreach (var p in Directory.EnumerateFileSystemEntries(full))
            {
                if (scanned++ >= MaxScanEntries) break;
                var name = Path.GetFileName(p);
                if (name.Length == 0 || name[0] == '.') continue;
                if (IsNoise(name)) continue;
                try
                {
                    if (Directory.Exists(p))
                    {
                        foreach (var c in Directory.EnumerateFiles(p))
                        {
                            if (scanned++ >= MaxScanEntries) break;
                            var cn = Path.GetFileName(c);
                            if (cn.Length == 0 || cn[0] == '.') continue;
                            cands.Add((File.GetLastWriteTimeUtc(c), name + "/" + cn));
                        }
                    }
                    else
                    {
                        cands.Add((File.GetLastWriteTimeUtc(p), name));
                    }
                }
                catch { /* 单项失败不影响整体 */ }
            }
        }
        catch { return list; }

        cands.Sort(static (a, b) => b.Ts.CompareTo(a.Ts));
        total = cands.Count;
        foreach (var c in cands)
        {
            if (list.Count >= max) break;
            long bytes = 0;
            var first = string.Empty;
            try
            {
                var path = Path.Combine(full, c.Rel.Replace('/', Path.DirectorySeparatorChar));
                bytes = new FileInfo(path).Length;
                first = ReadFirstLine(path);
            }
            catch { /* 读不到就用空首行, 但名字仍是真实存在的条目 */ }
            list.Add(new ArtifactFact(c.Rel, bytes, first));
        }
        return list;
    }

    /// <summary>承接块正文 (只列真实项; 空态 ⇒ 明确写"(无)"并禁止臆造)。</summary>
    public static string BuildBlock(IReadOnlyList<ArtifactFact>? artifacts, int total = -1)
    {
        var arts = artifacts ?? Array.Empty<ArtifactFact>();
        if (total < arts.Count) total = arts.Count;
        var sb = new StringBuilder(320);
        sb.Append(BlockTitle).Append(" (真实状态; 只列实际存在的项)\n");
        if (arts.Count == 0)
        {
            sb.Append("- 工作区产物: (无)\n");
        }
        else
        {
            sb.Append("- 工作区产物: ");
            for (var i = 0; i < arts.Count; i++)
            {
                if (i > 0) sb.Append(" | ");
                sb.Append(arts[i].Name).Append('=');
                sb.Append(arts[i].FirstLine.Length > 0 ? arts[i].FirstLine : "(空)");
                sb.Append(" (").Append(arts[i].Bytes).Append(" B)");
            }
            // 如实标注截断: 免得模型自己发现"清单被截断"并写进回复 (R458 run1 实测)
            if (total > arts.Count)
                sb.Append(" (共 ").Append(total).Append(" 项, 只列最近 ").Append(arts.Count).Append(" 项)");
            sb.Append('\n');
        }
        sb.Append("- 本轮性质: 承接/追问式输入 —— 没有给出新的任务对象。\n");
        sb.Append("- 回复要求: 先用一句话按上面的真实项承接 (逐项, 像人一样");
        sb.Append(arts.Count == 0
            ? "); 再反问\"继续什么\"并请对方给出具体动作。不得列举任何文件或完成状态 —— 确实没有。\n"
            : "); 再反问\"继续什么\"并给 2–3 个具体可选项。不得增补上面没列出的文件或完成状态。\n");
        return sb.ToString();
    }

    /// <summary>
    /// 收口判据: 承接轮的回复是否**没接地** —— 空回复, 或既无问句又不含任何真实产物名。
    /// 这是链的 fail-closed 闸门 (命中 ⇒ 用同一批事实组装反问), 不是对文风的评判。
    /// </summary>
    public static bool NeedsFallback(string? reply, IReadOnlyList<ArtifactFact>? artifacts)
    {
        if (string.IsNullOrWhiteSpace(reply)) return true;
        var hasQuestion = reply.IndexOf('?') >= 0 || reply.IndexOf('？') >= 0;
        if (hasQuestion) return false;
        var arts = artifacts;
        if (arts is null || arts.Count == 0) return true; // 无事实可用 ⇒ 无问句就是没承接
        foreach (var a in arts)
            if (a.Name.Length > 0 && reply.Contains(a.Name, StringComparison.Ordinal)) return false;
        return true;
    }

    /// <summary>确定性兜底反问 (只用真实事实; 事实为空时绝不提任何文件名)。</summary>
    public static string ComposeFallback(string? userText, IReadOnlyList<ArtifactFact>? artifacts)
    {
        var head = Shorten(userText, 12);
        var arts = artifacts ?? Array.Empty<ArtifactFact>();
        var sb = new StringBuilder(200);
        if (arts.Count == 0)
        {
            sb.Append('「').Append(head).Append("」这句我这边没有可对齐的待办上下文 (本会话还没有产物)。");
            sb.Append("继续什么？说一句具体要我做什么就行。");
            return sb.ToString();
        }
        sb.Append('「').Append(head).Append("」我这边没有待办指令。会话里已经有的产物: ");
        for (var i = 0; i < arts.Count; i++)
        {
            if (i > 0) sb.Append("、");
            sb.Append(arts[i].Name);
            if (arts[i].FirstLine.Length > 0) sb.Append('=').Append(arts[i].FirstLine);
        }
        sb.Append("。你是想接着其中哪一项, 还是换新任务？");
        return sb.ToString();
    }

    private static bool IsNoise(string name)
    {
        foreach (var n in NoiseNames)
            if (string.Equals(n, name, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private static string ReadFirstLine(string path)
    {
        var buf = new byte[HeadBytes];
        int read;
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, HeadBytes, FileOptions.SequentialScan))
        {
            read = fs.Read(buf, 0, buf.Length);
        }
        if (read <= 0) return string.Empty;
        var text = Encoding.UTF8.GetString(buf, 0, read);
        var cut = text.IndexOfAny(['\n', '\r']);
        if (cut >= 0) text = text[..cut];
        return Shorten(text, MaxFirstLineChars);
    }

    private static string Shorten(string? s, int max)
    {
        if (string.IsNullOrWhiteSpace(s)) return string.Empty;
        var t = s.Trim();
        return t.Length <= max ? t : t[..max];
    }
}
