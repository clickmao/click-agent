using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.tasks;

/// <summary>
/// v0.15.1-a (TaskCharter): 任务章程 — 一句话需求的结构化边界 (goal/验收/范围/里程碑/暂存输入)。
/// 生命周期: planning → running → accepting → done|failed。
/// v0.15.1 消费: 任务 running 期间新输入按 TopicRelevanceEvaluator 路由
/// (supplement→pending_inputs / isolate→隔离子 / pivot→重锚)。
/// AOT: STJ source-gen (TaskCharterJsonCtx), 手写持久化, 零反射。
/// </summary>
public sealed class TaskCharter
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..12];
    /// <summary>一句话需求原文 (用户输入)</summary>
    public string GoalText { get; set; } = string.Empty;
    /// <summary>章程实体 (判定锚 — 与 Goal.KeyEntities 同构)</summary>
    public List<string> KeyEntities { get; set; } = new();
    /// <summary>状态机</summary>
    public string Status { get; set; } = "planning";
    /// <summary>v0.15.1: 任务进行中的主题补充暂存 (下轮循环注入依据, 任务结束即清)</summary>
    public List<string> PendingInputs { get; set; } = new();
    /// <summary>验收标准 (v0.15.0-b 完整化; 最小版 = must_contain 关键词)</summary>
    public List<string> AcceptanceCriteria { get; set; } = new();
    /// <summary>范围外 (scope bounds — 防 creep)</summary>
    public List<string> ScopeOut { get; set; } = new();
    public string CreatedUtc { get; set; } = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");

    [JsonIgnore]
    public bool IsRunning => Status is "running" or "planning";

    // ---------- 持久化 (单活动章程: data/task-charters/active.json) ----------

    public static string ActivePath(string dataRoot) => Path.Combine(dataRoot, "task-charters", "active.json");

    public void Save(string dataRoot)
    {
        var path = ActivePath(dataRoot);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(this, TaskCharterJsonCtx.Default.TaskCharter));
    }

    /// <summary>读活动章程; 不存在/损坏 → null。</summary>
    public static TaskCharter? LoadActive(string dataRoot)
    {
        var path = ActivePath(dataRoot);
        if (!File.Exists(path))
            return null;
        try
        {
            return JsonSerializer.Deserialize(File.ReadAllText(path), TaskCharterJsonCtx.Default.TaskCharter);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    /// <summary>任务结束 (done/failed) → 归档移除活动位。</summary>
    public void Archive(string dataRoot, string finalStatus)
    {
        Status = finalStatus;
        PendingInputs.Clear(); // v0.15.1: 任务终态, 暂存输入随任务终结 (R322b E2E 发现: 归档快照含旧 pending)
        Save(dataRoot);        // 先落终态内容再移动 (R322b E2E 发现: 原 Move 快照是最后一次 Save 的内容)
        var path = ActivePath(dataRoot);
        if (File.Exists(path))
            File.Move(path, Path.Combine(Path.GetDirectoryName(path)!, $"{Id}-{finalStatus}.json"), overwrite: true);
    }

    /// <summary>路由结果 (v0.15.1 三态)。</summary>
    public enum InputRoute { Supplement, Isolate, Pivot }
}

[JsonSerializable(typeof(TaskCharter))]
internal partial class TaskCharterJsonCtx : JsonSerializerContext;
