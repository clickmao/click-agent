using System;
using System.Collections.Generic;
using System.Linq;

namespace agent.vectormemory
{
    /// <summary>
    /// v0.11.0 R100: embedding 提供者抽象 — 词频 hash 实现 (R58 词面召回) 与
    /// BgeEmbeddingProvider (LLamaSharp vendored 本地 bge 模型, JIT 形态) 可插拔切换。
    /// AOT 红线: LLamaSharp native interop 在 NativeAOT 下 SIGSEGV (R90 实测),
    /// 因此 BgeEmbeddingProvider 仅在 JIT 部署形态注册 (由 host 启动参数决定)。
    /// </summary>
    public interface IEmbeddingProvider
    {
        /// <summary>向量维度 (bge-small-zh=512, 词频 hash=EmbeddingConfig.Dimension)</summary>
        int Dimension { get; }

        /// <summary>提供者名称 (打点用: hash / bge-local)</summary>
        string Name { get; }

        /// <summary>文本 → 向量 (归一化与否由实现决定, 调用方仅做余弦比较)</summary>
        float[] Embed(string text);
    }

    /// <summary>
    /// 词频 hash 向量 (R58 现状实现的接口化提取, 行为保持一致 — 默认 provider)
    /// </summary>
    public class HashEmbeddingProvider : IEmbeddingProvider
    {
        private readonly int _dimension;
        public int Dimension => _dimension;
        public string Name => "hash";

        public HashEmbeddingProvider(int dimension = 384) => _dimension = dimension;

        public float[] Embed(string text)
        {
            var words = text.ToLowerInvariant()
                .Split(new[] { ' ', '\t', '\n', '\r', '.', ',', '!', '?' }, StringSplitOptions.RemoveEmptyEntries)
                .GroupBy(w => w)
                .ToDictionary(g => g.Key, g => g.Count());

            var embedding = new float[_dimension];
            var index = 0;
            foreach (var (word, count) in words.OrderBy(kvp => kvp.Key))
            {
                if (index >= _dimension) break;
                var hash = word.GetHashCode();
                var targetIndex = Math.Abs(hash % _dimension);
                embedding[targetIndex] = count;
                index++;
            }
            return embedding;
        }
    }
}
