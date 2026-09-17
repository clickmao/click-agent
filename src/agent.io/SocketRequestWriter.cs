using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace agent.io
{
    /// <summary>Socket 写侧: 实现 AgentRequestWriterBase (行 → utf8 + \n → 一次写入)。</summary>
    public sealed class SocketRequestWriter : AgentRequestWriterBase, IDisposable
    {
        private readonly NetworkStream _stream;
        private readonly TcpClient? _client;
        private readonly bool _ownsClient;
        private readonly object _lock = new object();

        public SocketRequestWriter(NetworkStream stream, TcpClient client = null, bool ownsClient = true)
        {
            _stream = stream ?? throw new ArgumentNullException(nameof(stream));
            _client = client;
            _ownsClient = ownsClient && client != null;
        }

        protected override void WriteLineCore(string line)
        {
            var bytes = Encoding.UTF8.GetBytes((line ?? string.Empty) + "\n");
            lock (_lock)
            {
                _stream.Write(bytes, 0, bytes.Length);
                _stream.Flush();
            }
        }

        public void Dispose()
        {
            _stream.Dispose();
            if (_ownsClient && _client != null)
                _client.Dispose();
        }
    }
}
