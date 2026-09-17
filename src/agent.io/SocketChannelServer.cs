using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace agent.io
{
    /// <summary>TCP 服务端 (agent 侧): 监听 + Accept 一条前端连接。</summary>
    public sealed class SocketChannelServer : IDisposable
    {
        private readonly TcpListener _listener;

        /// <param name="port">监听端口 (默认 47810)</param>
        public SocketChannelServer(int port = SocketChannel.DefaultPort)
        {
            _listener = TcpListener.Create(port);
            _listener.Start();
        }

        /// <summary>阻塞等待一条前端连接, 返回其 writer/reader 对 (每连接独立实例)。</summary>
        public (SocketRequestWriter Writer, SocketReportReader Reader) AcceptFrontend()
        {
            var client = _listener.AcceptTcpClient();
            var stream = client.GetStream();
            return (new SocketRequestWriter(stream, client), new SocketReportReader(stream, client));
        }

        public void Dispose() => _listener.Stop();
    }
}
