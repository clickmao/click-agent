// R480: 独立文本召回模块 —— 只读 IO / 计数 / 异常。
// 设计要点: 一律 pread(RandomAccess) 语义按需读取, 不 mmap 整索引 ⇒
//   进程常驻内存 ≠ 索引体积 (页缓存由内核拥有, 不计入本模块常驻面)。
using Microsoft.Win32.SafeHandles;

namespace agent.recall;


/// <summary>读取计数: 用于把「几十 ms」拆成 syscall 次数 + 字节量, 而不是只报一个墙钟。</summary>
public sealed class RecallReadStats
{
    public long Reads;
    public long BytesRead;
    public long TermLookups;
    public long BlocksScanned;
    public long BlocksSkipped;
    public long PostingsVisited;
    public long DocsScored;

    public void Reset()
    {
        Reads = 0;
        BytesRead = 0;
        TermLookups = 0;
        BlocksScanned = 0;
        BlocksSkipped = 0;
        PostingsVisited = 0;
        DocsScored = 0;
    }

    /// <summary>记一次 ad-hoc pread (链接表/正文等按需读取也计入器具口径)。</summary>
    public void CountRead(int bytes)
    {
        Reads++;
        BytesRead += bytes;
    }

    public RecallReadStats Snapshot() => new()
    {
        Reads = Reads,
        BytesRead = BytesRead,
        TermLookups = TermLookups,
        BlocksScanned = BlocksScanned,
        BlocksSkipped = BlocksSkipped,
        PostingsVisited = PostingsVisited,
        DocsScored = DocsScored,
    };
}
