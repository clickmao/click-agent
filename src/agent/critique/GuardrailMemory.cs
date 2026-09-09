using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.critique;

/// <summary>
/// v0.15.2 (GuardrailMemory): 警告/违规/铁律持久化 — 用户主动警告的结构化沉淀与联想抑制。
/// 语言学设计: 铁律 = 逻辑三元组 condition/prohibition/exception (保留用户的逻辑限定, 不做无界泛化)。
/// 心理学设计: 前置注入 (生成前) > 事后纠正; 具体案例随铁律; 同会话去重防 habituation。
/// 领域性: 条目带 domain (会话主题锚), recall 按 domain+pattern 双键 — 跨域不泛扰。
/// 来源秩: human_warning (用户主动, 最高) > review > metric。
/// AOT: STJ source-gen, 零反射 (FixMemory 同款约束)。
/// </summary>
public sealed class GuardrailMemory
{
    public sealed record GuardrailEntry
    {
        public string Id { get; set; } = Guid.NewGuid().ToString("N")[..12];
        /// <summary>领域 (会话主题锚归一 — 跨域不泛扰的关键)</summary>
        public string Domain { get; set; } = string.Empty;
        /// <summary>触发模式 (recall 键 — 关键词/形态)</summary>
        public string Pattern { get; set; } = string.Empty;
        /// <summary>条件 (何时适用 — "在Y情境下")</summary>
        public string Condition { get; set; } = string.Empty;
        /// <summary>禁令 (不要做什么)</summary>
        public string Prohibition { get; set; } = string.Empty;
        /// <summary>例外 ("除非Z" — 无此字段联想抑制会误伤合法操作)</summary>
        public string Exception { get; set; } = string.Empty;
        /// <summary>原始违规案例片段 (脱敏 — 少样本具体性)</summary>
        public string OriginCase { get; set; } = string.Empty;
        /// <summary>来源: human_warning | review | metric</summary>
        public string Source { get; set; } = "human_warning";
        /// <summary>多次警告合并计数</summary>
        public int Confirmations { get; set; } = 1;
        public string CreatedUtc { get; set; } = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
    }

    private readonly List<GuardrailEntry> _entries = new();
    private readonly string _path;

    public GuardrailMemory(string path) => _path = path;

    public IReadOnlyList<GuardrailEntry> Entries => _entries;

    /// <summary>写入/合并 (同 domain+pattern → confirmations++; 三元组允许强来源刷新)。</summary>
    public GuardrailEntry Write(string domain, string pattern, string condition,
        string prohibition, string exceptionCase, string originCase, string source)
    {
        var normKey = NormalizeKey(domain, pattern);
        var existing = _entries.FirstOrDefault(e => NormalizeKey(e.Domain, e.Pattern) == normKey);
        if (existing is not null)
        {
            existing.Confirmations++;
            if (SourceRank(source) > SourceRank(existing.Source))
            {
                existing.Condition = condition;
                existing.Prohibition = prohibition;
                existing.Exception = exceptionCase;
                existing.OriginCase = originCase;
                existing.Source = source;
            }
            Save();
            return existing;
        }
        var e = new GuardrailEntry
        {
            Domain = domain, Pattern = pattern, Condition = condition,
            Prohibition = prohibition, Exception = exceptionCase, OriginCase = originCase, Source = source,
        };
        _entries.Add(e);
        Save();
        return e;
    }

    /// <summary>联想召回: domain 匹配 + pattern 词面 (双键; 跨域不触发)。</summary>
    public IReadOnlyList<GuardrailEntry> Recall(string domain, string text, int topK = 2)
    {
        if (string.IsNullOrEmpty(text))
            return Array.Empty<GuardrailEntry>();
        var normDomain = (domain ?? "").Trim().ToLowerInvariant();
        return _entries
            .Where(e => MatchesDomain(e, normDomain) && MatchesPattern(e, text))
            .OrderByDescending(e => e.Confirmations)
            .ThenByDescending(e => SourceRank(e.Source))
            .Take(topK)
            .ToList();
    }

    private static bool MatchesDomain(GuardrailEntry e, string normDomain)
    {
        // R324b: "general" 域条目 = 通用警告 (用户未在任务上下文发的警告) → 全域触发。
        // 有域条目 + 当前无域 → 不触发 (跨域不泛扰是特性 — 无锚会话不吃领域警告)。
        var eNorm = (e.Domain ?? "").Trim().ToLowerInvariant();
        if (eNorm is "general" or "")
            return true;
        if (string.IsNullOrEmpty(normDomain))
            return false;
        // 双向词面: 条目域词任一出现在当前域串, 或当前域词出现在条目域
        var eWords = eNorm.Split(new[] { ' ', '|', '/' }, StringSplitOptions.RemoveEmptyEntries);
        return eWords.Any(w => w.Length > 1 && normDomain.Contains(w, StringComparison.OrdinalIgnoreCase))
            || normDomain.Split(' ').Any(w => w.Length > 1 && eNorm.Contains(w, StringComparison.OrdinalIgnoreCase));
    }

    private static bool MatchesPattern(GuardrailEntry e, string text)
    {
        var keys = e.Pattern.Split(new[] { ' ', '|', '/' }, StringSplitOptions.RemoveEmptyEntries);
        return keys.Any(k => k.Length > 1 && text.Contains(k, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>渲染注入文案 (三元组逻辑形态保留)。</summary>
    public static string Render(IReadOnlyList<GuardrailEntry> entries)
    {
        if (entries.Count == 0)
            return string.Empty;
        var sb = new System.Text.StringBuilder("⚠ 铁律 (历史用户警告, 本领域适用):\n");
        foreach (var e in entries)
        {
            var cond = string.IsNullOrEmpty(e.Condition) ? "" : $"在{e.Condition}时";
            var exc = string.IsNullOrEmpty(e.Exception) ? "" : $" (除非{e.Exception})";
            sb.Append($"- {cond}{e.Prohibition}{exc}");
            if (!string.IsNullOrEmpty(e.OriginCase))
                sb.Append($" [案例: {e.OriginCase}]");
            sb.Append('\n');
        }
        return sb.ToString();
    }

    private static string NormalizeKey(string domain, string pattern) =>
        $"{(domain ?? "").Trim().ToLowerInvariant()}::{(pattern ?? "").Trim().ToLowerInvariant()}";

    private static int SourceRank(string source) => source switch
    {
        "human_warning" => 3,
        "review" => 2,
        "metric" => 1,
        _ => 0,
    };

    public void Save()
    {
        var dir = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(_path, JsonSerializer.Serialize(_entries, GuardrailJsonCtx.Default.ListGuardrailEntry));
    }

    public static GuardrailMemory Load(string path)
    {
        var m = new GuardrailMemory(path);
        if (File.Exists(path))
        {
            try
            {
                var list = JsonSerializer.Deserialize(File.ReadAllText(path), GuardrailJsonCtx.Default.ListGuardrailEntry);
                if (list is not null) m._entries.AddRange(list);
            }
            catch (JsonException) { }
        }
        return m;
    }
}

[JsonSerializable(typeof(List<GuardrailMemory.GuardrailEntry>))]
internal partial class GuardrailJsonCtx : JsonSerializerContext;
