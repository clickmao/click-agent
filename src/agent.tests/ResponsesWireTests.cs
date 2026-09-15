using System.Text.Json;
using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R479 判据面 (承 R478 定因机制 + R474–R477 真值口径):
///   A. **工具声明面单一事实源**: 一份规格派生两种线格式, chat 形态与既有常量**逐字节相等** (禁漂移);
///   B. **真实输入格式**: instructions (本地指示/权限) 与 input[] (用户输入) 是**独立字段**,
///      工具结果回灌是**独立 typed item**, 协议恒为 store:false;
///   C. **精准语义校准**: 上游返回 → 本地动作, 判据**只取协议字段**; 本地 LLM 与远端 LLM 同一函数;
///   D. **fail-closed 与真值口径**: 未知/不可解析 ⇒ 不可用 (禁猜); usage 未上报 ≠ 0。
/// </summary>
public class ResponsesWireTests
{
    // ---------- A. 声明面单一事实源 ----------

    [Fact]
    public void A1_Chat形态与既有常量逐字节相等()
        => Assert.Equal(ActionToolDecl.ToolsJson, ActionToolSpec.ChatToolsJson);

    [Fact]
    public void A2_Responses形态为平铺且含全部工具()
    {
        var json = ActionToolSpec.ResponsesToolsJson;
        foreach (var n in ActionToolDecl.Names)
            Assert.Contains("\"type\":\"function\",\"name\":\"" + n + "\"", json, System.StringComparison.Ordinal);
        Assert.DoesNotContain("\"function\":{\"name\"", json, System.StringComparison.Ordinal);
        Assert.DoesNotContain("\n[", json, System.StringComparison.Ordinal);
        // 参数 schema 与声明面同源 (逐字节包含)
        foreach (var t in ActionToolSpec.All)
            Assert.Contains(t.ParametersJson, json, System.StringComparison.Ordinal);
    }

    // ---------- B. 真实输入格式 ----------

    [Fact]
    public void B1_instructions与input是独立字段且用户输入为typed_item()
    {
        var body = ResponsesWire.BuildRequest(
            "m1",
            "[SLOT:perm] fs=r,w; shell=none",
            new[] { ResponsesInputItem.SystemText("基线"), ResponsesInputItem.UserText("把构建命令写成一行。") },
            ActionToolSpec.ResponsesToolsJson,
            maxOutputTokens: 256,
            promptCacheKey: "sess-1");

        Assert.Contains(ResponsesWire.StoreFalse, body, System.StringComparison.Ordinal);
        Assert.Contains("\"max_output_tokens\":256", body, System.StringComparison.Ordinal);
        Assert.Contains("\"prompt_cache_key\":\"sess-1\"", body, System.StringComparison.Ordinal);
        Assert.Contains("{\"type\":\"message\",\"role\":\"user\",\"content\":[{\"type\":\"input_text\",\"text\":\"把构建命令写成一行。\"}]}", body, System.StringComparison.Ordinal);
        Assert.Contains("\"type\":\"input_text\"", body, System.StringComparison.Ordinal);

        using var doc = JsonDocument.Parse(body);
        var root = doc.RootElement;
        Assert.Equal("[SLOT:perm] fs=r,w; shell=none", root.GetProperty("instructions").GetString());
        Assert.Equal(2, root.GetProperty("input").GetArrayLength());
        Assert.Equal("user", root.GetProperty("input")[1].GetProperty("role").GetString());
        Assert.Equal(4, root.GetProperty("tools").GetArrayLength());
        Assert.False(root.GetProperty("store").GetBoolean());
    }

    [Fact]
    public void B2_工具回灌是独立typed_item不混入user文本()
    {
        var body = ResponsesWire.BuildRequest("m1", "", new[]
        {
            ResponsesInputItem.UserText("读 a.txt"),
            ResponsesInputItem.FunctionCallOutput("call_9", "hello"),
        });
        using var doc = JsonDocument.Parse(body);
        var input = doc.RootElement.GetProperty("input");
        Assert.Equal("function_call_output", input[1].GetProperty("type").GetString());
        Assert.Equal("call_9", input[1].GetProperty("call_id").GetString());
        Assert.Equal("hello", input[1].GetProperty("output").GetString());
        Assert.False(doc.RootElement.TryGetProperty("instructions", out _)); // 空 instructions 不占位
    }

    [Fact]
    public void B3_转义往返_含引号换行反斜杠()
    {
        var raw = "he said \"hi\"\nline2\\x\u0001end";
        var body = ResponsesWire.BuildRequest("m", "[p]", new[] { ResponsesInputItem.UserText(raw) });
        using var doc = JsonDocument.Parse(body);
        Assert.Equal(raw, doc.RootElement.GetProperty("input")[0].GetProperty("content")[0].GetProperty("text").GetString());
    }

    // ---------- C. 精准语义校准 (上游返回 → 本地动作) ----------

    private const string CompletedText =
        "{\"id\":\"r1\",\"status\":\"completed\",\"output\":[{\"type\":\"message\",\"role\":\"assistant\",\"content\":[{\"type\":\"output_text\",\"text\":\"好\"}]}],\"usage\":{\"input_tokens\":38,\"input_tokens_details\":{\"cached_tokens\":37},\"output_tokens\":2}}";

    private const string CompletedToolCall =
        "{\"id\":\"r2\",\"status\":\"completed\",\"output\":[{\"type\":\"function_call\",\"name\":\"read_file\",\"arguments\":\"{\\\"path\\\":\\\"a.txt\\\"}\",\"call_id\":\"call_1\"}],\"usage\":{\"input_tokens\":40,\"input_tokens_details\":{\"cached_tokens\":30},\"output_tokens\":9}}";

    private const string IncompleteMaxOut =
        "{\"id\":\"r3\",\"status\":\"incomplete\",\"incomplete_details\":{\"reason\":\"max_output_tokens\"},\"output\":[{\"type\":\"reasoning\",\"summary\":[{\"type\":\"summary_text\",\"text\":\"想了很久\"}]}],\"usage\":{\"input_tokens\":40,\"input_tokens_details\":{\"cached_tokens\":0},\"output_tokens\":500,\"output_tokens_details\":{\"reasoning_tokens\":500}}}";

    [Fact]
    public void C1_完成且有正文_判Answer()
    {
        var d = LocalDecisionMap.FromResponses(ResponsesParser.Parse(CompletedText), actionLoopEnabled: true);
        Assert.Equal(LocalAction.Answer, d.Action);
        Assert.Equal("好", d.Text);
        Assert.Equal("answer", d.Reason);
    }

    [Fact]
    public void C2_有工具调用且环开启_判RunTools_字段逐项对齐()
    {
        var d = LocalDecisionMap.FromResponses(ResponsesParser.Parse(CompletedToolCall), actionLoopEnabled: true);
        Assert.Equal(LocalAction.RunTools, d.Action);
        Assert.NotNull(d.ToolCalls);
        Assert.Single(d.ToolCalls!);
        Assert.Equal("call_1", d.ToolCalls![0].Id);
        Assert.Equal("read_file", d.ToolCalls![0].Name);
        Assert.Equal("{\"path\":\"a.txt\"}", d.ToolCalls![0].ArgumentsJson);
    }

    [Fact]
    public void C3_有工具调用但环关闭_可见失败且禁重试_文案单源()
    {
        var r = ResponsesParser.Parse(CompletedToolCall);
        var d = LocalDecisionMap.FromResponses(r, actionLoopEnabled: false);
        Assert.Equal(LocalAction.VisibleFailure, d.Action);
        Assert.Equal(EmptyBodyCause.ToolCall, d.Cause);
        Assert.False(d.Retryable); // R478: tool_calls 重试必空
        Assert.Equal(EmptyBodyDiagnosis.Banner(EmptyBodyCause.ToolCall, "tool_calls"), d.Banner);
    }

    [Fact]
    public void C4_输出预算耗尽_判Retry_文案单源()
    {
        var d = LocalDecisionMap.FromResponses(ResponsesParser.Parse(IncompleteMaxOut), actionLoopEnabled: true);
        Assert.Equal(LocalAction.Retry, d.Action);
        Assert.Equal(EmptyBodyCause.LengthExhausted, d.Cause);
        Assert.True(d.Retryable);
        Assert.Equal(EmptyBodyDiagnosis.Banner(EmptyBodyCause.LengthExhausted, "length"), d.Banner);
    }

    [Theory]
    [InlineData("{\"id\":\"x\",\"status\":\"completed\",\"output\":[]}", LocalAction.VisibleFailure, EmptyBodyCause.UpstreamStop)]
    [InlineData("{\"id\":\"x\",\"status\":\"failed\",\"output\":[]}", LocalAction.VisibleFailure, EmptyBodyCause.Unknown)]
    [InlineData("{\"id\":\"x\",\"status\":\"incomplete\",\"incomplete_details\":{\"reason\":\"content_filter\"},\"output\":[]}", LocalAction.VisibleFailure, EmptyBodyCause.Unknown)]
    [InlineData("{\"id\":\"x\",\"status\":\"queued\",\"output\":[]}", LocalAction.VisibleFailure, EmptyBodyCause.Unknown)]
    public void C5_非完成态一律可见失败_禁猜(string json, LocalAction action, EmptyBodyCause cause)
    {
        var d = LocalDecisionMap.FromResponses(ResponsesParser.Parse(json), actionLoopEnabled: true);
        Assert.Equal(action, d.Action);
        Assert.Equal(cause, d.Cause);
        Assert.NotNull(d.Banner);
    }

    [Fact]
    public void C6_仅有推理无正文_不得判Answer()
    {
        var r = ResponsesParser.Parse(IncompleteMaxOut);
        var d = LocalDecisionMap.FromResponses(r, actionLoopEnabled: true);
        Assert.NotEqual(LocalAction.Answer, d.Action);
        Assert.Empty(d.Text); // 推理内容不得被当成正文
    }

    // ---------- D. fail-closed 与真值口径 ----------

    [Fact]
    public void D1_不可解析或无非可读面_判Fatal()
    {
        Assert.Equal(LocalAction.Fatal, LocalDecisionMap.FromResponses(ResponsesParser.Parse("{\"id\":\"x\""), true).Action);
        Assert.Equal(LocalAction.Fatal, LocalDecisionMap.FromResponses(ResponsesParser.Parse("[]"), true).Action);
        Assert.Equal(LocalAction.Fatal, LocalDecisionMap.FromResponses(ResponsesParser.Parse("{\"output\":[{\"type\":\"web_search_call\"}]}"), true).Action);
    }

    [Fact]
    public void D2_未知item类型被计数而非静默丢弃()
    {
        var r = ResponsesParser.Parse("{\"status\":\"completed\",\"output\":[{\"type\":\"web_search_call\"},{\"type\":\"message\",\"content\":[{\"type\":\"output_text\",\"text\":\"hi\"}]}]}");
        Assert.Equal(1, r.UnknownItems);
        Assert.Equal("hi", r.Text);
        Assert.Null(r.Failure);
        Assert.Equal(LocalAction.Answer, LocalDecisionMap.FromResponses(r, true).Action);
    }

    [Fact]
    public void D3_usage未上报不得当0()
    {
        var r = ResponsesParser.Parse("{\"status\":\"completed\",\"output\":[{\"type\":\"message\",\"content\":[{\"type\":\"output_text\",\"text\":\"hi\"}]}]}");
        Assert.False(r.Usage.Present);
        Assert.False(r.Usage.CachedPresent);
        Assert.Null(r.Usage.NewTokens);

        var r2 = ResponsesParser.Parse(CompletedText);
        Assert.True(r2.Usage.Present);
        Assert.True(r2.Usage.CachedPresent);
        Assert.Equal(38, r2.Usage.InputTokens);
        Assert.Equal(37, r2.Usage.CachedTokens);
        Assert.Equal(1, r2.Usage.NewTokens);

        var r3 = ResponsesParser.Parse("{\"status\":\"completed\",\"usage\":{\"input_tokens\":5,\"output_tokens\":1},\"output\":[{\"type\":\"message\",\"content\":[{\"type\":\"output_text\",\"text\":\"x\"}]}]}");
        Assert.True(r3.Usage.Present);
        Assert.False(r3.Usage.CachedPresent);
        Assert.Null(r3.Usage.NewTokens); // 缺 cached_tokens ⇒ 新算不可得 (禁冒充 input 全为新算)
    }

    [Fact]
    public void D4_推理token与输出项可见()
    {
        var r = ResponsesParser.Parse(IncompleteMaxOut);
        Assert.Equal(500, r.Usage.ReasoningTokens);
        Assert.Equal(500, r.Usage.OutputTokens);
        Assert.Contains("想了很久", r.ReasoningText, System.StringComparison.Ordinal);
        Assert.Empty(r.Text);
    }

    [Fact]
    public void D5_传输失败不与上游判据混算()
    {
        var d = LocalDecisionMap.FromTransportFailure("http_503");
        Assert.Equal(LocalAction.Fatal, d.Action);
        Assert.Equal("transport_failure", d.Reason);
        Assert.Equal(EmptyBodyDiagnosis.Banner(EmptyBodyCause.Unknown, "http_503"), d.Banner);
    }

    // ---------- F. 真机返回体离线判档 (R479 E2E 证据回放) ----------

    [Fact]
    public void F1_真机返回体经产品语义面判档()
    {
        var dir = System.Environment.GetEnvironmentVariable("R479_E2E_DIR");
        if (string.IsNullOrEmpty(dir) || !System.IO.Directory.Exists(dir)) return; // 无真机证据则不判 (禁伪造)

        var seen = 0;
        foreach (var f in System.IO.Directory.GetFiles(dir, "e2e_*.raw.json"))
        {
            var r = ResponsesParser.Parse(System.IO.File.ReadAllText(f));
            Assert.Null(r.Failure);                       // 真机返回必须可解析
            Assert.True(r.Usage.Present);                 // 供应商 usage 必须在
            var d = LocalDecisionMap.FromResponses(r, actionLoopEnabled: true);
            Assert.NotEqual(LocalAction.Fatal, d.Action); // 真机可用返回不得被判不可用
            if (r.Status == "incomplete" && r.IncompleteReason == "max_output_tokens")
                Assert.Equal(LocalAction.Retry, d.Action); // 远端真机: reasoning 吃满预算 ⇒ 判 Retry
            seen++;
        }

        var toolBody = System.IO.Path.Combine(dir, "e2e_local_tool_1.raw.json");
        if (System.IO.File.Exists(toolBody))
        {
            var rt = ResponsesParser.Parse(System.IO.File.ReadAllText(toolBody));
            var dt = LocalDecisionMap.FromResponses(rt, actionLoopEnabled: true);
            Assert.Equal(LocalAction.RunTools, dt.Action); // 本地 LLM 真机发出的工具调用 ⇒ 动作环入口
            Assert.Contains(dt.ToolCalls!, c => c.Name == "read_file");
        }

        Assert.True(seen > 0, "E2E 证据目录里没有任何 e2e_*.raw.json");
    }

    // ---------- E. 产品自建请求体导出 (真机 E2E 用: 发出去的就是产品字节) ----------

    [Fact]
    public void E1_导出产品自建请求体()
    {
        var dir = System.Environment.GetEnvironmentVariable("R479_REQUEST_DUMP");
        var answer = ResponsesWire.BuildRequest(
            "local-model",
            "[SLOT:perm] fs=read; net=none\n[SLOT:cap] list_dir,read_file",
            new[]
            {
                ResponsesInputItem.SystemText("[基线] 中文回答, 简洁。"),
                ResponsesInputItem.UserText("用一句话说明: 前缀缓存为什么能省 token。"),
            },
            maxOutputTokens: 128,
            promptCacheKey: "r479-answer");

        var tool = ResponsesWire.BuildRequest(
            "local-model",
            "[SLOT:perm] fs=read; shell=none\n[SLOT:cap] read_file",
            new[] { ResponsesInputItem.UserText("读一下 README.md 的第一行。") },
            ActionToolSpec.ResponsesToolsJson,
            maxOutputTokens: 128,
            promptCacheKey: "r479-tool");

        foreach (var body in new[] { answer, tool })
        {
            using var doc = JsonDocument.Parse(body); // 产品自建体必须自洽
            Assert.Equal(JsonValueKind.Object, doc.RootElement.ValueKind);
        }

        if (string.IsNullOrEmpty(dir)) return; // 未设导出目录 ⇒ 只做自洽断言
        System.IO.Directory.CreateDirectory(dir);
        System.IO.File.WriteAllText(System.IO.Path.Combine(dir, "request_answer.json"), answer, new System.Text.UTF8Encoding(false));
        System.IO.File.WriteAllText(System.IO.Path.Combine(dir, "request_tool.json"), tool, new System.Text.UTF8Encoding(false));
    }
}
