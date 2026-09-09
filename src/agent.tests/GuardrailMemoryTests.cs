using agent.critique;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.15.2 GuardrailMemory 单测: 三元组/域隔离(跨域不泛扰)/来源秩/habituation/损坏容忍。
/// </summary>
public class GuardrailMemoryTests : IDisposable
{
    private readonly string _path = Path.Combine(Path.GetTempPath(), $"gr-{Guid.NewGuid():N}.json");

    public void Dispose()
    {
        if (File.Exists(_path)) File.Delete(_path);
    }

    [Fact]
    public void Write_Recall_SameDomain_Hits()
    {
        var m = GuardrailMemory.Load(_path);
        m.Write("用户登录接口", "登录接口", "处理密码时", "不要明文存储密码", "内网工具可豁免", "曾明文输出了密码", "human_warning");
        var hits = m.Recall("用户登录接口", "实现登录接口的密码校验");
        Assert.Single(hits);
        Assert.Equal("不要明文存储密码", hits[0].Prohibition);
    }

    [Fact]
    public void Recall_CrossDomain_DoesNotTrigger()
    {
        var m = GuardrailMemory.Load(_path);
        m.Write("用户登录接口", "登录接口", "处理密码时", "不要明文存储密码", "", "", "human_warning");
        // 换领域 (菜谱) — 相似词面无 → 不触发; 即使文本含"登录接口"但域不匹配也不触发
        Assert.Empty(m.Recall("菜谱领域", "做红烧肉需要登录接口的灵感"));
    }

    [Fact]
    public void Recall_NoDomainEntry_DoesNotTrigger()
    {
        var m = GuardrailMemory.Load(_path);
        m.Write("", "登录接口", "", "禁令", "", "", "human_warning"); // 无域条目
        // R324b: 无域条目 = general (通用警告) → 全域触发 — 语义已从"永不触发"改为"全域触发"
        Assert.Single(m.Recall("用户登录接口", "登录接口相关文本"));
    }

    [Fact]
    public void Render_TripleForm_Preserved()
    {
        var m = GuardrailMemory.Load(_path);
        var e = m.Write("代码域", "new[] {", "循环体内", "不要堆分配数组", "单元素常量数组除外", "曾 foreach new[]", "human_warning");
        var text = GuardrailMemory.Render(new[] { e });
        Assert.Contains("在循环体内时", text);
        Assert.Contains("不要堆分配数组", text);
        Assert.Contains("(除非单元素常量数组除外)", text);
        Assert.Contains("[案例:", text);
    }

    [Fact]
    public void Write_SameDomainPattern_MergesConfirmations()
    {
        var m = GuardrailMemory.Load(_path);
        m.Write("代码域", "new[] {", "c1", "p1", "e1", "o1", "metric");
        m.Write("代码域", "new[] {", "c2", "p2", "e2", "o2", "human_warning");
        Assert.Single(m.Entries);
        Assert.Equal(2, m.Entries[0].Confirmations);
        Assert.Equal("human_warning", m.Entries[0].Source); // 强来源刷新
    }

    [Fact]
    public void Recall_OrderedByConfirmationsThenSource()
    {
        var m = GuardrailMemory.Load(_path);
        m.Write("代码域", "linq", "", "规则A", "", "", "metric");
        m.Write("代码域", "linq", "", "规则B", "", "", "review");
        m.Write("代码域", "linq", "", "规则C", "", "", "human_warning");
        var hits = m.Recall("代码域", "这段 linq 代码");
        Assert.True(hits.Count >= 1);
        Assert.Equal("规则C", hits[0].Prohibition); // human_warning 最高秩
    }

    [Fact]
    public void Load_CorruptFile_StartsEmpty()
    {
        File.WriteAllText(_path, "{broken");
        Assert.Empty(GuardrailMemory.Load(_path).Entries);
    }

    [Fact]
    public void Render_Empty_ReturnsEmpty()
    {
        Assert.Equal(string.Empty, GuardrailMemory.Render(Array.Empty<GuardrailMemory.GuardrailEntry>()));
    }
}
