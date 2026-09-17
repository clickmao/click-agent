using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace agent.io
{
    /// <summary>
    /// Socket (TCP) 传输 (v0.11.0 用户定案方案③): 跨机/跨容器行协议通道。
    ///
    /// 拓扑: agent 侧为服务端 (<see cref="SocketChannelServer"/> — 监听端口, 每连接一组 writer/reader),
    /// 前端侧为客户端 (<see cref="SocketChannel.Connect"/>)。与 Console.IO/共享内存同一线协议,
    /// 命令层 (<see cref="AgentCommandWriter"/>/<see cref="AgentCommandReader"/>) 无感切换。
    ///
    /// 帧格式: 直接按 \n 分行 (与行协议一致 — 无额外二进制帧头, 抓包即读)。
    /// 写线程安全: lock 内单次写入; 读侧单线程消费假设 (前端事件循环)。
    /// </summary>
    public static class SocketChannel
    {
        /// <summary>默认端口 (click-agent 行协议通道; 部署可改)。</summary>
        public const int DefaultPort = 47_810;

        /// <summary>客户端连接 (前端侧): 返回该连接的 writer/reader 对。</summary>
        public static (SocketRequestWriter Writer, SocketReportReader Reader) Connect(string host, int port)
        {
            var client = new TcpClient();
            client.Connect(host, port);
            var stream = client.GetStream();
            return (new SocketRequestWriter(stream, client), new SocketReportReader(stream, client));
        }
    }
}
