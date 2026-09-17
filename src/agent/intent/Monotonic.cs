using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>单调时钟 (跨平台, 不受系统时间调整影响) —— 用于"本地先行与远程生成真重叠"的测量</summary>
public static class Monotonic
{
    private static readonly double TicksPerUs = Stopwatch.Frequency / 1_000_000.0;

    /// <summary>毫秒 (TickCount64, 跨平台单调): 长时段用</summary>
    public static long NowMs() => Environment.TickCount64;

    /// <summary>微秒 (Stopwatch 计时器): 本地节点常在**亚毫秒**完成 —— 毫秒分辨率会把"真重叠"舍入成 0,
    /// 那就成了假证据 (声称并行先行, 数字却是 0)。</summary>
    public static long NowUs() => (long)(Stopwatch.GetTimestamp() / TicksPerUs);
}
