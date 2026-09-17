using agent.core;
using agent.session;
using Microsoft.Extensions.Logging;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;


/// <summary>测试宿主: 提供 SessionManager 实例</summary>
public static class TestHost
{
    public static SessionManager CreateSessionManager()
    {
        var factory = Microsoft.Extensions.Logging.LoggerFactory.Create(b => { });
        return new SessionManager(factory.CreateLogger<SessionManager>());
    }
}
