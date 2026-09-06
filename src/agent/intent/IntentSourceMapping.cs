using agent.core;
using agent.context;
using agent.intent;

namespace agent.intent;

/// <summary>
/// 意图 → 数据源映射 (v7.6 从 V2 private 方法提取, 使映射矩阵可测)。
/// 基础源全意图启用: Memory (向量记忆) + UserTendency (用户倾向)。
/// WebSearch 仅在信息获取型意图启用 (search/general) — 代码生成唤起网络搜索纯属浪费 token 与延迟。
/// </summary>
public static class IntentSourceMapping
{
    /// <summary>返回该意图应启用的数据源集合 (新 HashSet, 调用方可自由增删)</summary>
    public static HashSet<DataSourceType> GetSources(string intent)
    {
        var sources = new HashSet<DataSourceType>
        {
            DataSourceType.Memory,
            DataSourceType.UserTendency
        };

        // 未知意图按 general 兜底 (保守启用网搜): 未来新增意图名若映射表未跟上,
        // 静默失去网搜能力的代价高于多一次搜索的代价
        if (intent == IntentRecognizer.Intents.Search ||
            intent == IntentRecognizer.Intents.General ||
            !IntentRecognizer.KnownIntents.Contains(intent))
        {
            sources.Add(DataSourceType.WebSearch);
        }

        // v0.11.0 R11: 文件相关意图启用工作区文件源
        if (intent == IntentRecognizer.Intents.FileOperation ||
            intent == IntentRecognizer.Intents.CodeGeneration ||
            intent == IntentRecognizer.Intents.Search ||
            intent == IntentRecognizer.Intents.General)
        {
            sources.Add(DataSourceType.WorkspaceFiles);
        }

        return sources;
    }

    /// <summary>是否信息获取型意图 (需要联网搜索补全)</summary>
    public static bool NeedsWebSearch(string intent) =>
        intent == IntentRecognizer.Intents.Search ||
        intent == IntentRecognizer.Intents.General;
}
