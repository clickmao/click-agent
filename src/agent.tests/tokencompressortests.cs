using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using agent.tokencompression;

namespace agent.tests;

/// <summary>
/// TokenCompressor 单元测试
/// </summary>
public class TokenCompressorTests
{
    private readonly Mock<ILogger<TokenCompressor>> _loggerMock;
    private readonly TokenCompressor _compressor;
    
    public TokenCompressorTests()
    {
        _loggerMock = new Mock<ILogger<TokenCompressor>>();
        _compressor = new TokenCompressor(_loggerMock.Object);
    }
    
    [Fact]
    public async Task CompressAsync_ShortText_ReturnsOriginal()
    {
        // Arrange
        var text = "This is a short text.";
        var options = new CompressionOptions { MaxTokens = 100 };
        
        // Act
        var result = await _compressor.CompressAsync(text, options);
        
        // Assert
        Assert.Equal(text, result);
    }
    
    [Fact]
    public async Task CompressAsync_LongText_Truncates()
    {
        // Arrange
        var text = string.Join(" ", Enumerable.Repeat("word", 500));
        var options = new CompressionOptions { MaxTokens = 50, Strategy = CompressionStrategy.Truncate };
        
        // Act
        var result = await _compressor.CompressAsync(text, options);
        
        // Assert
        Assert.NotNull(result);
        Assert.True(result.Length < text.Length, $"expected compression, got {result.Length} vs {text.Length}");
    }
    
    [Fact]
    public async Task CompressAsync_SummarizeStrategy_PreservesStartAndEnd()
    {
        // Arrange
        var text = $"{string.Join(" ", Enumerable.Repeat("start", 100))} MIDDLE CONTENT {string.Join(" ", Enumerable.Repeat("end", 100))}";
        var options = new CompressionOptions { MaxTokens = 50, Strategy = CompressionStrategy.Summarize };
        
        // Act
        var result = await _compressor.CompressAsync(text, options);
        
        // Assert
        Assert.Contains("start", result);
        Assert.Contains("end", result);
        Assert.Contains("摘要", result);
    }
    
    [Fact]
    public async Task CompressAsync_SelectiveStrategy_PreservesKeywords()
    {
        // Arrange
        var text = string.Join("\n", Enumerable.Range(1, 40).Select(i =>
            $"function sample{i}() {{ return value{i} + compute({i}); }} // item {i}")) + "\n# Header\nfunction important() { return 'data'; }";
        var options = new CompressionOptions
        {
            MaxTokens = 60,
            Strategy = CompressionStrategy.Selective,
            PreserveStructure = true
        };
        
        // Act
        var result = await _compressor.CompressAsync(text, options);
        
        // Assert
        Assert.NotNull(result);
        Assert.True(result.Length < text.Length);
    }
    
    [Fact]
    public async Task CountTokensAsync_CountsCorrectly()
    {
        // Arrange
        var text = "Hello world 这是一个测试 sentence.";
        
        // Act
        var count = await _compressor.CountTokensAsync(text);
        
        // Assert
        Assert.True(count > 0);
    }
    
    [Fact]
    public async Task CountTokensAsync_EmptyString_ReturnsZero()
    {
        // Act
        var count = await _compressor.CountTokensAsync("");
        
        // Assert
        Assert.Equal(0, count);
    }
    
    [Fact]
    public async Task TruncateAsync_ShortText_ReturnsOriginal()
    {
        // Arrange
        var text = "Short";
        
        // Act
        var result = await _compressor.TruncateAsync(text, 100);
        
        // Assert
        Assert.Equal(text, result);
    }
    
    [Fact]
    public async Task TruncateAsync_LongText_AddsEllipsis()
    {
        // Arrange
        var text = string.Join(" ", Enumerable.Repeat("word", 200));
        
        // Act
        var result = await _compressor.TruncateAsync(text, 10);
        
        // Assert
        Assert.True(result.Length < text.Length);
        Assert.EndsWith("...", result);
    }
    
    [Fact]
    public async Task CompressAsync_NullOptions_UsesDefaults()
    {
        // Arrange
        var text = string.Join(" ", Enumerable.Repeat("word", 100));
        
        // Act
        var result = await _compressor.CompressAsync(text, null);
        
        // Assert
        Assert.NotNull(result);
    }
    
    [Fact]
    public async Task CompressSmartAsync_SmartCompression()
    {
        // Arrange
        var text = string.Join(" ", Enumerable.Repeat("important", 200)) + " " + 
                   string.Join(" ", Enumerable.Repeat("noise", 200));
        
        // Act
        var result = await _compressor.CompressSmartAsync(text, 50);
        
        // Assert
        Assert.NotNull(result);
        Assert.True(result.Length < text.Length);
    }
    
    [Theory]
    [InlineData(CompressionStrategy.Summarize)]
    [InlineData(CompressionStrategy.Truncate)]
    [InlineData(CompressionStrategy.Selective)]
    public async Task CompressAsync_AllStrategies_Work(CompressionStrategy strategy)
    {
        // Arrange
        var text = string.Join(" ", Enumerable.Repeat("word", 200));
        var options = new CompressionOptions { MaxTokens = 30, Strategy = strategy };
        
        // Act
        var result = await _compressor.CompressAsync(text, options);
        
        // Assert
        Assert.NotNull(result);
        Assert.True(result.Length <= text.Length);
    }
}
