using System;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace agent.llmservice;

/// <summary>v0.20.2 (R345): llm-service 状态查询客户端 (供 CLI `/llm-service` 指令观测)。
/// 连 manager sock 发 {"op":"status"} → 解析 → 渲染文本。manager 不在 → 返回 offline 结果 (不抛)。</summary>
public sealed class LlmServiceStatus
{
    public bool Online { get; init; }
    public string? Error { get; init; }
    public int ManagerPid { get; init; }
    public bool WorkerRunning { get; init; }
    public int WorkerPid { get; init; }
    public long WorkerRssMb { get; init; }
    public long Requests { get; init; }
    public long Spawns { get; init; }
    public long Unloads { get; init; }
    public long MemAvailableMb { get; init; }
    public long MemFloorMb { get; init; }
    public int ActiveCli { get; init; }

    /// <summary>查询 (最长 800ms; manager 未运行 → Online=false, 不抛异常)。</summary>
    public static LlmServiceStatus Query(string? sockPath = null)
    {
        var sock = sockPath ?? agent.llamalocal.RemoteEmbedder.GetSockFromEnv();
        try
        {
            using var s = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            s.Connect(new UnixDomainSocketEndPoint(sock));
            s.ReceiveTimeout = 800;
            s.SendTimeout = 800;
            s.Send(Encoding.UTF8.GetBytes("{\"op\":\"status\"}\n"), SocketFlags.None);
            var buf = new byte[4096];
            var n = s.Receive(buf, 0, buf.Length, SocketFlags.None);
            if (n <= 0) return new LlmServiceStatus { Online = false, Error = "无响应" };
            var text = Encoding.UTF8.GetString(buf, 0, n).Trim();
            using var doc = JsonDocument.Parse(text);
            var r = doc.RootElement;
            return new LlmServiceStatus
            {
                Online = r.TryGetProperty("ok", out var ok) && ok.GetBoolean(),
                ManagerPid = GetInt(r, "manager_pid"),
                WorkerRunning = r.TryGetProperty("worker_running", out var wr) && wr.GetBoolean(),
                WorkerPid = GetInt(r, "worker_pid"),
                WorkerRssMb = GetLong(r, "worker_rss_mb"),
                Requests = GetLong(r, "requests"),
                Spawns = GetLong(r, "spawns"),
                Unloads = GetLong(r, "unloads"),
                MemAvailableMb = GetLong(r, "mem_available_mb"),
                MemFloorMb = GetLong(r, "mem_floor_mb"),
                ActiveCli = GetInt(r, "active_cli"),
            };
        }
        catch (Exception ex)
        {
            return new LlmServiceStatus { Online = false, Error = ex.Message };
        }
    }

    private static long GetLong(JsonElement r, string name)
        => r.TryGetProperty(name, out var v) && v.TryGetInt64(out var x) ? x : -1;

    private static int GetInt(JsonElement r, string name)
        => r.TryGetProperty(name, out var v) && v.TryGetInt32(out var x) ? x : -1;

    /// <summary>渲染 (CLI 输出; 纯文本, 无 ANSI)。</summary>
    public string Render(string sockPath)
    {
        if (!Online)
            return $"llm-service: 未运行 (sock={sockPath}"
                + (string.IsNullOrEmpty(Error) ? "" : $", {Error}")
                + ")\n  启动: agenthost --llm-manager   (或 env AGENTFRAMEWORK_BGE_MODE=remote 时自动拉起)";
        var sb = new StringBuilder();
        sb.Append("llm-service 状态 (llm-manager 独立进程):\n");
        sb.Append($"  manager: pid={ManagerPid} 常驻 (0 模型)\n");
        sb.Append(WorkerRunning
            ? $"  worker:  运行中 pid={WorkerPid} RSS={WorkerRssMb}MB (bge 常驻, 全 CLI 共享)\n"
            : "  worker:  未运行 (lazy — 首个使用请求时拉起)\n");
        sb.Append($"  请求数: {Requests} / lazy 拉起: {Spawns} 次 / 卸载: {Unloads} 次\n");
        sb.Append($"  内存: 可用 {MemAvailableMb}MB (卸载阈值 <{MemFloorMb}MB) / 活跃 CLI 实例: {ActiveCli}\n");
        sb.Append(WorkerRunning
            ? "  卸载条件: 资源紧张 ∧ 无 CLI 实例 ∧ 无进行中请求 (空闲长连接不阻止; 不按时间)"
            : "  (worker 未运行 = 0 内存占用; 下次使用自动 lazy 重载)");
        return sb.ToString();
    }
}
