using System;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;

namespace agent.io
{
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
}
