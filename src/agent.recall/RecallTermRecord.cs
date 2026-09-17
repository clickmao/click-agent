// R480: 独立文本召回模块 —— 段读取面 (词表二级跳表查找 + postings 块游标 + 文档/正文按需 pread)。
using System.Buffers.Binary;

namespace agent.recall;


public sealed class RecallTermRecord
{
    public required bool Found { get; init; }
    public required int DocFreq { get; init; }
    public required long PostingsOffset { get; init; }
    public required int PostingsLength { get; init; }
}
