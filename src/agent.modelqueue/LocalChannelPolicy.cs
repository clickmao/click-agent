using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>
/// 本地通道采用判据 (预注册, 单点可测)。判定顺序 = 配置 → 请求形态 → 端口, 每步都有显式原因。
/// </summary>
public static class LocalChannelPolicy
{
    /// <summary>默认可本地化的任务种类 (轻任务, 输出短且性能不敏感; 与 ModelSelectionPolicy.LowSensitivityKinds 同源)。</summary>
    public static readonly TaskKindHint[] DefaultAllowedKinds =
    {
        TaskKindHint.ContextCompression,
        TaskKindHint.KeywordTagging,
        TaskKindHint.TendencyAnalysis,
        TaskKindHint.IntentClassification,
    };

    public static bool KindAllowed(LocalChannelConfig config, TaskKindHint kind)
    {
        if (config.AllowGeneral && kind == TaskKindHint.General)
            return true;

        if (config.AllowedKinds.Count > 0)
        {
            foreach (var name in config.AllowedKinds)
            {
                if (string.Equals(name, kind.ToString(), StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        foreach (var k in DefaultAllowedKinds)
        {
            if (k == kind)
                return true;
        }
        return false;
    }

    public static LocalChannelDecision Evaluate(
        QueuePrompt prompt, TaskKindHint kind, LocalChannelConfig config, ILocalGenerationPort? port)
    {
        if (!config.IsReady)
            return new LocalChannelDecision(false, LocalChannelRejectReason.ChannelDisabled);

        // 带图请求必须落视觉模型 (远端) — 本地通道是纯文本执行面
        if (prompt.ImageUrls.Count > 0)
            return new LocalChannelDecision(false, LocalChannelRejectReason.ImageRequest);

        if (!KindAllowed(config, kind))
            return new LocalChannelDecision(false, LocalChannelRejectReason.KindNotAllowed);

        if (config.MaxPromptTokens > 0 && prompt.EstimatedTokens > config.MaxPromptTokens)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PromptTooLong);

        if (port is null)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PortMissing);

        if (!port.IsAvailable)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PortUnavailable);

        return LocalChannelDecision.Allow;
    }
}
