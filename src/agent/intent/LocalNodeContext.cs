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
/// 本地节点执行上下文 (v0.22.0 exp9 D3) —— 本地执行器只允许依赖这些**本地事实**,
/// 禁止联网/调模型 (接口契约: 本地执行 = 零 token)。
/// </summary>
public sealed class LocalNodeContext
{
    /// <summary>本轮产物路径 (远程节点产出的可跑对象; 由台账/主链提供)</summary>
    public string? ArtifactPath { get; set; }

    /// <summary>本轮远程生成正文 (Hybrid 节点的第二段输入; 主链产出, 不重复调用模型)</summary>
    public string? RemoteText { get; set; }

    /// <summary>远程产物是否已就绪 (未就绪 ⇒ 依赖它的本地节点不许假装成功)</summary>
    public bool HasRemoteProduct => !string.IsNullOrEmpty(ArtifactPath) || !string.IsNullOrEmpty(RemoteText);

    public string? SessionId { get; init; }

    /// <summary>本轮用户原文 (v0.22.0 exp9 D4): 无依赖本地文本节点的输入 —— 模型生成前即已就绪,
    /// 这正是"本地先行"能真并行的前提。</summary>
    public string? SourceText { get; init; }

    /// <summary>python 解释器路径 (null = 由运行级解析器决定)</summary>
    public string? PythonPath { get; init; }

    public int TimeoutMs { get; init; } = PythonRunVerifier.DefaultTimeoutMs;

    /// <summary>运行级闸门 (null = 读 AGENTFRAMEWORK_PY_RUN)</summary>
    public Func<bool>? PythonRunGate { get; init; }

    /// <summary>上游节点输出 (键=节点 Id; 由 PlanRunner 按执行序写入, 本地执行器可读)</summary>
    public Dictionary<string, string?> NodeOutputs { get; } = new(StringComparer.Ordinal);
}
