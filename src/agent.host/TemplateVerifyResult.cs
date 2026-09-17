using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>R409 模板验证结果（判据预注册; 字段可空语义同 E2EResult）。</summary>
public sealed class TemplateVerifyResult
{
    public string Mode { get; set; } = "verify_template";
    public string BaseUrl { get; set; } = "";
    public string Model { get; set; } = "";
    public string? BosToken { get; set; }
    public string? EosToken { get; set; }
    public int ChatTemplateLength { get; set; }
    /// <summary>由模型元数据 BOS 文本自测得到的 token id（不硬编码）。</summary>
    public int? BosId { get; set; }
    /// <summary>臂 A（受闸门保护）: 渲染产物字节数 / sha256 / token 数 / BOS 计数 / 首 6 个 id。</summary>
    public int RenderedBytes { get; set; }
    public string RenderedSha256 { get; set; } = "";
    public int RenderedTokens { get; set; }
    public int RenderedBosCount { get; set; }
    public int[] RenderedHeadIds { get; set; } = [];
    /// <summary>臂 B（负控，未提供时为 null）: 字面串在默认/非默认 tokenization 下的读数。</summary>
    public int? LiteralBytes { get; set; }
    public string? LiteralSha256 { get; set; }
    public int? LiteralTokens { get; set; }
    public int? LiteralBosCount { get; set; }
    public int? LiteralTokensNoSpecial { get; set; }
    /// <summary>交叉等价: ids(字面串, add_special=false) ≡ ids(渲染产物, add_special=true)。</summary>
    public bool? IdsEquivalent { get; set; }
    public string Verdict { get; set; } = "";
    public long TemplateRenders { get; set; }
}
