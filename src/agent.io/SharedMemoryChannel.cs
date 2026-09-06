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

    /// <summary>共享内存写侧 (agent → 前端): 实现 AgentRequestWriterBase 行写出。</summary>
    public sealed class SharedMemoryRequestWriter : AgentRequestWriterBase, IDisposable
    {
        private readonly MemoryMappedFile _mmf;
        private readonly MemoryMappedViewAccessor _header;
        private readonly MemoryMappedViewAccessor _data;
        private readonly int _dataCapacity;
        private readonly bool _ownsFile;
        private readonly byte[] _lenBuf = new byte[4];
        private readonly object _lock = new object();

        /// <param name="mmf">共享内存块 (见 <see cref="SharedMemoryChannel.OpenOrCreate"/>)</param>
        /// <param name="dataCapacityBytes">数据区容量 (与 OpenOrCreate 传入一致; netstandard2.1 无 Capacity 属性 — 显式携带)</param>
        /// <param name="ownsFile">dispose 时是否释放 mmf (创建方 true, 附着方 false)</param>
        public SharedMemoryRequestWriter(MemoryMappedFile mmf, int dataCapacityBytes, bool ownsFile = true)
        {
            _mmf = mmf ?? throw new ArgumentNullException(nameof(mmf));
            _ownsFile = ownsFile;
            _dataCapacity = dataCapacityBytes;
            _header = mmf.CreateViewAccessor(0, SharedMemoryChannel.HeaderBytes);
            _data = mmf.CreateViewAccessor(SharedMemoryChannel.HeaderBytes, dataCapacityBytes);
        }

        protected override void WriteLineCore(string line)
        {
            var payload = (line ?? string.Empty) + "\n";
            var bytes = Encoding.UTF8.GetBytes(payload);
            if (bytes.Length > SharedMemoryChannel.MaxRecordBytes)
                throw new IOException($"共享内存单条记录 {bytes.Length}B 超上限 {SharedMemoryChannel.MaxRecordBytes}B");

            lock (_lock)
            {
                uint writePos = _header.ReadUInt32(0);
                uint readPos = _header.ReadUInt32(4);

                // 环形可用空间 (保留 1 字节判满); 不够 → 等消费者推进 (有限重试, 背压可见)
                var recordLen = 4 + bytes.Length;
                for (int attempt = 0; attempt < 10_000; attempt++)
                {
                    writePos = _header.ReadUInt32(0);
                    readPos = _header.ReadUInt32(4);
                    ulong used = writePos >= readPos
                        ? (ulong)(writePos - readPos)
                        : (ulong)(_dataCapacity - (long)(readPos - writePos));
                    if (used + (ulong)recordLen < (ulong)_dataCapacity)
                        break;
                    if (attempt == 9_999)
                        throw new IOException("共享内存环形区满且消费者长时间未推进 (背压超限)");
                    Thread.Yield();
                }

                // [uint len][bytes] — 跨环形边界拆两段写
                WriteCircular(writePos, _lenBuf, 0, 4);
                _lenBuf[0] = (byte)recordLen;
                _lenBuf[1] = (byte)(recordLen >> 8);
                _lenBuf[2] = (byte)(recordLen >> 16);
                _lenBuf[3] = (byte)(recordLen >> 24);
                WriteCircular(writePos, _lenBuf, 0, 4);
                WriteCircular(writePos + 4, bytes, 0, bytes.Length);

                _header.Write(0, writePos + (uint)recordLen);
                _header.Flush();
            }
        }

        /// <summary>环形写: pos 起写 src[0..count) (自动回绕)。</summary>
        private void WriteCircular(uint pos, byte[] src, int srcOffset, int count)
        {
            var p = (int)(pos % (uint)_dataCapacity);
            var first = Math.Min(count, _dataCapacity - p);
            _data.WriteArray(p, src, srcOffset, first);
            if (first < count)
                _data.WriteArray(0, src, srcOffset + first, count - first);
        }

        public void Dispose()
        {
            _header.Dispose();
            _data.Dispose();
            if (_ownsFile)
                _mmf.Dispose();
        }
    }

    /// <summary>共享内存读侧 (前端消费 agent 输出): 实现 AgentReportReaderBase 按行读。</summary>
    public sealed class SharedMemoryReportReader : AgentReportReaderBase, IDisposable
    {
        private readonly MemoryMappedFile _mmf;
        private readonly MemoryMappedViewAccessor _header;
        private readonly MemoryMappedViewAccessor _data;
        private readonly int _dataCapacity;
        private readonly bool _ownsFile;
        private readonly byte[] _lenBuf = new byte[4];
        private readonly MemoryStream _lineBuf = new MemoryStream();

        public SharedMemoryReportReader(MemoryMappedFile mmf, int dataCapacityBytes, bool ownsFile = false)
        {
            _mmf = mmf ?? throw new ArgumentNullException(nameof(mmf));
            _ownsFile = ownsFile;
            _dataCapacity = dataCapacityBytes;
            _header = mmf.CreateViewAccessor(0, SharedMemoryChannel.HeaderBytes);
            _data = mmf.CreateViewAccessor(SharedMemoryChannel.HeaderBytes, dataCapacityBytes);
        }

        /// <summary>读一行 (阻塞自旋直到有完整记录)。EOF 恒 null — 共享内存通道无自然 EOF (进程退出由宿主层处置)。</summary>
        protected override string? ReadLineCore()
        {
            var line = new StringBuilder();
            while (true)
            {
                var chunk = ReadRecord();
                if (chunk is null)
                    continue; // 无数据 → 自旋等待
                var text = Encoding.UTF8.GetString(chunk);
                var nl = text.IndexOf('\n');
                if (nl < 0)
                {
                    line.Append(text); // 记录未含行尾 (写侧保证带 \n — 防御: 继续聚合)
                    continue;
                }
                line.Append(text, 0, nl);
                return line.ToString();
            }
        }

        /// <summary>读一条完整记录 (无数据返回 null; 读位置前推)。</summary>
        private byte[]? ReadRecord()
        {
            uint writePos = _header.ReadUInt32(0);
            uint readPos = _header.ReadUInt32(4);
            if (readPos == writePos)
                return null; // 空

            ReadCircular(readPos, _lenBuf, 0, 4);
            int recordLen = _lenBuf[0] | (_lenBuf[1] << 8) | (_lenBuf[2] << 16) | (_lenBuf[3] << 24);
            if (recordLen <= 4 || recordLen > SharedMemoryChannel.MaxRecordBytes + 4)
                throw new IOException($"共享内存记录长度非法 ({recordLen}B) — 通道错位或版本不匹配");

            var bytes = new byte[recordLen - 4];
            ReadCircular(readPos + 4, bytes, 0, bytes.Length);
            _header.Write(4, readPos + (uint)recordLen);
            _header.Flush();
            return bytes;
        }

        /// <summary>环形读: pos 起读 count 字节到 dst[dstOffset..] (自动回绕)。</summary>
        private void ReadCircular(uint pos, byte[] dst, int dstOffset, int count)
        {
            var p = (int)(pos % (uint)_dataCapacity);
            var first = Math.Min(count, _dataCapacity - p);
            _data.ReadArray(p, dst, dstOffset, first);
            if (first < count)
                _data.ReadArray(0, dst, dstOffset + first, count - first);
        }

        public void Dispose()
        {
            _header.Dispose();
            _data.Dispose();
            if (_ownsFile)
                _mmf.Dispose();
        }
    }
}
