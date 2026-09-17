// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.recall;


public sealed class RecallUpdateReport
{
    public required string Root { get; init; }
    public required string IndexDirectory { get; init; }
    public long ScanMs { get; set; }
    public long IndexMs { get; set; }
    public int FilesSeen { get; set; }
    public int DirsVisited { get; set; }
    public int DirsPruned { get; set; }
    /// <summary>本轮为「全量核验轮」(因上轮剪枝而抑制剪枝) ⇒ 该轮 DirsPruned 恒为 0 (§D9)。</summary>
    public bool VerifiedAllDirs { get; set; }
    /// <summary>上轮扫描是否发生过剪枝 (决定本轮是否必须核验)。</summary>
    public bool PrevScanPruned { get; set; }
    public int Added { get; set; }
    public int Modified { get; set; }
    public int Deleted { get; set; }
    public int DocsIndexed { get; set; }
    public int DocsRemoved { get; set; }
    public bool WroteIndex { get; set; }

    /// <summary>本次是否有脏 (判脏快速路径: 无脏则索引面零写入)。</summary>
    public bool Dirty => Added + Modified + Deleted > 0;
    public long TotalMs => ScanMs + IndexMs;
}
