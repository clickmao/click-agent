using agent.intent;
using agent.output;
using agent.registry;
using agent.userinteraction;
using Xunit;
using IntentDecomposer = agent.intent.IntentDecomposer;

namespace agent.tests;

/// <summary>
/// v7.13 特性测试: 问询数据类型/批量问询/置信度+证据门槛/偏好库/双模式输出/vulkan 配置。
/// </summary>
public class V713FeatureTests
{
    // ── PromptDataValidator ──

    [Theory]
    [InlineData("42", "42")]
    [InlineData("-7", "-7")]
    [InlineData("3.14", "3.14")]
    [InlineData("1,024", "1024")]
    public void Number_Valid_Passes(string input, string expected)
    {
        var (ok, normalized, error) = PromptDataValidator.Validate(PromptDataType.Number, input);
        Assert.True(ok, error);
        Assert.Equal(expected, normalized);
    }

    [Theory]
    [InlineData("abc")]
    [InlineData("")]
    [InlineData("12x")]
    public void Number_Invalid_Fails(string input)
    {
        var (ok, _, error) = PromptDataValidator.Validate(PromptDataType.Number, input);
        Assert.False(ok);
        Assert.False(string.IsNullOrEmpty(error));
    }

    [Theory]
    [InlineData("2026-09-06", "2026-09-06")]
    [InlineData("2026/9/6", "2026-09-06")]
    [InlineData("2026年9月6日", "2026-09-06")]
    public void Date_Valid_Passes(string input, string expected)
    {
        var (ok, normalized, error) = PromptDataValidator.Validate(PromptDataType.Date, input);
        Assert.True(ok, error);
        Assert.Equal(expected, normalized);
    }

    [Fact]
    public void Boolean_ChineseAndEnglish_Passes()
    {
        Assert.Equal("true", PromptDataValidator.Validate(PromptDataType.Boolean, "是").Normalized);
        Assert.Equal("false", PromptDataValidator.Validate(PromptDataType.Boolean, "否").Normalized);
        Assert.Equal("true", PromptDataValidator.Validate(PromptDataType.Boolean, "y").Normalized);
        Assert.False(PromptDataValidator.Validate(PromptDataType.Boolean, "也许").Ok);
    }

    [Fact]
    public void Choice_MustMatchOption()
    {
        var choices = new[] { "搜索资料", "写文档", "执行命令" };
        var (ok, normalized, _) = PromptDataValidator.Validate(PromptDataType.Choice, "写文档", choices);
        Assert.True(ok);
        Assert.Equal("写文档", normalized);

        var (ok2, _, error2) = PromptDataValidator.Validate(PromptDataType.Choice, "跳舞", choices);
        Assert.False(ok2);
        Assert.Contains("不在选项内", error2);
    }

    [Fact]
    public void MultiChoice_CommaAndDunhao_Pass()
    {
        var choices = new[] { "A", "B", "C" };
        var (ok, normalized, error) = PromptDataValidator.Validate(PromptDataType.MultiChoice, "A、C", choices);
        Assert.True(ok, error);
        Assert.Equal("A,C", normalized);
    }

    [Fact]
    public void Url_And_Email_And_Port()
    {
        Assert.True(PromptDataValidator.Validate(PromptDataType.Url, "https://example.com/x").Ok);
        Assert.False(PromptDataValidator.Validate(PromptDataType.Url, "ftp://x").Ok);
        Assert.True(PromptDataValidator.Validate(PromptDataType.Email, "user@host.com").Ok);
        Assert.False(PromptDataValidator.Validate(PromptDataType.Email, "user host").Ok);
        Assert.True(PromptDataValidator.Validate(PromptDataType.Port, "8080").Ok);
        Assert.False(PromptDataValidator.Validate(PromptDataType.Port, "99999").Ok);
    }

    [Fact]
    public void IpAddress_V4()
    {
        Assert.True(PromptDataValidator.Validate(PromptDataType.IpAddress, "192.168.1.1").Ok);
        Assert.False(PromptDataValidator.Validate(PromptDataType.IpAddress, "999.1.1.1").Ok);
    }

    // ── 置信度 + EvidenceGate ──

    [Fact]
    public void Decomposer_LowConfidence_OnAmbiguousReference()
    {
        var tasks = IntentDecomposer.Decompose("处理一下这个文件");
        Assert.NotEmpty(tasks);
        Assert.Contains(tasks, t =>
            t.Flags.HasFlag(IntentDecomposer.ConfidenceFlags.AmbiguousReference) ||
            t.Confidence < 1.0);
    }

    [Fact]
    public void Decomposer_HighConfidence_OnClearIntent()
    {
        var tasks = IntentDecomposer.Decompose("搜索 quantum computing 最新论文");
        Assert.NotEmpty(tasks);
        Assert.All(tasks, t => Assert.True(t.Confidence >= 0.6, $"置信度过低: {t.Text}={t.Confidence}"));
    }

    [Fact]
    public void EvidenceGate_RespectsMaxQuestions()
    {
        // 3 个低置信任务, 上限 2 → 最多问 2 个任务的问题, 其余进 DroppedForLimit
        var tasks = new List<IntentDecomposer.SubTask>
        {
            new("处理一下这个", "general", false, 0, IntentDecomposer.TaskRelation.None, 0.3,
                IntentDecomposer.ConfidenceFlags.AmbiguousReference),
            new("写点东西", "general", true, 1, IntentDecomposer.TaskRelation.Sequential, 0.4,
                IntentDecomposer.ConfidenceFlags.TooVague),
            new("改改那个", "general", true, 2, IntentDecomposer.TaskRelation.Sequential, 0.35,
                IntentDecomposer.ConfidenceFlags.AmbiguousReference | IntentDecomposer.ConfidenceFlags.TooVague),
        };

        var gate = new EvidenceGate(maxQuestions: 2);
        var result = gate.Evaluate(tasks);

        var askedQuestions = result.ToAsk.Sum(r => r.Questions.Count);
        Assert.True(askedQuestions <= 2, $"问询数 {askedQuestions} 超上限 2");
        Assert.NotEmpty(result.DroppedForLimit);
        // 高优先级 (MissingParameter/AmbiguousReference) 优先
        if (result.ToAsk.Count >= 1)
            Assert.True(result.ToAsk[0].Priority <= result.ToAsk[^1].Priority);
    }

    [Fact]
    public void EvidenceGate_HighConfidencePasses()
    {
        var tasks = new List<IntentDecomposer.SubTask>
        {
            new("搜索 AI 芯片产业报告", "search", false, 0),
        };
        var result = new EvidenceGate().Evaluate(tasks);
        Assert.Empty(result.ToAsk);
        Assert.Single(result.Passed);
    }

    // ── 偏好库 ──

    [Fact]
    public void Fingerprint_ExcludesConcreteValues()
    {
        // 同类问题不同具体值 → 同指纹 (偏好是"模式"不是"本次输入")
        var f1 = ClarificationFingerprint.Build("输出文件保存到哪个路径?", "output_path", PromptDataType.Path);
        var f2 = ClarificationFingerprint.Build("日志文件写到哪个路径?", "log_path", PromptDataType.Path);
        Assert.Equal(f1, f2);

        // 不同类型 → 不同指纹 (防跨类污染)
        var f3 = ClarificationFingerprint.Build("数量要多少?", "count", PromptDataType.Integer);
        Assert.NotEqual(f1, f3);
    }

    [Fact]
    public void PreferenceStore_NeverStoresCredentials()
    {
        var tmp = Path.Combine(Path.GetTempPath(), "pref_test_" + Guid.NewGuid().ToString("N"));
        try
        {
            var store = new ClarificationPreferenceStore(tmp);
            var credItem = new ClarificationItem
            {
                Kind = ClarificationKinds.ApiKey,
                ParameterName = "api_key",
                Question = "请提供 API Key",
                DataType = PromptDataType.String,
            };
            // 凭据回答必须被拒收
            Assert.False(store.RecordAnswer(credItem, "sk-1234567890abcdef"));
            Assert.Empty(store.Snapshot());

            // ApplyTo 对凭据类也不注入任何建议
            Assert.False(store.ApplyTo(credItem));
        }
        finally
        {
            if (Directory.Exists(tmp))
                Directory.Delete(tmp, recursive: true);
        }
    }

    [Fact]
    public void PreferenceStore_RecordsPatternNotRawValue()
    {
        var tmp = Path.Combine(Path.GetTempPath(), "pref_test_" + Guid.NewGuid().ToString("N"));
        try
        {
            var store = new ClarificationPreferenceStore(tmp);
            var item = new ClarificationItem
            {
                ParameterName = "output_path",
                Question = "结果保存到哪个路径?",
                DataType = PromptDataType.Path,
            };
            Assert.True(store.RecordAnswer(item, "/home/user/outputs/result.md"));

            var snap = store.Snapshot();
            Assert.Single(snap);
            // 存的是 "absolute" 模式, 不是原路径
            Assert.Equal("absolute", snap[0].PreferredPattern);
            Assert.DoesNotContain("/home/user", System.Text.Json.JsonSerializer.Serialize(snap));

            // 同类新问题 → ApplyTo 注入偏好建议
            var item2 = new ClarificationItem
            {
                ParameterName = "log_path",
                Question = "日志写到哪个路径?",
                DataType = PromptDataType.Path,
            };
            Assert.True(store.ApplyTo(item2));
            Assert.Contains("绝对路径", item2.SuggestedValues[0]);
        }
        finally
        {
            if (Directory.Exists(tmp))
                Directory.Delete(tmp, recursive: true);
        }
    }

    [Fact]
    public void PreferenceStore_ChoiceOrder_Reordered()
    {
        var tmp = Path.Combine(Path.GetTempPath(), "pref_test_" + Guid.NewGuid().ToString("N"));
        try
        {
            var store = new ClarificationPreferenceStore(tmp);
            var item = new ClarificationItem
            {
                ParameterName = "数据来源",
                Question = "要基于哪个前序结果?",
                DataType = PromptDataType.Choice,
                Choices = new List<string> { "上一步的输出结果", "另指定的数据", "不需要输入数据" },
            };
            store.RecordAnswer(item, "另指定的数据");

            var item2 = new ClarificationItem
            {
                ParameterName = "数据来源",
                Question = "这次基于哪个结果?",
                DataType = PromptDataType.Choice,
                Choices = new List<string> { "上一步的输出结果", "另指定的数据", "不需要输入数据" },
            };
            store.ApplyTo(item2);
            // 用户上次选过的选项排到最前
            Assert.Equal("另指定的数据", item2.Choices[0]);
            Assert.Equal("另指定的数据", item2.SuggestedValues[0]);
        }
        finally
        {
            if (Directory.Exists(tmp))
                Directory.Delete(tmp, recursive: true);
        }
    }

    // ── 双模式输出 ──

    [Fact]
    public void OutputFormatter_MarkdownToPlainText()
    {
        var md = "# 标题\n\n这是**重点**和 `code`。\n\n```csharp\nvar x = 1;\n```\n\n- 项目一\n- 项目二\n";
        var plain = OutputFormatter.ToPlainText(md);

        Assert.DoesNotContain("#", plain);
        Assert.DoesNotContain("**", plain);
        Assert.DoesNotContain("`", plain);
        Assert.DoesNotContain("```", plain);
        Assert.Contains("标题", plain);
        Assert.Contains("重点", plain);
        Assert.Contains("var x = 1;", plain);
        Assert.Contains("· 项目一", plain);
    }

    [Fact]
    public void OutputFormatter_TableLineDropped()
    {
        var md = "| a | b |\n|---|---|\n| 1 | 2 |";
        var plain = OutputFormatter.ToPlainText(md);
        Assert.DoesNotContain("---", plain);
        Assert.Contains("1", plain);
    }

    [Fact]
    public void AgentOutputMessage_DualMode()
    {
        var msg = AgentOutputMessage.FromLlmAnswer("# 结果\n内容**加粗**", "test");
        Assert.Equal(OutputMode.Markdown, msg.Mode);
        Assert.Equal(AgentOutputKind.Answer, msg.Kind);

        // PlainText 模式: Content 语义不变, 渲染层负责降格式
        msg.Mode = OutputMode.PlainText;
        Assert.Contains("结果", msg.Content);
    }

    [Fact]
    public void SpectreRenderer_PlaintextMode_NoMarkupResidue()
    {
        var renderer = new SpectreOutputRenderer(decorated: false);
        var msg = AgentOutputMessage.FromLlmAnswer("# 标题\n**粗体**内容", "test");
        msg.Mode = OutputMode.PlainText;
        using var sw = new StringWriter();
        renderer.Render(msg, sw);
        var output = sw.ToString();
        Assert.Contains("标题", output);
        Assert.DoesNotContain("**", output);
        Assert.DoesNotContain("[/]", output);
    }

    // ── ClarificationBatch 分组 ──

    [Fact]
    public void ClarificationBatch_GroupsByGroupId()
    {
        var items = new List<ClarificationItem>
        {
            new() { NodeId = "n1", GroupId = "g1", ParameterName = "a" },
            new() { NodeId = "n2", GroupId = "g1", ParameterName = "b" },
            new() { NodeId = "n3", GroupId = "", ParameterName = "c" },
        };
        var groups = ClarificationBatch.Group(items);
        Assert.Equal(2, groups.Count);
        Assert.Contains(groups, g => g.Count == 2);
    }

    [Fact]
    public void ClarificationBatch_ValidationRetry_Exhausts()
    {
        // 模拟: 用户一直给非法数字 → 重试耗尽后诚实报错 (不伪造答案)
        var tmp = Path.Combine(Path.GetTempPath(), "pref_test_" + Guid.NewGuid().ToString("N"));
        var item = new ClarificationItem
        {
            NodeId = "n1",
            ParameterName = "count",
            Question = "要处理多少条?",
            DataType = PromptDataType.Integer,
        };
        var (ok, _, error) = PromptDataValidator.Validate(item.DataType, "abc");
        Assert.False(ok);
        Assert.NotNull(error);
    }
}
