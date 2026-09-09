using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using agent.core;
using agent.context;
using agent.rag;
using agent.session;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.tests;

/// <summary>
/// P4 (R330): 工作区召回流式化 + 整轮字节预算测试。
/// 覆盖: ①尾部命中不丢 (无前缀截断, 零语义回退) ②整轮预算截断 (反射注入小预算)
/// ③超 200KB 大文件跳过 ④多文件正常召回 (相对路径片段)。
/// 通过反射调 private RecallFromWorkspaceAsync (既有模式, 见 WorkspaceRelevanceTests)。
/// </summary>
public class WorkspaceRecallBudgetTests
{
    private readonly Mock<ILogger<ContextAssembler>> _loggerMock;
    private readonly Mock<ILogger<TokenCompressor>> _tokenCompressorLoggerMock;
    private readonly Mock<IRAGRecall> _ragRecallMock;
    private readonly Mock<ISessionManager> _sessionManagerMock;
    private readonly Mock<ITendencyAnalyzer> _tendencyAnalyzerMock;
    private readonly Mock<ISearchService> _searchServiceMock;
    private readonly ITokenCompressor _tokenCompressor;

    private static readonly System.Reflection.MethodInfo RecallMethod = typeof(ContextAssembler)
        .GetMethod("RecallFromWorkspaceAsync",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
        ?? throw new InvalidOperationException("RecallFromWorkspaceAsync not found");

    private static readonly System.Reflection.FieldInfo BudgetField = typeof(ContextAssembler)
        .GetField("WorkspaceRecallBytesBudget",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)
        ?? throw new InvalidOperationException("WorkspaceRecallBytesBudget not found");

    public WorkspaceRecallBudgetTests()
    {
        _loggerMock = new Mock<ILogger<ContextAssembler>>();
        _tokenCompressorLoggerMock = new Mock<ILogger<TokenCompressor>>();
        _ragRecallMock = new Mock<IRAGRecall>();
        _sessionManagerMock = new Mock<ISessionManager>();
        _tendencyAnalyzerMock = new Mock<ITendencyAnalyzer>();
        _searchServiceMock = new Mock<ISearchService>();
        _tokenCompressor = new TokenCompressor(_tokenCompressorLoggerMock.Object);
    }

    private ContextAssembler CreateAssembler()
    {
        return new ContextAssembler(
            _loggerMock.Object,
            _ragRecallMock.Object,
            _sessionManagerMock.Object,
            _tendencyAnalyzerMock.Object,
            _searchServiceMock.Object,
            _tokenCompressor);
    }

    private static async Task<List<ContextSnippet>> InvokeRecallAsync(
        ContextAssembler assembler, string workspaceRoot, string message)
    {
        var request = new ContextAssemblyRequest
        {
            UserMessage = message,
            SessionId = "ws-test-session",
            UserId = "ws-test-user",
            WorkspaceRoot = workspaceRoot,
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.WorkspaceFiles }
        };
        var task = (Task<List<ContextSnippet>>)RecallMethod.Invoke(
            assembler, new object[] { request, CancellationToken.None })!;
        return await task;
    }

    private static string CreateTempWorkspace(out string root)
    {
        root = Path.Combine(Path.GetTempPath(), "wsrecall_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }

    [Fact]
    public async Task WorkspaceRecall_Finds_Keyword_In_File_Tail_No_Prefix_Truncation()
    {
        // 回归锚: 流式版不得截断 — 关键词在 ~35KB 深处 (远超任何前缀窗口) 必须仍命中。
        var root = CreateTempWorkspace(out _);
        try
        {
            var filler = new string('x', 100) + "\n";
            var head = string.Concat(Enumerable.Repeat(filler, 350)); // ~35KB 无关内容
            var target = "return QuickSelectPivot(target); // 深度命中锚";
            await File.WriteAllTextAsync(Path.Combine(root, "deep.cs"),
                head + "\n" + target + "\n" + head);
            // 中文 2-gram 关键词由消息提取; 这里用英文词更稳 (ExtractQueryKeywords 会提取 ≥2 长词)
            var snippets = await InvokeRecallAsync(CreateAssembler(), root, "QuickSelectPivot");
            var hit = Assert.Single(snippets);
            Assert.Contains("deep.cs", hit.Content);
            Assert.Contains("QuickSelectPivot", hit.Content);
            Assert.Equal(DataSourceType.WorkspaceFiles, hit.SourceType);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public async Task WorkspaceRecall_Respects_TotalByteBudget()
    {
        // 注入 2KB 预算: 第 1 文件 (最新, ~1.2KB) 读完; 第 2 个将超预算 → 截断不读。
        var root = CreateTempWorkspace(out _);
        var original = (long)BudgetField.GetValue(null)!;
        try
        {
            BudgetField.SetValue(null, 2048L);
            for (var i = 1; i <= 3; i++)
            {
                // 每行 60 x + 空格 + Alpha{i} ≈ 68B; ×25 行 ≈ 1.7KB/文件
                var line = new string('x', 60) + $" Alpha{i}\n";
                var body = string.Concat(Enumerable.Repeat(line, 25));
                var path = Path.Combine(root, $"f{i}.cs");
                await File.WriteAllTextAsync(path, body);
                File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddSeconds(i)); // f3 最新
            }
            var snippets = await InvokeRecallAsync(CreateAssembler(), root, "Alpha2 Alpha3");
            // 预算 2KB: f3(最新, ~1.7KB) 读完 total≈1.7KB; f2 读前 1.7+1.7>2KB → break
            Assert.Single(snippets);
            Assert.Contains("f3.cs", snippets[0].Content);
        }
        finally
        {
            BudgetField.SetValue(null, original);
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public async Task WorkspaceRecall_Skips_File_Over_MaxBytes()
    {
        // >200KB 单文件阈值保留: 超大文件跳过 (不整读), 小文件仍命中。
        var root = CreateTempWorkspace(out _);
        try
        {
            var big = new string('y', 100) + "\n";
            await File.WriteAllTextAsync(Path.Combine(root, "huge.md"),
                string.Concat(Enumerable.Repeat(big, 2100)) + "\nHugeMarkerInside\n"); // >200KB
            await File.WriteAllTextAsync(Path.Combine(root, "small.md"), "SmallMarkerLine ok\n");
            var snippets = await InvokeRecallAsync(CreateAssembler(), root, "HugeMarkerInside SmallMarkerLine");
            var hit = Assert.Single(snippets);
            Assert.Contains("small.md", hit.Content);
            Assert.DoesNotContain("huge.md", hit.Content);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public async Task WorkspaceRecall_MultiHit_Ranks_Best_Line()
    {
        // 流式版最佳行语义: 命中 2 词的行优于 1 词行 (R118 相关分锚)。
        var root = CreateTempWorkspace(out _);
        try
        {
            await File.WriteAllTextAsync(Path.Combine(root, "a.cs"),
                "using System;\npublic class K1 { int alpha; }\npublic class K2 { int two; }\n");
            var snippets = await InvokeRecallAsync(CreateAssembler(), root, "K1 K2 two");
            var hit = Assert.Single(snippets);
            Assert.Contains("class K2", hit.Content); // K2 行含 2 词 (K2+two) 优于 K1 行 1 词 (K1)
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
