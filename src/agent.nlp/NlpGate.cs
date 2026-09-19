namespace agent.nlp;

/// <summary>
/// 闸族系 (NLP 版) — 流程: 文本 → NLP 结构化特征 → 闸判 → 通过则本地消化 / 不通过则直接交 LLM
/// → LLM 返回后回补「闸数据」(签名入库) → 下次同族输入本地通过 ⇒ **使用中自动升级, 无开发期预制规则**。
/// 判定依据只有两类模型输出: fastText 语言标签、ML.Tokenizers 分词; 无中文词表、无正则表、无标记枚举。
/// 持久化 = 行式文本 (零反射, AOT 安全), 上限封顶防膨胀。
///
/// R575: 补丁**按面隔离** —— 同一形状在不同族里语义不同 (复述 = 回放上一条答复 / 改写 = 本地改写 /
/// 声明词 = 本地改写的守卫面), 故回补与命中一律带面标; 行格式 `&lt;face&gt;\t&lt;signature&gt;`,
/// 无 tab 的旧行按「任意面」载入 (兼容零消费者的历史库, 不丢数据)。
/// </summary>
public static class NlpGate
{
    private const int MaxPatches = 4096;
    private const int SignatureTokens = 8;

    /// <summary>面标: 闸族系通用 (语言/分词语义面)。</summary>
    public const string FaceGate = "gate";

    /// <summary>面标: 纯复述族 (命中 ⇒ 本地回放上一条答复)。</summary>
    public const string FaceRepeat = "repeat";

    /// <summary>面标: 同义改写族 (命中 ⇒ 本地改写上一条答复)。</summary>
    public const string FaceParaphrase = "para";

    /// <summary>面标: 动作声明词面 (命中 ⇒ 本地改写守卫判「动作声明禁增」)。</summary>
    public const string FaceClaim = "claim";

    private const char FaceSeparator = '\t';

    private static readonly object Sync = new();
    private static readonly HashSet<string> Patches = new(StringComparer.Ordinal);
    private static string _patchPath = Path.Combine("data", "nlp", "gate-patches.txt");
    private static bool _loaded;
    private static long _localHits;
    private static long _escalations;
    private static long _learned;

    /// <summary>回补库路径 (测试/多实例可改; 改后下次访问重载)。</summary>
    public static string PatchPath
    {
        get => _patchPath;
        set
        {
            lock (Sync)
            {
                _patchPath = value;
                _loaded = false;
                Patches.Clear();
            }
        }
    }

    public static (long LocalHits, long Escalations, long Learned) Counters
    {
        get { lock (Sync) { return (_localHits, _escalations, _learned); } }
    }

    /// <summary>补丁键 = 面标 + 分隔符 + 签名 (回补与命中两侧共用, 防两面互相命中)。</summary>
    public static string Key(string face, string signature) => face + FaceSeparator + signature;

    /// <summary>文本签名 (公开读取面: 回补侧与判定侧必须看到同一个键)。</summary>
    public static string SignatureOf(string? text) => Signature(text ?? string.Empty);

    /// <summary>NLP 结构化特征: 语言标签 + token 数 + 关键词签名。</summary>
    public static GateFeatures Extract(string? text)
    {
        var s = text ?? string.Empty;
        return new GateFeatures(TextSignal.Language(s), TextSignal.TokenCount(s), Signature(s));
    }

    /// <summary>
    /// 补丁命中判定 (不计数, 纯查表): <paramref name="patches"/> 非空 ⇒ 只用给定集合 (判定纯函数化,
    /// 供机检/差分器具注入); 为空 ⇒ 读回补库。
    /// 空签名 (空文本 / 分词不可用) 一律不命中 ⇒ 方向恒为「交 LLM」(fail-safe)。
    /// </summary>
    public static bool IsPatched(string? text, string face, IReadOnlyCollection<string>? patches = null)
    {
        var sig = SignatureOf(text);
        if (sig.Length == 0)
        {
            return false;
        }

        var key = Key(face, sig);
        if (patches != null)
        {
            return patches.Contains(key) || patches.Contains(Key(string.Empty, sig));
        }

        lock (Sync)
        {
            Load();
            return Patches.Contains(key) || Patches.Contains(Key(string.Empty, sig));
        }
    }

    /// <summary>
    /// 闸判: 命中回补库 / 与锚文本同语言且关键词重叠 ⇒ 本地消化; 否则升级 LLM。
    /// 无锚文本 (首轮/无目标) ⇒ 一律升级 (不做无依据的本地消化)。
    /// </summary>
    public static GateDecision Decide(string? text, string? anchorText) => Decide(text, anchorText, FaceGate, null);

    /// <summary>带面的闸判 (面标只影响回补命中面; 语言/重叠面与面标无关)。</summary>
    public static GateDecision Decide(string? text, string? anchorText, string face, IReadOnlyCollection<string>? patches = null)
    {
        var f = Extract(text);
        if (f.TokenCount == 0)
        {
            return new GateDecision(true, "empty-input", f.Signature);
        }

        if (IsPatched(text, face, patches))
        {
            lock (Sync) { _localHits++; }
            return new GateDecision(true, "learned-patch", f.Signature);
        }

        if (string.IsNullOrWhiteSpace(anchorText))
        {
            lock (Sync) { _escalations++; }
            return new GateDecision(false, "no-anchor", f.Signature);
        }

        var a = Extract(anchorText);
        if (a.TokenCount == 0 || f.TokenCount == 0)
        {
            lock (Sync) { _escalations++; }
            return new GateDecision(false, "anchor-empty", f.Signature);
        }

        // 语言一致 + 签名 token 重叠 (模型输出驱动; 跨语言/新语言 ⇒ 自动升级而非错杀)
        var sameLanguage = string.Equals(a.Language, f.Language, StringComparison.Ordinal);
        var overlap = Overlap(a.Signature, f.Signature);
        if (sameLanguage && overlap > 0)
        {
            lock (Sync) { _localHits++; }
            return new GateDecision(true, "lang+token-overlap", f.Signature);
        }

        lock (Sync) { _escalations++; }
        return new GateDecision(false, sameLanguage ? "token-disjoint" : "language-shift", f.Signature);
    }

    /// <summary>LLM 返回后回补闸数据: 成功轮 ⇒ 该签名入库, 下次同族输入本地通过 (使用中自动升级)。</summary>
    public static void Observe(string? text, bool success) => Observe(text, success, FaceGate);

    /// <summary>带面的回补 (面标 = 该形状所属的判定面; 面不同则互不命中)。</summary>
    public static void Observe(string? text, bool success, string face)
    {
        if (!success)
        {
            return;
        }

        var f = Extract(text);
        if (f.TokenCount == 0 || f.Signature.Length == 0)
        {
            return;
        }

        var key = Key(face, f.Signature);
        lock (Sync)
        {
            Load();
            if (Patches.Count >= MaxPatches || !Patches.Add(key))
            {
                return;
            }

            _learned++;
            try
            {
                var dir = Path.GetDirectoryName(_patchPath);
                if (!string.IsNullOrEmpty(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                File.AppendAllText(_patchPath, key + Environment.NewLine);
            }
            catch (Exception)
            {
                // 落盘失败不影响主链 (内存补丁仍生效)
            }
        }
    }

    private static int Overlap(string a, string b)
    {
        if (a.Length == 0 || b.Length == 0)
        {
            return 0;
        }

        var set = new HashSet<string>(a.Split('|'), StringComparer.Ordinal);
        var n = 0;
        foreach (var token in b.Split('|'))
        {
            if (set.Contains(token))
            {
                n++;
            }
        }

        return n;
    }

    private static string Signature(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return string.Empty;
        }

        try
        {
            var tokens = TextSignal.KeyTokens(text, SignatureTokens)
                .Select(t => t.ToLowerInvariant())
                .Distinct(StringComparer.Ordinal)
                .OrderBy(t => t, StringComparer.Ordinal);
            return string.Join("|", tokens);
        }
        catch (Exception)
        {
            // 分词数据/原生库不可用 ⇒ 空签名 (不命中 ⇒ 交 LLM)。判定面不得因环境缺失而抛穿主链。
            return string.Empty;
        }
    }

    private static void Load()
    {
        if (_loaded)
        {
            return;
        }

        _loaded = true;
        try
        {
            if (!File.Exists(_patchPath))
            {
                return;
            }

            foreach (var line in File.ReadLines(_patchPath))
            {
                var s = line.Trim();
                if (s.Length == 0 || Patches.Count >= MaxPatches)
                {
                    continue;
                }

                Patches.Add(s.Contains(FaceSeparator) ? s : Key(string.Empty, s));
            }
        }
        catch (Exception)
        {
            // 读失败 ⇒ 空库 (闸退化为「无补丁」, 不影响安全方向: 一律升级 LLM)
        }
    }
}
