using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 框架自产的本地节点意图常量 (v0.22.0 exp9 D2)。
/// 注意: 这些意图**不进 IntentPromptTemplates** (不是用户意图) —— 它们只描述"本地执行器要干什么",
/// 由 LocalVerifyNodePlanner 生成节点时写入, 供路由与执行体分派使用。
/// </summary>
public static class PlanNodeIntents
{
    /// <summary>本地验证 (跑产物自测/机器判据)</summary>
    public const string VerifyLocal = "verify_local";

    /// <summary>本地文本处理 (证据汇总/格式化/统计 — 纯本地, 零 token)</summary>
    public const string TextProcessing = "text_processing";

    /// <summary>本地形式化验证 (R391 C7): clickproof 断言 → 本地内核确定性裁决, 零 token</summary>
    public const string VerifyFormal = "verify_formal";
}
