namespace agent.recall;


public sealed class RecallScanResult
{
    public List<RecallFileEntry> Added { get; } = new();
    public List<RecallFileEntry> Modified { get; } = new();
    public List<RecallFileEntry> Deleted { get; } = new();
    public int FilesSeen { get; set; }
    public int DirsVisited { get; set; }
    public int DirsPruned { get; set; }
    public int StoreEntries { get; set; }
    public long ElapsedMs { get; set; }
    /// <summary>上轮扫描 (指纹头 stamp 低位) 是否发生过目录剪枝。</summary>
    public bool PrevScanPruned { get; set; }
    /// <summary>本轮是否因上轮剪枝而**抑制剪枝、全量核验** (此轮 DirsPruned 恒为 0)。</summary>
    public bool VerifiedAllDirs { get; set; }
    public bool Dirty => Added.Count > 0 || Modified.Count > 0 || Deleted.Count > 0;
}
