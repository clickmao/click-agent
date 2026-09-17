using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


/// <summary>R350: 状态域 + 元域 handler (P1; payload 由 caller 注入 — AgentRuntime 状态组装点)。</summary>
public static class FrontendApiRouter
{
    public static Func<string, string?> Build(
        Func<string> snapshotBuilder,   // state.snapshot payload 组装 (宿主注入)
        Func<string> metaInfo)          // meta.info
        => api => api switch
        {
            "state.snapshot" => snapshotBuilder(),
            "state.hello" => "{\"hello\":true}",
            "meta.ping" => "{\"pong\":true}",
            "meta.info" => metaInfo(),
            _ => null,
        };
}
