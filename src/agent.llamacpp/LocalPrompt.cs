namespace agent.llamacpp;

/// <summary>会话轮次（本地 prompt 渲染的输入单位；裸 prompt 不再进入生成热路径）。</summary>
public sealed record ChatTurn(string Role, string Content);

/// <summary>
/// 本地 prompt 的来源凭证。闸门只承认 <see cref="GgufJinja"/>：模板取自 GGUF 元数据、由服务端内嵌 jinja 渲染，
/// 调用方物理上无法绕过模板。 <see cref="Literal"/> 仅由诊断入口产生，一律被闸门拒收（负控锚点）。
/// </summary>
public enum LocalPromptProvenance
{
    /// <summary>模板来自模型元数据（服务端 /apply-template）。</summary>
    GgufJinja = 0,

    /// <summary>调用方手拼字面 prompt（诊断/对账专用；生产路径必须被闸门拒收）。</summary>
    Literal = 1,
}

/// <summary>渲染产物。字段只放真实测得的东西：文本与来源凭证（token 数由 /completion 的 tokens_evaluated 提供）。</summary>
public sealed record RenderedPrompt(string Text, LocalPromptProvenance Provenance);

/// <summary>模型侧身份与特殊 token（闸门规则的数据来源，来自 GET /props；不硬编码任何模型字面量）。</summary>
public sealed record ModelProps(string? BosToken, string? EosToken, int ChatTemplateLength, string? ModelPath);

/// <summary>
/// 本地 prompt 渲染端口。实现可替换（当前 = llama-server 内嵌 jinja；未来可换其它渲染器），
/// 但闸门只认 GgufJinja 凭证：换实现必须能证明模板来自模型元数据。
/// </summary>
public interface ILocalPromptRenderer
{
    ValueTask<RenderedPrompt> RenderAsync(IReadOnlyList<ChatTurn> turns, CancellationToken ct = default);
}

/// <summary>
/// 本地 prompt 闸门（结构性，非启发式）。规则:
///   1) 来源必须是模型元数据模板（手拼 prompt ⇒ prompt_not_templated）；
///   2) 渲染产物非空；
///   3) 渲染产物不得**字面包含 BOS 文本** —— BOS 归 tokenizer 管，重复注入即双 BOS；
///   4) 渲染产物不得**以 EOS 文本结尾** —— 结尾是 EOS 等于没有可生成位置。
///      （注意: EOS 文本出现在中间是**合法**的 —— 多轮渲染用 EOS 分隔 assistant 轮次，
///       R409 实测 3 条 messages 的渲染产物 118 B 且含 EOS、但不以 EOS 结尾 ⇒ 不能按「包含」拦。）
///
/// 依据（R409 实测，判据预注册后测量）:
///   • 96 B 字面串（BOS 文本 + 渲染体）在 llama.cpp 默认 tokenization 下 = **18 token / 2 个 BOS**；
///   • 67 B 渲染串 + tokenizer 自动 BOS = **17 token / 1 个 BOS**；
///   • 二者所依赖的 token 流相同（ids(96B, add_special=false) ≡ ids(67B, add_special=true)，逐位相等）。
///   ⇒ 规范形式是「渲染串 + 自动 BOS」，字面注入 BOS 是缺陷（每 token 多算一次、且与远端 Jinja 路径前缀不一致 ⇒ K2b 受损）。
/// </summary>
public static class LocalPromptGate
{
    public static void Validate(RenderedPrompt rendered, ModelProps props)
    {
        ArgumentNullException.ThrowIfNull(rendered);
        ArgumentNullException.ThrowIfNull(props);

        if (rendered.Provenance != LocalPromptProvenance.GgufJinja)
        {
            throw new LlamaCppException(LlamaCppException.PromptNotTemplated,
                $"prompt 来源={rendered.Provenance}，非模型元数据模板；手拼 prompt 无模板保证（R409: 裸文本 ⇒ 跑题且不出 EOS）");
        }

        if (string.IsNullOrEmpty(rendered.Text))
            throw new LlamaCppException(LlamaCppException.PromptEmpty, "渲染产物为空（模板未生效或 messages 为空）");

        if (props.BosToken is { Length: > 0 } bos && rendered.Text.Contains(bos, StringComparison.Ordinal))
        {
            throw new LlamaCppException(LlamaCppException.PromptLiteralSpecialToken,
                "渲染产物字面包含 BOS 文本；BOS 由 tokenizer 添加，重复注入即双 BOS（R409 实测 18 vs 规范 17 token）");
        }

        if (props.EosToken is { Length: > 0 } eos && rendered.Text.EndsWith(eos, StringComparison.Ordinal))
        {
            throw new LlamaCppException(LlamaCppException.PromptLiteralSpecialToken,
                "渲染产物以 EOS 文本结尾；结尾是 EOS 等于没有可生成位置（中间出现 EOS 是多轮分隔符，合法）");
        }
    }
}
