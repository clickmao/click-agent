using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.core;
using agent.userinteraction;
using agent.frontendapi;
using agent.modelqueue;
namespace agent.tests;

/// <summary>
/// R510: (1) 动作环步进上报面 (task.progress 的**真数据源**) —— 断言穿过**真** ActionLoopRunner,
///          不是"直接给 registry.Progress 喂值"的自证;
///       (2) 审批域最小闭环 (approval.requested/responded + approval.respond 回程), fail-closed 语义。
/// 负控: 未绑定观察者 ⇒ 零上报; 出站面抛错 ⇒ 不中断主链但计数; 未知/重复 approval_id 显式拒绝。
/// </summary>
public class R510StepProgressAndApprovalTests
{
    private sealed class StubPort : IActionPort
    {
        public string Name => "stub";
        public int Executions;
        public Task<ActionExecutionResult> ExecuteAsync(ActionToolCall call, CancellationToken ct)
        {
            Interlocked.Increment(ref Executions);
            return Task.FromResult(new ActionExecutionResult { Ok = true, Output = "ok", ExitCode = 0, ElapsedMs = 7 });
        }
    }

    private sealed class StepAgent : IAgent
    {
        private readonly Func<Task<AgentResponse>> _resp;
        public StepAgent(Func<Task<AgentResponse>> resp) => _resp = resp;
        public string Id => "stub";
        public string Name => "stub";
        public AgentState State => default;
        public event EventHandler<AgentStateChangedEventArgs>? StateChanged { add { } remove { } }
        public event EventHandler<Message>? MessageReceived { add { } remove { } }
        public Task InitializeAsync(IAgentContext context, CancellationToken ct = default) => Task.CompletedTask;
        public Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default) => _resp();
        public Task<AgentResponse> ExecuteTaskAsync(agent.subagent.SubAgentTask task, CancellationToken ct = default) => _resp();
        public Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default) => _resp();
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
        return (r.GetProperty("event").GetString()!, r.GetProperty("payload").GetRawText());
    }

    /// <summary>取**最后一条** approval.requested 的 id (被覆盖的旧请求会留在事件流里, 取第一条会取错)。</summary>
    private static async Task<string> WaitForApprovalId(List<string> lines, int timeoutMs = 3000)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        while (sw.ElapsedMilliseconds < timeoutMs)
        {
            string? found = null;
            lock (lines)
            {
                foreach (var l in lines)
                {
                    var (evt, payload) = Split(l);
                    using var p = JsonDocument.Parse(payload);
                    if (evt == ApprovalEnvelope.EventRequested && p.RootElement.TryGetProperty("approval_id", out var id))
                        found = id.GetString();
                }
            }
            if (found is not null) return found;
            await Task.Delay(10);
        }
        throw new TimeoutException("approval.requested 未在超时内出现");
    }

    // ---------- (1) 步进上报面 ----------

    [Fact]
    public void Observer_Unbound_ReportsNothing()
    {
        Assert.False(ActionProgressObserver.Bound);
        var before = ActionProgressObserver.Reported;
        ActionProgressObserver.ReportAsync(new ActionStepProgress(1, "write_file", true, 1)).GetAwaiter().GetResult();
        Assert.Equal(before, ActionProgressObserver.Reported); // 未绑定 ⇒ 不计数不投递 (零开销负控)
    }

    [Fact]
    public async Task Observer_SinkThrows_IsCounted_AndDoesNotPropagate()
    {
        var before = ActionProgressObserver.Failed;
        using (ActionProgressObserver.Bind(_ => throw new InvalidOperationException("sink-boom")))
        {
            Assert.True(ActionProgressObserver.Bound);
            await ActionProgressObserver.ReportAsync(new ActionStepProgress(1, "run_command", false, 9));
        }
        Assert.Equal(before + 1, ActionProgressObserver.Failed);   // 不静默
        Assert.False(ActionProgressObserver.Bound);                 // Dispose 后解绑
        Assert.Contains("sink-boom", ActionProgressObserver.LastError ?? "");
    }

    [Fact]
    public async Task ChatSend_ThroughRealActionLoop_EmitsTaskProgressPerStep()
    {
        var (reg, hub, lines) = Wire();
        var port = new StubPort();
        var calls = 0;
        Task<QueueResponse> Call(QueuePrompt p, CancellationToken ct)
        {
            calls++;
            if (calls == 1)
                return Task.FromResult(new QueueResponse
                {
                    Success = true,
                    Content = string.Empty,
                    FinishReason = "tool_calls",
                    ToolCalls = new List<ActionToolCall>
                    {
                        new() { Id = "c1", Name = "write_file", ArgumentsJson = "{\"path\":\"a.txt\",\"content\":\"hi\"}" },
                    },
                });
            return Task.FromResult(new QueueResponse { Success = true, Content = "done" });
        }
        var agent = new StepAgent(async () =>
        {
            var (resp, _) = await ActionLoopRunner.RunAsync(
                new QueuePrompt { UserMessage = "u" }, Call, port, 4, CancellationToken.None);
            return new AgentResponse { Content = resp.Content, Success = resp.Success };
        });
        var router = new FrontendApiChatRouter(agent, sessionId: "s1", askSink: null, tasks: reg, hub: hub);
        var payload = await router.HandleAsync("chat.send", "{\"text\":\"do it\"}");

        Assert.Equal(1, port.Executions);      // 真执行了工具 (不是空转)
        Assert.NotNull(payload);
        string[] names;
        string progressPayload;
        lock (lines)
        {
            names = new string[lines.Count];
            for (var i = 0; i < lines.Count; i++) names[i] = Split(lines[i]).Event;
            Assert.Equal(3, lines.Count);      // started → progress → completed 单调
            Assert.Equal("task.started", names[0]);
            Assert.Equal("task.progress", names[1]);
            Assert.Equal("task.completed", names[2]);
            progressPayload = Split(lines[1]).Payload;
        }
        using (var d = JsonDocument.Parse(progressPayload))
        {
            var r = d.RootElement;
            Assert.Equal(1, r.GetProperty("step_index").GetInt32());
            Assert.Equal("write_file", r.GetProperty("tool").GetString());  // 事实来自动作环记录
            Assert.True(r.GetProperty("ok").GetBoolean());
            Assert.Equal(7, r.GetProperty("elapsed_ms").GetInt64());        // 执行面耗时原样透传
        }
        // 快照面同步: 步号/动作已登记 (断线重连可读)
        using (var snap = JsonDocument.Parse(reg.SnapshotJson()))
        {
            Assert.Equal(1, snap.RootElement[0].GetProperty("step_index").GetInt32());
            Assert.Equal("write_file", snap.RootElement[0].GetProperty("current_action").GetString());
        }
    }

    [Fact]
    public async Task ChatSend_WithoutTaskWiring_DoesNotBindObserver()
    {
        var agent = new StepAgent(async () =>
        {
            var (resp, _) = await ActionLoopRunner.RunAsync(
                new QueuePrompt { UserMessage = "u" },
                (p, ct) => Task.FromResult(new QueueResponse { Success = true, Content = "plain" }),
                new StubPort(), 3, CancellationToken.None);
            return new AgentResponse { Content = resp.Content, Success = resp.Success };
        });
        var router = new FrontendApiChatRouter(agent, sessionId: "s1");   // 未接线: 无 registry/hub
        var payload = await router.HandleAsync("chat.send", "{\"text\":\"hi\"}");
        Assert.False(ActionProgressObserver.Bound);
        using var d = JsonDocument.Parse(payload!);
        Assert.False(d.RootElement.TryGetProperty("task_id", out _));
    }

    // ---------- (2) 审批域最小闭环 ----------

    private static FrontendPromptService PromptService(List<string> lines, int timeoutSeconds = 5) =>
        new(l => { lock (lines) lines.Add(l); return Task.CompletedTask; }, timeoutSeconds);

    private static SensitiveOperationRequest DeleteRequest() => new()
    {
        Kind = SensitiveOperationKind.DeleteFile,
        Summary = "删除文件: /ws/a.txt",
        Details = "将永久删除文件 /ws/a.txt (不可恢复)",
        Initiator = "Workspace",
    };

    [Fact]
    public async Task Approval_ApprovedByFrontend_ReturnsRealUser()
    {
        var lines = new List<string>();
        var prompts = PromptService(lines);
        var task = prompts.RequestOperationApprovalAsync(DeleteRequest());
        var id = await WaitForApprovalId(lines);

        string requestedPayload;
        lock (lines) requestedPayload = Split(lines[0]).Payload;
        using (var d = JsonDocument.Parse(requestedPayload))
        {
            var r = d.RootElement;
            Assert.Equal("DeleteFile", r.GetProperty("kind").GetString());
            Assert.Equal("删除文件: /ws/a.txt", r.GetProperty("summary").GetString());
            Assert.Equal("Workspace", r.GetProperty("initiator").GetString());
            Assert.Equal(5, r.GetProperty("timeout_s").GetInt32());
            Assert.StartsWith("apr-", r.GetProperty("approval_id").GetString());
        }

        Assert.Equal(ApprovalReplyOutcome.Applied, prompts.CompleteApproval(id, true, "同意"));
        var result = await task;
        Assert.True(result.Approved);
        Assert.Equal(PromptAnswerSource.RealUser, result.AnsweredBy);
        Assert.Equal("同意", result.Reason);

        lock (lines)
        {
            Assert.Equal(2, lines.Count);
            Assert.Equal("approval.requested", Split(lines[0]).Event);
            var responded = Split(lines[1]);
            Assert.Equal("approval.responded", responded.Event);
            using var d = JsonDocument.Parse(responded.Payload);
            Assert.Equal(id, d.RootElement.GetProperty("approval_id").GetString());
            Assert.True(d.RootElement.GetProperty("approved").GetBoolean());
            Assert.Equal("RealUser", d.RootElement.GetProperty("answered_by").GetString());
        }
    }

    [Fact]
    public async Task Approval_Denied_FailClosed_And_IdempotentUnknownId()
    {
        var lines = new List<string>();
        var prompts = PromptService(lines);
        var task = prompts.RequestOperationApprovalAsync(DeleteRequest());
        var id = await WaitForApprovalId(lines);

        Assert.Equal(ApprovalReplyOutcome.UnknownApproval, prompts.CompleteApproval("apr-nope", true, null));
        Assert.Equal(ApprovalReplyOutcome.Applied, prompts.CompleteApproval(id, false, "不同意"));
        var result = await task;
        Assert.False(result.Approved);                                  // 拒绝 ⇒ 绝不批准
        Assert.Equal(PromptAnswerSource.Denied, result.AnsweredBy);
        Assert.Equal(ApprovalReplyOutcome.AlreadyAnswered, prompts.CompleteApproval(id, true, "反悔")); // 幂等
        Assert.False(result.Approved);
    }

    [Fact]
    public async Task Approval_Timeout_NotApproved_AndRespondedEmitted()
    {
        var lines = new List<string>();
        var prompts = PromptService(lines, timeoutSeconds: 1);
        var result = await prompts.RequestOperationApprovalAsync(DeleteRequest());
        Assert.False(result.Approved);
        Assert.Equal(PromptAnswerSource.Timeout, result.AnsweredBy);
        lock (lines)
        {
            Assert.Equal("approval.requested", Split(lines[0]).Event);
            var responded = Split(lines[1]);
            Assert.Equal("approval.responded", responded.Event);
            using var d = JsonDocument.Parse(responded.Payload);
            Assert.False(d.RootElement.GetProperty("approved").GetBoolean());
            Assert.Equal("Timeout", d.RootElement.GetProperty("answered_by").GetString());
        }
    }

    [Fact]
    public async Task Approval_Superseded_FirstNotApproved_SecondAnswerable()
    {
        var lines = new List<string>();
        var prompts = PromptService(lines);
        var first = prompts.RequestOperationApprovalAsync(DeleteRequest());
        var id1 = await WaitForApprovalId(lines);
        var second = prompts.RequestOperationApprovalAsync(DeleteRequest());
        var r1 = await first;                                           // 被覆盖 ⇒ 诚实放弃
        Assert.False(r1.Approved);
        Assert.Equal("superseded_by_new_approval", r1.Reason);
        var id2 = await WaitForApprovalId(lines);
        Assert.NotEqual(id1, id2);
        // 被覆盖的旧请求也必须有 responded 收口 (前端不会停在等待态)
        var sawSuperseded = false;
        lock (lines)
        {
            foreach (var l in lines)
            {
                var (evt, payload) = Split(l);
                if (evt != ApprovalEnvelope.EventResponded) continue;
                using var d = JsonDocument.Parse(payload);
                if (d.RootElement.GetProperty("approval_id").GetString() == id1
                    && !d.RootElement.GetProperty("approved").GetBoolean()) sawSuperseded = true;
            }
        }
        Assert.True(sawSuperseded, "被覆盖的审批缺少 responded 收口事件");
        Assert.Equal(ApprovalReplyOutcome.Applied, prompts.CompleteApproval(id2, true, null));
        Assert.True((await second).Approved);
    }

    [Fact]
    public async Task Router_ApprovalRespond_AppliesAndReportsOutcome()
    {
        var lines = new List<string>();
        var prompts = PromptService(lines);
        var hub = new FrontendEventHub();
        hub.AttachServer(l => { lock (lines) lines.Add(l); return Task.CompletedTask; });
        hub.AttachApproval(prompts);
        var router = new FrontendApiChatRouter(new StepAgent(() =>
            Task.FromResult(new AgentResponse { Content = "ok", Success = true })),
            sessionId: "s1", tasks: null, hub: hub, approvalSink: hub.ApprovalSink);

        var task = prompts.RequestOperationApprovalAsync(DeleteRequest());
        var id = await WaitForApprovalId(lines);
        var payload = await router.HandleAsync("approval.respond",
            "{\"approval_id\":\"" + id + "\",\"approved\":true,\"reason\":\"ok\"}");
        using (var d = JsonDocument.Parse(payload!))
        {
            Assert.Equal(id, d.RootElement.GetProperty("approval_id").GetString());
            Assert.Equal("approved", d.RootElement.GetProperty("outcome").GetString());
        }
        Assert.True((await task).Approved);

        // 负控: 未知 id 显式拒绝 (不静默当批准); 非法载荷 = bad_payload
        var unknown = await router.HandleAsync("approval.respond", "{\"approval_id\":\"apr-zzzzzzzz\",\"approved\":true}");
        using (var d = JsonDocument.Parse(unknown!))
            Assert.Equal("unknown_approval", d.RootElement.GetProperty("outcome").GetString());
        await Assert.ThrowsAsync<FrontendApiChatRouter.BadPayloadException>(() =>
            router.HandleAsync("approval.respond", "{\"approval_id\":\"apr-1\"}"));
    }

    [Fact]
    public async Task Router_ApprovalRespond_WithoutSink_ReportsChannelUnavailable()
    {
        var router = new FrontendApiChatRouter(new StepAgent(() =>
            Task.FromResult(new AgentResponse { Content = "ok", Success = true })), sessionId: "s1");
        var payload = await router.HandleAsync("approval.respond", "{\"approval_id\":\"apr-1\",\"approved\":true}");
        using var d = JsonDocument.Parse(payload!);
        Assert.Equal("channel_unavailable", d.RootElement.GetProperty("outcome").GetString()); // 不伪造批准
    }
}
