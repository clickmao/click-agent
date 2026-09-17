// R480: 独立文本召回模块 —— 只读 IO / 计数 / 异常。
// 设计要点: 一律 pread(RandomAccess) 语义按需读取, 不 mmap 整索引 ⇒
//   进程常驻内存 ≠ 索引体积 (页缓存由内核拥有, 不计入本模块常驻面)。
using Microsoft.Win32.SafeHandles;

namespace agent.recall;


public sealed class RecallFormatException : Exception
{
    public RecallFormatException(string message) : base(message) { }
}
