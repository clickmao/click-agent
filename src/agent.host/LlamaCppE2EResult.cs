using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>E2E 结果载体（字段可空语义: 未产出的读数显式为 null/0，读方不得当作"已测到"）。</summary>
public sealed class LlamaCppE2EResult
{
    public string Mode { get; set; } = "";
    /// <summary>prompt 通路来源: "chat_template" = 经 /apply-template 渲染（受闸门保护）；"literal" = 诊断通路（绕过闸门，计入 LiteralPromptCalls）。</summary>
    public string PromptMode { get; set; } = "";
    /// <summary>R410 生成口径: "Session"（开前缀缓存，K2b 用）/"Reconciliation"（关缓存，对账用）。</summary>
    public string ReuseMode { get; set; } = "";
    /// <summary>服务端自报的复用前缀 token 数（cache_n）；Reconciliation 口径下恒 0。</summary>
    public int CachedTokens { get; set; }
    /// <summary>被使用计数: 会话口径调用数。</summary>
    public long SessionReuseCalls { get; set; }
    /// <summary>被使用计数: 对账口径调用数。</summary>
    public long ReconciliationCalls { get; set; }
    /// <summary>会话口径下前缀未命中次数（静默失效可见化）。</summary>
    public long SessionCacheMisses { get; set; }
    public string BaseUrl { get; set; } = "";
    public string Model { get; set; } = "";
    public string PromptSha256 { get; set; } = "";
    public string? Content { get; set; }
    public int[]? TokenIds { get; set; }
    public int TokensPredicted { get; set; }
    public int TokensEvaluated { get; set; }
    public double PredictedPerSecond { get; set; }
    public double PromptPerSecond { get; set; }
    public int[]? ExpectedIds { get; set; }
    public bool? IdsMatch { get; set; }
    public int EmbeddingDim { get; set; }
    public double EmbeddingL2Norm { get; set; }
    public string? EmbeddingSha256 { get; set; }
    public float[]? EmbeddingHead { get; set; }
    public long Requests { get; set; }
    public long TokensGenerated { get; set; }
    public long EmbeddingsServed { get; set; }
    /// <summary>被使用计数: 模板渲染次数（受闸门保护的生成通路）。</summary>
    public long TemplateRenders { get; set; }
    /// <summary>被使用计数: 被闸门拒收的生成请求数。</summary>
    public long PromptGateRejections { get; set; }
    /// <summary>被使用计数: 诊断字面通路调用次数（非 0 说明有调用方绕过模板闸门）。</summary>
    public long LiteralPromptCalls { get; set; }
}
