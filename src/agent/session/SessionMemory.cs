using System.Text.Json.Serialization;

namespace agent.session;

/// <summary>
/// 会话长期记忆 + 任务目标画像 (v7.14):
///   - LongTermMemory: 跨轮滚动摘要 (默认 ≤1000 字符, 可配), 老旧内容按序裁剪, 目标句最后裁
///   - GoalProfile: 任务目标画像 — 当前任务的总方向指示 (目标句/关键实体/约束/已完成里程碑)
/// 不是凭据存储: 绝不记录 API Key 等敏感值 (写入前过滤)。
/// 线程安全: Session 内单线程使用; 跨线程访问由 SessionManager 的会话锁保证。
/// </summary>
public sealed class SessionMemory
{
    /// <summary>长期记忆上限字符数 (默认 1000, 构造可调; 硬上限 10000 防滥用)</summary>
    public const int DefaultMaxChars = 1000;
    public const int HardMaxChars = 10000;

    private readonly int _maxChars;
    private readonly object _lock = new();

    public SessionMemory(int maxChars = DefaultMaxChars)
    {
        if (maxChars < 100)
            maxChars = 100;
        _maxChars = Math.Min(maxChars, HardMaxChars);
    }

    /// <summary>长期记忆字符上限 (配置快照, 只读)</summary>
    public int MaxChars => _maxChars;

    /// <summary>长期记忆滚动摘要 (≤ MaxChars)</summary>
    public string LongTermMemory { get; private set; } = string.Empty;

    /// <summary>任务目标画像 (当前任务总方向; null = 尚未形成)</summary>
    public GoalProfile? Goal { get; private set; }

    /// <summary>记忆条目数 (诊断用)</summary>
    public int EntryCount { get; private set; }

    /// <summary>最近更新时间 (面板排序用)</summary>
    public DateTime UpdatedAt { get; private set; } = DateTime.UtcNow;

    /// <summary>
    /// 追加一条长期记忆 (自动过滤敏感值; 超限裁剪最旧条目, 目标相关条目最后裁)。
    /// </summary>
    public void Remember(string note, bool goalRelated = false)
    {
        if (string.IsNullOrWhiteSpace(note))
            return;
        var text = MemorySanitizer.StripSecrets(note.Trim());
        if (text.Length > _maxChars)
            text = text[.._maxChars]; // 单条超限: 截断保留头部 (摘要本来就是短句)

        lock (_lock)
        {
            var entries = ParseEntries(LongTermMemory);
            if (entries.Count > 0 && string.Equals(entries[^1].Text, text, StringComparison.Ordinal))
                return; // 连续重复条目去重
            entries.Add(new MemoryEntry(text, goalRelated));
            EntryCount = entries.Count;
            LongTermMemory = Compress(entries);
            UpdatedAt = DateTime.UtcNow;
        }
    }

    /// <summary>
    /// 设置/更新任务目标画像 (方向指示)。目标句同步进长期记忆 (goalRelated, 最后裁)。
    /// </summary>
    public void SetGoal(string goalText, IEnumerable<string>? keyEntities = null,
        IEnumerable<string>? constraints = null)
    {
        if (string.IsNullOrWhiteSpace(goalText))
            return;
        lock (_lock)
        {
            Goal = new GoalProfile
            {
                GoalText = MemorySanitizer.StripSecrets(goalText.Trim()),
                KeyEntities = (keyEntities ?? Enumerable.Empty<string>())
                    .Select(e => e.Trim())
                    .Where(e => e.Length > 0)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Take(12)
                    .ToList(),
                Constraints = (constraints ?? Enumerable.Empty<string>())
                    .Select(e => e.Trim())
                    .Where(e => e.Length > 0)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Take(8)
                    .ToList(),
                UpdatedAt = DateTime.UtcNow,
            };
            Remember($"[目标] {Goal.GoalText}", goalRelated: true);
        }
    }

    /// <summary>记录一个已完成里程碑 (进画像, 用于方向校准: 剩余工作 = 目标 − 里程碑)</summary>
    public void AddMilestone(string milestone)
    {
        if (string.IsNullOrWhiteSpace(milestone))
            return;
        lock (_lock)
        {
            if (Goal == null)
                Goal = new GoalProfile();
            var m = MemorySanitizer.StripSecrets(milestone.Trim());
            if (!Goal.Milestones.Contains(m))
            {
                Goal.Milestones.Add(m);
                if (Goal.Milestones.Count > 16)
                    Goal.Milestones.RemoveAt(0);
            }
            Remember($"[完成] {m}", goalRelated: true);
        }
    }

    /// <summary>
    /// 渲染注入 prompt 的记忆块 (③核心输出: 总方向 + 长期记忆)。
    /// 空记忆返回空串 (不产生空段落)。
    /// </summary>
    public string RenderForPrompt()
    {
        lock (_lock)
        {
            var sb = new System.Text.StringBuilder();
            if (Goal != null)
            {
                sb.Append("【任务方向】").AppendLine(Goal.GoalText);
                if (Goal.KeyEntities.Count > 0)
                    sb.Append("【关键实体】").AppendLine(string.Join("、", Goal.KeyEntities));
                if (Goal.Constraints.Count > 0)
                    sb.Append("【约束】").AppendLine(string.Join("; ", Goal.Constraints));
                if (Goal.Milestones.Count > 0)
                    sb.Append("【已完成】").AppendLine(string.Join("; ", Goal.Milestones.TakeLast(4)));
            }
            if (!string.IsNullOrEmpty(LongTermMemory))
                sb.Append("【长期记忆】").Append(LongTermMemory);
            return sb.ToString().TrimEnd();
        }
    }

    /// <summary>从落盘恢复 (JsonSessionMemoryStore 专用): 直接还原内部态, 不再过 Sanitizer (落盘前已过滤)</summary>
    public void Restore(string longTermMemory, GoalProfile? goal, int entryCount)
    {
        lock (_lock)
        {
            LongTermMemory = longTermMemory ?? string.Empty;
        UpdatedAt = DateTime.UtcNow;
            Goal = goal;
            EntryCount = Math.Max(0, entryCount);
        }
    }

    /// <summary>超限裁剪: 非目标条目从最旧开始丢; 目标条目最后丢 (方向指示优先存活)</summary>
    private string Compress(List<MemoryEntry> entries)
    {
        while (entries.Sum(e => e.Text.Length + 1) > _maxChars && entries.Count > 1)
        {
            var idx = entries.FindIndex(e => !e.GoalRelated);
            if (idx < 0)
                idx = 0; // 全是目标条目也丢最旧
            entries.RemoveAt(idx);
        }
        // 兜底: 单条仍超限 (maxChars 很小) → 直接截整段
        var joined = string.Join("\n", entries.Select(e => e.Text));
        if (joined.Length > _maxChars)
            joined = joined[.._maxChars];
        return joined;
    }

    private static List<MemoryEntry> ParseEntries(string memory)
    {
        var list = new List<MemoryEntry>();
        foreach (var line in memory.Split('\n'))
            if (!string.IsNullOrWhiteSpace(line))
                list.Add(new MemoryEntry(line.Trim(), line.StartsWith("[目标]", StringComparison.Ordinal) ||
                                                    line.StartsWith("[完成]", StringComparison.Ordinal)));
        return list;
    }

    private sealed record MemoryEntry(string Text, bool GoalRelated);
}

/// <summary>任务目标画像: 当前任务的总方向指示 (③)</summary>
public sealed class GoalProfile
{
    /// <summary>目标一句话 (用户最新钦定的总方向)</summary>
    public string GoalText { get; set; } = string.Empty;

    /// <summary>关键实体 (项目名/模块名/组件名, 12 上限)</summary>
    public List<string> KeyEntities { get; set; } = new();

    /// <summary>约束 (AOT/0警告/不过度设计等, 8 上限)</summary>
    public List<string> Constraints { get; set; } = new();

    /// <summary>已完成里程碑 (16 上限, 新的在尾)</summary>
    public List<string> Milestones { get; set; } = new();

    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>记忆净化: 写入前剥离疑似凭据 (对齐偏好库铁律: 记忆不存凭据)</summary>
public static class MemorySanitizer
{
    public static string StripSecrets(string text)
    {
        if (string.IsNullOrEmpty(text))
            return text;
        // token/key/password 形态: 赋值段打码 (保留键名, 值换 [REDACTED])
        var sb = new System.Text.StringBuilder(text.Length);
        var lower = text.ToLowerInvariant();
        int i = 0;
        while (i < text.Length)
        {
            var hit = FindSecretKeyword(lower, i);
            if (hit < 0)
            {
                sb.Append(text[i..]);
                break;
            }
            sb.Append(text[i..hit]);
            i = hit;
            // 关键字后找分隔符 (=/:) 与值
            var sep = text.IndexOfAny(new[] { '=', ':', '：' }, hit);
            if (sep < 0 || sep - hit > 24)
            {
                // 不是赋值形态, 只是普通词, 原样跳过关键字
                sb.Append(text[hit..Math.Min(text.Length, hit + 12)]);
                i = Math.Min(text.Length, hit + 12);
                continue;
            }
            sb.Append(text[hit..(sep + 1)]);
            // 值段: 非空白即打码
            int v = sep + 1;
            while (v < text.Length && char.IsWhiteSpace(text[v]))
            {
                sb.Append(text[v]);
                v++;
            }
            var vend = v;
            while (vend < text.Length && !char.IsWhiteSpace(text[vend]))
                vend++;
            sb.Append(vend > v ? "[REDACTED]" : string.Empty);
            i = Math.Max(vend, v);
        }
        return sb.ToString();
    }

    private static int FindSecretKeyword(string lower, int from)
    {
        string[] keys = { "api_key", "apikey", "token", "password", "passwd", "secret", "ghp_" };
        var best = -1;
        foreach (var k in keys)
        {
            var idx = lower.IndexOf(k, from, StringComparison.Ordinal);
            if (idx >= 0 && (best < 0 || idx < best))
                best = idx;
        }
        return best;
    }
}

/// <summary>会话记忆持久化契约 (落盘由 SessionManager/宿主实现; 接口只管序列化往返)</summary>
public interface ISessionMemoryStore
{
    /// <summary>读回会话记忆 (不存在返回 null)</summary>
    SessionMemory? Load(string sessionId);

    /// <summary>落盘会话记忆 (JSON source-gen, AOT 安全)</summary>
    void Save(string sessionId, SessionMemory memory);
}
