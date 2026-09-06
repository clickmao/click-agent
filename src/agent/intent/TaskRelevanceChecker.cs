namespace agent.intent;

/// <summary>
/// 任务无关性判定 (v7.15 隔离任务 I.2) — 纯规则打分, 无 LLM 参与。
/// 判定"主任务执行中收到的新提问是否与当前目标无关" → 无关则开隔离子 agent。
/// 锚 = SessionMemory.GoalProfile.KeyEntities (v7.14 ③)。
/// </summary>
public static class TaskRelevanceChecker
{
    /// <summary>指代词表 — 新消息依赖上文, 必然相关 (强信号, 一票否决无关判定)</summary>
    private static readonly string[] DeixisWords =
    {
        "它", "他们", "这个", "那个", "刚才", "继续", "上面", "刚才说的", "前面的", "再", "接着", "然后",
    };

    /// <summary>显式无关信号词 — "顺便/另外/帮我查" 提出新话题</summary>
    private static readonly string[] OffTopicMarkers = { "顺便", "另外", "帮我查", "查一下", "问一下", "帮我算", "帮我写" };

    /// <summary>无关判定阈值 (无关分 ≥ 此值且无指代词 → 隔离任务)</summary>
    public const int DefaultIsolationThreshold = 2;

    /// <summary>简单中文实体抽取 (规则版): 去停用词后取 2-4 字词块 — 与 GoalProfile 抽取口径一致</summary>
    public static List<string> ExtractEntities(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return new List<string>();
        var cleaned = new string(text.Where(c => !char.IsWhiteSpace(c) && !char.IsPunctuation(c)).ToArray());
        // 规则版: 抽英文词与数字串 + 2-4 字中文滑窗 (去常见虚词开头)
        var entities = new List<string>();
        var sb = new System.Text.StringBuilder();
        foreach (var ch in cleaned)
        {
            if (char.IsAsciiLetterOrDigit(ch))
                sb.Append(ch);
            else
            {
                if (sb.Length > 0) { entities.Add(sb.ToString()); sb.Clear(); }
            }
        }
        if (sb.Length > 0) entities.Add(sb.ToString());
        for (var i = 0; i < cleaned.Length - 1; i++)
        {
            foreach (var len in new[] { 4, 3, 2 })
            {
                if (i + len > cleaned.Length) continue;
                var w = cleaned.Substring(i, len);
                if (w.All(c => c >= 0x4e00 && c <= 0x9fff) && !IsStopword(w))
                    entities.Add(w);
            }
        }
        return entities.Distinct().ToList();
    }

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

    private static bool IsStopword(string w) =>
        w is "可以" or "这个" or "那个" or "什么" or "怎么" or "如果" or "但是" or "或者" or "需要" or "帮我";

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

        // 强信号: 指代词 → 相关 (一票否决)
        if (DeixisWords.Any(w => incomingMessage.Contains(w, StringComparison.Ordinal)))
            return (false, 0, "含指代词, 依赖上文");

        // v0.11.0 R39c (真缺陷 26): 技术细节追问 ("用 X 怎么写/怎么实现") 实体上常与任务标题零重叠
        // (requests vs 爬虫标题) — 但语义上强依赖上文。实现询问标记 + 短消息 → 一票否决。
        string[] howToMarkers = { "怎么写", "怎么实现", "怎么做", "怎么配", "如何写", "如何实现", "如何做", "怎么用", "如何用" };
        if (incomingMessage.Length <= 30 && howToMarkers.Any(w => incomingMessage.Contains(w, StringComparison.Ordinal)))
            return (false, 0, "实现询问, 依赖上文任务");

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

        // 显式离题词 → +1
        if (OffTopicMarkers.Any(w => incomingMessage.Contains(w, StringComparison.Ordinal)))
        {
            score += 1;
            reasons.Add("显式离题信号词");
        }

        var isolated = score >= threshold;
        return (isolated, score, string.Join("; ", reasons));
    }
}
