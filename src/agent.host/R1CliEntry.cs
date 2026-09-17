using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;

namespace agent.host;

/// <summary>
/// R1 接线的宿主入口（薄壳：只做 DI 取 ILLMCaller + 上屏 + 返回 rc）。
/// 上屏次序：契约 JSON 正文 → R1_STATS 单行标记（机读取数，不靠 grep 锚）。
/// 返回 rc ∈ {0,2,3,4,5,6}，与 agent.contract.PipelineOutcome 同域（6 = 前缀漂移/传输失败）。
/// </summary>
public static class R1CliEntry
{
    public static async Task<int> RunAsync(ServiceProvider provider, IOutputSink sink, string taskText, CancellationToken ct)
    {
        var caller = provider.GetRequiredService<agent.ILLMCaller>();
        var opt = agent.r1.R1Options.FromEnvironment("./");
        var result = await agent.r1.R1Pipeline.RunAsync(caller, taskText, opt, ct).ConfigureAwait(false);

        if (!string.IsNullOrEmpty(result.ReplyText))
        {
            sink.Write(result.ReplyText);
        }
        sink.Write(agent.r1.R1Transcript.Marker(result));
        return result.Rc;
    }
}
