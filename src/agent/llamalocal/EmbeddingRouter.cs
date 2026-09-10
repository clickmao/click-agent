using System;
using System.Collections.Generic;

namespace agent.llamalocal;

/// <summary>
/// v0.20.5 R352 (用户钦定): RAG 嵌入路由 — 语义档 (ITextEmbedder 注入: llm-service RemoteEmbedder) + 词频 hash 兜底。
/// 变更: 本地 bge 进程内加载 (LLamaSharp) 移除 — embed 语义档全走 llm-service API 调用 (旁路, 不改主链);
/// llm-service 不可用 → HashEmbeddingProvider (纯托管零依赖, 384 维词频)。
/// </summary>
public sealed class EmbeddingRouter : agent.vectormemory.IEmbeddingProvider
{
    private readonly agent.contextgradient.ITextEmbedder? _semantic;
    private readonly agent.vectormemory.HashEmbeddingProvider _hash;
    private readonly agent.vectormemory.HashEmbeddingProvider _fallback = new();

    public EmbeddingRouter(agent.contextgradient.ITextEmbedder? semantic = null)
    {
        _semantic = semantic;
        _hash = new agent.vectormemory.HashEmbeddingProvider();
    }

    public int Dimension => _hash.Dimension;

    public string Name => _semantic is null ? "hash" : "semantic+hash-fallback";

    public float[] Embed(string text)
    {
        // 语义档: 同步包装 (RAG 接口是同步 Embed; 上层调用点已并发化 — R352-b)
        if (_semantic is not null)
        {
            try
            {
                return _semantic.EmbedAsync(text).GetAwaiter().GetResult();
            }
            catch
            {
                // 语义档失败 (daemon 离线/熔断) → hash 兜底 (行为兼容, 不阻塞召回主链)
            }
        }
        return _hash.Embed(text);
    }

    /// <summary>384 维词频兜底暴露 (测试/对照用)</summary>
    public agent.vectormemory.HashEmbeddingProvider Fallback => _fallback;
}
