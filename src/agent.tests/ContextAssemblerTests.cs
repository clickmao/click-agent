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
/// ContextAssembler 单元测试
/// </summary>
public class ContextAssemblerTests
{
    private readonly Mock<ILogger<ContextAssembler>> _loggerMock;
    private readonly Mock<ILogger<TokenCompressor>> _tokenCompressorLoggerMock;
    private readonly Mock<IRAGRecall> _ragRecallMock;
    private readonly Mock<ISessionManager> _sessionManagerMock;
    private readonly Mock<ITendencyAnalyzer> _tendencyAnalyzerMock;
    private readonly Mock<ISearchService> _searchServiceMock;
    private readonly ITokenCompressor _tokenCompressor;
    
    public ContextAssemblerTests()
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
    
    [Fact]
    public async Task AssembleAsync_WithMemory_ReturnsSnippets()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        var mockDocs = new List<RecallResult>
        {
            new RecallResult
            {
                Document = new RAGDocument
                {
                    Id = "doc1",
                    Content = "Test document content",
                    Keywords = new List<string> { "test" }
                },
                Score = 0.9
            }
        };
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(mockDocs);
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test query",
            SessionId = "session1",
            UserId = "user1",
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.NotEmpty(result.Snippets);
        Assert.Contains(result.Snippets, s => s.SourceType == DataSourceType.Memory);
        Assert.True(result.TotalTokens > 0);
    }
    
    [Fact]
    public async Task AssembleAsync_WithSession_ReturnsSessionSnippets()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        var mockSession = new Session
        {
            Id = "session1",
            UserId = "user1",
            Messages = new List<Message>
            {
                new Message
                {
                    Id = "msg1",
                    Role = MessageRole.User,
                    Content = "Previous user message about testing",
                    Timestamp = DateTime.UtcNow.AddHours(-1)
                },
                new Message
                {
                    Id = "msg2",
                    Role = MessageRole.Assistant,
                    Content = "Previous assistant response",
                    Timestamp = DateTime.UtcNow.AddMinutes(-30)
                }
            }
        };
        
        _sessionManagerMock
            .Setup(x => x.GetSessionAsync("session1"))
            .ReturnsAsync(mockSession);
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test query about testing",
            SessionId = "session1",
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Session }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.Contains(result.Snippets, s => s.SourceType == DataSourceType.Session);
    }
    
    [Fact]
    public async Task AssembleAsync_WithRelevanceThreshold_FiltersLowScore()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        var mockDocs = new List<RecallResult>
        {
            new RecallResult
            {
                Document = new RAGDocument
                {
                    Id = "high",
                    Content = "High relevance content",
                    Keywords = new List<string> { "test" }
                },
                Score = 0.9
            },
            new RecallResult
            {
                Document = new RAGDocument
                {
                    Id = "low",
                    Content = "Low relevance content",
                    Keywords = new List<string> { "other" }
                },
                Score = 0.2
            }
        };
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(mockDocs);
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test query",
            MinRelevanceScore = 0.5,
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.All(result.Snippets, s => Assert.True(s.RelevanceScore >= 0.5));
        Assert.DoesNotContain(result.Snippets, s => s.Id == "low");
    }
    
    [Fact]
    public async Task AssembleAsync_WithCompression_CompressesLongContent()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        var longContent = string.Join(" ", Enumerable.Repeat("word", 1000));
        var mockDocs = new List<RecallResult>
        {
            new RecallResult
            {
                Document = new RAGDocument
                {
                    Id = "long",
                    Content = longContent,
                    Keywords = new List<string> { "test" }
                },
                Score = 0.8
            }
        };
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(mockDocs);
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test",
            EnableCompression = true,
            CompressionStrategy = CompressionStrategy.Selective,
            MaxTokenBudget = 500,
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.True(result.TokenBudgetUsage <= 1.0);
    }
    
    [Fact]
    public async Task AssembleAsync_MultiSource_CombinesAllSources()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(new List<RecallResult>
            {
                new RecallResult
                {
                    Document = new RAGDocument { Id = "mem1", Content = "Memory content" },
                    Score = 0.8
                }
            });
        
        _sessionManagerMock
            .Setup(x => x.GetSessionAsync(It.IsAny<string>()))
            .ReturnsAsync(new Session
            {
                Id = "s1",
                Messages = new List<Message>
                {
                    new Message { Id = "m1", Role = MessageRole.User, Content = "test session content" }
                }
            });
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test",
            SessionId = "session1",
            EnabledSources = new HashSet<DataSourceType>
            {
                DataSourceType.Memory,
                DataSourceType.Session,
                DataSourceType.WebSearch
            }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.True(result.SourceStats.Count >= 2);
        Assert.True(result.Snippets.Count >= 2);
    }
    
    [Fact]
    public async Task AssembleAsync_EmptyQuery_ReturnsEmptyResult()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "",
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        var result = await assembler.AssembleAsync(request);
        
        // Assert
        Assert.True(result.Success);
        Assert.Empty(result.Snippets);
    }
    
    [Fact]
    public async Task GetQuickSummary_ReturnsSummary()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(new List<RecallResult>
            {
                new RecallResult
                {
                    Document = new RAGDocument
                    {
                        Id = "doc1",
                        Content = "Test content with important keywords"
                    },
                    Score = 0.9
                }
            });
        
        _sessionManagerMock
            .Setup(x => x.GetSessionAsync(It.IsAny<string>()))
            .ReturnsAsync(new Session { Id = "s1", Messages = new List<Message>() });
        
        // Act
        var summary = await assembler.GetQuickSummaryAsync("test query", "session1");
        
        // Assert
        Assert.NotNull(summary);
        Assert.True(summary.TotalSnippets >= 0);
    }
    
    [Fact]
    public async Task Invalidate_RemovesFromCache()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(new List<RecallResult>
            {
                new RecallResult
                {
                    Document = new RAGDocument { Id = "cached_doc", Content = "Cached content" },
                    Score = 0.9
                }
            });
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test",
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        await assembler.AssembleAsync(request);
        await assembler.InvalidateAsync("cached_doc");
        var stats = assembler.GetStats();
        
        // Assert
        Assert.NotNull(stats);
    }
    
    [Fact]
    public async Task AssembleWithProgress_YieldsSnippets()
    {
        // Arrange
        var assembler = CreateAssembler();
        
        _ragRecallMock
            .Setup(x => x.RecallAsync(It.IsAny<RecallRequest>()))
            .ReturnsAsync(new List<RecallResult>
            {
                new RecallResult
                {
                    Document = new RAGDocument { Id = "doc1", Content = "Progress content" },
                    Score = 0.8
                }
            });
        
        var request = new ContextAssemblyRequest
        {
            UserMessage = "test",
            EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory }
        };
        
        // Act
        var snippets = new List<ContextSnippet>();
        await foreach (var snippet in assembler.AssembleWithProgressAsync(request))
        {
            snippets.Add(snippet);
        }
        
        // Assert
        Assert.NotEmpty(snippets);
    }
}
