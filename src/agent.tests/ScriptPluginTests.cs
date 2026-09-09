using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.skills;

namespace agentframework.tests;

/// <summary>
/// v0.17.2-b/c (R337): 脚本插件协议 — JSON Lines 事件流解析 / py_compile 验证门 /
/// 插件服务执行 (真实 python3 子进程: done 回填、error 权威、噪声容忍、超时挂起观测) /
/// 条件定时原语 (空闲执行/忙拒绝/验证拒绝)。协议权威: docs/plans/v0.17.2-activity-script-plan.md §2。
/// </summary>
public class ScriptPluginTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "af-sp-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }

    private static Func<string, string, int, int> Cfg(params (string Key, int Val)[] overrides)
    {
        var map = new Dictionary<string, int>();
        foreach (var (k, v) in overrides) map[k] = v;
        return (m, k, d) => map.TryGetValue(m + ":" + k, out var v) ? v : d;
    }

    // 演示脚本 (v0.17.2-b 协议实现): heartbeat + 产物 + done
    private const string PyOk = @"
import argparse, json, os, sys, time
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
def emit(o):
    o.setdefault('ts', time.time())
    sys.stdout.write(json.dumps(o, ensure_ascii=False) + '\n'); sys.stdout.flush()
ap = argparse.ArgumentParser()
ap.add_argument('--task-json', required=True)
ap.add_argument('--heartbeat-secs', type=int, default=30)
ap.add_argument('--output-dir')
a = ap.parse_args()
task = json.load(open(a.task_json, encoding='utf-8'))
emit({'type':'progress','progress_pct':0,'msg':'start'})
emit({'type':'heartbeat','progress_pct':50,'msg':'working'})
out_dir = task.get('outputDir') or os.path.dirname(a.task_json)
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, 'result.txt')
open(out, 'w', encoding='utf-8').write('goal=' + str(task.get('goal','')) + '\n')
emit({'type':'done','exit_code':0,'summary':'demo 完成','data':{'outputs':[out]}})
";

    private static async Task<string> WritePyAsync(string dir, string name, string body)
    {
        var path = Path.Combine(dir, name);
        await File.WriteAllTextAsync(path, body).ConfigureAwait(false);
        return path;
    }

    // ---------- 解析器 (协议状态机) ----------

    [Fact]
    public void Parser_DoneLine_TerminalWithSummaryAndOutputs()
    {
        var p = new ScriptEventStreamParser(nowMs: () => 1_000);
        p.FeedLine("{\"type\":\"done\",\"ts\":5000,\"summary\":\"全部完成\",\"exit_code\":0,\"data\":{\"outputs\":[\"/tmp/a.txt\",\"/tmp/b.txt\"]}}");
        Assert.True(p.TerminalReached);
        Assert.Equal(ScriptPluginEventType.Done, p.TerminalType);
        Assert.Equal("全部完成", p.TerminalEvent!.Summary);
        Assert.Equal(0, p.TerminalEvent.ExitCode);
        Assert.Equal(new[] { "/tmp/a.txt", "/tmp/b.txt" }, p.TerminalEvent.Outputs.ToArray());
        Assert.Equal(1, p.EventLines);
        Assert.Equal(5_000, p.LastEventUnixMs);
    }

    [Fact]
    public void Parser_ErrorLine_TerminalFailed()
    {
        var p = new ScriptEventStreamParser();
        p.FeedLine("{\"type\":\"error\",\"exit_code\":1,\"error\":\"boom\"}");
        Assert.True(p.TerminalReached);
        Assert.Equal(ScriptPluginEventType.Error, p.TerminalType);
        Assert.Equal("boom", p.TerminalEvent!.Error);
    }

    [Fact]
    public void Parser_NonJsonAndUnknownType_NoiseIgnored_ProgressCounted()
    {
        var p = new ScriptEventStreamParser();
        p.FeedLine("plain text 调试噪声");
        p.FeedLine("{bad json");
        p.FeedLine("{\"type\":\"weird\",\"msg\":\"x\"}");
        p.FeedLine("{\"type\":\"progress\",\"progress_pct\":10,\"msg\":\"go\"}");
        Assert.Equal(3, p.NoiseLines);
        Assert.Equal(1, p.EventLines);
        Assert.Equal(1, p.ProgressCount);
        Assert.False(p.TerminalReached);
    }

    [Fact]
    public void Parser_HangStaleness_ResetsOnEvent()
    {
        var now = 1_000L;
        var p = new ScriptEventStreamParser(nowMs: () => now);
        p.FeedLine("{\"type\":\"heartbeat\",\"ts\":2000,\"msg\":\"tick\"}");
        now = 7_000; // 距最后事件 5000ms
        Assert.True(p.IsSuspectedHang(now, hangAfterMs: 4_000));
        p.FeedLine("{\"type\":\"progress\",\"ts\":7000,\"msg\":\"alive\"}"); // 活性刷新
        now = 9_000; // 2000ms
        Assert.False(p.IsSuspectedHang(now, hangAfterMs: 4_000));
        Assert.True(p.TerminalReached is false);
    }

    [Fact]
    public void Parser_TsSeconds_ToleratedToMilliseconds()
    {
        var p = new ScriptEventStreamParser();
        Assert.True(ScriptEventStreamParser.TryParseEvent("{\"type\":\"progress\",\"ts\":1700000000,\"msg\":\"s\"}", out var ev));
        Assert.Equal(1_700_000_000_000L, ev.TsUnixMs);
    }

    [Fact]
    public void Parser_DoneExitCode_DataFallback()
    {
        var p = new ScriptEventStreamParser();
        p.FeedLine("{\"type\":\"done\",\"data\":{\"exit_code\":3,\"summary\":\"s3\"}}");
        Assert.Equal(3, p.TerminalEvent!.ExitCode);
        Assert.Equal("s3", p.TerminalEvent.Summary);
    }

    // ---------- 验证门 (真实 py_compile) ----------

    [Fact]
    public async Task Validator_GoodPy_Valid()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "good.py", "print(1)\n").ConfigureAwait(false);
        var r = await PythonScriptValidator.ValidateAsync(py).ConfigureAwait(false);
        Assert.True(r.Valid, r.Detail);
    }

    [Fact]
    public async Task Validator_BadSyntax_InvalidWithDetail()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "bad.py", "def broken(:\n    pass\n").ConfigureAwait(false);
        var r = await PythonScriptValidator.ValidateAsync(py).ConfigureAwait(false);
        Assert.False(r.Valid);
        Assert.Contains("SyntaxError", r.Detail, StringComparison.OrdinalIgnoreCase);
        Assert.NotEqual(0, r.ExitCode);
    }

    // ---------- 插件服务执行 (真实 python3 子进程) ----------

    [Fact]
    public async Task Runner_OkScript_Completed_OutputsBackfilled()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "ok.py", PyOk).ConfigureAwait(false);
        var outDir = Path.Combine(dir, "out");
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload { Goal = "写个报告", OutputDir = outDir }).ConfigureAwait(false);

        Assert.Equal(ScriptPluginRunStatus.Completed, res.Status);
        Assert.Equal("demo 完成", res.Summary);
        Assert.True(res.HeartbeatCount >= 1);
        Assert.True(res.ProgressCount >= 1);
        Assert.True(res.EventCount >= 3);
        Assert.Single(res.Outputs);
        Assert.True(File.Exists(res.Outputs[0]), "done.data.outputs 路径必须真实落盘");
        Assert.Contains("goal=写个报告", File.ReadAllText(res.Outputs[0]));
        Assert.Equal(0, res.ProcessExitCode);
    }

    [Fact]
    public async Task Runner_ErrorEvent_Failed_EventAuthoritativeOverExitCode()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "err.py", @"
import json, sys
sys.stdout.write(json.dumps({'type':'error','exit_code':1,'error':'模拟失败'}) + '\n')
sys.stdout.flush()
").ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload()).ConfigureAwait(false);
        Assert.Equal(ScriptPluginRunStatus.Failed, res.Status);
        Assert.Contains("模拟失败", res.Error);
        Assert.Equal(0, res.ProcessExitCode); // 进程退出 0 但 error 事件 → 以事件为准判失败
    }

    [Fact]
    public async Task Runner_JunkLines_NoiseIgnored_DoneCompletes()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "junk.py", @"
import json, sys
print('hello 调试输出')
print('{bad json')
sys.stdout.write(json.dumps({'type':'done','summary':'junk done'}) + '\n')
sys.stdout.flush()
").ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload()).ConfigureAwait(false);
        Assert.Equal(ScriptPluginRunStatus.Completed, res.Status);
        Assert.Equal("junk done", res.Summary);
        Assert.True(res.NoiseLines >= 2);
    }

    [Fact]
    public async Task Runner_NoTerminalEvent_ExitZero_ProtocolViolationFailed()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "plain.py", "print('done-ish')\nprint('no protocol')\n").ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload()).ConfigureAwait(false);
        Assert.Equal(ScriptPluginRunStatus.Failed, res.Status);
        Assert.Contains("未发 done/error", res.Error);
        Assert.True(res.NoiseLines >= 2);
    }

    [Fact]
    public async Task Runner_SilentScript_TimeoutAndHangObserved()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "silent.py", "import time\ntime.sleep(60)\n").ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir,
            getConfig: Cfg(("script_plugin:heartbeat_secs", 1), ("script_plugin:timeout_seconds", 4)));
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload()).ConfigureAwait(false);
        sw.Stop();
        Assert.Equal(ScriptPluginRunStatus.Failed, res.Status);
        Assert.Contains("超时", res.Error);
        Assert.True(res.HangObserved, "静默超过 2×heartbeat 必须观测到疑似挂起");
        Assert.InRange(sw.ElapsedMilliseconds, 3_000, 15_000);
    }

    [Fact]
    public async Task Runner_BadPy_Rejected_RealLessonStorePersisted()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "broken.py", "def broken(:\n  pass\n").ConfigureAwait(false);
        var storePath = Path.Combine(dir, "lessons.json");
        var lessons = new agent.execution.ExecutorLessonMemory(storePath);
        var runner = new ScriptPluginRunner(dataRoot: dir,
            lessonSink: (p, s, so, ctx) => lessons.Record(p, s, so, ctx));

        var res = await runner.RunPluginScriptAsync(py, new ScriptTaskPayload { Goal = "x" }).ConfigureAwait(false);
        Assert.Equal(ScriptPluginRunStatus.RejectedInvalid, res.Status);
        Assert.True(File.Exists(storePath), "坏 py 拒绝教训必须真实落盘");
        var json = File.ReadAllText(storePath);
        Assert.Contains("script-invalid:broken.py", json);
        var hint = lessons.RenderInjectionHint("script-invalid:broken.py");
        Assert.Contains("py_compile", hint);
    }

    // ---------- 条件定时原语 (v0.17.2-c) ----------

    private const string PyFastDone = @"
import json, sys
sys.stdout.write(json.dumps({'type':'done','summary':'idle-ok'}) + '\n')
sys.stdout.flush()
";

    [Fact]
    public async Task Scheduler_WhenIdle_ExecutesAfterDue()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "sched_ok.py", PyFastDone).ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var delays = new List<TimeSpan>();
        var scheduler = new ConditionalScriptScheduler(runner, otherAgentBusy: () => false,
            delayFn: (t, c) => { delays.Add(t); return Task.CompletedTask; });

        var verdict = await scheduler.RunWhenIdleAfterAsync(py, new ScriptTaskPayload { Goal = "g" },
            TimeSpan.FromSeconds(30)).ConfigureAwait(false);

        Assert.Equal(ConditionalRunVerdictType.Executed, verdict.Verdict);
        Assert.Equal(ScriptPluginRunStatus.Completed, verdict.Run!.Status);
        Assert.Equal("idle-ok", verdict.Run.Summary);
        Assert.True(delays.Count >= 1 && delays[0] == TimeSpan.FromSeconds(30), "先等延时到期再执行");
    }

    [Fact]
    public async Task Scheduler_WhenBusy_RefusedAfterGiveUp()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "sched_busy.py", PyFastDone).ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var scheduler = new ConditionalScriptScheduler(runner, otherAgentBusy: () => true,
            getConfig: Cfg(("script_plugin:condition_retry_secs", 1), ("script_plugin:condition_giveup_secs", 1)),
            delayFn: (t, c) => Task.CompletedTask);

        var sw = System.Diagnostics.Stopwatch.StartNew();
        var verdict = await scheduler.RunWhenIdleAfterAsync(py, new ScriptTaskPayload(),
            TimeSpan.Zero).ConfigureAwait(false);
        sw.Stop();

        Assert.Equal(ConditionalRunVerdictType.RefusedBusy, verdict.Verdict);
        Assert.Null(verdict.Run);
        Assert.InRange(sw.ElapsedMilliseconds, 500, 8_000); // give-up 1s 窗口后放弃
    }

    [Fact]
    public async Task Scheduler_BadPy_RejectedInvalid()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "sched_bad.py", "def broken(:\n").ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var scheduler = new ConditionalScriptScheduler(runner, otherAgentBusy: () => false,
            delayFn: (t, c) => Task.CompletedTask);

        var verdict = await scheduler.RunWhenIdleAfterAsync(py, new ScriptTaskPayload(), TimeSpan.Zero).ConfigureAwait(false);
        Assert.Equal(ConditionalRunVerdictType.RejectedInvalid, verdict.Verdict);
        Assert.Equal(ScriptPluginRunStatus.RejectedInvalid, verdict.Run!.Status);
    }

    [Fact]
    public async Task Runner_CancelledBeforeDue_ReturnsCancelled()
    {
        var dir = TempDir();
        var py = await WritePyAsync(dir, "sched_cancel.py", PyFastDone).ConfigureAwait(false);
        var runner = new ScriptPluginRunner(dataRoot: dir);
        var scheduler = new ConditionalScriptScheduler(runner, otherAgentBusy: () => false,
            delayFn: (t, c) => throw new OperationCanceledException());
        using var cts = new CancellationTokenSource();
        cts.Cancel();
        var verdict = await scheduler.RunWhenIdleAfterAsync(py, new ScriptTaskPayload(), TimeSpan.Zero, cts.Token).ConfigureAwait(false);
        Assert.Equal(ConditionalRunVerdictType.Cancelled, verdict.Verdict);
    }
}
