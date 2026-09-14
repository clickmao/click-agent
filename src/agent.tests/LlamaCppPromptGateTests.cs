using System;
using System.Security.Cryptography;
using System.Text;
using Xunit;
using agent.llamacpp;

namespace agentframework.tests;

/// <summary>
/// R409: 本地 prompt 模板闸门的负控测试（判据预注册，纯逻辑，不需要 llama-server）。
///
/// 锚点全部来自 R409 同机实测（llama-server 8932, r1-distill-qwen-1.5b-q4km, --jinja）:
///   • 96 B 字面串 sha256 d1e94bf7… —— 默认 tokenization(add_special=true) = 18 token / 2 个 BOS；
///     add_special=false = 17 token / 1 个 BOS（R407/R408 曾把该串当「权威 prompt」，实为非规范形式）。
///   • 67 B 渲染串 sha256 25e467ee… —— /apply-template 产物（无 BOS 文本），+ 自动 BOS = 17 token，
///     其 token 流与「96 B + add_special=false」逐位相等 ⇒ 规范形式是渲染串。
///   • 3 条 messages 的多轮渲染 = 118 B，含 EOS 文本（轮分隔符）但不以 EOS 结尾 ⇒ EOS 只能按「结尾」判，不能按「包含」判。
///
/// 负控要求（反向注入）:
///   ① 来源=Literal ⇒ 必须红（prompt_not_templated）；
///   ② 来源=GgufJinja 但文本含 BOS 字面 ⇒ 必须红（prompt_literal_special_token）—— 防「渲染 + 再塞一次 BOS」回归；
///   ③ 以 EOS 结尾 ⇒ 必须红；但中间含 EOS 的合法多轮产物必须绿（防过度拦截）；
///   ④ 空产物 ⇒ 必须红；
///   ⑤ 无元数据（BosToken/EosToken 为 null）时不得误拦。
/// </summary>
public sealed class LlamaCppPromptGateTests
{
    private const string BosText = "<｜begin▁of▁sentence｜>";
    private const string EosText = "<｜end▁of▁sentence｜>";

    /// <summary>/apply-template 对单条 user 消息的产物（67 B，无 BOS 文本）。</summary>
    private const string RenderedUserProbe = "<｜User｜>What is 12*12? Answer with the number.<｜Assistant｜>";

    /// <summary>R407/R408 归档的「权威」字面串（96 B = BOS 文本 + 渲染体）。</summary>
    private static readonly string LiteralAuthority = BosText + RenderedUserProbe;

    /// <summary>3 条 messages 的多轮渲染产物（118 B；EOS 作轮分隔符，不以 EOS 结尾）。</summary>
    private const string RenderedMultiTurn =
        "<｜User｜>What is 12*12?<｜Assistant｜>144<｜end▁of▁sentence｜><｜User｜>And double that?<｜Assistant｜>";

    private static ModelProps Props => new(BosText, EosText, 2081, "r1-distill-qwen-1.5b-q4km.gguf");

    // ── 锚点（防漂移）────────────────────────────────────────────────
    [Fact]
    public void Anchors_MatchR409MeasuredFacts()
    {
        Assert.Equal(96, Encoding.UTF8.GetByteCount(LiteralAuthority));
        Assert.Equal("d1e94bf720adbab7b376d0014bfeb01a8c03864cae7c4a1110ab9be5750fa947", Sha256Hex(LiteralAuthority));
        Assert.Equal(67, Encoding.UTF8.GetByteCount(RenderedUserProbe));
        Assert.Equal("25e467ee2ae3bb0f68707bf6d51246dc4f9ce0476ecb8154cf3098f781174567", Sha256Hex(RenderedUserProbe));
        Assert.Equal(118, Encoding.UTF8.GetByteCount(RenderedMultiTurn));
        Assert.Contains(EosText, RenderedMultiTurn, StringComparison.Ordinal);
        Assert.False(RenderedMultiTurn.EndsWith(EosText, StringComparison.Ordinal));
    }

    // ── 正例：受闸门保护的通路必须绿 ─────────────────────────────────
    [Fact]
    public void SingleTurnRenderedPrompt_Passes()
    {
        LocalPromptGate.Validate(new RenderedPrompt(RenderedUserProbe, LocalPromptProvenance.GgufJinja), Props);
    }

    [Fact]
    public void MultiTurnRenderedPrompt_WithEosSeparator_Passes()
    {
        // 中间含 EOS 文本是合法轮分隔符 ⇒ 不得被拦
        LocalPromptGate.Validate(new RenderedPrompt(RenderedMultiTurn, LocalPromptProvenance.GgufJinja), Props);
    }

    // ── 负控 ①：来源 = Literal（手拼）必须红 ─────────────────────────
    [Fact]
    public void NegativeControl_LiteralProvenance_IsRejected_NotTemplated()
    {
        var ex = Assert.Throws<LlamaCppException>(() =>
            LocalPromptGate.Validate(new RenderedPrompt(RenderedUserProbe, LocalPromptProvenance.Literal), Props));
        Assert.Equal(LlamaCppException.PromptNotTemplated, ex.Code);
    }

    [Fact]
    public void NegativeControl_LiteralProvenanceWithCleanText_StillRejected()
    {
        var ex = Assert.Throws<LlamaCppException>(() =>
            LocalPromptGate.Validate(new RenderedPrompt("plain text, no markers", LocalPromptProvenance.Literal), Props));
        Assert.Equal(LlamaCppException.PromptNotTemplated, ex.Code);
    }

    // ── 负控 ②：渲染 + 字面 BOS ⇒ 必须红（防双 BOS 回归）─────────────
    [Fact]
    public void NegativeControl_LiteralBosTextInRenderedPrompt_IsRejected()
    {
        var ex = Assert.Throws<LlamaCppException>(() =>
            LocalPromptGate.Validate(new RenderedPrompt(LiteralAuthority, LocalPromptProvenance.GgufJinja), Props));
        Assert.Equal(LlamaCppException.PromptLiteralSpecialToken, ex.Code);
    }

    // ── 负控 ③：以 EOS 结尾 ⇒ 必须红 ────────────────────────────────
    [Fact]
    public void NegativeControl_TrailingEosText_IsRejected()
    {
        var ex = Assert.Throws<LlamaCppException>(() =>
            LocalPromptGate.Validate(new RenderedPrompt(RenderedUserProbe + EosText, LocalPromptProvenance.GgufJinja), Props));
        Assert.Equal(LlamaCppException.PromptLiteralSpecialToken, ex.Code);
    }

    // ── 负控 ④：空产物 ⇒ 必须红 ─────────────────────────────────────
    [Fact]
    public void NegativeControl_EmptyRenderedPrompt_IsRejected()
    {
        var ex = Assert.Throws<LlamaCppException>(() =>
            LocalPromptGate.Validate(new RenderedPrompt("", LocalPromptProvenance.GgufJinja), Props));
        Assert.Equal(LlamaCppException.PromptEmpty, ex.Code);
    }

    // ── 负控 ⑤：无元数据时不得误拦 ──────────────────────────────────
    [Fact]
    public void NoMetadata_MustNotOverBlock()
    {
        LocalPromptGate.Validate(
            new RenderedPrompt(RenderedUserProbe, LocalPromptProvenance.GgufJinja),
            new ModelProps(null, null, 0, null));
    }

    private static string Sha256Hex(string s) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(s))).ToLowerInvariant();
}
