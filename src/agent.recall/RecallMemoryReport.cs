// R480: 独立文本召回模块 —— 只读 IO / 计数 / 异常。
// 设计要点: 一律 pread(RandomAccess) 语义按需读取, 不 mmap 整索引 ⇒
//   进程常驻内存 ≠ 索引体积 (页缓存由内核拥有, 不计入本模块常驻面)。
using Microsoft.Win32.SafeHandles;

namespace agent.recall;


/// <summary>常驻内存账本: 每一条都必须能被源码事实对上, 空白声明不算数。</summary>
public sealed class RecallMemoryReport
{
    private readonly List<(string Name, long Bytes)> _items = new();

    public void Add(string name, long bytes) => _items.Add((name, bytes));

    public long TotalBytes
    {
        get
        {
            long t = 0;
            for (int i = 0; i < _items.Count; i++)
            {
                t += _items[i].Bytes;
            }
            return t;
        }
    }

    public IReadOnlyList<(string Name, long Bytes)> Items => _items;

    public string Describe()
    {
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < _items.Count; i++)
        {
            sb.Append(_items[i].Name).Append('=').Append(_items[i].Bytes).Append(' ');
        }
        sb.Append("total=").Append(TotalBytes);
        return sb.ToString();
    }
}
