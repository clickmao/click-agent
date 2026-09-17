using System.Text;

namespace agent.context;

public static class ContinuationBrief
{
    public const string BlockTitle = "[承接状态 v1]";

    /// <summary>
    /// R460 精炼令: 注入块里最多列几项。用户令「r458回复要精炼」实测根因 = 块里列 8 项 ⇒
    /// 模型逐项复述 (T5 回复 241 字符)。降到 3 项 + 如实标注总数 (截断诚实性不丢)。
    /// </summary>
    public const int MaxArtifacts = 3;

    /// <summary>注入块长度上限 (机检: BuildBlock ≤ 此值; 控每轮 token 增量)。</summary>
    public const int MaxBlockChars = 200;

    /// <summary>菜单项数上限 (R460: 后续选择必须以「编号菜单」给出, 且不超过 3 项)。</summary>
    public const int MaxMenuItems = 3;

    /// <summary>菜单单项长度上限 (机检: 每项 ≤ 此值; 「精炼」的可验证形态)。</summary>
    public const int MaxMenuItemChars = 24;

    /// <summary>确定性反问长度上限 (机检: BuildAsk ≤ 此值)。</summary>
    public const int MaxAskChars = 220;

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

    /// <summary>承接块正文 (只列真实项; 空态写成"(无产物)"并禁止臆造)。R460: 紧凑 2 行, ≤ <see cref="MaxBlockChars"/>。</summary>
    public static string BuildBlock(IReadOnlyList<ArtifactFact>? artifacts, int total = -1)
    {
        var arts = artifacts ?? Array.Empty<ArtifactFact>();
        if (total < arts.Count) total = arts.Count;
        var sb = new StringBuilder(MaxBlockChars + 40);
        sb.Append(BlockTitle).Append('\n');
        if (arts.Count == 0)
        {
            sb.Append("已有: (无产物)\n");
        }
        else
        {
            sb.Append("已有: ");
            for (var i = 0; i < arts.Count; i++)
            {
                if (i > 0) sb.Append(" | ");
                AppendFact(sb, arts[i]);
            }
            // 如实标注截断: 免得模型自己发现"清单被截断"并写进回复 (R458 run1 实测)
            if (total > arts.Count)
                sb.Append(" …共 ").Append(total).Append(" 项, 只列最近 ").Append(arts.Count).Append(" 项");
            sb.Append('\n');
        }
        sb.Append("本轮=承接/追问(无新任务对象)。回复: 一句承接");
        sb.Append(arts.Count == 0
            ? " + 反问\"继续什么\"并请对方给具体动作; 不得列举任何文件或完成状态 —— 确实没有。\n"
            : " + 反问\"继续什么\" + 2–3 句可选项(用上面的真实项); 不复述本块, 不加解释。\n");
        return sb.ToString();
    }

    /// <summary>
    /// R460: 后续选择的**编号菜单** (单源 —— 门问句与兜底反问共用同一批真实事实)。
    /// 首项接地到最近改动的真实产物; 无产物 ⇒ 单项「说清要我做什么」, 绝不臆造候选。
    /// </summary>
    public static IReadOnlyList<string> BuildMenu(IReadOnlyList<ArtifactFact>? artifacts, int total = -1)
    {
        var arts = artifacts ?? Array.Empty<ArtifactFact>();
        if (total < arts.Count) total = arts.Count;
        if (arts.Count == 0) return ["说清要我做什么"];
        var list = new List<string>(MaxMenuItems) { "接着 " + Shorten(arts[0].Name, MaxMenuItemChars - 6) + " 往下做" };
        if (total > 1) list.Add("汇总现有 " + total + " 项产物");
        list.Add("换一个新任务");
        return list;
    }

    /// <summary>
    /// R460 单源反问: 门问句 (EvidenceGate) 与链兜底 (ComposeFallback) 用**同一个**构造器 ⇒
    /// 「先承接真实事实 + 再反问『继续什么』+ 编号菜单」在两条路径上恒同形, 不靠模型自觉。
    /// </summary>
    public static string BuildAsk(string? userText, IReadOnlyList<ArtifactFact>? artifacts, int total = -1)
    {
        var arts = artifacts ?? Array.Empty<ArtifactFact>();
        if (total < arts.Count) total = arts.Count;
        var head = Shorten(userText, 12);
        var sb = new StringBuilder(MaxAskChars + 40);
        sb.Append('「').Append(head).Append("」我这边没有待办指令");
        if (arts.Count == 0)
        {
            sb.Append(" (本会话还没有产物)。继续什么？说一句具体要我做什么就行。");
            return sb.ToString();
        }
        sb.Append("。已有: ");
        for (var i = 0; i < arts.Count; i++)
        {
            if (i > 0) sb.Append('、');
            sb.Append(arts[i].Name);
            if (arts[i].Bytes == 0 && arts[i].FirstLine.Length == 0) sb.Append("=(空)");
            else if (arts[i].FirstLine.Length > 0) sb.Append('=').Append(arts[i].FirstLine);
        }
        if (total > arts.Count) sb.Append(" 等 ").Append(total).Append(" 项");
        sb.Append("。你要接着哪一项？\n");
        var menu = BuildMenu(arts, total);
        for (var i = 0; i < menu.Count; i++) sb.Append(i + 1).Append(". ").Append(menu[i]).Append('\n');
        return sb.ToString().TrimEnd();
    }

    /// <summary>
    /// R461: 单条产物事实的渲染 (块与问句共用) —— **零字节文件如实标 "(空)"**。
    /// 实发证据 (R460 run T4): 0 B 产物未标空 ⇒ 模型改用记忆里的假值宣称"已写入 chars=15" ⇒ 产物不落地。
    /// 诚实边界: 标空只让缺口**可见**, 不阻止模型编造 (编造面由产物收口闸单独负责)。
    /// </summary>
    private static void AppendFact(StringBuilder sb, ArtifactFact a)
    {
        sb.Append(a.Name);
        if (a.Bytes == 0 && a.FirstLine.Length == 0) sb.Append("=(空)");
        else if (a.FirstLine.Length > 0) sb.Append('=').Append(a.FirstLine);
        sb.Append(" (").Append(a.Bytes).Append("B)");
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

    /// <summary>
    /// R466 本地结算类的**唯一字符串口径** —— 与 IndustrialAgentV2 的 skip 层打点
    /// (「kind」字段) 及判据同源; 两处漂移会让优先级规则静默失效 (机检见 G40)。
    /// </summary>
    public const string SettleRepeatVerbatim = "repeat_verbatim";

    /// <summary>
    /// R498 候选③ (R413 主线): 本地**改写**结算类 —— 答复对象是「上一条助手实质答复的改写」。
    ///
    /// 与 <see cref="SettleRepeatVerbatim"/> 同因同理: 对象真实存在 (链自己刚取到那一条实质答复)、
    /// 内容承载 (不是模板/确认语) ⇒ 「本轮无可确定的答复对象」这一前提同样不成立 ⇒ 承接反问不得覆盖。
    /// 若不给本类开这个口, 改写轮的成果会在下游被兜底横幅整条顶掉 —— 表现与 R465 的 t6 失守同形。
    /// </summary>
    public const string SettleLocalParaphrase = "local_paraphrase";

    /// <summary>
    /// R466 优先级判定 (纯函数, 单源): 承接反问**不得**覆盖已经确定性落地的本地答复。
    ///
    /// 因果链 (不是文风评判): 承接反问的**前提**是「本轮无可确定的答复对象」——
    /// 见 <see cref="IsContinuationTurn"/> 判据 (意图弱 + 无更具体缺口)。
    /// 而纯复述轮 (settleKind = <see cref="SettleRepeatVerbatim"/>) 的答复对象**就是**
    /// 会话里上一条助手答复原文: 真实存在、逐字可核验、链自己刚取到 ⇒ 前提不成立 ⇒ 覆盖非法。
    ///
    /// 实测依据 (R465 p12 网格 / role=skeptic / 同 AOT 二进制): t6「再讲一遍。」本应回放
    /// 上一条答复 (21 字符), 却被承接反问覆盖成 46 字符 ⇒ 预注册判据 C3 FAIL ("回复质量不降" 硬线失守)。
    /// 开关消融: 关掉优先级 (settleKind 视作 null) 必须复现该覆盖 —— 否则判据没绑到机制上 (负控)。
    ///
    /// R498 候选③: 判定面由「一个本地结算类」扩为「本地结算类集合」——
    /// <see cref="SettleRepeatVerbatim"/> (回放) 与 <see cref="SettleLocalParaphrase"/> (改写)
    /// 同属「答复对象已被链自己确定」, 共用同一条「前提不成立」的论证 ⇒ 单源收敛到此判定。
    /// </summary>
    public static bool ShouldApplyFallback(string? settleKind, string? reply, IReadOnlyList<ArtifactFact>? artifacts)
        => !IsLocalSettled(settleKind)
           && NeedsFallback(reply, artifacts);

    /// <summary>
    /// R498 候选③: 本地结算类 (答复对象已由链自己确定) 的**单源**判定。
    /// 新增本地结算类只在此处登记一次 —— 否则优先级规则会在新通道上静默失效。
    /// </summary>
    public static bool IsLocalSettled(string? settleKind)
        => string.Equals(settleKind, SettleRepeatVerbatim, StringComparison.Ordinal)
           || string.Equals(settleKind, SettleLocalParaphrase, StringComparison.Ordinal);

    /// <summary>确定性兜底反问 —— R460 起与门问句**同源** (<see cref="BuildAsk"/>): 事实为空时绝不提任何文件名。</summary>
    public static string ComposeFallback(string? userText, IReadOnlyList<ArtifactFact>? artifacts, int total = -1)
        => BuildAsk(userText, artifacts, total);

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
