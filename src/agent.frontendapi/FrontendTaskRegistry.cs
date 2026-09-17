using System.Text;
using System.Text.Json;

namespace agent.frontendapi;

/// <summary>
/// R509 (对标 codex 展示面, 取 R508 分析稿路线 A): 任务生命周期登记 + 事件载荷组装。
/// 出站点仍唯一 = <see cref="FrontendEventHub"/> (EmitAsync); 本类只做**状态登记**与**手写 JSON**
/// (零反射 AOT 铁律; 不引入 STJ 反射序列化)。事件域:
///   task.started / task.progress / task.completed  (字段与 R508 分析稿 §事件契约 一致)。
/// 线程模型: 内部锁; 同一 task_id 的 started → progress* → completed 单调推进。
/// 快照面: <see cref="SnapshotJson"/> 供 state.snapshot 合并 (断线重连可读在飞/最近任务)。
/// </summary>
public sealed class FrontendTaskRegistry
{
    public const int KeepLast = 32;

    public sealed class TaskState
    {
        public string TaskId = "";
        public string SessionId = "";
        public string Api = "";
        public long StartedAtMs;
        public long EndedAtMs;
        public int StepIndex;
        public int Steps;
        public string CurrentAction = "";
        public int ReplyChars;
        public bool Success;
        public bool Completed;
    }

    private readonly object _gate = new();
    private readonly LinkedList<TaskState> _tasks = new();
    private long _seq;

    public string Start(string sessionId, string api, long? startedAtMs = null)
    {
        var ts = startedAtMs ?? DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string id;
        lock (_gate)
        {
            _seq++;
            id = "task-" + ts.ToString(System.Globalization.CultureInfo.InvariantCulture) + "-"
                 + _seq.ToString(System.Globalization.CultureInfo.InvariantCulture);
            _tasks.AddLast(new TaskState
            {
                TaskId = id,
                SessionId = sessionId ?? "",
                Api = api ?? "",
                StartedAtMs = ts,
            });
            while (_tasks.Count > KeepLast) _tasks.RemoveFirst();
        }
        return id;
    }

    /// <summary>记一步 (工具调用/阶段推进)。返回 false = task_id 未知 (不静默接受)。</summary>
    public bool Progress(string taskId, int stepIndex, string tool, bool ok, long elapsedMs, string currentAction = "")
    {
        lock (_gate)
        {
            var t = Find(taskId);
            if (t is null || t.Completed) return false;
            t.StepIndex = stepIndex;
            t.Steps = Math.Max(t.Steps, stepIndex);
            t.CurrentAction = currentAction ?? "";
            return true;
        }
    }

    /// <summary>收口。返回 false = task_id 未知或已收口 (幂等: 不覆盖首次终态)。</summary>
    public bool Complete(string taskId, bool success, int replyChars, long? endedAtMs = null)
    {
        lock (_gate)
        {
            var t = Find(taskId);
            if (t is null || t.Completed) return false;
            t.Completed = true;
            t.Success = success;
            t.ReplyChars = replyChars;
            t.EndedAtMs = endedAtMs ?? DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            return true;
        }
    }

    public TaskState? Get(string taskId)
    {
        lock (_gate) return Find(taskId);
    }

    private TaskState? Find(string taskId)
    {
        for (var n = _tasks.Last; n is not null; n = n.Previous)
            if (n.Value.TaskId == taskId) return n.Value;
        return null;
    }

    // ---------- 载荷 (手写 JSON; 字段名与 R508 分析稿一致) ----------

    public string StartedJson(string taskId)
    {
        TaskState? t;
        lock (_gate) t = Find(taskId);
        if (t is null) return "{}";
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("task_id", t.TaskId);
            w.WriteString("session_id", t.SessionId);
            w.WriteString("api", t.Api);
            w.WriteNumber("started_at_ms", t.StartedAtMs);
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    public string ProgressJson(string taskId, string tool, bool ok, long elapsedMs, string currentAction)
    {
        TaskState? t;
        lock (_gate) t = Find(taskId);
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("task_id", taskId);
            w.WriteNumber("step_index", t?.StepIndex ?? 0);
            w.WriteString("tool", tool ?? "");
            w.WriteBoolean("ok", ok);
            w.WriteNumber("elapsed_ms", elapsedMs);
            w.WriteString("current_action", currentAction ?? "");
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    public string CompletedJson(string taskId)
    {
        TaskState? t;
        lock (_gate) t = Find(taskId);
        if (t is null) return "{}";
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("task_id", t.TaskId);
            w.WriteBoolean("success", t.Success);
            w.WriteNumber("elapsed_ms", Math.Max(0, t.EndedAtMs - t.StartedAtMs));
            w.WriteNumber("reply_chars", t.ReplyChars);
            w.WriteNumber("steps", t.Steps);
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>state.snapshot 的 "tasks" 数组 (最近 KeepLast 条; 新→旧序不进契约, 按开始时间升序稳定输出)。</summary>
    public string SnapshotJson()
    {
        List<TaskState> snap;
        lock (_gate) snap = _tasks.ToList();
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartArray();
            foreach (var t in snap)
            {
                w.WriteStartObject();
                w.WriteString("task_id", t.TaskId);
                w.WriteString("state", t.Completed ? (t.Success ? "done" : "failed") : "running");
                w.WriteString("session_id", t.SessionId);
                w.WriteString("api", t.Api);
                w.WriteNumber("started_at_ms", t.StartedAtMs);
                if (t.Completed) w.WriteNumber("ended_at_ms", t.EndedAtMs);
                else w.WriteNull("ended_at_ms");
                w.WriteNumber("step_index", t.StepIndex);
                w.WriteString("current_action", t.CurrentAction);
                w.WriteNumber("reply_chars", t.ReplyChars);
                if (t.Completed) w.WriteBoolean("success", t.Success);
                else w.WriteNull("success");
                w.WriteEndObject();
            }
            w.WriteEndArray();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }
}
