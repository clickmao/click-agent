using System;
using System.Collections.Generic;
using System.Text;

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
    /// v0.16.1 R329 (T-B4 统一): 词频 hash 向量 — 三份 hash 语义 (vectormemory R100 英文版 /
    /// llamalocal R103 fallback 256 版 / RAGConfig 内联) 收敛到本类为唯一实现:
    ///   • 分词: lower + ASCII 标点全切 + ascii↔非ascii 边界切 (R44 中英混写 "rust的所有权")
    ///     + 中文 2-gram 滑窗补充 (R6 中文整句 1 桶失效) — RAGConfig.Tokenize 同族语义 (无停用词表依赖)。
    ///   • 桶分配: 3-seed 摊开 ((h+seed*31337)%dim 每桶 +1) — 冲突分散, llamalocal/RAGConfig 同款。
    ///   • dim 可配默认 384 (T-B4 钦定; llamalocal 256 硬编码版已退役)。
    ///   • 不做预归一化: 全部调用方走 CosineSimilarity (自归一), 与 RAGConfig 内联一致。
    /// 兼容面: VectorStore (记忆整合) 与 EmbeddingRouter fallback (RAG 降级档) 共用, 维度统一 384。
    /// </summary>
    public class HashEmbeddingProvider : IEmbeddingProvider
    {
        private readonly int _dimension;
        public int Dimension => _dimension;
        public string Name => "hash";

        public HashEmbeddingProvider(int dimension = 384) => _dimension = dimension;

        public float[] Embed(string text)
        {
            var tokens = Tokenize(text);
            var embedding = new float[_dimension];
            foreach (var token in tokens)
            {
                var hash = Math.Abs(token.GetHashCode());
                // 3-seed 摊开: 冲突分散到 3 个桶, 稀疏向量对同词不同上下文更鲁棒
                for (int seed = 0; seed < 3; seed++)
                    embedding[(hash + seed * 31337) % _dimension] += 1f;
            }
            return embedding;
        }

        /// <summary>
        /// 分词 — RAGConfig.Tokenize 同族语义 (R44/R6 教训沉淀), 无停用词表依赖:
        /// ASCII 标点切整词 → ascii↔非ascii 边界切段 → 中文段 2-gram 滑窗补充。
        /// </summary>
        private static List<string> Tokenize(string text)
        {
            var tokens = new List<string>();
            var words = text.ToLowerInvariant()
                .Split(new[] { ' ', '\t', '\n', '\r', '.', ',', '!', '?', ';', ':', '(', ')', '[', ']', '{', '}', '"', '\'', '`', '~', '@', '#', '$', '%', '^', '&', '*', '+', '=', '<', '>', '/', '\\', '|' },
                       StringSplitOptions.RemoveEmptyEntries);

            foreach (var word in words)
            {
                // R44 (真缺陷 27): 中英混写黏连 ("rust的所有权" 一个 token) — 按 ascii↔非 ascii 边界再切
                var segments = new List<string>();
                var sb = new StringBuilder();
                var prevAscii = false;
                foreach (var ch in word)
                {
                    var isAscii = ch < 0x80;
                    if (sb.Length > 0 && isAscii != prevAscii)
                    {
                        segments.Add(sb.ToString());
                        sb.Clear();
                    }
                    sb.Append(ch);
                    prevAscii = isAscii;
                }
                if (sb.Length > 0) segments.Add(sb.ToString());

                foreach (var seg in segments)
                {
                    if (seg.Length >= 2) tokens.Add(seg);
                }

                // R6 (打点驱动修复): 中文无分词导致整句成一个 token — 中文段 2-gram 滑窗补充
                for (var i = 0; i + 2 <= word.Length; i++)
                {
                    var gram = word.Substring(i, 2);
                    if (gram[0] >= 0x4e00 && gram[0] <= 0x9fff &&
                        gram[1] >= 0x4e00 && gram[1] <= 0x9fff)
                    {
                        tokens.Add(gram);
                    }
                }
            }

            return tokens;
        }
    }
}
