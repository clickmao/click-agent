// R480: 独立文本召回模块 —— 段写入 + 索引构建/追加。
// 主键命名空间: 文本 token 首字节 ≥ 0x21 或 ≥ 0xC2(UTF-8 多字节), 因此 0x01/0x02 前缀
// 只可能来自本模块自己写入的「文档键」, 不会与正文 token 冲突 (单一定义处, 读侧同一函数)。
using System.Text;

namespace agent.recall;


public sealed class RecallSegmentWriteResult
{
    public required string Name { get; init; }
    public required string Directory { get; init; }
    public required int DocCount { get; init; }
    public required int TermCount { get; init; }
    public required double AvgDocLen { get; init; }
    public required long TermTopsResidentBytes { get; init; }
    public required long IndexBytes { get; init; }
}
