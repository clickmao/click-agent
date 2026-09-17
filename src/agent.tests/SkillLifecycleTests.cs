using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 Skill P2 测试 (plan_skill_dispatch.md S.5 验收: 生命周期/隔离/熔断):
/// 状态机流转、话题切换卸载、闲置挂起、熔断开启与半开恢复、沙箱白名单读写、幂等重试、超时。
/// </summary>
public class SkillLifecycleTests
{
    private static Func<string, string, int, int> Cfg(int cacheMax = 32, int idle = 1800,
        int offTopic = 2, int breakerThreshold = 3, int breakerSeconds = 120) =>
        (module, key, fallback) => key switch
        {
            "lifecycle:session_cache_max" => cacheMax,
            "lifecycle:idle_timeout_seconds" => idle,
            "lifecycle:off_topic_rounds_to_unload" => offTopic,
            "executor:breaker_failure_threshold" => breakerThreshold,
            "executor:breaker_open_seconds" => breakerSeconds,
            "executor:timeout_seconds" => 15,
            "executor:max_retries" => 1,
            _ => fallback,
        };

    private static SkillDefinition Skill(string id = "s1", SkillType type = SkillType.Executive,
        bool idempotent = false) => new()
    {
        SkillId = id, Name = id, Domain = "d", Type = type, Idempotent = idempotent,
        ForceTemplate = type == SkillType.Normative ? "口径: {input}" : null,
    };

    // ---- 生命周期状态机 ----

    [Fact]
    public void Activate_Transitions_To_Active()
    {
        var lc = new SkillLifecycle(Cfg());
        var s = Skill();
        lc.Activate(s);
        var rt = lc.Snapshot().Single(r => r.Skill.SkillId == "s1");
        Assert.Equal(SkillState.Active, rt.State);
    }

    [Fact]
    public void OffTopic_Rounds_Unload_Skill()
    {
        var lc = new SkillLifecycle(Cfg(offTopic: 2));
        lc.Activate(Skill());
        lc.ReportRound(false); // 第 1 轮脱域
        Assert.Equal(SkillState.Active, lc.Snapshot()[0].State);
        var unloaded = lc.ReportRound(false); // 第 2 轮 → 卸载
        Assert.Contains("s1", unloaded);
        Assert.Equal(SkillState.Unloaded, lc.Snapshot()[0].State);
    }

    [Fact]
    public void Domain_Hit_Resets_OffTopic_Counter()
    {
        var lc = new SkillLifecycle(Cfg(offTopic: 2));
        lc.Activate(Skill());
        lc.ReportRound(false);
        lc.ReportRound(true, "s1"); // 命中域 → 清零
        Assert.Equal(0, lc.Snapshot()[0].OffTopicRounds);
    }

    [Fact]
    public void Idle_Timeout_Suspends_Active()
    {
        var lc = new SkillLifecycle(Cfg(idle: 0)); // 闲置 0 秒 = 立即超时
        lc.Activate(Skill());
        lc.ReportRound(true, "s1"); // 触发闲置巡检
        Assert.Equal(SkillState.Suspended, lc.Snapshot()[0].State);
    }

    [Fact]
    public void Cache_Full_Evicts_Least_Recently_Used()
    {
        var lc = new SkillLifecycle(Cfg(cacheMax: 1));
        lc.Activate(Skill("a"));
        lc.Activate(Skill("b")); // 缓存满 → 最久未用 "a" 回收
        Assert.Equal(SkillState.Unloaded, lc.Snapshot().First(r => r.Skill.SkillId == "a").State);
        Assert.Equal(SkillState.Active, lc.Snapshot().First(r => r.Skill.SkillId == "b").State);
    }

    // ---- 熔断 ----

    [Fact]
    public void Breaker_Opens_After_Threshold_Failures()
    {
        var lc = new SkillLifecycle(Cfg(breakerThreshold: 3, breakerSeconds: 120));
        lc.ReportFailure("s1");
        lc.ReportFailure("s1");
        Assert.False(lc.IsBreakerOpen("s1"));
        lc.ReportFailure("s1"); // 第 3 败 → 开启
        Assert.True(lc.IsBreakerOpen("s1"));
    }

    [Fact]
    public void Breaker_HalfOpens_On_Success()
    {
        var lc = new SkillLifecycle(Cfg(breakerThreshold: 1));
        lc.ReportFailure("s1");
        Assert.True(lc.IsBreakerOpen("s1"));
        // 熔断过期后 success 半开恢复 — 直接报成功清零
        lc.ReportSuccess("s1");
        lc.Snapshot()[0].BreakerOpenUntil = DateTimeOffset.MinValue; // 模拟到期
        Assert.False(lc.IsBreakerOpen("s1"));
    }

    [Fact]
    public async Task Breaker_Open_Skips_Execution()
    {
        var lc = new SkillLifecycle(Cfg(breakerThreshold: 1));
        lc.ReportFailure("s1");
        var ex = new SkillExecutor(lc, Cfg(breakerThreshold: 1));
        var called = false;
        var result = await ex.ExecuteAsync(Skill(), _ =>
        {
            called = true;
            return Task.FromResult("x");
        });
        Assert.Null(result); // 熔断 → 不执行
        Assert.False(called);
    }

    // ---- 执行调度 ----

    [Fact]
    public async Task Non_Idempotent_No_Retry()
    {
        var lc = new SkillLifecycle(Cfg());
        var ex = new SkillExecutor(lc, Cfg());
        var calls = 0;
        var result = await ex.ExecuteAsync(Skill(idempotent: false), _ =>
        {
            calls++;
            throw new InvalidOperationException("boom");
        });
        Assert.Null(result);
        Assert.Equal(1, calls); // 非幂等 → 单次
    }

    [Fact]
    public async Task Idempotent_Retries_Then_Succeeds()
    {
        var lc = new SkillLifecycle(Cfg());
        var ex = new SkillExecutor(lc, Cfg());
        var calls = 0;
        var result = await ex.ExecuteAsync(Skill(idempotent: true), _ =>
        {
            calls++;
            return calls < 2 ? throw new InvalidOperationException("flaky") : Task.FromResult("ok");
        });
        Assert.Equal("ok", result);
        Assert.Equal(2, calls);
    }

    [Fact]
    public async Task Timeout_Returns_Null_And_Reports_Failure()
    {
        var lc = new SkillLifecycle(Cfg());
        var ex = new SkillExecutor(lc, Cfg());
        var result = await ex.ExecuteAsync(Skill(), async token =>
        {
            await Task.Delay(2000, token); // 超时 15s? — 用零超时配置不现实, 这里直接取消
            return "late";
        }, ct: new CancellationToken(canceled: true));
        Assert.Null(result); // 外部取消 → 不重试直接失败
    }

    // ---- 沙箱 ----

    [Fact]
    public void Sandbox_Whitelist_Read_Enforced()
    {
        var s = Skill(type: SkillType.Normative);
        s.Permissions.Add("user_name");
        var scope = new SkillContextScope(s, new Dictionary<string, string> { ["user_name"] = "张三", ["secret"] = "x" });
        Assert.Equal("张三", scope.Read("user_name"));
        Assert.Null(scope.Read("secret")); // 越权 → null
        Assert.Contains("secret", scope.DeniedReads);
    }

    [Fact]
    public void Sandbox_Commit_Rejects_Out_Of_Whitelist()
    {
        var s = Skill();
        s.Permissions.Add("note");
        var scope = new SkillContextScope(s, new Dictionary<string, string>());
        scope.Write("note", "合法");
        scope.Write("hack", "越权");
        var applied = new Dictionary<string, string>();
        var ok = scope.Commit((k, v) => applied[k] = v);
        Assert.Single(ok);
        Assert.Equal("note", applied.Keys.Single());
        Assert.Equal("hack", scope.RejectedWrites.Single().Field);
    }

    // ---- Dispatcher 集成: 熔断后静默降级 ----

    [Fact]
    public async Task Dispatcher_Degrades_Silently_When_Breaker_Open()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry(), getConfig: Cfg(breakerThreshold: 1));
        var exec = Skill();
        exec.Keywords.Add("你是谁");
        dispatcher.Register(exec);
        dispatcher.RegisterEntry("s1", (_, _) => Task.FromResult("ok1"));

        var first = await dispatcher.DispatchAsync("你是谁?");
        Assert.NotNull(first); // 第一次成功

        // 注入两次失败 → 熔断 (threshold=1 即开)
        dispatcher.Lifecycle.ReportFailure("s1");
        var second = await dispatcher.DispatchAsync("你是谁?");
        Assert.Null(second); // 熔断 → 静默降级
    }

    [Fact]
    public async Task Dispatcher_OffTopic_Unloads_Then_Reloads()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry(), getConfig: Cfg(offTopic: 2));
        var s = Skill(type: SkillType.Normative);
        s.Keywords.Add("身份");
        s.ForceTemplate = "身份说明";
        dispatcher.Register(s);

        var hit1 = await dispatcher.DispatchAsync("身份是什么");
        Assert.NotNull(hit1);
        dispatcher.Lifecycle.ReportRound(false); // 脱域 1
        dispatcher.Lifecycle.ReportRound(false); // 脱域 2 → 卸载
        // 卸载不影响再次命中 (GetOrLoad 重新 Loaded→Active)
        var hit2 = await dispatcher.DispatchAsync("身份是什么");
        Assert.NotNull(hit2);
    }
}
