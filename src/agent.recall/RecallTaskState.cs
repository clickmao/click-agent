// R480: 独立文本召回模块 —— 任务级 memory / 当前状态 (用户令: 「每个任务应该有个memory或当前状态? 不应该仅靠上下文」)。
// 设计闭环 (双向优化):
//   产出物 → 自带地址 (RecallHit.Links / Artifacts) → 落入任务状态 → SyncToIndex 回流成可召回文档 → 下次探索召回命中。
// 本文件不依赖任何模型上下文: 状态在磁盘, 进程重启后按 taskId 读回即可。
using System.Text;
using System.Text.Json;

namespace agent.Recall;

public sealed class TaskStateEvent
{
    public required long Ts { get; init; }
    public required string Kind { get; init; }
    public required string Text { get; init; }
    public IReadOnlyList<string> Artifacts { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> Links { get; init; } = Array.Empty<string>();
}

/// <summary>任务状态物化视图: 由事件流按序折叠而来 (不含模型上下文)。</summary>
public sealed class TaskState
{
    public required string TaskId { get; init; }
    public string LastText { get; set; } = "";
    public long LastTs { get; set; }
    public int EventCount { get; set; }
    public List<string> Artifacts { get; } = new();
    public List<string> Links { get; } = new();

    /// <summary>状态文档自身的地址 (产出物自带地址的一员)。</summary>
    public string Address => "task://" + TaskId;

    public string ToStateText()
    {
        var sb = new StringBuilder(256);
        sb.Append("任务 ").Append(TaskId).Append(" 当前状态: ").Append(LastText);
        if (Artifacts.Count > 0)
        {
            sb.Append(" | 产出物: ").Append(string.Join(" ", Artifacts));
        }
        if (Links.Count > 0)
        {
            sb.Append(" | 关联地址: ").Append(string.Join(" ", Links));
        }
        return sb.ToString();
    }
}

public sealed class RecallTaskStateStore
{
    private readonly string _root;

    public RecallTaskStateStore(string root) => _root = root;

    public string TasksDirectory => Path.Combine(_root, "tasks");

    public string TaskPath(string taskId) => Path.Combine(TasksDirectory, Sanitize(taskId) + ".jsonl");

    public void Append(string taskId, TaskStateEvent e)
    {
        Directory.CreateDirectory(TasksDirectory);
        string line = ToJson(e);
        using var fs = new FileStream(TaskPath(taskId), FileMode.Append, FileAccess.Write, FileShare.None);
        var bytes = Encoding.UTF8.GetBytes(line + "\n");
        fs.Write(bytes);
        fs.Flush();
    }

    /// <summary>把一次召回结果写回任务状态 (召回 → 状态 的反向那一半)。</summary>
    public void RecordRecall(string taskId, string query, IReadOnlyList<RecallHit> hits)
    {
        var artifacts = new List<string>();
        var links = new List<string>();
        foreach (var h in hits)
        {
            if (!string.IsNullOrEmpty(h.Path))
            {
                artifacts.Add(h.Path);
            }
            if (!string.IsNullOrEmpty(h.Id) && h.Id != h.Path)
            {
                artifacts.Add(h.Id);
            }
            foreach (string l in h.Links)
            {
                links.Add(l);
            }
        }
        Append(taskId, new TaskStateEvent
        {
            Ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            Kind = "recall",
            Text = "探索召回: " + query,
            Artifacts = artifacts,
            Links = links,
        });
    }

    public string? TryReadRaw(string taskId)
    {
        string path = TaskPath(taskId);
        return File.Exists(path) ? File.ReadAllText(path, Encoding.UTF8) : null;
    }

    public TaskState Load(string taskId)
    {
        var state = new TaskState { TaskId = taskId };
        string? raw = TryReadRaw(taskId);
        if (raw is null)
        {
            return state;
        }
        foreach (string line in raw.Split('\n'))
        {
            if (line.Length == 0)
            {
                continue;
            }
            TaskStateEvent? e = Parse(line);
            if (e is null)
            {
                continue;
            }
            state.EventCount++;
            state.LastText = e.Text;
            state.LastTs = e.Ts;
            foreach (string a in e.Artifacts)
            {
                if (!state.Artifacts.Contains(a, StringComparer.Ordinal))
                {
                    state.Artifacts.Add(a);
                }
            }
            foreach (string l in e.Links)
            {
                if (!state.Links.Contains(l, StringComparer.Ordinal))
                {
                    state.Links.Add(l);
                }
            }
        }
        return state;
    }

    /// <summary>回流: 把任务状态写成一条可召回文档 (地址 = task://id) 追加进召回索引。</summary>
    public int SyncToIndex(string taskId, string indexDirectory)
    {
        var state = Load(taskId);
        if (state.EventCount == 0)
        {
            return 0;
        }
        using var builder = RecallIndexBuilder.Open(indexDirectory);
        string linkText = state.Links.Count == 0 ? "" : "\n关联地址: " + string.Join(" ", state.Links);
        builder.DeleteByKey(state.Address);
        builder.AddOne(new RecallSourceDoc
        {
            Id = state.Address,
            Path = state.Address,
            Text = state.ToStateText() + linkText,
            Size = 0,
            MtimeTicks = state.LastTs,
            Inode = 0,
        });
        return 1;
    }

    private static string Sanitize(string taskId)
    {
        var sb = new StringBuilder(taskId.Length);
        foreach (char c in taskId)
        {
            sb.Append(char.IsLetterOrDigit(c) || c == '-' || c == '_' || c == '.' ? c : '_');
        }
        return sb.Length == 0 ? "unnamed" : sb.ToString();
    }

    private static string ToJson(TaskStateEvent e)
    {
        var sb = new StringBuilder(256);
        sb.Append("{\"ts\":").Append(e.Ts).Append(",\"kind\":\"").Append(Escape(e.Kind)).Append("\",\"text\":\"").Append(Escape(e.Text)).Append('"');
        sb.Append(",\"artifacts\":[");
        for (int i = 0; i < e.Artifacts.Count; i++)
        {
            if (i > 0)
            {
                sb.Append(',');
            }
            sb.Append('"').Append(Escape(e.Artifacts[i])).Append('"');
        }
        sb.Append("],\"links\":[");
        for (int i = 0; i < e.Links.Count; i++)
        {
            if (i > 0)
            {
                sb.Append(',');
            }
            sb.Append('"').Append(Escape(e.Links[i])).Append('"');
        }
        sb.Append("]}");
        return sb.ToString();
    }

    private static TaskStateEvent? Parse(string line)
    {
        try
        {
            using var doc = JsonDocument.Parse(line);
            var r = doc.RootElement;
            var artifacts = new List<string>();
            var links = new List<string>();
            if (r.TryGetProperty("artifacts", out var a) && a.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in a.EnumerateArray())
                {
                    artifacts.Add(item.GetString() ?? "");
                }
            }
            if (r.TryGetProperty("links", out var l) && l.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in l.EnumerateArray())
                {
                    links.Add(item.GetString() ?? "");
                }
            }
            return new TaskStateEvent
            {
                Ts = r.TryGetProperty("ts", out var ts) && ts.ValueKind == JsonValueKind.Number ? ts.GetInt64() : 0,
                Kind = r.TryGetProperty("kind", out var k) ? k.GetString() ?? "" : "",
                Text = r.TryGetProperty("text", out var t) ? t.GetString() ?? "" : "",
                Artifacts = artifacts,
                Links = links,
            };
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string Escape(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        foreach (char c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20)
                    {
                        sb.Append("\\u").Append(((int)c).ToString("x4"));
                    }
                    else
                    {
                        sb.Append(c);
                    }
                    break;
            }
        }
        return sb.ToString();
    }
}
