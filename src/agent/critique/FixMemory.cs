using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.critique;

/// <summary>
/// v0.14.0 T2b (FixMemory): 修法记忆 — 评审反馈 (人/LLM自审过锚) 显式化的存储层。
/// 条目 = (反模式描述, 修法, 来源, 命中统计); 生成前按关键词/嵌入注入少样本。
/// AOT: 手写 JSON + STJ source-gen 模式 (与 ThinkMemory 同款约束); 零反射。
/// </summary>
public sealed class FixMemory
{
    public sealed record FixEntry
    {
        public string Id { get; set; } = Guid.NewGuid().ToString("N")[..16];
        /// <summary>反模式触发模式 (关键词/正则描述 — 检索键)</summary>
        public string Pattern { get; set; } = string.Empty;
        /// <summary>机制解释 (为何伤性能/正确性)</summary>
        public string Mechanism { get; set; } = string.Empty;
        /// <summary>修法 (代码形态或文案)</summary>
        public string Fix { get; set; } = string.Empty;
        /// <summary>来源: human_review / llm_self_confirmed / metric_delta</summary>
        public string Source { get; set; } = "human_review";
        /// <summary>独立同判次数 (多源确认次数 — 提升可信度)</string></summary>
        public int Confirmations { get; set; } = 1;
        public string CreatedUtc { get; set; } = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
    }

    private readonly List<FixEntry> _entries = new();
    private readonly string _path;

    public FixMemory(string path) => _path = path;

    public IReadOnlyList<FixEntry> Entries => _entries;

    /// <summary>写入/合并 (pattern 归一化相同 → Confirmations++ 而非重复条目)。</summary>
    public FixEntry Write(string pattern, string mechanism, string fix, string source)
    {
        var norm = pattern.Trim().ToLowerInvariant();
        var existing = _entries.FirstOrDefault(e =>
            e.Pattern.Trim().ToLowerInvariant() == norm);
        if (existing is not null)
        {
            existing.Confirmations++;
            // 修法/机制允许被更强来源刷新 (human > metric > llm)
            if (SourceRank(source) > SourceRank(existing.Source))
            {
                existing.Source = source;
                existing.Mechanism = mechanism;
                existing.Fix = fix;
            }
            Save();
            return existing;
        }
        var e = new FixEntry { Pattern = pattern, Mechanism = mechanism, Fix = fix, Source = source };
        _entries.Add(e);
        Save();
        return e;
    }

    /// <summary>检索: pattern 关键词与消息/自审 quote 的包含匹配 (零 embedding 依赖 — 规则检索)。</summary>
    public IReadOnlyList<FixEntry> Recall(string text, int topK = 3)
    {
        if (string.IsNullOrEmpty(text))
            return Array.Empty<FixEntry>();
        return _entries
            .Where(e => text.Contains(e.Pattern, StringComparison.OrdinalIgnoreCase)
                        || e.Pattern.Split(' ', '|').Any(k => k.Length > 3 && text.Contains(k, StringComparison.OrdinalIgnoreCase)))
            .OrderByDescending(e => e.Confirmations)
            .Take(topK)
            .ToList();
    }

    private static int SourceRank(string source) => source switch
    {
        "human_review" => 3,
        "metric_delta" => 2,
        "llm_self_confirmed" => 1,
        _ => 0,
    };

    public void Save()
    {
        var dir = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        var json = JsonSerializer.Serialize(_entries, FixJsonCtx.Default.ListFixEntry);
        File.WriteAllText(_path, json);
    }

    public static FixMemory Load(string path)
    {
        var m = new FixMemory(path);
        if (File.Exists(path))
        {
            try
            {
                var list = JsonSerializer.Deserialize(File.ReadAllText(path), FixJsonCtx.Default.ListFixEntry);
                if (list is not null) m._entries.AddRange(list);
            }
            catch (JsonException) { /* 损坏文件从空开始 — 打点由调用方 */ }
        }
        return m;
    }
}

[JsonSerializable(typeof(List<FixMemory.FixEntry>))]
internal partial class FixJsonCtx : JsonSerializerContext;
