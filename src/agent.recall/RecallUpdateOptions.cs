// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.recall;


public sealed class RecallUpdateOptions
{
    public RecallWriteOptions Write { get; init; } = new();
    public RecallScanOptions Scan { get; init; } = new();
    public int ChunkChars { get; init; } = 512;
    public long MaxFileBytes { get; init; } = 2_000_000;
    public double BinaryNulRatio { get; init; } = 0.02;
}
