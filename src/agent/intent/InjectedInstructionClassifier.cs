using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 插入指令分类器: 文本 → 语义分级。
/// 显式停止指令与敏感词在这里判定 (工业规则: 停止指令永远生效, 不需要问询)。
/// </summary>
public static class InjectedInstructionClassifier
{
    private static readonly string[] CancelMarkers =
    [
        "停止", "取消", "停下", "别做了", "终止", "中止", "撤销",
        "stop", "cancel", "abort", "halt"
    ];

    private static readonly string[] ApprovalMarkers =
    [
        "先停下确认", "问过我", "先问我", "暂停确认", "需要我确认",
        "ask me first", "confirm with me", "pause before"
    ];

    /// <summary>敏感意图集合: 这些意图的节点默认需要审批 (非全托管模式)</summary>
    private static readonly HashSet<string> SensitiveIntents = new(StringComparer.Ordinal)
    {
        IntentRecognizer.Intents.FileOperation,   // 删除/移动文件不可逆
        IntentRecognizer.Intents.GitOperation,    // push/reset 影响远端
    };

    public static bool IsCancel(string text)
    {
        foreach (var m in CancelMarkers)
        {
            if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    public static bool IsApprovalRequest(string text)
    {
        foreach (var m in ApprovalMarkers)
        {
            if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    public static bool IsSensitiveIntent(string intent) => SensitiveIntents.Contains(intent);

    /// <summary>分类入口 (顺序: 取消 > 审批请求 > 其余按内容拆解定性)</summary>
    public static InjectedInstructionKind Classify(string text)
    {
        if (IsCancel(text))
            return InjectedInstructionKind.Cancel;
        if (IsApprovalRequest(text))
            return InjectedInstructionKind.RequestApproval;
        return InjectedInstructionKind.NewTask;
    }
}
