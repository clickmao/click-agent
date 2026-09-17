using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using agent.contract;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// 对照 claude-fable-5.1 设计动因（docs/external-reference/DESIGN-RATIONALE.md）的机械断言。
/// 每条断言绑一条动因，全部可在无网络、无模型条件下判定；全部为**负控可红**形态（改回旧形态必红）。
///   动因2 安全前置          → SafetyBlock_PrecedesOutputContract
///   动因5 工具契约=调用协议 → EveryToolDescription_CarriesExclusionProtocol / DeleteTool_DeclaresApprovalAndFailClosed
///   动因6 schema 字母序     → Names_AreAlphabeticallySorted / ToolsJson_OrderMatchesNames
///   动因1 前缀无易变物      → Prefix_CarriesNoVolatileFacts / IntentSystemPrompt_IsDeterministic_AndDateFree
/// </summary>
public class Fable51AlignmentTests
{
    [Fact]
    public void Names_AreAlphabeticallySorted()
    {
        var sorted = ActionToolDecl.Names.OrderBy(n => n, StringComparer.Ordinal).ToArray();
        Assert.Equal(sorted, ActionToolDecl.Names);
        Assert.Equal(ActionToolDecl.Names.Length, ActionToolDecl.Names.Distinct(StringComparer.Ordinal).Count());
    }

    [Fact]
    public void ToolsJson_OrderMatchesNames()
    {
        using var doc = JsonDocument.Parse(ActionToolDecl.ToolsJson);
        var names = doc.RootElement.EnumerateArray()
            .Select(t => t.GetProperty("function").GetProperty("name").GetString()!)
            .ToArray();
        Assert.Equal(ActionToolDecl.Names, names);
    }

    [Fact]
    public void EveryToolDescription_CarriesExclusionProtocol()
    {
        using var doc = JsonDocument.Parse(ActionToolDecl.ToolsJson);
        foreach (var t in doc.RootElement.EnumerateArray())
        {
            var fn = t.GetProperty("function");
            var desc = fn.GetProperty("description").GetString()!;
            Assert.Contains("不要用于", desc, StringComparison.Ordinal);
        }
    }

    [Fact]
    public void DeleteTool_DeclaresApprovalAndFailClosed()
    {
        using var doc = JsonDocument.Parse(ActionToolDecl.ToolsJson);
        var desc = doc.RootElement.EnumerateArray()
            .First(t => t.GetProperty("function").GetProperty("name").GetString() == ActionToolDecl.DeleteFile)
            .GetProperty("function").GetProperty("description").GetString()!;
        Assert.Contains("审批", desc, StringComparison.Ordinal);
        Assert.Contains("拒绝", desc, StringComparison.Ordinal);
    }

    [Fact]
    public void SafetyBlock_PrecedesOutputContract()
    {
        var gates = StructuredPrompt.Prefix.IndexOf("<hard_gates>", StringComparison.Ordinal);
        var contract = StructuredPrompt.Prefix.IndexOf("<output_contract>", StringComparison.Ordinal);
        Assert.True(gates >= 0, "<hard_gates> 必须存在");
        Assert.True(contract >= 0, "<output_contract> 必须存在");
        Assert.True(gates < contract, "安全硬门必须前置（fable 动因2）");
    }

    [Fact]
    public void Prefix_CarriesNoVolatileFacts()
    {
        var p = StructuredPrompt.Prefix;
        Assert.DoesNotContain(DateTime.UtcNow.Year.ToString(), p, StringComparison.Ordinal);
        Assert.DoesNotContain(DateTime.Now.ToString("yyyy-MM-dd"), p, StringComparison.Ordinal);
        Assert.DoesNotContain("{{", p, StringComparison.Ordinal);
        Assert.DoesNotContain("Environment.", p, StringComparison.Ordinal);
    }

    [Fact]
    public void IntentSystemPrompt_IsDeterministic_AndDateFree()
    {
        var a = IntentPromptTemplates.GetSystemPrompt("general");
        var b = IntentPromptTemplates.GetSystemPrompt("general");
        Assert.Equal(a, b);
        Assert.DoesNotContain(DateTime.Now.ToString("yyyy-MM-dd"), a, StringComparison.Ordinal);
        Assert.DoesNotContain(DateTime.UtcNow.Year.ToString(), a, StringComparison.Ordinal);
    }
}
