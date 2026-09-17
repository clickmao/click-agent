using System.Collections.Concurrent;
using System.Globalization;

namespace agent.modelqueue;


/// <summary>单次调用用量记录</summary>
public sealed record UsageRecord(string ModelId, string Provider, int PromptTokens, int CompletionTokens, DateTime At);
