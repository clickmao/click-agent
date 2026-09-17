using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>本地生成请求。</summary>
public sealed class LocalGenerationRequest
{
    /// <summary>会话标识 (长驻前缀缓存归属; 空 = 一次性请求)。</summary>
    public string? SessionKey { get; init; }
    public int TurnIndex { get; init; } = 1;
    public List<LocalChatTurn> Turns { get; init; } = new();
    public int MaxTokens { get; init; } = 256;

    /// <summary>
    /// R429 决策路径缓存钉死: false ⇒ 该次生成本地关前缀缓存 (CompletionReuse.Reconciliation)。
    /// 默认 true = 既有生产口径 (逐位零回归)。
    /// 依据 (R429 传输级实测): 同一 prompt 在「全量评估」与「部分前缀复用」下 token 序列不等
    /// (180 / 97 / 215), 且可出现 S/P 判定翻转 ⇒ 决策路径不得依赖缓存复用。
    /// </summary>
    public bool CacheReuse { get; init; } = true;
}
