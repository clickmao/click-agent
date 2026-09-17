using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>
/// R479: 供应商 usage 口径 (真值面)。**未上报 ≠ 0**: 缺字段 ⇒ Present=false (R474–R477 铁律)。
/// </summary>
public sealed class ResponsesUsage
{
    public bool Present { get; set; }

    public bool CachedPresent { get; set; }

    public int InputTokens { get; set; }

    public int CachedTokens { get; set; }

    public int OutputTokens { get; set; }

    public int ReasoningTokens { get; set; }

    /// <summary>新算 token = input − cached (供应商自洽口径); 任一侧缺失 ⇒ null (不冒充 0)。</summary>
    public int? NewTokens => Present && CachedPresent ? Math.Max(0, InputTokens - CachedTokens) : null;
}
