using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>队列调用请求 (协议自洽 — 不依赖 agent 主程序集, adapter 负责转换)</summary>
public sealed class QueuePrompt
{
    public string SystemPrompt { get; set; } = string.Empty;
    public string ContextPrompt { get; set; } = string.Empty;

    /// <summary>(role, content) 历史</summary>
    public List<QueueHistoryMessage> History { get; set; } = new();
    public string UserMessage { get; set; } = string.Empty;

    /// <summary>预估输入 token (费用估算/选模)</summary>
    public int EstimatedTokens { get; set; }

    /// <summary>R379: 会话标识 + 轮次 (缓存前缀 KPI 逐轮归属; 空/0 = 一次性请求)</summary>
    public string? SessionId { get; set; }
    public int TurnIndex { get; set; }

    /// <summary>v0.11.0 R22: 推理档位建议 (null=默认深推理; low=轻思考)。</summary>
    public string? ReasoningEffort { get; set; }

    /// <summary>v0.12.0 A2: 图像附件 (URL/base64 data URL) — 非空时路由强制云端 + user 消息 parts[] 形态。</summary>
    public List<string> ImageUrls { get; set; } = new();
    public int ImageCount => ImageUrls.Count;

    /// <summary>R456 声明面: 工具声明 JSON (OpenAI function-calling 形态; null/空 = 不带工具, 行为与旧版逐字节一致)。</summary>
    public string? ToolsJson { get; set; }

    /// <summary>R490: 意图键透传 (仅用于声明面打点/判据归属; 选模仍走 CallAsync 的 intent 形参)。</summary>
    public string? Intent { get; set; }

    /// <summary>R494: 隔离通道标记透传 (结构量; 声明面通道轴判据的输入)。</summary>
    public bool IsolatedChannel { get; set; }

    /// <summary>
    /// R495: 本地决策台账挂载块 (r1 侧真值的可引用面)。关 (默认) ⇒ <see cref="LedgerMount.Off"/> ⇒
    /// 消息列表与本字段存在之前逐字节同形; 开 ⇒ 在 user 之后**尾部追加**一条 system 消息
    /// (前缀 system/context/history/user 逐字节不变 ⇒ provider 缓存前缀单调增长不破)。
    /// 只在**远端**调用前渲染 (本地 r1 通道不消费) ⇒ 闸的判据输入面在开关两态下逐字节相同。
    /// </summary>
    public LedgerMount Mount { get; set; } = LedgerMount.Off;

    /// <summary>
    /// R490 回放剪裁: 被剔出远端回放的**本地模板答复**条数。
    /// 剪裁依据 = 该答复从未发往任何 provider (零远端调用的 Skip 轮产物) ⇒ 不是任何缓存前缀的一部分。
    /// </summary>
    public int ReplayTrimmedLocalTemplates { get; set; }

    /// <summary>
    /// R491 配对剪裁: 被剔出远端回放的**零远端调用轮的 user 侧**条数 (闸开才可能 &gt; 0)。
    /// 与 <see cref="ReplayTrimmedLocalTemplates"/> 成对: 一对 = 一轮既没发 user 也没发 assistant。
    /// </summary>
    public int ReplayTrimmedLocalUserTurns { get; set; }

    /// <summary>R456 回灌面: user 之后的追加消息 (assistant(tool_calls) / tool(...)) —— 前缀不变, 只增长尾部。</summary>
    public List<QueuePostUserMessage> PostUser { get; set; } = new();
}
