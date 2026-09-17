// R480: 独立文本召回模块 —— 行为测试 (判据: 与独立暴力实现一致 / 极小常驻 / 增量正确 / 损坏 fail-closed)。
using System.Text;
using agent.recall;
using Xunit;

namespace agent.recall.tests;


public sealed class RecallTokenizerTests
{
    [Fact]
    public void EmitsIdeographicBigramsAndAsciiWords()
    {
        var sink = new CollectingSink();
        RecallTokenizer.Tokenize("用户权限 API access".AsSpan(), RecallTokenizerOptions.Default, sink);
        Assert.Contains("用户", sink.Tokens);
        Assert.Contains("户权", sink.Tokens);
        Assert.Contains("权限", sink.Tokens);
        Assert.Contains("api", sink.Tokens);
        Assert.Contains("access", sink.Tokens);
    }

    [Fact]
    public void TokenizesIdenticallyRegardlessOfFileLikeSuffix()
    {
        var a = new CollectingSink();
        var b = new CollectingSink();
        RecallTokenizer.Tokenize("alpha.cs".AsSpan(), RecallTokenizerOptions.Default, a);
        RecallTokenizer.Tokenize("alpha-md".AsSpan(), RecallTokenizerOptions.Default, b);
        Assert.Equal(new[] { "alpha", "cs" }, a.Tokens);
        Assert.Equal(new[] { "alpha", "md" }, b.Tokens);
    }

    [Fact]
    public void HashIsStable()
    {
        var bytes = Encoding.UTF8.GetBytes("权限");
        Assert.Equal(RecallTokenizer.Hash(bytes), RecallTokenizer.Hash(Encoding.UTF8.GetBytes("权限")));
        Assert.NotEqual(RecallTokenizer.Hash(bytes), RecallTokenizer.Hash(Encoding.UTF8.GetBytes("限权")));
    }
}
