using System;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;

namespace agent.io
{
    /// <summary>
    /// 共享内存传输 (v0.11.0 用户定案方案②): 同机进程间零拷贝行协议通道。
    ///
    /// 结构 (一块 MemoryMappedFile, 头部元数据 + 环形数据区):
    ///   [0..3)  uint 写位置 (生产者推进; LE)
    ///   [4..7)  uint 读位置 (消费者推进; LE)
    ///   [8..)   环形数据区: 每条记录 = [uint 长度 LE][utf8 字节 (含行尾 \n)]
    ///
    /// 写侧 <see cref="SharedMemoryRequestWriter"/> (agent → 前端方向) 与
    /// 读侧 <see cref="SharedMemoryReportReader"/> (前端读取) 可分属两进程。
    /// 同步策略: 自旋 + Thread.Yield (短临界, 无内核事件对象 — AOT 可用, netstandard2.1 无 named EventWaitHandle 依赖)。
    /// 容量管理: 消费者不推进且环形区满 → 写侧重试若干次后抛 IOException (背压上抛, 不静默丢弃 — 工业约定)。
    /// </summary>
    public static class SharedMemoryChannel
    {
        /// <summary>头部字节数 (写位置 4 + 读位置 4)。</summary>
        public const int HeaderBytes = 8;

        /// <summary>单条记录上限 (协议为行, 1 MiB 足够任何单行/流式块行)。</summary>
        public const int MaxRecordBytes = 1 * 1024 * 1024;

        /// <summary>
        /// 打开或创建一块通道 (两进程用同一路径即接通; capacity 为数据区字节数)。
        /// .NET (Core) 不支持命名 MMF → 文件-backed (mmap): Linux 建议 /dev/shm 下 (tmpfs, 零磁盘 IO)。
        /// </summary>
        public static MemoryMappedFile OpenOrCreate(string mapPath, int dataCapacityBytes = 4 * 1024 * 1024)
        {
            if (dataCapacityBytes < 4096)
                throw new ArgumentOutOfRangeException(nameof(dataCapacityBytes), "数据区至少 4096 字节");
            var fs = new FileStream(mapPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.ReadWrite,
                bufferSize: 4096, FileOptions.None);
            fs.SetLength(HeaderBytes + (long)dataCapacityBytes);
            return MemoryMappedFile.CreateFromFile(fs, mapName: null, capacity: HeaderBytes + (long)dataCapacityBytes,
                MemoryMappedFileAccess.ReadWrite, HandleInheritability.None, leaveOpen: false);
        }
    }
}
