using agent.config;

namespace agent.skills;

/// <summary>
/// Skill 执行调度 (P2, plan_skill_dispatch.md S.2 SkillExecutor; 原文 §6.2):
/// 超时中断 (CancellationTokenSource 超时) + 幂等才重试 (SkillDefinition.Idempotent) +
/// 熔断 (Lifecycle 托管: 连续 N 败临时禁用, 开启期直接拒绝执行 → 调用方降级)。
/// 阈值全走配置委托, 零硬编码。
/// </summary>
public sealed class SkillExecutor
{
    private readonly SkillLifecycle _lifecycle;
    private readonly int _timeoutSeconds;
    private readonly int _maxRetries;

    public SkillExecutor(SkillLifecycle lifecycle, Func<string, string, int, int> getConfig)
    {
        _lifecycle = lifecycle;
        _timeoutSeconds = getConfig("skill", "executor:timeout_seconds", 15);
        _maxRetries = getConfig("skill", "executor:max_retries", 1);
    }

    /// <summary>执行入口: 熔断开启 → null (降级); 超时/异常按幂等性重试; 结果上报生命周期。</summary>
    public async Task<string?> ExecuteAsync(
        SkillDefinition skill,
        Func<CancellationToken, Task<string>> entry,
        CancellationToken ct = default)
    {
        if (_lifecycle.IsBreakerOpen(skill.SkillId))
            return null; // 熔断开启 → 降级普通推理

        var attempts = skill.Idempotent ? _maxRetries + 1 : 1;
        for (var attempt = 0; attempt < attempts; attempt++)
        {
            try
            {
                using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                timeoutCts.CancelAfter(TimeSpan.FromSeconds(_timeoutSeconds));
                var result = await entry(timeoutCts.Token);
                _lifecycle.ReportSuccess(skill.SkillId);
                return result;
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                // 超时 (外部取消不重试 — 上层取消语义优先)
                if (attempt >= attempts - 1)
                {
                    _lifecycle.ReportFailure(skill.SkillId);
                    return null;
                }
            }
            catch (Exception)
            {
                if (attempt >= attempts - 1)
                {
                    _lifecycle.ReportFailure(skill.SkillId);
                    return null;
                }
            }
        }
        return null;
    }
}
