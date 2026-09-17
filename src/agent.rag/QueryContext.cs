using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>查询侧上下文 (原文 + 已算好的查询向量, 可为 null ⇒ 该路自行降级)。</summary>
public readonly struct QueryContext
{
    public QueryContext(string text, float[]? embedding)
    {
        Text = text ?? string.Empty;
        Embedding = embedding;
    }

    public string Text { get; }
    public float[]? Embedding { get; }
}
