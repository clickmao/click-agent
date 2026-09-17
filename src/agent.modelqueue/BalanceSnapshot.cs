using System.Collections.Concurrent;
using System.Globalization;

namespace agent.modelqueue;


/// <summary>模型余额快照 (真实 API 查询结果或本地推算)</summary>
public sealed record BalanceSnapshot(
    string Provider, double? TotalRemaining, DateTime At, bool FromApi,
    string Currency = "USD"); // v0.11.0 R15: 原始币种 (默认 USD 兼容旧调用)
