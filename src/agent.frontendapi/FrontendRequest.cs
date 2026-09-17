using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


public sealed class FrontendRequest
{
    public string ReqId { get; init; } = "";
    public string Api { get; init; } = "";
    public string PayloadJson { get; init; } = "{}";
}
