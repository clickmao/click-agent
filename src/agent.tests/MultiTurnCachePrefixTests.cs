using agent.context;
using agent.core;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R379 缓存前缀不变式机检 (用户钦定 KPI 红线: 多轮会话第 2 轮起命中率 ≥ PromptCacheRedline.Threshold, 现 97%; 目标 98~99%)。
/// M1 的比值是**字节级必要前提** (字节前缀比 ≥ 红线); 真正的红线判定在 PromptCacheRedline (token 口径, 另含 64-token 单元对齐损耗)。
///
/// 背景 (决定性实测): DeepSeek 上下文缓存以 64 token 为单元, 必须"自 token 0 起完整匹配缓存前缀"
/// 才命中 (api-docs.deepseek.com/zh-cn/guides/kv_cache)。因此请求体必须是**追加式**的:
/// 第 N+1 轮的请求体 = 第 N 轮请求体 + 尾部追加。任何对已发前缀 (system / 历史字节) 的改写都会
/// 让该轮命中率塌到接近 0 —— 实测三处破坏点: 意图漂移改写 messages[0]、历史窗口滑动+滚动摘要重写、
/// 上下文块插在历史之前。
///
/// 本文件断言的是**结构不变式** (逐字节前缀), 不依赖真实网络与 provider 配额; 负向控制保证断言有牙。
/// </summary>
public class MultiTurnCachePrefixTests
{
    private static readonly DateTime T0 = new(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

    /// <summary>模拟生产装配: 每轮 user 内容 = 任务 + 尾部内联块 (易变内容一律在尾部追加区)。</summary>
    private static Prompt BuildTurn(
        List<Message> session, int turn, string task, string volatileBlock, string systemPrompt, int padChars = 0)
    {
        var inline = new List<string>();
        if (volatileBlock.Length > 0) inline.Add(volatileBlock);
        if (padChars > 0) inline.Add(new string('背', padChars)); // 模拟长上下文 (真实会话的正文体量)
        var sent = inline.Count == 0 ? task : task + "\n\n[本轮参考上下文]\n" + string.Join("\n\n", inline);

        var user = new Message
        {
            Id = $"u{turn}",
            SessionId = "s1",
            Role = MessageRole.User,
            Content = sent,
            SentContent = sent,
            Timestamp = T0.AddSeconds(turn * 2),
        };

        var history = session.ToList();   // 生产由 GetConversationHistoryAsync 提供 (SentContent 优先)
        session.Add(user);

        var prompt = new PromptBuilder().BuildWithHistory(user, new ContextAssemblyResult(), systemPrompt, history);
        prompt.UserMessage = sent;
        prompt.ContextPrompt = string.Empty;   // 上下文已内联进 user 尾部 (不再作为独立 system 消息)
        return prompt;
    }

    private static void AddAssistant(List<Message> session, int turn, string content)
        => session.Add(new Message
        {
            Id = $"a{turn}",
            SessionId = "s1",
            Role = MessageRole.Assistant,
            Content = content,
            SentContent = content,
            Timestamp = T0.AddSeconds(turn * 2 + 1),
        });

    /// <summary>
    /// 走生产通道: Prompt → QueuePrompt (ModelQueueAdapter) → 消息装配 (Router) → 序列化,
    /// 取 **messages 数组**的字节区间 (provider 缓存只对提示词=messages 计费; 尾部 max_tokens/temperature 不影响缓存)。
    /// </summary>
    private static string MessagesBytes(Prompt p)
    {
        var qp = ModelQueueAdapter.ToQueuePrompt(p);
        var full = ModelQueueRouter.SerializeChatRequest(new QueueChatRequest
        {
            Model = "deepseek-flash",
            Messages = ModelQueueRouter.BuildMessages(qp),
        });
        var start = full.IndexOf("\"messages\":", StringComparison.Ordinal);
        // end = messages 数组的收尾 ']' 位置 (其后是 max_tokens/temperature); 不含 ']' 才能做"追加式"前缀比较
        var end = full.LastIndexOf("],\"max_tokens\"", StringComparison.Ordinal);
        Assert.True(start >= 0 && end > start, $"请求体形状变化, 无法截取 messages 区间: {full[..Math.Min(200, full.Length)]}");
        return full[start..end];
    }

    /// <summary>诊断: 报首个分歧字节位置与两侧上下文 (回归时可直接定位破坏点)。</summary>
    private static string FirstDiff(string prev, string cur)
    {
        var n = Math.Min(prev.Length, cur.Length);
        for (var i = 0; i < n; i++)
        {
            if (prev[i] != cur[i])
            {
                var lo = Math.Max(0, i - 60);
                var a = prev[lo..Math.Min(prev.Length, i + 60)];
                var b = cur[lo..Math.Min(cur.Length, i + 60)];
                return $"首个分歧 @ {i}:\n  prev={a}\n  cur ={b}";
            }
        }
        return $"前缀全同, 仅长度不同: prev={prev.Length} cur={cur.Length} (新增 {cur.Length - prev.Length} 字符)";
    }

    /// <summary>M1 — 主断言: 三轮请求体逐字节前缀 + 字节级上界过红线 (条件取自 PromptCacheRedline.Threshold, 不写死)。</summary>
    [Fact]
    public void M1_三轮请求体逐字节前缀_且命中率上界过红线()
    {
        const string sys = "你是一个智能助手。请结合上下文信息回答用户问题。\n\n要求：\n1. 参考上下文中的相关信息\n";
        var session = new List<Message>();
        var tasks = new[]
        {
            "用一句话说明二分查找成立的前提条件。",
            "那它的时间复杂度是多少？",
            "什么情况下它会退化成线性？",
        };
        var bodies = new List<string>();   // 每轮的 messages 字节
        for (var i = 0; i < tasks.Length; i++)
        {
            // 每轮易变块 (实况: 心跳文件名带 PID / 下轮预估 / 召回片段) —— 必须只出现在尾部
            var ctx = $"[工作区文件 data/activity/{1000 + i}.json]\n[下轮预估] 轮次={i}";
            // 首轮给足正文 (真实会话体量), 后续轮只追加短问 → 命中率口径才有意义
            bodies.Add(MessagesBytes(BuildTurn(session, i + 1, tasks[i], ctx, sys, padChars: i == 0 ? 3000 : 0)));
            AddAssistant(session, i + 1, $"**答 {i + 1}**: 这是第 {i + 1} 轮的回答正文。");
        }

        for (var i = 1; i < bodies.Count; i++)
        {
            Assert.True(
                bodies[i].StartsWith(bodies[i - 1], StringComparison.Ordinal),
                $"第 {i + 1} 轮请求体不是第 {i} 轮的逐字节追加 → 缓存前缀自首个分歧字节起全部失配\n{FirstDiff(bodies[i - 1], bodies[i])}");
            var rate = (double)bodies[i - 1].Length / bodies[i].Length;
            Assert.True(
                rate >= PromptCacheRedline.Threshold,
                $"轮{i}→轮{i + 1} 字节级上界 {rate:P2} < {PromptCacheRedline.Threshold:P0} 红线 (前缀 {bodies[i - 1].Length} / 全量 {bodies[i].Length} 字符)");
        }
    }

    /// <summary>M2 — 负向控制: 把易变块写回 system (messages[0]) → 前缀必须断裂, 断言库有牙。</summary>
    [Fact]
    public void M2_负向控制_易变块入system则前缀必断()
    {
        const string sysBase = "你是一个智能助手。请结合上下文信息回答用户问题。\n\n要求：\n1. 参考上下文中的相关信息\n";
        var session = new List<Message>();
        var bodies = new List<string>();
        for (var i = 0; i < 3; i++)
        {
            // 复现旧行为: 每轮把易变块拼进 systemPrompt
            var sys = sysBase + $"\n[工作区文件 data/activity/{1000 + i}.json]";
            bodies.Add(MessagesBytes(BuildTurn(session, i + 1, i == 0 ? "用一句话说明二分查找成立的前提条件。" : "继续。", string.Empty, sys,
                padChars: i == 0 ? 3000 : 0)));
            AddAssistant(session, i + 1, $"**答 {i + 1}**");
        }

        Assert.False(
            bodies[1].StartsWith(bodies[0], StringComparison.Ordinal),
            "负向控制失效: 易变块进 system 后前缀仍被判为一致 → 断言无牙 (机检自身有 bug)");
    }

    /// <summary>M3 — 历史回放逐字节 + 不滚动摘要重写 + 1M 预算不触发丢弃 (用户令: 2000 → 1M)。</summary>
    [Fact]
    public void M3_历史全量追加式回放_无摘要重写_1M预算零丢弃()
    {
        var session = new List<Message>();
        var sentBytes = new List<string>();
        for (var turn = 1; turn <= 20; turn++)
        {
            var task = $"第 {turn} 轮问题。";
            var ctx = $"[工作区文件 data/activity/{2000 + turn}.json]";
            var sent = task + "\n\n[本轮参考上下文]\n" + ctx;
            session.Add(new Message
            {
                Id = $"u{turn}", SessionId = "s1", Role = MessageRole.User,
                Content = sent, SentContent = sent, Timestamp = T0.AddSeconds(turn * 2),
            });
            sentBytes.Add(sent);
            session.Add(new Message
            {
                Id = $"a{turn}", SessionId = "s1", Role = MessageRole.Assistant,
                Content = $"答 {turn}", SentContent = $"答 {turn}", Timestamp = T0.AddSeconds(turn * 2 + 1),
            });
        }

        var prompt = new PromptBuilder().BuildWithHistory(
            new Message { Id = "u21", SessionId = "s1", Role = MessageRole.User, Content = "第 21 轮。", Timestamp = T0.AddSeconds(100) },
            new ContextAssemblyResult(), "系统提示", session);

        Assert.Equal(40, prompt.History.Count);                  // 20 轮 × (user+assistant), 全量保留
        Assert.Equal(0, prompt.HistoryTrimmedMessages);          // 1M 预算 → 不触发整轮丢弃
        Assert.DoesNotContain(prompt.History, h => h.Content.Contains("早前对话摘要", StringComparison.Ordinal));
        for (var i = 0; i < sentBytes.Count; i++)
            Assert.Equal(sentBytes[i], prompt.History[i * 2].Content);   // 回放字节 = 当初实发字节
    }

    /// <summary>M4 — 1M 预算边界: 超上限时只从最旧整轮整体丢弃 (丢弃量可归因, 且剩余序列原样)。</summary>
    [Fact]
    public void M4_超预算时按整轮丢弃且剩余序列不变()
    {
        var session = new List<Message>();
        for (var turn = 1; turn <= 6; turn++)
        {
            var body = new string('字', 10_000);
            session.Add(new Message { Id = $"u{turn}", Role = MessageRole.User, Content = body, SentContent = body, Timestamp = T0.AddSeconds(turn * 2) });
            session.Add(new Message { Id = $"a{turn}", Role = MessageRole.Assistant, Content = "答", SentContent = "答", Timestamp = T0.AddSeconds(turn * 2 + 1) });
        }

        // 预算按 30 万字符量级设 (实现按 token 估算, 这里只验证"整轮丢弃"语义)
        var prompt = new PromptBuilder(maxHistoryTokens: 60_000).BuildWithHistory(
            new Message { Id = "u9", Role = MessageRole.User, Content = "末轮", Timestamp = T0.AddSeconds(999) },
            new ContextAssemblyResult(), "系统提示", session);

        Assert.True(prompt.HistoryTrimmedMessages > 0, "超预算未触发丢弃");
        Assert.Equal(0, prompt.HistoryTrimmedMessages % 2);                       // 必然是整轮 (user+assistant 对)
        Assert.Equal(MessageRole.User, prompt.History[0].Role);                   // 剩余序列从整轮边界开始
        Assert.DoesNotContain(prompt.History, h => h.Content.Contains("早前对话摘要", StringComparison.Ordinal));
    }
}
