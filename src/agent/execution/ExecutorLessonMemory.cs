using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace agent.execution;

/// <summary>
/// v0.17.0 T3 (R334, 用户钦定): 执行层失败教训临时记忆 — 失败(IO 冲突/锁超时/占用) → 获取原因 →
/// 记入临时记忆, **随教训频率提高记忆越长** (count 升级内容: 1 行摘要 → 补解决方案 → 补触发上下文),
/// 下次同类操作前注入避免重复失败。TTL 衰减: 24h 无命中降级, 7d 无命中移除。
/// 持久化: data/executor-lessons.json (经 AtomicFileWriter 原子写)。AOT 兼容 (STJ source-gen 手动 JSON 亦可 — 用 JsonDocument 手写往返防反射)。
/// </summary>
public sealed class ExecutorLesson
{
    public string Pattern { get; set; } = "";       // 教训键: "file-lock:data/guardrails.json"
    public string Summary { get; set; } = "";       // 失败原因摘要 (首次记入)
    public int Count { get; set; }
    public long FirstSeenUnixMs { get; set; }
    public long LastSeenUnixMs { get; set; }
    public string? Solution { get; set; }            // 解决方案 (count≥3 记入)
    public string? ContextTail { get; set; }         // 触发上下文 (count≥8 记入)
}

/// <summary>见 ExecutorLesson 摘要。</summary>
public sealed class ExecutorLessonMemory
{
    private readonly Dictionary<string, ExecutorLesson> _lessons = new();
    private readonly string _storePath;
    private readonly object _lock = new();
    private readonly Func<long> _nowMs;              // 时钟注入 (测试)

    /// <summary>进程级默认单例 (v0.17.0 T4 接入点共用; 路径 data/executor-lessons.json 相对 cwd)。</summary>
    public static ExecutorLessonMemory Default { get; } = new();

    private const int Level2Solution = 3;            // 3 次 → 补解决方案
    private const int Level3Context = 8;             // 8 次 → 补触发上下文
    private const long DecayMs = 24 * 60 * 60 * 1000L;      // 24h 无命中: count 降级
    private const long ExpireMs = 7 * 24 * 60 * 60 * 1000L; // 7d 无命中: 移除

    public ExecutorLessonMemory(string? storePath = null, Func<long>? nowMs = null)
    {
        _storePath = storePath ?? Path.Combine(Environment.CurrentDirectory, "data", "executor-lessons.json");
        _nowMs = nowMs ?? (() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());
        Load();
    }

    /// <summary>记录一条失败教训。同 pattern 递增 count 并升级内容; 返回是否新增/升级。</summary>
    public bool Record(string pattern, string summary, string? solution = null, string? contextTail = null)
    {
        lock (_lock)
        {
            var now = _nowMs();
            if (!_lessons.TryGetValue(pattern, out var lesson))
            {
                lesson = new ExecutorLesson
                {
                    Pattern = pattern, Summary = summary, Count = 1,
                    FirstSeenUnixMs = now, LastSeenUnixMs = now,
                    Solution = solution, ContextTail = null,
                };
                _lessons[pattern] = lesson;
                Save();
                return true;
            }
            lesson.Count++;
            lesson.LastSeenUnixMs = now;
            if (lesson.Count >= Level2Solution && solution != null && lesson.Solution == null)
                lesson.Solution = solution;
            if (lesson.Count >= Level3Context && contextTail != null && lesson.ContextTail == null)
                lesson.ContextTail = contextTail;
            Save();
            return true;
        }
    }

    /// <summary>命中检查 + 频率加权注入文本 (摘要; count≥3 补方案; count≥8 补上下文)。无命中/空 → 空串。</summary>
    public string RenderInjectionHint(string pattern)
    {
        lock (_lock)
        {
            DecayAndPrune();
            if (!_lessons.TryGetValue(pattern, out var lesson)) return "";
            var sb = new StringBuilder();
            sb.Append("⚠ 执行层教训 (历史失败 ").Append(lesson.Count).Append(" 次): ")
              .Append(lesson.Summary);
            if (lesson.Count >= Level2Solution && !string.IsNullOrEmpty(lesson.Solution))
                sb.Append(" → 方案: ").Append(lesson.Solution);
            if (lesson.Count >= Level3Context && !string.IsNullOrEmpty(lesson.ContextTail))
                sb.Append(" → 上次上下文: ").Append(lesson.ContextTail);
            sb.Append(" [避免重蹈]");
            return sb.ToString();
        }
    }

    public IReadOnlyDictionary<string, ExecutorLesson> Snapshot()
    {
        lock (_lock) { DecayAndPrune(); return new Dictionary<string, ExecutorLesson>(_lessons); }
    }

    public void Clear() { lock (_lock) { _lessons.Clear(); Save(); } }

    private void DecayAndPrune()
    {
        var now = _nowMs();
        List<string>? remove = null;
        foreach (var kv in _lessons)
        {
            if (now - kv.Value.LastSeenUnixMs > ExpireMs)
            {
                (remove ??= new List<string>()).Add(kv.Key);
            }
            else if (now - kv.Value.LastSeenUnixMs > DecayMs && kv.Value.Count > 1)
            {
                kv.Value.Count = Math.Max(1, kv.Value.Count / 2);
            }
        }
        if (remove is not null)
            foreach (var k in remove) _lessons.Remove(k);
    }

    // ---- 持久化 (手写 JSON 防反射; AOT 安全) ----
    private void Load()
    {
        try
        {
            if (!File.Exists(_storePath)) return;
            var json = File.ReadAllText(_storePath);
            using var doc = System.Text.Json.JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("lessons", out var arr)) return;
            foreach (var el in arr.EnumerateArray())
            {
                var l = new ExecutorLesson
                {
                    Pattern = el.GetProperty("pattern").GetString() ?? "",
                    Summary = el.GetProperty("summary").GetString() ?? "",
                    Count = el.GetProperty("count").GetInt32(),
                    FirstSeenUnixMs = el.GetProperty("first").GetInt64(),
                    LastSeenUnixMs = el.GetProperty("last").GetInt64(),
                    Solution = el.TryGetProperty("solution", out var s) ? s.GetString() : null,
                    ContextTail = el.TryGetProperty("ctx", out var c) ? c.GetString() : null,
                };
                if (l.Pattern.Length > 0) _lessons[l.Pattern] = l;
            }
        }
        catch { /* 损坏容忍 — 记忆丢了不可惜, 执行层不能因教训文件崩 */ }
    }

    private void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(Path.GetFullPath(_storePath));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var sb = new StringBuilder();
            sb.Append("{\"lessons\":[");
            var first = true;
            foreach (var l in _lessons.Values.OrderByDescending(x => x.Count))
            {
                if (!first) sb.Append(',');
                first = false;
                sb.Append("{\"pattern\":").Append(Esc(l.Pattern))
                  .Append(",\"summary\":").Append(Esc(l.Summary))
                  .Append(",\"count\":").Append(l.Count)
                  .Append(",\"first\":").Append(l.FirstSeenUnixMs)
                  .Append(",\"last\":").Append(l.LastSeenUnixMs);
                if (l.Solution != null) sb.Append(",\"solution\":").Append(Esc(l.Solution));
                if (l.ContextTail != null) sb.Append(",\"ctx\":").Append(Esc(l.ContextTail));
                sb.Append('}');
            }
            sb.Append("]}");
            AtomicFileWriter.WriteAllText(_storePath, sb.ToString());
        }
        catch { /* 持久化失败不致命 — 内存态教训仍生效 */ }
    }

    private static string Esc(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        sb.Append('"');
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                    else sb.Append(c);
                    break;
            }
        }
        sb.Append('"');
        return sb.ToString(); // 完整 JSON 字符串值 (含引号) — Save 直接 Append 即合法
    }
}
