using System.Text.Json;
using agent.core;

namespace agent.host;

/// <summary>
/// CLI 会话 (v7.12): 任务执行步骤明细 + 当前状态可查询。
/// 每轮 ProcessAsync 前后记录步骤 (意图/拆解/源装配/LLM/后处理),
/// /status 随时查询; /plan 输出当前 TaskPlan JSON。
/// </summary>
public sealed class CliSession
{
    private readonly IOutputSink _out;
    private readonly string _dataPath;
    private readonly List<string> _steps = new();

    public string SessionId { get; } = "cli-" + Guid.NewGuid().ToString("N")[..8];

    /// <summary>本轮步骤明细 (执行后可查)</summary>
    public IReadOnlyList<string> Steps => _steps;

    public CliSession(IOutputSink output, string dataPath)
    {
        _out = output;
        _dataPath = dataPath;
    }

    public void RecordStep(string what) => _steps.Add($"[{DateTime.Now:HH:mm:ss}] {what}");

    /// <summary>渲染一轮响应: 步骤明细 → markdown 正文 → Data 摘要</summary>
    public void RenderResponse(AgentResponse response, string intent)
    {
        _out.Write("");
        _out.Write(CliRenderer.Bold("── 回复 " + new string('─', 44)));
        if (!response.Success)
        {
            _out.Write(CliRenderer.Red("✗ 失败: " + (response.Error ?? "(无错误信息)")));
            return;
        }

        _out.WriteMarkdown(response.Content);

        if (response.Data.Count > 0)
        {
            var items = response.Data
                .Where(kv => kv.Value is not string s || s.Length < 60)
                .Select(kv => $"{CliRenderer.Dim(kv.Key + "=")}{kv.Value}");
            _out.Write(CliRenderer.Dim("  · " + string.Join("  ", items)));
        }
        _out.Write(CliRenderer.Dim($"  ({response.ExecutionTimeMs}ms, intent={intent})"));
    }

    /// <summary>/status: 当前状态面板</summary>
    public void RenderStatus(int turnCount, string? lastIntent, string? forecastTendency)
    {
        _out.Write(CliRenderer.Bold("── 状态 " + new string('─', 46)));
        _out.Write($"  会话: {SessionId}   轮次: {turnCount}   最近意图: {lastIntent ?? "-"}");
        _out.Write($"  下轮预估倾向: {forecastTendency ?? "(无)"}");
        _out.Write($"  本轮步骤数: {_steps.Count}");
        for (var i = 0; i < _steps.Count; i++)
            _out.Write($"    {CliRenderer.Dim($"[{i + 1:00}]")} {_steps[i]}");
    }
}
