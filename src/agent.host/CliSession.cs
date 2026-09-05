using System.Text.Json;
using agent.core;
using agent.output;

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
    private readonly OutputMode _mode;
    private readonly SpectreOutputRenderer _renderer;
    private readonly List<string> _steps = new();

    public string SessionId { get; } = "cli-" + Guid.NewGuid().ToString("N")[..8];

    /// <summary>本轮步骤明细 (执行后可查)</summary>
    public IReadOnlyList<string> Steps => _steps;

    /// <param name="mode">输出模式 (v7.13): Markdown=全格式美化 / PlainText=平铺着色 (默认 markdown)</param>
    public CliSession(IOutputSink output, string dataPath, OutputMode mode = OutputMode.Markdown)
    {
        _out = output;
        _dataPath = dataPath;
        _mode = mode;
        _renderer = new SpectreOutputRenderer();
    }

    public void RecordStep(string what) => _steps.Add($"[{DateTime.Now:HH:mm:ss}] {what}");

    /// <summary>渲染一轮响应: 步骤明细 → 底层消息 (双模式) → Data 摘要</summary>
    public void RenderResponse(AgentResponse response, string intent, List<AgentOutputSegment>? segments = null)
    {
        _out.Write("");
        _out.Write(CliRenderer.Bold("── 回复 " + new string('─', 44)));
        if (!response.Success)
        {
            // 错误也走底层格式 (统一管道, 控制台着色)
            _renderer.Render(new AgentOutputMessage
            {
                Kind = AgentOutputKind.Error,
                Mode = _mode,
                Content = "失败: " + (response.Error ?? "(无错误信息)"),
                Source = "CliSession",
            });
            return;
        }

        // v7.13: LLM 内容 → 底层 AgentOutputMessage → 双模式渲染 (markdown 全格式 / 纯文本平铺, 控制台均着色)
        var message = AgentOutputMessage.FromLlmAnswer(response.Content, "pipeline", segments);
        message.Mode = _mode;
        _renderer.Render(message);

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
