using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.core;
using agent.frontendapi;
namespace agent.tests;

/// <summary>
/// R509 (对标 codex 展示面, 路线 A): 任务生命周期事件域 — task.started / task.completed
/// + state.snapshot.tasks。断言只吃**出站信封原文** (hub 为唯一出站口) 与登记状态,
/// 不读实现内部字段名之外的东西 (手写 JSON 契约即字段名契约)。
/// 负控: 未知 task_id 必须显式拒绝 (不静默接受); 幂等收口不得覆盖首次终态。
/// </summary>
public class FrontendTaskEventsTests
{
    private sealed class StubAgent : IAgent
    {
        private readonly Func<AgentResponse> _resp;
        public StubAgent(Func<AgentResponse>? resp = null) =>
            _resp = resp ?? (() => new AgentResponse { Content = "ok", Success = true });
        public string Id => "stub";
        public string Name => "stub";
        public AgentState State => default;
        public event EventHandler<AgentStateChangedEventArgs>? StateChanged { add { } remove { } }
        public event EventHandler<Message>? MessageReceived { add { } remove { } }
        public Task InitializeAsync(IAgentContext context, CancellationToken ct = default) => Task.CompletedTask;
        public Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default) => Task.FromResult(_resp());
        public Task<AgentResponse> ExecuteTaskAsync(agent.core.SubAgentTask task, CancellationToken ct = default) => Task.FromResult(_resp());
        public Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default) => Task.FromResult(_resp());
        public Task ShutdownAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private static (FrontendTaskRegistry Reg, FrontendEventHub Hub, List<string> Lines) Wire()
    {
        var reg = new FrontendTaskRegistry();
        var hub = new FrontendEventHub();
        var lines = new List<string>();
        hub.AttachServer(l => { lock (lines) lines.Add(l); return Task.CompletedTask; });
        return (reg, hub, lines);
    }

    private static (string Event, string Payload) Split(string line)
    {
        using var doc = JsonDocument.Parse(line);
        var r = doc.RootElement;
        Assert.Equal("event", r.GetProperty("type").GetString());
        Assert.Equal(1, r.GetProperty("v").GetInt32());
        return (r.GetProperty("event").GetString()!, r.GetProperty("payload").GetRawText());
    }

    [Fact]
    public void Registry_Lifecycle_EmitsContractFields_InOrder()
    {
        var (reg, hub, lines) = Wire();
        var id = reg.Start("frontend-main", "chat.send", startedAtMs: 1_700_000_000_000);
        Assert.True(reg.Progress(id, 2, "write_file", true, 120, "写文件 a.py"));
        Assert.True(reg.Complete(id, success: true, replyChars: 42, endedAtMs: 1_700_000_001_500));

        // 出站面: 事件名 + 载荷必为契约字段 (手写 JSON)
        var p0 = Split(FrontendApiContract.FormatEvent("task.started", reg.StartedJson(id)));
        Assert.Equal("task.started", p0.Event);
        using (var d = JsonDocument.Parse(p0.Payload))
        {
            Assert.Equal(id, d.RootElement.GetProperty("task_id").GetString());
            Assert.Equal("frontend-main", d.RootElement.GetProperty("session_id").GetString());
            Assert.Equal(1_700_000_000_000, d.RootElement.GetProperty("started_at_ms").GetInt64());
        }

        var p1 = Split(FrontendApiContract.FormatEvent("task.progress", reg.ProgressJson(id, "write_file", true, 120, "写文件 a.py")));
        Assert.Equal("task.progress", p1.Event);
        using (var d = JsonDocument.Parse(p1.Payload))
        {
            Assert.Equal(2, d.RootElement.GetProperty("step_index").GetInt32());
            Assert.Equal("write_file", d.RootElement.GetProperty("tool").GetString());
            Assert.True(d.RootElement.GetProperty("ok").GetBoolean());
            Assert.Equal("写文件 a.py", d.RootElement.GetProperty("current_action").GetString());
        }

        var p2 = Split(FrontendApiContract.FormatEvent("task.completed", reg.CompletedJson(id)));
        Assert.Equal("task.completed", p2.Event);
        using (var d = JsonDocument.Parse(p2.Payload))
        {
            Assert.True(d.RootElement.GetProperty("success").GetBoolean());
            Assert.Equal(1500, d.RootElement.GetProperty("elapsed_ms").GetInt64());
            Assert.Equal(42, d.RootElement.GetProperty("reply_chars").GetInt32());
            Assert.Equal(2, d.RootElement.GetProperty("steps").GetInt32());
        }

        // 快照面: state 与终态字段 (断线重连可读)
        using (var snap = JsonDocument.Parse(reg.SnapshotJson()))
        {
            var arr = snap.RootElement;
            Assert.Equal(1, arr.GetArrayLength());
            var t = arr[0];
            Assert.Equal("done", t.GetProperty("state").GetString());
            Assert.Equal(1_700_000_001_500, t.GetProperty("ended_at_ms").GetInt64());
            Assert.True(t.GetProperty("success").GetBoolean());
        }
        Assert.Equal(0, hub.Dropped);
    }

    [Fact]
    public void Registry_UnknownId_Rejected_And_CompleteIdempotent()
    {
        var reg = new FrontendTaskRegistry();
        Assert.False(reg.Progress("task-nope", 1, "t", true, 1));      // 负控: 不静默接受
        Assert.False(reg.Complete("task-nope", true, 1));
        var id = reg.Start("s", "chat.send", 1);
        Assert.True(reg.Complete(id, success: false, replyChars: 7, endedAtMs: 9));
        Assert.False(reg.Complete(id, success: true, replyChars: 999, endedAtMs: 99)); // 幂等: 不覆盖终态
        var t = reg.Get(id)!;
        Assert.False(t.Success);
        Assert.Equal(7, t.ReplyChars);
        Assert.False(reg.Progress(id, 5, "t", true, 1));               // 收口后不再推进
    }

    [Fact]
    public void Registry_KeepsLastN_And_SnapshotIncludesRunning()
    {
        var reg = new FrontendTaskRegistry();
        for (var i = 0; i < FrontendTaskRegistry.KeepLast + 8; i++) reg.Start("s", "chat.send", i);
        using (var snap = JsonDocument.Parse(reg.SnapshotJson()))
        {
            Assert.Equal(FrontendTaskRegistry.KeepLast, snap.RootElement.GetArrayLength());
            Assert.Equal("running", snap.RootElement[0].GetProperty("state").GetString());
            Assert.Equal(JsonValueKind.Null, snap.RootElement[0].GetProperty("success").ValueKind);
        }
        Assert.Null(reg.Get("task-0")); // 最早的被淘汰 (未知 = null, 不伪造成 done)
    }

    [Fact]
    public async Task ChatSend_EmitsStartedThenCompleted_AndResponseCarriesTaskId()
    {
        var (reg, hub, lines) = Wire();
        var router = new FrontendApiChatRouter(new StubAgent(), sessionId: "s1", askSink: null, tasks: reg, hub: hub);
        var payload = await router.HandleAsync("chat.send", "{\"text\":\"hi\"}");
        Assert.NotNull(payload);
        lock (lines)
        {
            Assert.Equal(2, lines.Count);
            Assert.Equal("task.started", Split(lines[0]).Event);
            Assert.Equal("task.completed", Split(lines[1]).Event);
            var id = JsonDocument.Parse(Split(lines[0]).Payload).RootElement.GetProperty("task_id").GetString();
            Assert.StartsWith("task-", id);
            using var resp = JsonDocument.Parse(payload!);
            Assert.Equal("ok", resp.RootElement.GetProperty("reply").GetString());
            Assert.True(resp.RootElement.GetProperty("success").GetBoolean());
            Assert.Equal(id, resp.RootElement.GetProperty("task_id").GetString()); // 增量字段
        }
    }

    [Fact]
    public async Task ChatSend_OnAgentThrow_StillEmitsCompleted_FailClosed()
    {
        var (reg, hub, lines) = Wire();
        var router = new FrontendApiChatRouter(new StubAgent(() => throw new InvalidOperationException("boom")),
            sessionId: "s1", askSink: null, tasks: reg, hub: hub);
        await Assert.ThrowsAsync<InvalidOperationException>(() => router.HandleAsync("chat.send", "{\"text\":\"hi\"}"));
        lock (lines)
        {
            Assert.Equal(2, lines.Count); // started 必须已被终态收口 (前端不会永远 running)
            Assert.Equal("task.started", Split(lines[0]).Event);
            var done = Split(lines[1]);
            Assert.Equal("task.failed", done.Event); // 异常路径 = 显式 failed, 不是静默 completed
            using var d = JsonDocument.Parse(done.Payload);
            Assert.False(d.RootElement.GetProperty("success").GetBoolean());
            using var snap = JsonDocument.Parse(reg.SnapshotJson());
            Assert.Equal("failed", snap.RootElement[0].GetProperty("state").GetString());
        }
    }

    [Fact]
    public async Task ChatSend_WithoutRegistry_IsUnchanged_LegacyShape()
    {
        var router = new FrontendApiChatRouter(new StubAgent(), sessionId: "s1");
        var payload = await router.HandleAsync("chat.send", "{\"text\":\"hi\"}");
        using var d = JsonDocument.Parse(payload!);
        Assert.Equal("ok", d.RootElement.GetProperty("reply").GetString());
        Assert.True(d.RootElement.GetProperty("success").GetBoolean());
        Assert.False(d.RootElement.TryGetProperty("task_id", out _)); // 未接线时不新增字段 (老前端形状)
    }

    [Fact]
    public async Task ChatSend_BadPayload_Throws_AndEmitsNothing()
    {
        var (reg, hub, lines) = Wire();
        var router = new FrontendApiChatRouter(new StubAgent(), sessionId: "s1", askSink: null, tasks: reg, hub: hub);
        await Assert.ThrowsAsync<FrontendApiChatRouter.BadPayloadException>(
            () => router.HandleAsync("chat.send", "{\"text\":\"  \"}"));
        lock (lines) Assert.Empty(lines); // 校验失败不得产生伪任务事件
    }
}
