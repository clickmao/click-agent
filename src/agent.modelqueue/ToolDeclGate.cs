namespace agent.modelqueue;

/// <summary>
/// R490: 声明面**按需** —— 工作区工具只在**工作区动作类意图**下下发。
///
/// 依据 (R489 真机三臂, `eval/rover/r489/calls-*.jsonl` 逐调用取证):
///   · 51 次远端请求**全部** `tools_n=4` (4 个工作区工具), 而 12 轮 fixture 的 intent 全为 `general`;
///   · 上游 deepseek-flash 在**对话轮**上频繁回 `finish_reason=tool_calls` + 空正文
///     (空正文调用数 R1 4/10、R2 10/16、R3 2/8、B 4/17; R2 空正文轮 prompt 占该臂 57.6% token);
///   · 每次空正文 → 动作环执行工具 → **重发一次全量 prompt** (调用均价 ≈4.4k tok)
///     ⇒ 这正是用户口径里"不必要的远端 LLM API 请求"的主要来源。
///
/// 判据只吃**意图键** (产品自身分类器的输出值, 非用户文本关键词表 ⇒ 不违 R458 铁律)。
/// 本类位于 agent.modelqueue (库) 故以字面常量持有意图键; **与 IntentRecognizer.Intents 的同源关系
/// 由单测锁死** (`R490ToolDeclGateTests.GateOn_KeepsDeclarationForToolIntents` + 一致性断言) ——
/// 分类器改名即红, 不允许静默漂移。
/// 开关默认**关** ⇒ 未开时声明行为与 R456..R489 逐字节相同 (零回归, 且可做同网格单变量消融)。
/// </summary>
public static class ToolDeclGate
{
    public const string EnvName = "AGENTFRAMEWORK_TOOL_DECL_GATE";

    /// <summary>
    /// R494: **通道轴**开关 —— 隔离通道 (微步骤隔离问询 / 一次性隔离子任务) 恒不下发工作区工具。
    /// 与 <see cref="EnvName"/> **分轴**: 意图轴管"这一轮要不要动手", 通道轴管"这条通道有没有工作区"。
    /// 默认**关** ⇒ 未开时与 R490..R493 逐字节相同 (同二进制单变量消融的前提)。
    /// </summary>
    public const string ChannelEnvName = "AGENTFRAMEWORK_TOOL_DECL_CHANNEL";

    /// <summary>开关: off/0/false = 关; 其余 = 开; **未设 = 关** (生产行为不变)。</summary>
    public static bool IsEnabled() => IsOn(EnvName);

    /// <summary>R494 通道轴开关 (未设 = 关)。</summary>
    public static bool IsChannelGateEnabled() => IsOn(ChannelEnvName);

    private static bool IsOn(string name)
    {
        var v = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(v)) return false;
        v = v.Trim();
        return !(v.Equals("off", StringComparison.OrdinalIgnoreCase)
                 || v.Equals("0", StringComparison.Ordinal)
                 || v.Equals("false", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>
    /// 工作区动作类意图键 (需要工作区工具的最小充分集)。
    /// 与 <c>agent.intent.IntentRecognizer.Intents</c> 同源 — 由单测机检锁定。
    /// </summary>
    public static readonly string[] ToolIntents =
    {
        "code_generation",   // IntentRecognizer.Intents.CodeGeneration
        "code_modification", // IntentRecognizer.Intents.CodeModification
        "code_review",       // IntentRecognizer.Intents.CodeReview
        "test_generation",   // IntentRecognizer.Intents.TestGeneration
        "file_operation",    // IntentRecognizer.Intents.FileOperation
        "git_operation",     // IntentRecognizer.Intents.GitOperation
    };

    public static bool IsToolIntent(string? intent)
    {
        if (string.IsNullOrWhiteSpace(intent)) return false;
        var v = intent.Trim();
        foreach (var t in ToolIntents)
            if (string.Equals(v, t, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    /// <summary>
    /// 是否下发工具声明。门关 ⇒ 恒 true (零回归)。
    /// 门开: 只对工作区动作类意图下发; **空/未知意图 ⇒ 下发** (未命中判据不得变成能力丢失)。
    /// </summary>
    public static bool ShouldDeclare(string? intent, bool gateEnabled)
        => ShouldDeclare(intent, gateEnabled, isolatedChannel: false, channelGateEnabled: false);

    /// <summary>
    /// R494: 是否下发工具声明 (**通道轴 + 意图轴**)。
    /// 通道轴开 ∧ 隔离通道 ⇒ 恒不下发 (隔离通道**结构上**没有工作区: 上下文为空、system 明示"不引用外部会话"
    /// ⇒ 声明工具只会招来对不存在路径的读写)。
    /// 通道轴关 或 非隔离通道 ⇒ 退回 R490 的意图轴判据 (逐字节不变)。
    /// </summary>
    public static bool ShouldDeclare(string? intent, bool gateEnabled, bool isolatedChannel, bool channelGateEnabled)
    {
        if (channelGateEnabled && isolatedChannel) return false;
        return !gateEnabled || string.IsNullOrWhiteSpace(intent) || IsToolIntent(intent);
    }

    /// <summary>打点用稳定短名 (禁本地化, 禁自由文本)。</summary>
    public static string DecideReason(string? intent, bool gateEnabled)
        => DecideReason(intent, gateEnabled, isolatedChannel: false, channelGateEnabled: false);

    /// <summary>R494: 带通道轴的稳定短名 (通道轴判据优先于意图轴 —— 两者同时命中时归因到更结构化的那一轴)。</summary>
    public static string DecideReason(string? intent, bool gateEnabled, bool isolatedChannel, bool channelGateEnabled)
    {
        if (channelGateEnabled && isolatedChannel) return "isolated_channel_drop";
        if (!gateEnabled) return "gate_off";
        if (string.IsNullOrWhiteSpace(intent)) return "unknown_intent_keep";
        return IsToolIntent(intent) ? "tool_intent_keep" : "non_tool_intent_drop";
    }
}
