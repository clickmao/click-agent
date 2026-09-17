using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

namespace agent.tests;


/// <summary>测试用 HTTP 客户端工厂 (不共享连接, 保证每次调用都是一次真实 HTTP 往返)。</summary>
internal sealed class StubHttpClientFactory : IHttpClientFactory
{
    public HttpClient CreateClient(string name) => new();
}
