// R480: 独立文本召回模块 —— 行为测试 (判据: 与独立暴力实现一致 / 极小常驻 / 增量正确 / 损坏 fail-closed)。
using System.Text;
using agent.recall;
using Xunit;

namespace agent.recall.tests;


internal sealed class CollectingSink : ITokenSink
{
    public List<string> Tokens { get; } = new();

    public void AddToken(ReadOnlySpan<byte> token) => Tokens.Add(Encoding.UTF8.GetString(token));
}
