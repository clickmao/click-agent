using Xunit;
using agent.context;
using agent.core;

namespace agent.tests;

/// <summary>
/// PromptHeaderBuilder 单元测试
/// </summary>
public class PromptHeaderBuilderTests
{
    [Fact]
    public void Build_EmptySnippets_ReturnsHeaderOnly()
    {
        // Arrange
        var builder = new PromptHeaderBuilder();
        
        // Act
        var result = builder.Build();
        
        // Assert: 默认 markdown 模式自带 \`\`\`context 壳 (第 7 轮决策: 不再用 CONTEXT/END CONTEXT 文本壳)
        Assert.Contains("```context", result);
    }
    
    [Fact]
    public void Build_WithSnippets_IncludesContent()
    {
        // Arrange
        var snippets = new List<ContextSnippet>
        {
            new ContextSnippet
            {
                SourceType = DataSourceType.Memory,
                Content = "Test memory content",
                RelevanceScore = 0.9
            }
        };
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("Memory", result);
        Assert.Contains("Test memory content", result);
    }
    
    [Fact]
    public void Build_WithMultipleSources_GroupsBySource()
    {
        // Arrange
        var snippets = new List<ContextSnippet>
        {
            new ContextSnippet { SourceType = DataSourceType.Memory, Content = "Memory 1", RelevanceScore = 0.8 },
            new ContextSnippet { SourceType = DataSourceType.Session, Content = "Session 1", RelevanceScore = 0.7 },
            new ContextSnippet { SourceType = DataSourceType.Memory, Content = "Memory 2", RelevanceScore = 0.6 }
        };
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("Memory", result);
        Assert.Contains("Session", result);
    }
    
    [Fact]
    public void WithFormat_Detailed_IncludesMetadata()
    {
        // Arrange
        var snippets = new List<ContextSnippet>
        {
            new ContextSnippet
            {
                SourceType = DataSourceType.Memory,
                Content = "Test",
                RelevanceScore = 0.9,
                Tags = new List<string> { "code", "test" }
            }
        };
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets)
            .WithFormat(PromptHeaderFormat.Detailed)
            .WithRelevanceScores(true);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("code", result);
    }
    
    [Fact]
    public void WithFormat_Debug_IncludesStatistics()
    {
        // Arrange
        var snippets = new List<ContextSnippet>
        {
            new ContextSnippet { SourceType = DataSourceType.Memory, Content = "Test", RelevanceScore = 0.9, EstimatedTokens = 50 }
        };
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets)
            .WithFormat(PromptHeaderFormat.Debug)
            .WithTokenStats(true);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("Statistics", result);
    }
    
    [Fact]
    public void WithMaxSnippetsPerSource_LimitsOutput()
    {
        // Arrange
        var snippets = Enumerable.Range(1, 10)
            .Select(i => new ContextSnippet
            {
                SourceType = DataSourceType.Memory,
                Content = $"Content {i}",
                RelevanceScore = 1.0 - (i * 0.05)
            })
            .ToList();
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets)
            .WithMaxSnippetsPerSource(3);
        
        // Act
        var result = builder.Build();
        
        // Assert
        // Should only contain first 3 due to sorting by relevance
        Assert.Contains("Content 1", result);
        Assert.Contains("Content 2", result);
        Assert.Contains("Content 3", result);
    }
    
    [Fact]
    public void AddWarning_IncludesWarning()
    {
        // Arrange
        var builder = new PromptHeaderBuilder()
            .AddWarning("Test warning message")
            .WithFormat(PromptHeaderFormat.Detailed);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("Warning", result);
        Assert.Contains("Test warning message", result);
    }
    
    [Fact]
    public void WithDelimiters_CustomizesDelimiters()
    {
        // Arrange
        var builder = new PromptHeaderBuilder()
            .WithDelimiters("=== START", "=== END");
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.Contains("=== START", result);
        Assert.Contains("=== END", result);
    }
    
    [Fact]
    public void UseMarkdown_False_UsesPlainFormat()
    {
        // Arrange
        var snippets = new List<ContextSnippet>
        {
            new ContextSnippet { SourceType = DataSourceType.Memory, Content = "Test", RelevanceScore = 0.9 }
        };
        
        var builder = new PromptHeaderBuilder()
            .AddSnippets(snippets)
            .UseMarkdown(false);
        
        // Act
        var result = builder.Build();
        
        // Assert
        Assert.DoesNotContain("```context", result);
    }
    
    [Fact]
    public void ChainMethods_FluentInterface()
    {
        // Arrange & Act
        var result = new PromptHeaderBuilder()
            .AddSnippet(new ContextSnippet { SourceType = DataSourceType.Memory, Content = "Test" })
            .AddSnippet(new ContextSnippet { SourceType = DataSourceType.Session, Content = "Session" })
            .WithFormat(PromptHeaderFormat.Standard)
            .WithTimestamp(true)
            .WithTokenStats(true)
            .WithMaxSnippetsPerSource(5)
            .AddWarning("Test warning")
            .Build();
        
        // Assert
        Assert.NotEmpty(result);
        Assert.Contains("Multi-Source Context Assembly", result);
    }
    
    [Fact]
    public void FromMessage_Extension_CreatesSnippet()
    {
        // Arrange
        var message = new Message
        {
            Id = "msg1",
            Role = MessageRole.User,
            Content = "Test message content",
            Timestamp = DateTime.UtcNow
        };
        
        // Act
        var snippet = ContextSnippetExtensions.FromMessage(message, 0.8);
        
        // Assert
        Assert.Equal(DataSourceType.Session, snippet.SourceType);
        Assert.Contains("Test message content", snippet.Content);
        Assert.Equal(0.8, snippet.RelevanceScore);
    }
    
    [Fact]
    public void EstimateTokens_CalculatesCorrectly()
    {
        // Arrange
        var text = "Hello world 你好";
        
        // Act
        var tokens = ContextSnippetExtensions.EstimateTokens(text);
        
        // Assert
        Assert.True(tokens > 0);
    }
}
