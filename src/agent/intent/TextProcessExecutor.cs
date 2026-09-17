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


/// <summary>
/// 本地文本处理 / 证据汇总 (v0.22.0 exp9 D3): 统计/摘要/格式化 —— 纯 CPU, 零 token。
/// 这是"远程生成后如果是文本处理任务就可以本地先跑起来"里的本地那一段。
/// </summary>
public sealed class TextProcessExecutor : ILocalNodeExecutor
{
    public string Id => LocalExecutorRegistry.TextProcess;

    public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
    {
        var text = ResolveInput(node, ctx);
        if (string.IsNullOrEmpty(text) && ctx.ArtifactPath is null)
        {
            return Task.FromResult(PythonSelfTestExecutor.Fail(node.Id,
                "无可用输入 (无上游输出 / 无远程正文 / 无产物) ⇒ 本地处理无对象", NodeFailureKind.Permanent));
        }

        var sb = new StringBuilder();
        sb.Append("本地统计: ");
        if (!string.IsNullOrEmpty(text))
        {
            var lines = text.Split('\n').Length;
            var cjk = text.Count(c => c >= '\u4e00' && c <= '\u9fff');
            sb.Append($"字符={text.Length} 行={lines} 中文={cjk} 词≈{text.Split([' ', '\t', '\n', '\r'], StringSplitOptions.RemoveEmptyEntries).Length} 指纹={Sha(text)}");
        }
        if (ctx.ArtifactPath is { } p && File.Exists(p))
        {
            var fi = new FileInfo(p);
            sb.Append($" | 产物={Path.GetFileName(p)} 字节={fi.Length} 改动={fi.LastWriteTimeUtc:HH:mm:ss}");
        }
        if (ctx.NodeOutputs.Count > 0)
        {
            sb.Append(" | 上游:");
            foreach (var kv in ctx.NodeOutputs)
                sb.Append($" {kv.Key}={(string.IsNullOrEmpty(kv.Value) ? "-" : "有输出")}");
        }

        var summary = sb.ToString();
        AgentTelemetry.Emit("plan_local_text", "PlanRunner",
            ("node", node.Id), ("exec", Id), ("chars", summary.Length), ("tokens", 0L));
        return Task.FromResult(new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = PlanNodeState.Completed,
            Output = summary,
        });
    }

    /// <summary>
    /// 输入解析顺序: 上游输出 → **无依赖? 本轮原文** → 远程正文 (确定性, 可单测)。
    /// D4: 无依赖节点的输入是"用户原文"(模型生成前就在手) —— 不许误取生成正文, 否则本地先行
    ///     会变成"处理别人的产物", 语义就错了。
    /// </summary>
    internal static string ResolveInput(PlanNode node, LocalNodeContext ctx)
    {
        // v0.22.0 exp9 D7: 运行时依赖 (执行中发现的) 与声明依赖同权 —— 它是"我确实要它的产出"的显式契约,
        // 排在声明依赖之前解析, 因为它是更晚、更具体的需求 (调度器已保证其产出就绪才会跑到这里)。
        foreach (var dep in node.RuntimeDeps)
        {
            if (ctx.NodeOutputs.TryGetValue(dep, out var ro) && !string.IsNullOrEmpty(ro))
                return ro!;
        }
        foreach (var dep in node.DependsOn)
        {
            if (ctx.NodeOutputs.TryGetValue(dep, out var o) && !string.IsNullOrEmpty(o))
                return o!;
        }
        if (node.DependsOn.Count == 0 && !string.IsNullOrEmpty(ctx.SourceText))
            return ctx.SourceText!;
        return ctx.RemoteText ?? string.Empty;
    }

    internal static string Sha(string s) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(s)))[..8];
}
