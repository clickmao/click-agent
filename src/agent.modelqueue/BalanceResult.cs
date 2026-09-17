using System.Text.Json;

namespace agent.modelqueue;


/// <summary>余额查询结果 (C.3.5: JSON 输出可被程序解析; 不支持/失败诚实报错, 不编造数字)</summary>
public sealed class BalanceResult
{
    public string Command { get; set; } = "balance";
    public bool Ok { get; set; }
    public string Model { get; set; } = string.Empty;
    public string? Provider { get; set; }

    /// <summary>余额数值 (provider 语义不同: OpenAI=USD 上限, DeepSeek=USD 余额)</summary>
    public double? TotalGranted { get; set; }
    public double? TotalUsed { get; set; }
    public double? TotalRemaining { get; set; }

    /// <summary>v0.11.0 R15: 原始币种 (USD/CNY/…) — 空串=未声明 (按 USD 处理并标注)</summary>
    public string Currency { get; set; } = string.Empty;

    public string? Error { get; set; }

    /// <summary>provider 不支持时的调研备注 (目录 balance_schemes.note)</summary>
    public string? Note { get; set; }
}
