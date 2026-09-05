using agent.intent;
using Xunit;

namespace agent.tests;

/// <summary>
/// 意图识别误判矩阵 (v7.6): 覆盖 9 意图正例 + 子串误判反例 + 中英文混合。
/// 这些用例在裸 Contains 时代全部误判 (sales→file_operation 等)。
/// </summary>
public class IntentRecognizerTests
{
    // ---------- 正例: 9 意图至少 1 条 ----------

    [Theory]
    [InlineData("帮我写一个 HTTP 客户端类", IntentRecognizer.Intents.CodeGeneration)]
    [InlineData("创建新的用户服务", IntentRecognizer.Intents.CodeGeneration)]
    [InlineData("实现一个分页组件", IntentRecognizer.Intents.CodeGeneration)]
    public void CodeGeneration_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("给这个方法写单元测试", IntentRecognizer.Intents.TestGeneration)]
    [InlineData("为 UserService 生成测试用例", IntentRecognizer.Intents.TestGeneration)]
    public void TestGeneration_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("修改这个方法 supporting 分页", IntentRecognizer.Intents.CodeModification)]
    [InlineData("重构 OrderService", IntentRecognizer.Intents.CodeModification)]
    public void CodeModification_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("帮我审查这段代码", IntentRecognizer.Intents.CodeReview)]
    [InlineData("code review for PR 123", IntentRecognizer.Intents.CodeReview)]
    public void CodeReview_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("搜索一下 .NET 10 的新特性", IntentRecognizer.Intents.Search)]
    [InlineData("帮我找一下 Blazor 教程", IntentRecognizer.Intents.Search)]
    [InlineData(".NET AOT 是什么", IntentRecognizer.Intents.Search)]
    public void Search_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("列出项目里的文件", IntentRecognizer.Intents.FileOperation)]
    [InlineData("读取 appsettings.json", IntentRecognizer.Intents.FileOperation)]
    public void FileOperation_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("git 提交规范有哪些", IntentRecognizer.Intents.GitOperation)]
    [InlineData("commit 一下当前改动", IntentRecognizer.Intents.GitOperation)]
    [InlineData("新建一个 feature 分支", IntentRecognizer.Intents.GitOperation)]
    public void GitOperation_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("我们之前说到哪了", IntentRecognizer.Intents.MemorySearch)]
    [InlineData("你记得吗 上次讨论的架构", IntentRecognizer.Intents.MemorySearch)]
    public void MemorySearch_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Theory]
    [InlineData("你好", IntentRecognizer.Intents.General)]
    [InlineData("", IntentRecognizer.Intents.General)]
    [InlineData("   ", IntentRecognizer.Intents.General)]
    public void General_Positive(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    // ---------- 反例: 裸 Contains 时代的误判 (本组是 v7.6 修复的核心证据) ----------

    [Theory]
    [InlineData("统计销售额 sales 数据", IntentRecognizer.Intents.General)]       // 曾命中 "ls"
    [InlineData("商品分类 category 怎么设计", IntentRecognizer.Intents.General)]   // 曾命中 "cat"
    [InlineData("boss 直聘上找工作", IntentRecognizer.Intents.General)]            // 曾命中 "找"
    [InlineData("他写了一本小说", IntentRecognizer.Intents.General)]               // 曾命中 "写"→code_generation
    [InlineData("直接 dir 显示", IntentRecognizer.Intents.FileOperation)]          // 词边界: "直接dir" 中 dir 独立
    public void Substring_FalsePositives_Eliminated(string input, string expected) =>
        Assert.Equal(expected, IntentRecognizer.Recognize(input));

    [Fact]
    public void GitIgnore_IsNotGitOperation()
    {
        // "gitignore" 含 "git" 子串, 词边界后不应命中
        Assert.NotEqual(IntentRecognizer.Intents.GitOperation,
            IntentRecognizer.Recognize("gitignore 文件怎么写"));
    }

    [Fact]
    public void WriteTests_Wins_OverCodeGeneration()
    {
        // "写测试" 必须是 test_generation 而非 code_generation (规则顺序: 测试先于代码)
        Assert.Equal(IntentRecognizer.Intents.TestGeneration,
            IntentRecognizer.Recognize("帮我写测试"));
    }
}
