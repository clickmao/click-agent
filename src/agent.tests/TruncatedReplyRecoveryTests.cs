using System;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R371 D7 机检 (真机 RUN3 实证的真缺陷): 正文被输出预算**截断** (completion=8192 上限,
/// content=1209 字符, 断在 `start_len: int =` 半行) 却 success=true → 用户拿到半份实现。
/// 断言:
///   ① 语法检测器: 尾部未完结构 (运算符/开括号/未闭合三引号/未闭合围栏) 判截断; 完整正文零误报;
///   ② 真 HTTP 通路: 截断 → **升预算 + 断点提示续写一次** → 去重重拼, 且续写请求确实带提示;
///   ③ 完整正文 → 不触发续写 (零额外成本);
///   ④ 续写返回空 → 保留原文, 不崩、不假装完整。
/// </summary>
public class TruncatedReplyRecoveryTests
{
    private const string KeyEnv = "R371_TRUNCATED_KEY";

    private static ModelCatalog Catalog(string endpoint) => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r371-coder", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
                PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5, CodingScore = 9, ContextWindow = 64000,
                SuitedFor = { "coding" },
            },
        },
    };

    private static ModelQueueRouter Router(string endpoint)
        => new(Catalog(endpoint), new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

    private static async Task<QueueResponse> CallAsync(ModelQueueRouter router)
        => await router.CallAsync(
            new QueuePrompt { UserMessage = "用 Python 写一个贪吃蛇", ReasoningEffort = "high" },
            TaskKindHint.General, "coding");

    // ── ① 检测器 ────────────────────────────────────────────────────────────
    [Theory]
    [InlineData("def f():\n    return 1\nprint(", true)]          // 断在开括号
    [InlineData("x = 1 +\n", true)]                                // 断在运算符
    [InlineData("import os\n# doc\n\"\"\"未闭合的文档串\n", true)]      // 未闭合三引号
    [InlineData("```python\nprint(1)\n", true)]                    // 未闭合围栏
    [InlineData("values = [1, 2,\n", true)]                        // 断在列表中间
    [InlineData("说明如下：\n\n以上。", false)]                     // 中文全角标点 = 完整句
    [InlineData("def f():\n    return 1\n\nprint(\"ok\")\n", false)] // 完整实现
    [InlineData("```python\nprint(1)\n```\n", false)]              // 闭合围栏
    [InlineData("", false)]
    [InlineData(null, false)]
    // ── R556 新增: JSON 本体已闭合时, 尾随内容**不是**截断证据 (R555 w82/w84 rc=4 实证) ──
    [InlineData("{\"a\":1}\n\n说明: 以上为完整计划 (", false)]          // 完整对象 + 尾随散文
    [InlineData("[1,2] 后记：", false)]                              // 完整数组 + 中文尾随
    [InlineData("{\"steps\":[{\"id\":\"s1\"}]}\n```", false)]        // 完整对象 + 尾随围栏
    [InlineData("{\"a\":[1,2,\n", true)]                            // 真截断 (值未配平) 仍判真
    [InlineData("{\"a\":\"未闭合\n", true)]                          // 断在字符串内 仍判真
    public void 截断检测_语法未闭合判真_完整正文零误报(string? content, bool expected)
        => Assert.Equal(expected, ModelQueueRouter.LooksTruncated(content));

    // ── ①b R556 回归: 完整契约 + 尾随内容 ⇒ 不触发续写 (省一次全价调用), 且原文不改写 ──
    [Fact]
    public void 契约已完整_尾随内容不触发续写_R555回归()
    {
        var complete = "{\"schema_version\":\"r1.0\",\"plan\":[{\"id\":\"s1\"}]}\n\n说明: 完整 (21 25)";
        Assert.False(ModelQueueRouter.LooksTruncated(complete));
        // 判别力: 同样"结尾带触发字符"但对象未闭合 ⇒ 仍判真 (新判据只豁免**已闭合**的对象)
        Assert.True(ModelQueueRouter.LooksTruncated("{\"schema_version\":\"r1.0\" ("));
    }

    // ── ② 续写去重 ──────────────────────────────────────────────────────────
    [Fact]
    public void 续写去重_重叠部分只保留一份()
    {
        var head = "    def step(self, direction):\n        self.dir = direction";
        var tail = "self.dir = direction\n        return self.dir";

        var merged = ModelQueueRouter.MergeContinuation(head, tail);

        Assert.Equal("    def step(self, direction):\n        self.dir = direction\n        return self.dir", merged);
    }

    [Fact]
    public void 续写去重_无重叠直接拼接()
    {
        Assert.Equal("abcdef\nghij", ModelQueueRouter.MergeContinuation("abcdef\n", "ghij"));
        Assert.Equal("abcdef", ModelQueueRouter.MergeContinuation("abcdef", ""));
    }

    // ── ③ 真 HTTP 通路: 截断 → 续写 ───────────────────────────────────────
    [Fact]
    public async Task 截断正文_升预算加断点提示续写一次_去重重拼()
    {
        var head = "from __future__ import annotations\n\ndef selftest():\n    print(";
        var cont = "print(\"PASS\")\n    return True\n";

        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply(head, completionTokens: 8192),
            FakeLlmEndpoint.Reply(cont, completionTokens: 120),
        });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var resp = await CallAsync(Router(fake.Endpoint));

            Assert.Equal(2, fake.Hits);                                  // 恰好续写一次
            Assert.Equal("from __future__ import annotations\n\ndef selftest():\n    print(\"PASS\")\n    return True\n", resp.Content);
            Assert.DoesNotContain("print(print(", resp.Content);         // 断点未重复
            Assert.Contains("\"max_tokens\":32768", fake.Bodies[1]);      // 预算升级
            // 续写提示确实随请求发出: 取值后比较 (JSON 里中文会被转义成 \uXXXX, 直接找子串会假阴性)
            var sysText = System.Text.Json.JsonDocument.Parse(fake.Bodies[1]).RootElement
                .GetProperty("messages").EnumerateArray()
                .Where(m => m.GetProperty("role").GetString() == "system")
                .Select(m => m.GetProperty("content").GetString())
                .Aggregate("", (a, b) => a + b);
            Assert.Contains("截断", sysText);
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }

    [Fact]
    public async Task 完整正文_不触发续写_零额外成本()
    {
        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply("def f():\n    return 1\n\nprint(\"ok\")\n"),
        });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var resp = await CallAsync(Router(fake.Endpoint));

            Assert.Equal(1, fake.Hits);
            Assert.True(resp.Success);
            Assert.Contains("print(\"ok\")", resp.Content);
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }

    [Fact]
    public async Task 续写返回空_保留原文_不崩不假装完整()
    {
        var head = "def f():\n    return 1\nprint(";

        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply(head, completionTokens: 8192),
            FakeLlmEndpoint.Reply("", completionTokens: 0),
        });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var resp = await CallAsync(Router(fake.Endpoint));

            Assert.Equal(2, fake.Hits);
            Assert.Equal(head, resp.Content);                             // 原文保留 (半份也是真产出)
            Assert.True(ModelQueueRouter.LooksTruncated(resp.Content));   // 截断事实仍可被检测
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }
}
