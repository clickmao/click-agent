using System.Text.Json;
using Xunit;
using agent.frontendapi;
namespace agent.tests;

/// <summary>
/// R375 (exp2 P0-2/P0-3): ask 域信封 — 结构化选项/数据类型必须进通道 (不得只拼进文本),
/// 非法 payload 必须显式拒绝 (不静默当空答案)。
/// </summary>
public class AskEnvelopeTests
{
    private static AskQuestion ChoiceQuestion() => new(
        "region", "部署区域", Required: true, Sensitive: false, DataType: "choice", MultiSelect: false,
        Options: new[]
        {
            new AskOption("cn-north", "华北 (推荐)", true),
            new AskOption("cn-south", "华南", false),
        },
        DefaultValue: "cn-north");

    [Fact]
    public void 信封形状_契约字段齐全()
    {
        var json = AskEnvelope.BuildAsk("ask-1a2b3c4d", "deploy", "选择部署区域", 120, 1, new[] { ChoiceQuestion() });
        using var d = JsonDocument.Parse(json);
        var r = d.RootElement;
        Assert.Equal(1, r.GetProperty("v").GetInt32());
        Assert.Equal("event", r.GetProperty("type").GetString());
        Assert.Equal("ask", r.GetProperty("event").GetString());
        var p = r.GetProperty("payload");
        Assert.Equal("ask-1a2b3c4d", p.GetProperty("ask_id").GetString());
        Assert.Equal("deploy", p.GetProperty("service").GetString());
        Assert.Equal(120, p.GetProperty("timeout_s").GetInt32());
        Assert.Equal(1, p.GetProperty("group_size").GetInt32());
    }

    [Fact]
    public void 选项结构化下发_不只拼文本()
    {
        using var d = JsonDocument.Parse(
            AskEnvelope.BuildAsk("ask-x", "svc", "p", 30, 1, new[] { ChoiceQuestion() }));
        var q = d.RootElement.GetProperty("payload").GetProperty("questions")[0];
        Assert.Equal("choice", q.GetProperty("data_type").GetString());
        Assert.False(q.GetProperty("multi_select").GetBoolean());
        Assert.Equal("cn-north", q.GetProperty("default_value").GetString());
        var opts = q.GetProperty("options");
        Assert.Equal(2, opts.GetArrayLength());
        Assert.Equal("cn-north", opts[0].GetProperty("value").GetString());
        Assert.Equal("华北 (推荐)", opts[0].GetProperty("label").GetString());
        Assert.True(opts[0].GetProperty("recommended").GetBoolean());
        Assert.Equal("cn-south", opts[1].GetProperty("value").GetString());
        Assert.False(opts[1].GetProperty("recommended").GetBoolean());
    }

    [Fact]
    public void 多选与无默认值_进通道()
    {
        var q = new AskQuestion("mods", "启用模块", true, false, "multi_choice", true,
            new[] { new AskOption("a", "A", false) }, null);
        using var d = JsonDocument.Parse(AskEnvelope.BuildAsk("ask-m", "svc", "p", 30, 1, new[] { q }));
        var node = d.RootElement.GetProperty("payload").GetProperty("questions")[0];
        Assert.Equal("multi_choice", node.GetProperty("data_type").GetString());
        Assert.True(node.GetProperty("multi_select").GetBoolean());
        Assert.False(node.TryGetProperty("default_value", out _)); // null 默认值不下发, 不伪造
    }

    [Fact]
    public void 关闭事件_带原因()
    {
        using var d = JsonDocument.Parse(AskEnvelope.BuildClosed("ask-9", "timeout"));
        Assert.Equal(1, d.RootElement.GetProperty("v").GetInt32());
        Assert.Equal("event", d.RootElement.GetProperty("type").GetString());
        Assert.Equal("ask_closed", d.RootElement.GetProperty("event").GetString());
        Assert.Equal("timeout", d.RootElement.GetProperty("payload").GetProperty("reason").GetString());
    }

    [Fact]
    public void 解析回复_合法()
    {
        Assert.True(AskEnvelope.TryParseReply("{\"ask_id\":\"ask-1\",\"answers\":{\"region\":\"cn-south\"}}", out var r));
        Assert.Equal("ask-1", r!.AskId);
        Assert.Equal("cn-south", r.Answers!["region"]);
        Assert.False(r.Cancel);
    }

    [Fact]
    public void 解析回复_取消_答案为空()
    {
        Assert.True(AskEnvelope.TryParseReply("{\"ask_id\":\"ask-2\",\"cancel\":true}", out var r));
        Assert.True(r!.Cancel);
        Assert.Null(r.Answers);
    }

    [Fact]
    public void 解析回复_标量答案转字符串()
    {
        Assert.True(AskEnvelope.TryParseReply("{\"ask_id\":\"ask-3\",\"answers\":{\"n\":42,\"b\":true}}", out var r));
        Assert.Equal("42", r!.Answers!["n"]);
        Assert.Equal("true", r.Answers["b"]);
    }

    [Fact]
    public void 解析回复_非法必须显式拒绝()
    {
        Assert.False(AskEnvelope.TryParseReply("{}", out _));
        Assert.False(AskEnvelope.TryParseReply("{\"ask_id\":\"\"}", out _));
        Assert.False(AskEnvelope.TryParseReply("{\"ask_id\":123}", out _));
        Assert.False(AskEnvelope.TryParseReply("{\"ask_id\":null}", out _));
        Assert.False(AskEnvelope.TryParseReply("not-json", out _));
        Assert.False(AskEnvelope.TryParseReply("[1,2]", out _));
    }
}
