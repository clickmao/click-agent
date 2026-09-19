using agent.nlp;

namespace agent.intent;

/// <summary>
/// 任务无关性判定 (v7.15 隔离任务 I.2) — 纯规则打分, 无 LLM 参与。
/// 判定"主任务执行中收到的新提问是否与当前目标无关" → 无关则开隔离子 agent。
/// 锚 = SessionMemory.GoalProfile.KeyEntities (v7.14 ③)。
/// </summary>
public static class TaskRelevanceChecker
{
    /// <summary>
    /// 证据充分性下限 (token 数, o200k 口径实测校准) — 无词表后「离题」结论必须建立在充分文本证据上:
    /// 短消息一律不下结论 (fail-safe, 防指代/追问/新语言被错杀)。校准点: 指代/追问短句 2..11 token
    /// (须不隔离) vs 长离题句 14/26 token (须隔离)。
    /// 已知边界 (诚实记录): 短句且确属无关新任务 (如 "帮我查一下明天天气") 也不再隔离 —
    /// 它与指代追问在 token 口径上不可分, 按 fail-safe 方向让位。
    /// </summary>
    public const int EvidenceTokenFloor = 12;

    /// <summary>无关判定阈值 (无关分 ≥ 此值且无指代词 → 隔离任务)</summary>
    public const int DefaultIsolationThreshold = 2;

    /// <summary>简单中文实体抽取 — 已改为**现有机制** `agent.nlp.TextSignal.KeyTokens` (fastText 语言标签 + o200k BPE 分词)。
    /// 原实现只认 ASCII 字母数字 + CJK 0x4E00-0x9FFF 码点区间 (词表时代): 对俄语/日语/阿拉伯语/新梗抽取为空 ⇒ 判定停摆。</summary>
    public static List<string> ExtractEntities(string text) =>
        TextSignal.KeyTokens(text)
            // 单字 token 无区分度 (o200k 会把中文切成单字), 会造成字面假重叠 ⇒ 污染「零重叠」判据
            .Where(t => t.Length >= 2)
            .Distinct(StringComparer.Ordinal)
            .ToList();

    /// <summary>v0.11.0 R39b: 两 token 是否共享 ascii 4-gram (连写技术名交叉匹配, 忽略大小写)。</summary>
    private static bool SharesAsciiGram(string a, string b)
    {
        if (a.Length < 4 || b.Length < 4)
            return false;
        if (!a.Any(char.IsAsciiLetter) || !b.Any(char.IsAsciiLetter))
            return false;
        var gramsA = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i + 4 <= a.Length; i++)
            gramsA.Add(a.Substring(i, 4));
        for (var i = 0; i + 4 <= b.Length; i++)
            if (gramsA.Contains(b.Substring(i, 4)))
                return true;
        return false;
    }

    // (原 IsStopword / NormCache 随中文词表一并移除 — 现机制不再需要停用词与词表归一化缓存)

    /// <summary>
    /// R183 归一化: 去空白/标点/符号 + 全角→半角 + 小写。
    /// 使词表匹配对"空格/标点插入、全半角混排"机械免疫。
    /// </summary>
    private static string Normalize(string text)
    {
        var sb = new System.Text.StringBuilder(text.Length);
        foreach (var ch in text)
        {
            var c = ch;
            if (c == 0x3000) c = ' ';                                   // 全角空格
            else if (c >= 0xFF01 && c <= 0xFF5E) c = (char)(c - 0xFEE0); // 全角 ASCII → 半角
            if (char.IsWhiteSpace(c) || char.IsPunctuation(c) || char.IsSymbol(c))
                continue;                                                // 中英文标点统一消失
            sb.Append(char.ToLowerInvariant(c));
        }
        return sb.ToString();
    }

    /// <summary>
    /// 无关性判定。返回 (isIsolated, score, reason) 供审计。
    /// score 越高越可能无关: 实体重叠 0 +2 / 意图类别不同 +1 / 显式离题词 +1; 指代词一票否决 (score 清零)。
    /// </summary>
    public static (bool IsIsolated, int Score, string Reason) Check(
        IReadOnlyList<string> goalKeyEntities, string goalIntent, string incomingMessage, string incomingIntent,
        int threshold = DefaultIsolationThreshold)
    {
        if (string.IsNullOrWhiteSpace(incomingMessage))
            return (false, 0, "空消息");

        // R183 归一化层保留 (仅服务长度/结构信号; 词表匹配已全部移除)。
        var normalized = Normalize(incomingMessage);

        // 原四张中文词表 (指代词/离题词/实现询问词/纯疑问词) 已移除 ⇒ 词表槽位由**证据充分性**承担:
        // 有锚时, 短消息 (token 数 < EvidenceTokenFloor) 或跨语言 (语义不可比) ⇒ 一律不下「离题」结论。
        // fail-safe: 宁可交 LLM 也不用无证据的规则错杀; 依据 = agent.nlp 的语言标签 + 分词 (语言无关)。
        var anchorText = string.Join(" ", goalKeyEntities);
        var msgTokens = TextSignal.TokenCount(incomingMessage);
        var floorReasons = new List<string>();
        // 跨语言**不**参与本否决 (换一种语言的新任务照样该隔离; 语言只服务于 NlpGate 的"本地消化 vs 升级"面)。
        if (goalKeyEntities.Count > 0 && anchorText.Length > 0 && msgTokens > 0 && msgTokens < EvidenceTokenFloor)
            floorReasons.Add($"短消息证据不足 token={msgTokens}<{EvidenceTokenFloor}");

        var score = 0;
        var reasons = new List<string>();

        // 实体重叠: 目标 KeyEntities ∩ 新消息实体 = 0 → +2
        // v0.11.0 R39b: ascii 长词含连写技术名 (RESTAPI vs FastAPI) 互不 Contains → 误判零重叠。
        // 补充 4-gram 交叉匹配: 两词共享 ≥1 个 ascii 4-gram 即视为重叠 (RESTAPI∩FastAPI = {"stap","tapi"}→"stap"? 
        // restapi 4grams: rest,esta,stap,tapi; fastapi: fast,asta,stap,tapi → 共享 stap/tapi ✓)
        var incomingEntities = ExtractEntities(incomingMessage);
        var overlap = goalKeyEntities.Count == 0 || incomingEntities.Count == 0
            ? 0
            : goalKeyEntities.Count(e => incomingEntities.Any(i =>
                i.Contains(e, StringComparison.OrdinalIgnoreCase) ||
                e.Contains(i, StringComparison.OrdinalIgnoreCase) ||
                SharesAsciiGram(e, i)));
        if (goalKeyEntities.Count > 0 && overlap == 0 && incomingEntities.Count > 0)
        {
            score += 2;
            reasons.Add("实体零重叠");
        }
        else if (overlap > 0)
        {
            score -= 2;
            reasons.Add($"实体重叠 {overlap}");
        }

        // 意图类别不同 → +1
        if (!string.IsNullOrEmpty(goalIntent) && !string.IsNullOrEmpty(incomingIntent) &&
            !string.Equals(goalIntent, incomingIntent, StringComparison.OrdinalIgnoreCase))
        {
            score += 1;
            reasons.Add($"意图不同 {goalIntent}→{incomingIntent}");
        }

        // (原「显式离题词表 +1」已移除 — 离题证据现由 实体零重叠 +2 / 意图不同 +1 承担,
        //  且必须通过上方的「证据充分性」闸: 短消息/跨语言一律不下结论)

        // R183 结构信号 (语言无关): 归一化后极短 + 以问号结尾 = 元问询 (对历史的追问),
        // 不是新任务 → 减 1。对任何语言/新词生效 (不依赖词表); 长任务句不受影响。
        var isQuestion = incomingMessage.TrimEnd().EndsWith("?", StringComparison.Ordinal)
                      || incomingMessage.TrimEnd().EndsWith("？", StringComparison.Ordinal);
        if (isQuestion && normalized.Length <= 12)
        {
            score -= 1;
            reasons.Add("短问句元问询信号");
        }

        // 证据不足 (短消息/跨语言) ⇒ 不下「离题」结论 (score 保留供审计, 只否决 isolated)
        if (floorReasons.Count > 0)
        {
            reasons.AddRange(floorReasons);
            return (false, score, string.Join("; ", reasons));
        }

        var isolated = score >= threshold;
        return (isolated, score, string.Join("; ", reasons));
    }
}
