using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using agent.action;
using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R456 动作环 (Action Loop) 单测 —— 声明面/解析面/执行面/回灌面 四段各有断言。
/// 设计铁律: 关闸时请求体必须与旧版逐字节相同 (缓存前缀零回归); 越界路径必须拒绝; 回灌消息必须追加在尾部。
/// </summary>
public sealed class ActionLoopTests
{
    // ---------- 面 1: 声明面 ----------
    [Fact]
    public void Decls_AreValidJson_AndDeclaredFourTools()
    {
        using var doc = JsonDocument.Parse(ActionToolDecl.ToolsJson);
        Assert.Equal(JsonValueKind.Array, doc.RootElement.ValueKind);
        var names = new List<string>();
        foreach (var t in doc.RootElement.EnumerateArray())
        {
            Assert.Equal("function", t.GetProperty("type").GetString());
            var fn = t.GetProperty("function");
            Assert.False(string.IsNullOrWhiteSpace(fn.GetProperty("name").GetString()));
            Assert.Equal("object", fn.GetProperty("parameters").GetProperty("type").GetString());
            names.Add(fn.GetProperty("name").GetString()!);
        }
        Assert.Equal(4, names.Count);
        foreach (var n in names) Assert.True(ActionToolDecl.IsDeclared(n), n);
        Assert.False(ActionToolDecl.IsDeclared("rm_rf_everything"));
    }

    // ---------- 面 2: 解析面 (source-gen DTO, 零反射) ----------
    [Fact]
    public void Parse_ToolCallsFromResponseBody_IsAotSafe()
    {
        const string body = """
        {"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","content":null,
        "tool_calls":[{"id":"call_1","type":"function","function":{"name":"run_command","arguments":"{\"command\":\"ls\"}"}}]}}],
        "usage":{"prompt_tokens":10,"total_tokens":12}}
        """;
        var parsed = JsonSerializer.Deserialize(body, ModelQueueJsonContext.Default.OpenAIChatResponse);
        var msg = parsed!.Choices![0].Message!;
        Assert.Equal("tool_calls", parsed.Choices![0].FinishReason);
        Assert.Single(msg.ToolCalls!);
        Assert.Equal("run_command", msg.ToolCalls![0].Function!.Name);
        Assert.Contains("ls", msg.ToolCalls![0].Function!.Arguments);
    }

    // ---------- 面 3: 关闸零回归 ----------
    [Fact]
    public void Serialize_WithoutTools_StaysByteIdentical()
    {
        var req = new QueueChatRequest
        {
            Model = "deepseek-flash",
            Messages = new List<QueueChatMessage>
            {
                new() { Role = "system", Content = "s" },
                new() { Role = "user", Content = "u" },
            },
        };
        Assert.Equal(JsonSerializer.Serialize(req, ModelQueueJsonContext.Default.QueueChatRequest), ModelQueueRouter.SerializeChatRequest(req));
    }

    // ---------- 面 3b: 回灌序列化形态 (tools + tool_calls + tool_call_id + 顺序) ----------
    [Fact]
    public void Serialize_WithToolsAndToolMessages_WritesProtocolFields()
    {
        var req = new QueueChatRequest
        {
            Model = "deepseek-flash",
            ToolsJson = ActionToolDecl.ToolsJson,
            Messages = new List<QueueChatMessage>
            {
                new() { Role = "system", Content = "s" },
                new() { Role = "user", Content = "u" },
                new()
                {
                    Role = "assistant",
                    Content = string.Empty,
                    ToolCalls = new List<ActionToolCall> { new() { Id = "call_1", Name = "list_dir", ArgumentsJson = "{\"path\":\".\"}" } },
                },
                new() { Role = "tool", Content = "f a.txt 3", ToolCallId = "call_1" },
            },
        };
        var body = ModelQueueRouter.SerializeChatRequest(req);
        using var doc = JsonDocument.Parse(body);
        Assert.True(doc.RootElement.TryGetProperty("tools", out var tools));
        Assert.Equal(4, tools.GetArrayLength());
        var msgs = doc.RootElement.GetProperty("messages");
        Assert.Equal(4, msgs.GetArrayLength());
        Assert.Equal("assistant", msgs[2].GetProperty("role").GetString());
        Assert.Equal("call_1", msgs[2].GetProperty("tool_calls")[0].GetProperty("id").GetString());
        Assert.Equal("list_dir", msgs[2].GetProperty("tool_calls")[0].GetProperty("function").GetProperty("name").GetString());
        Assert.Equal("tool", msgs[3].GetProperty("role").GetString());
        Assert.Equal("call_1", msgs[3].GetProperty("tool_call_id").GetString());
    }

    // ---------- 面 4: 回灌顺序 + 循环收敛 ----------
    [Fact]
    public async Task Loop_ExecutesToolCallsThenConverges()
    {
        var root = NewTempDir();
        try
        {
            var port = new WorkspaceActionPort(root);
            var seen = new List<QueuePrompt>();
            var step = 0;
            Task<QueueResponse> Call(QueuePrompt p, CancellationToken ct)
            {
                seen.Add(Clone(p));
                step++;
                if (step == 1)
                    return Task.FromResult(new QueueResponse
                    {
                        Success = true,
                        Content = string.Empty,
                        ToolCalls = new List<ActionToolCall>
                        {
                            new() { Id = "c1", Name = "write_file", ArgumentsJson = "{\"path\":\"count.txt\",\"content\":\"4\\n\"}" },
                        },
                    });
                return Task.FromResult(new QueueResponse { Success = true, Content = "已完成" });
            }

            var prompt = new QueuePrompt { SystemPrompt = "s", ContextPrompt = "c", UserMessage = "u" };
            var (resp, outcome) = await ActionLoopRunner.RunAsync(prompt, Call, port, 6, CancellationToken.None);

            Assert.Equal("已完成", resp.Content);
            Assert.Equal(1, outcome.Steps);
            Assert.Equal(1, outcome.Executed);
            Assert.True(outcome.Converged);
            Assert.False(outcome.MaxStepsHit);
            Assert.Equal("4\n", File.ReadAllText(Path.Combine(root, "count.txt")));
            // 回灌: 第一次调用无 PostUser; 第二次调用尾部追加 assistant(tool_calls)+tool 各 1
            Assert.Empty(seen[0].PostUser);
            Assert.Equal(2, seen[1].PostUser.Count);
            Assert.Equal("assistant", seen[1].PostUser[0].Role);
            Assert.Equal("tool", seen[1].PostUser[1].Role);
            Assert.Equal("c1", seen[1].PostUser[1].ToolCallId);
            // 前缀守恒: 第二次请求的 system/context/user 逐字节不变 (缓存前缀单调增长)
            Assert.Equal(seen[0].SystemPrompt, seen[1].SystemPrompt);
            Assert.Equal(seen[0].UserMessage, seen[1].UserMessage);
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public async Task Loop_StopsAtMaxSteps_WhenModelKeepsCallingTools()
    {
        var root = NewTempDir();
        try
        {
            var port = new WorkspaceActionPort(root);
            var calls = 0;
            Task<QueueResponse> Call(QueuePrompt p, CancellationToken ct)
            {
                calls++;
                return Task.FromResult(new QueueResponse
                {
                    Success = true,
                    Content = string.Empty,
                    ToolCalls = new List<ActionToolCall> { new() { Id = "c" + calls, Name = "list_dir", ArgumentsJson = "{}" } },
                });
            }
            var (_, outcome) = await ActionLoopRunner.RunAsync(new QueuePrompt { UserMessage = "u" }, Call, port, 3, CancellationToken.None);
            Assert.Equal(3, outcome.Steps);
            Assert.True(outcome.MaxStepsHit);
            Assert.False(outcome.Converged);
            Assert.Equal(4, calls); // 1 首调 + 3 步
        }
        finally { Directory.Delete(root, true); }
    }

    // ---------- 面 5: 执行面边界 ----------
    [Fact]
    public async Task Port_FileRoundTrip_AndPathEscapeRejected()
    {
        var root = NewTempDir();
        try
        {
            var port = new WorkspaceActionPort(root);
            var w = await port.ExecuteAsync(new ActionToolCall { Name = "write_file", ArgumentsJson = "{\"path\":\"sub/a.txt\",\"content\":\"hello\"}" }, CancellationToken.None);
            Assert.True(w.Ok, w.Output);
            var r = await port.ExecuteAsync(new ActionToolCall { Name = "read_file", ArgumentsJson = "{\"path\":\"sub/a.txt\"}" }, CancellationToken.None);
            Assert.True(r.Ok);
            Assert.Equal("hello", r.Output);
            var l = await port.ExecuteAsync(new ActionToolCall { Name = "list_dir", ArgumentsJson = "{\"path\":\"sub\"}" }, CancellationToken.None);
            Assert.True(l.Ok);
            Assert.Contains("a.txt", l.Output);
            var esc = await port.ExecuteAsync(new ActionToolCall { Name = "read_file", ArgumentsJson = "{\"path\":\"../../etc/passwd\"}" }, CancellationToken.None);
            Assert.False(esc.Ok);
            Assert.Contains("越界", esc.Output);
            var esc2 = await port.ExecuteAsync(new ActionToolCall { Name = "write_file", ArgumentsJson = "{\"path\":\"/tmp/r456_escape.txt\",\"content\":\"x\"}" }, CancellationToken.None);
            Assert.False(esc2.Ok);
            Assert.False(File.Exists("/tmp/r456_escape.txt"));
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public async Task Port_RunCommand_CapturesExitCodeAndOutput()
    {
        var root = NewTempDir();
        try
        {
            var port = new WorkspaceActionPort(root);
            var ok = await port.ExecuteAsync(new ActionToolCall { Name = "run_command", ArgumentsJson = "{\"command\":\"echo hi\"}" }, CancellationToken.None);
            Assert.True(ok.Ok, ok.Output);
            Assert.Contains("hi", ok.Output);
            var bad = await port.ExecuteAsync(new ActionToolCall { Name = "run_command", ArgumentsJson = "{\"command\":\"exit 3\"}" }, CancellationToken.None);
            Assert.False(bad.Ok);
            Assert.Equal(3, bad.ExitCode);
            // cwd 必须是工作区根
            var pwd = await port.ExecuteAsync(new ActionToolCall { Name = "run_command", ArgumentsJson = "{\"command\":\"pwd\"}" }, CancellationToken.None);
            Assert.Contains(Path.GetFileName(root), pwd.Output);
        }
        finally { Directory.Delete(root, true); }
    }

    // ---------- 面 6: 开关语义 ----------
    [Fact]
    public void Gate_OffMeansDisabled_UnsetMeansEnabled()
    {
        var old = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP", "off");
            Assert.False(ActionLoopRunner.IsEnabled());
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP", "on");
            Assert.True(ActionLoopRunner.IsEnabled());
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP", null);
            Assert.True(ActionLoopRunner.IsEnabled());
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP", "0");
            Assert.False(ActionLoopRunner.IsEnabled());
        }
        finally { Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP", old); }
    }

    private static string NewTempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "r456_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(d);
        return d;
    }

    private static QueuePrompt Clone(QueuePrompt p) => new()
    {
        SystemPrompt = p.SystemPrompt,
        ContextPrompt = p.ContextPrompt,
        UserMessage = p.UserMessage,
        ToolsJson = p.ToolsJson,
        PostUser = new List<QueuePostUserMessage>(p.PostUser),
    };
}
