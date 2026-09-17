using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>检索候选 (文档侧一行)。<see cref="Bigrams"/> 可外部注入 (记忆化), 未注入则惰性计算。</summary>
public sealed class RetrievalCandidate
{
    public string Id = string.Empty;
    public string Text = string.Empty;
    public float[]? Embedding;

    private string[]? _bigrams;

    /// <summary>去空白字符二元组集合 (与 eval/bge/fusion.py 的 grams() 同口径)。</summary>
    public string[] Bigrams
    {
        get => _bigrams ??= FusionMath.CharacterBigrams(Text);
        set => _bigrams = value;
    }
}
