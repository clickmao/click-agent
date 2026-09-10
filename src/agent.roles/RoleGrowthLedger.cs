using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;

/// <summary>
/// R360: Role 成长账本 — 按「域」(intent/主题键) 累计赏罚, Beta 后验即倾向。
/// 用户钦定 (v0.21.0 修订): 无前置人格语料; 倾向 = 对用户问题的置信度, 由赏罚自然涌现。
/// 数学: confidence = (reward+1)/(total+2) (Laplace 平滑);
///   confidence < suspicionThreshold → Role 对该域自动"先怀疑/先问" (doubt 涌现);
///   confidence > confidenceThreshold → "直接答" (trust 涌现);
///   中间 → 正常 (无倾向)。
/// 落盘: data/roles/{roleId}.growth.json (手写序列化, AOT 零反射)。
/// </summary>
public sealed class RoleGrowthLedger
{
    private const double SuspicionThreshold = 0.4;
    private const double ConfidenceThreshold = 0.7;
    private const double MinSamplesForTendency = 5; // 样本 <5 不产生倾向 (防冷启动误判)

    private readonly string _roleId;
    private readonly string _storeDir;
    private readonly object _lock = new();

    public sealed record DomainStats(int Reward, int Penalty);
    private Dictionary<string, (int Reward, int Penalty)> _domains = new(StringComparer.OrdinalIgnoreCase);
    public int TotalTokensUsed { get; private set; }

    public RoleGrowthLedger(string roleId, string storeDir = "data/roles")
    {
        _roleId = roleId;
        _storeDir = storeDir;
        Load();
    }

    /// <summary>R363: 从 .rbin 文档播种 (账本空时用文档内计数初始化; 文件已有增量以文件为准)。</summary>
    public void SeedFrom(IEnumerable<KeyValuePair<string, (int Reward, int Penalty)>> growth)
    {
        lock (_lock)
        {
            foreach (var (domain, s) in growth)
                if (!_domains.ContainsKey(domain))
                    _domains[domain] = (s.Reward, s.Penalty);
        }
    }

    /// <summary>记一次赏罚。kind=Correct→罚, Adopt→赏, Neutral→忽略。</summary>
    public void Record(CorrectionDetector.CorrectionKind kind, string domain)
    {
        if (kind == CorrectionDetector.CorrectionKind.Neutral) return;
        lock (_lock)
        {
            var cur = _domains.GetValueOrDefault(domain);
            _domains[domain] = kind == CorrectionDetector.CorrectionKind.Adopt
                ? (cur.Reward + 1, cur.Penalty)
                : (cur.Reward, cur.Penalty + 1);
        }
    }

    public void AddTokens(int n) { if (n > 0) lock (_lock) TotalTokensUsed += n; }

    /// <summary>域置信度 (Laplace 平滑); 无样本 → null。</summary>
    public double? ConfidenceFor(string domain)
    {
        lock (_lock)
        {
            if (!_domains.TryGetValue(domain, out var s) || s.Reward + s.Penalty == 0) return null;
            return (s.Reward + 1.0) / (s.Reward + s.Penalty + 2.0);
        }
    }

    /// <summary>域倾向: Distrust / Trust / None (样本不足= None, 诚实语义)。</summary>
    public (string Tendency, double Confidence) TendencyFor(string domain)
    {
        var c = ConfidenceFor(domain);
        if (c is null) return ("None", 0.5);
        lock (_lock)
        {
            var s = _domains[domain];
            if (s.Reward + s.Penalty < MinSamplesForTendency) return ("None", c.Value);
        }
        return c switch
        {
            < SuspicionThreshold => ("Distrust", c.Value),
            > ConfidenceThreshold => ("Trust", c.Value),
            _ => ("None", c.Value),
        };
    }

    /// <summary>prompt 注入块 (成长实况; ≤400 chars 截断)。</summary>
    public string RenderForPrompt()
    {
        lock (_lock)
        {
            if (_domains.Count == 0) return string.Empty;
            var sb = new System.Text.StringBuilder("【Role 成长经历】");
            foreach (var (d, s) in _domains.OrderByDescending(kv => kv.Value.Reward + kv.Value.Penalty).Take(5))
            {
                var total = s.Reward + s.Penalty;
                var conf = (s.Reward + 1.0) / (total + 2.0);
                var tend = total < MinSamplesForTendency ? "观察中"
                    : conf < SuspicionThreshold ? "⚠先怀疑" : conf > ConfidenceThreshold ? "✓信任" : "—";
                sb.Append($"\n{d}: 赏{s.Reward}/罚{s.Penalty} → {tend}");
            }
            var text = sb.ToString();
            return text.Length <= 400 ? text : text[..400];
        }
    }

    // ── 落盘 (手写 JSON, AOT) ──
    private string StorePath()
    {
        Directory.CreateDirectory(_storeDir);
        return Path.Combine(_storeDir, $"{_roleId}.growth.json");
    }

    public void Save()
    {
        lock (_lock)
        {
            using var fs = File.Create(StorePath());
            using var w = new Utf8JsonWriter(fs);
            w.WriteStartObject();
            w.WriteNumber("tokens", TotalTokensUsed);
            w.WriteStartObject("domains");
            foreach (var (d, s) in _domains)
            {
                w.WriteStartObject(d);
                w.WriteNumber("r", s.Reward);
                w.WriteNumber("p", s.Penalty);
                w.WriteEndObject();
            }
            w.WriteEndObject();
            w.WriteEndObject();
        }
    }

    private void Load()
    {
        try
        {
            var path = StorePath();
            if (!File.Exists(path)) return;
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var root = doc.RootElement;
            TotalTokensUsed = root.TryGetProperty("tokens", out var t) ? t.GetInt32() : 0;
            if (root.TryGetProperty("domains", out var domains) && domains.ValueKind == JsonValueKind.Object)
                foreach (var p in domains.EnumerateObject())
                {
                    var r = p.Value.TryGetProperty("r", out var rv) ? rv.GetInt32() : 0;
                    var pn = p.Value.TryGetProperty("p", out var pv) ? pv.GetInt32() : 0;
                    _domains[p.Name] = (r, pn);
                }
        }
        catch { /* 损坏 → 从零开始 (诚实重建) */ }
    }
}
