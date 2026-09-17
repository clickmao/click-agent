using System;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;

/// <summary>
/// v0.17.2-c (用户钦定: "如果当前没有其他任务存在则 XX (分钟/小时/天) 执行"): 条件定时调度原语 —
/// 延时到期后轮询"其他 agent 是否忙"(接线方注入, 默认由 ActivityService.IsOtherAgentBusy 提供,
/// 自身排除), 空闲即经插件服务执行 py 脚本 (v0.17.2-b 事件流协议), 忙则重试至 give-up。
/// 重试/放弃窗口全走配置委托, 零硬编码; 延时/时钟可注入 (测试确定性)。
/// </summary>
public sealed class ConditionalScriptScheduler
{
    private readonly ScriptPluginRunner _runner;
    private readonly Func<bool> _otherAgentBusy;
    private readonly Func<TimeSpan, CancellationToken, Task> _delay;
    private readonly Func<long> _nowMs;
    private readonly Func<string, string, int, int> _cfg;

    public ConditionalScriptScheduler(
        ScriptPluginRunner runner,
        Func<bool> otherAgentBusy,
        Func<string, string, int, int>? getConfig = null,
        Func<TimeSpan, CancellationToken, Task>? delayFn = null,
        Func<long>? nowMs = null)
    {
        _runner = runner ?? throw new ArgumentNullException(nameof(runner));
        _otherAgentBusy = otherAgentBusy ?? throw new ArgumentNullException(nameof(otherAgentBusy));
        _cfg = getConfig ?? ((_, _, d) => d);
        _delay = delayFn ?? ((t, c) => Task.Delay(t, c));
        _nowMs = nowMs ?? (() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());
    }

    /// <summary>
    /// 到期且空闲执行。dueIn = 从当前起的延时; 到期后若忙按 retry 间隔重试, 超过 give-up 窗口 → RefusedBusy。
    /// </summary>
    public async Task<ConditionalRunVerdict> RunWhenIdleAfterAsync(
        string scriptPath, ScriptTaskPayload task, TimeSpan dueIn, CancellationToken ct = default)
    {
        var retrySecs = Math.Max(1, _cfg("script_plugin", "condition_retry_secs", 5));
        var giveUpSecs = Math.Max(1, _cfg("script_plugin", "condition_giveup_secs", 60));
        var deadline = _nowMs() + (long)Math.Max(0, dueIn.TotalMilliseconds) + giveUpSecs * 1000L;

        try
        {
            if (dueIn > TimeSpan.Zero)
                await _delay(dueIn, ct).ConfigureAwait(false); // 先等延时到期
            if (ct.IsCancellationRequested)
                return new ConditionalRunVerdict { Verdict = ConditionalRunVerdictType.Cancelled };

            while (true)
            {
                if (!_otherAgentBusy())
                {
                    var run = await _runner.RunPluginScriptAsync(scriptPath, task, ct).ConfigureAwait(false);
                    return run.Status switch
                    {
                        ScriptPluginRunStatus.RejectedInvalid => new ConditionalRunVerdict
                        {
                            Verdict = ConditionalRunVerdictType.RejectedInvalid,
                            Run = run, Reason = run.ValidationDetail,
                        },
                        ScriptPluginRunStatus.Completed => new ConditionalRunVerdict
                        {
                            Verdict = ConditionalRunVerdictType.Executed, Run = run,
                        },
                        _ => new ConditionalRunVerdict
                        {
                            Verdict = ConditionalRunVerdictType.Failed, Run = run, Reason = run.Error,
                        },
                    };
                }
                if (_nowMs() >= deadline)
                    return new ConditionalRunVerdict
                    {
                        Verdict = ConditionalRunVerdictType.RefusedBusy,
                        Reason = $"give-up {giveUpSecs}s 后其他 agent 仍忙",
                    };
                await _delay(TimeSpan.FromSeconds(retrySecs), ct).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            return new ConditionalRunVerdict { Verdict = ConditionalRunVerdictType.Cancelled };
        }
    }
}
