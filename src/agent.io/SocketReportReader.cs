using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace agent.io
{
    /// <summary>Socket 读侧: 实现 AgentReportReaderBase (跨 TCP 段聚行 — 单缓冲 + 已消费指针)。</summary>
    public sealed class SocketReportReader : AgentReportReaderBase, IDisposable
    {
        private readonly NetworkStream _stream;
        private readonly TcpClient? _client;
        private readonly bool _ownsClient;

        /// <summary>接收缓冲 (已消费部分不搬移, 用 _pos 指针; 单行超长时扩容)。</summary>
        private byte[] _buf = new byte[8192];
        private int _len;   // 缓冲内有效字节数
        private int _pos;   // 下一个待消费字节

        public SocketReportReader(NetworkStream stream, TcpClient client = null, bool ownsClient = true)
        {
            _stream = stream ?? throw new ArgumentNullException(nameof(stream));
            _client = client;
            _ownsClient = ownsClient && client != null;
        }

        /// <summary>读一行 (阻塞直到完整行; 对端关闭/异常返回 null = EOF 语义)。</summary>
        protected override string? ReadLineCore()
        {
            while (true)
            {
                // 1) 本地缓冲找行尾
                var start = _pos;
                while (_pos < _len)
                {
                    if (_buf[_pos] == (byte)'\n')
                    {
                        var line = Encoding.UTF8.GetString(_buf, start, _pos - start);
                        _pos++;
                        return line;
                    }
                    _pos++;
                }

                // 2) 无行尾 → 腾空间再收一段 (对端一行可跨多个 TCP 段)
                EnsureCapacity(_len + 1);
                int read;
                try
                {
                    read = _stream.Read(_buf, _len, _buf.Length - _len);
                }
                catch (Exception ex) when (ex is IOException || ex is ObjectDisposedException || ex is SocketException)
                {
                    return null; // 连接异常 = EOF (宿主层决定重连)
                }
                if (read == 0)
                {
                    // 对端关闭但还有未消费数据 → 先吐完 (防御; 协议保证以 \n 结尾故此处 _pos == _len)
                    if (start < _len)
                        return Encoding.UTF8.GetString(_buf, start, _len - start);
                    return null;
                }
                _len += read;
            }
        }

        /// <summary>确保缓冲有 ≥1 字节空闲 (满则扩容或压实头部)。</summary>
        private void EnsureCapacity(int requiredEnd)
        {
            if (_buf.Length - _len >= 1)
                return;
            if (_pos > 0)
            {
                // 压实: 已消费头部丢弃
                System.Array.Copy(_buf, _pos, _buf, 0, _len - _pos);
                _len -= _pos;
                _pos = 0;
                if (_buf.Length - _len >= 1)
                    return;
            }
            var bigger = new byte[_buf.Length * 2];
            System.Array.Copy(_buf, bigger, _len);
            _buf = bigger;
        }

        public void Dispose()
        {
            _stream.Dispose();
            if (_ownsClient && _client != null)
                _client.Dispose();
        }
    }
}
