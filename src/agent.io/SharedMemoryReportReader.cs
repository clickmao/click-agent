using System;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;

namespace agent.io
{
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
