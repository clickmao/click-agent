using System.Text.Json;

namespace agent.registry;

/// <summary>
/// 下轮任务预估 (v7.11): 任务循环完成后生成, 落本地文件;
/// 关闭程序后, 下次对话通过读回预估来指示 LLM 用户本轮输入倾向。
/// 每个主/子 agent 独立一份 — 按 AgentRegistry UID 隔离在工作目录下。
/// </summary>
public class ForecastRecord
{
    /// <summary>所属 agent UID (隔离键)</summary>
    public string AgentUid { get; set; } = string.Empty;

    /// <summary>本轮任务摘要 (供下轮延续判断)</summary>
    public string TaskSummary { get; set; } = string.Empty;

    /// <summary>本轮主意图 (agent.intent 常量)</summary>
    public string LastIntent { get; set; } = string.Empty;

    /// <summary>下轮输入倾向 (规则推断, 非编造)</summary>
    public string Tendency { get; set; } = string.Empty;

    /// <summary>延续提示 (拼进 prompt header 的一句话)</summary>
    public string ContinuationHint { get; set; } = string.Empty;

    /// <summary>本轮是否像任务的中间态 (用户大概率会继续)</summary>
    public bool LikelyContinues { get; set; }

    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>累计完成的轮次 (同一 agent 的会话计数)</summary>
    public int TurnCount { get; set; }
}

/// <summary>
/// 预估存储 + 生成器。
/// 文件位置: {dataStoragePath}/agents/{uid}/forecast.json — 工作目录归属, agent 隔离。
/// </summary>
public static class NextTurnForecast
{
    private const string FileName = "forecast.json";

    /// <summary>任务循环完成后调用: 生成并落盘下轮预估 (规则式, 零 LLM 成本)</summary>
    public static ForecastRecord Save(string dataStoragePath, string agentUid, string taskText, string intent)
    {
        var record = BuildRecord(agentUid, taskText, intent);
        var previous = Load(dataStoragePath, agentUid);
        record.TurnCount = (previous?.TurnCount ?? 0) + 1;

        var dir = AgentRegistry.AgentDir(dataStoragePath, agentUid);
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, FileName);
        var json = JsonSerializer.Serialize(record, RegistryJsonContext.Default.ForecastRecord);
        File.WriteAllText(path, json);
        return record;
    }

    /// <summary>下次对话开头调用: 读回上轮预估 (无文件/损坏 → null)</summary>
    public static ForecastRecord? Load(string dataStoragePath, string agentUid)
    {
        try
        {
            var path = Path.Combine(AgentRegistry.AgentDir(dataStoragePath, agentUid), FileName);
            if (!File.Exists(path))
                return null;

            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize(json, RegistryJsonContext.Default.ForecastRecord);
        }
        catch
        {
            return null; // 预估是提示增强, 任何损坏都不应阻断对话
        }
    }

    /// <summary>拼进 prompt 的 header 行 (无预估 → 空串, 调用方零特判)</summary>
    public static string ToPromptHeader(ForecastRecord? record)
    {
        if (record == null || string.IsNullOrWhiteSpace(record.TaskSummary))
            return string.Empty;

        var header = $"[下轮预估·上轮任务: {record.TaskSummary}";
        if (record.LikelyContinues)
            header += $" | 倾向: {record.Tendency}";
        header += "]";
        return header;
    }

    /// <summary>
    /// 规则式预估生成: 意图 + 任务文本特征 → 下轮倾向。
    /// 判定依据必须真实 (意图可执行性/文本中的未完成信号), 不做无据猜测。
    /// </summary>
    private static ForecastRecord BuildRecord(string agentUid, string taskText, string intent)
    {
        // 未完成信号: 迭代词/续作词/待办词 → 大概率继续
        var continuationMarkers = new[]
        {
            "先", "然后", "接着", "下一步", "首先", "之后", "待", "继续",
            "阶段", "第一步", "第二步", "草稿", "初版",
        };
        var likelyContinues = continuationMarkers.Any(taskText.Contains);

        var tendency = intent switch
        {
            "search" => "补充检索条件或要求深入某个结果",
            "code_generation" => likelyContinues
                ? "对生成的代码提出修改/补全"
                : "提出新的编码任务或对本次代码的审查",
            "test_generation" => "要求扩大测试覆盖或修复失败用例",
            "code_review" => "按审查意见要求修复",
            "git_operation" => "继续其他 git 操作或回退",
            "file_operation" => "继续读写其他文件或调整内容",
            _ => likelyContinues ? "延续当前任务的下一阶段" : "提出新任务",
        };

        var summary = taskText.Length > 80 ? taskText[..80] + "…" : taskText;

        return new ForecastRecord
        {
            AgentUid = agentUid,
            TaskSummary = summary,
            LastIntent = intent,
            Tendency = tendency,
            LikelyContinues = likelyContinues,
            ContinuationHint = likelyContinues
                ? "用户上轮任务未完结, 若本轮输入与上轮任务相关则优先延续"
                : "用户上轮任务已收尾, 本轮可能是新任务; 若提及上轮内容则按上下文延续",
            UpdatedAt = DateTime.UtcNow,
        };
    }
}
