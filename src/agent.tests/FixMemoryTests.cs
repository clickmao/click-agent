using agent.critique;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.14.0 T2b FixMemory 单测: 写入合并/来源秩/检索/持久化往返。
/// </summary>
public class FixMemoryTests : IDisposable
{
    private readonly string _path = Path.Combine(Path.GetTempPath(), $"fixmem-{Guid.NewGuid():N}.json");

    public void Dispose()
    {
        if (File.Exists(_path)) File.Delete(_path);
    }

    [Fact]
    public void Write_New_PersistsAndReloads()
    {
        var m = new FixMemory(_path);
        m.Write("new[] {", "循环内堆分配", "ref 局部变量", "human_review");
        var m2 = FixMemory.Load(_path);
        Assert.Single(m2.Entries);
        Assert.Equal("human_review", m2.Entries[0].Source);
    }

    [Fact]
    public void Write_SamePattern_MergesConfirmations()
    {
        var m = new FixMemory(_path);
        m.Write("new[] {", "机制A", "修法A", "llm_self_confirmed");
        m.Write("New[] {", "机制A强", "修法A强", "human_review");
        Assert.Single(m.Entries);
        Assert.Equal(2, m.Entries[0].Confirmations);
        Assert.Equal("human_review", m.Entries[0].Source); // 强来源刷新
        Assert.Equal("修法A强", m.Entries[0].Fix);
    }

    [Fact]
    public void Write_WeakerSource_DoesNotDowngrade()
    {
        var m = new FixMemory(_path);
        m.Write("async void", "机制", "修法", "human_review");
        m.Write("async void", "机制弱", "修法弱", "llm_self_confirmed");
        Assert.Single(m.Entries);
        Assert.Equal("human_review", m.Entries[0].Source);
        Assert.Equal("修法", m.Entries[0].Fix);
    }

    [Fact]
    public void Recall_PatternHit_OrderedByConfirmations()
    {
        var m = new FixMemory(_path);
        m.Write("new[] {", "m1", "f1", "llm_self_confirmed");
        m.Write("async void", "m2", "f2", "human_review");
        m.Write("async void", "m2", "f2", "human_review"); // confirmations=2
        var hits = m.Recall("这段代码用了 async void 和 new[] {");
        Assert.Equal(2, hits.Count);
        Assert.Equal("async void", hits[0].Pattern); // confirmations 高者先
    }

    [Fact]
    public void Recall_NoHit_Empty()
    {
        var m = new FixMemory(_path);
        m.Write("new[] {", "m", "f", "human_review");
        Assert.Empty(m.Recall("完全无关的文本内容"));
    }

    [Fact]
    public void Load_CorruptFile_StartsEmpty()
    {
        File.WriteAllText(_path, "{broken json");
        var m = FixMemory.Load(_path);
        Assert.Empty(m.Entries);
    }
}
