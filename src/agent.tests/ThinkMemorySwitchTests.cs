using agent.exploration;
using Xunit;
namespace agent.tests;

/// <summary>
/// R449 — think-memory 开关 (四档) + 计数器非空心 + HitCount 语义修复 + 维度不一致可见化。
/// 铁律: 默认档 = 现网行为 (零产品变更); 未知取值必须 fail-open ⇒ On (开关不得成为主链故障点);
/// 计数器断言一律用**增量** (全局静态计数器与并行测试类共享, 绝对值会假红)。
/// </summary>
public class ThinkMemorySwitchTests
{
    // ── 档位解析 ──
    [Theory]
    [InlineData(null, ThinkMemorySwitch.Mode.On)]
    [InlineData("", ThinkMemorySwitch.Mode.On)]
    [InlineData("  ", ThinkMemorySwitch.Mode.On)]
    [InlineData("1", ThinkMemorySwitch.Mode.On)]
    [InlineData("on", ThinkMemorySwitch.Mode.On)]
    [InlineData("ON", ThinkMemorySwitch.Mode.On)]
    [InlineData("true", ThinkMemorySwitch.Mode.On)]
    [InlineData("garbage", ThinkMemorySwitch.Mode.On)]      // fail-open
    [InlineData("off", ThinkMemorySwitch.Mode.Off)]
    [InlineData(" off ", ThinkMemorySwitch.Mode.Off)]
    [InlineData("0", ThinkMemorySwitch.Mode.Off)]
    [InlineData("false", ThinkMemorySwitch.Mode.Off)]
    [InlineData("recall0", ThinkMemorySwitch.Mode.RecallOff)]
    [InlineData("no-recall", ThinkMemorySwitch.Mode.RecallOff)]
    [InlineData("write0", ThinkMemorySwitch.Mode.WriteOff)]
    [InlineData("no-write", ThinkMemorySwitch.Mode.WriteOff)]
    public void Parse_MapsRawValueToMode(string? raw, ThinkMemorySwitch.Mode expected)
        => Assert.Equal(expected, ThinkMemorySwitch.Parse(raw));

    [Fact]
    public void Parse_Name_RoundTrips()
    {
        foreach (var m in new[] { ThinkMemorySwitch.Mode.On, ThinkMemorySwitch.Mode.Off,
                                  ThinkMemorySwitch.Mode.RecallOff, ThinkMemorySwitch.Mode.WriteOff })
        {
            Assert.Equal(m, ThinkMemorySwitch.Parse(ThinkMemorySwitch.Name(m)));
        }
    }

    // ── 四档行为 ──
    [Fact]
    public void On_档_写入与召回均生效()
    {
        var before = ThinkMemoryStats.Snapshot();
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.On);
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f }, });
        var afterWrite = ThinkMemoryStats.Snapshot();
        Assert.Equal(1, tm.Count);
        Assert.True(afterWrite.Writes - before.Writes >= 1);
        Assert.Equal("on", tm.ModeName);
    }

    [Fact]
    public void Recall0_档_写入仍生效但召回被抑制且计数可见()
    {
        var before = ThinkMemoryStats.Snapshot();
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.RecallOff);
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f } });
        var hits = tm.Recall(new float[] { 1f, 0f });
        var after = ThinkMemoryStats.Snapshot();

        Assert.Equal(1, tm.Count);                                   // 写入未被抑制
        Assert.Empty(hits);                                          // 召回被抑制
        Assert.Equal(1, after.Recalls - before.Recalls);             // 非空心: 尝试过
        Assert.Equal(1, after.RecallsSuppressed - before.RecallsSuppressed);
    }

    [Fact]
    public void Write0_档_写入被抑制且召回路径仍尝试()
    {
        var before = ThinkMemoryStats.Snapshot();
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.WriteOff);
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f } });
        var hits = tm.Recall(new float[] { 1f, 0f });
        var after = ThinkMemoryStats.Snapshot();

        Assert.Equal(0, tm.Count);                                   // 写入被抑制
        Assert.Empty(hits);
        Assert.Equal(1, after.WritesSuppressed - before.WritesSuppressed);
        Assert.Equal(1, after.Recalls - before.Recalls);             // 召回仍在跑 (非空心)
        Assert.Equal(0, after.RecallsSuppressed - before.RecallsSuppressed);
    }

    [Fact]
    public void Off_档_写读召回全抑制_且不落盘()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tmsw-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "think-memory.json");
        var before = ThinkMemoryStats.Snapshot();

        var tm = ThinkMemory.Load(path, ThinkMemorySwitch.Mode.Off);   // 不读盘 (文件不存在 ⇒ 空库)
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f } });
        tm.Save(path);
        var hits = tm.Recall(new float[] { 1f, 0f });
        var after = ThinkMemoryStats.Snapshot();

        Assert.Equal(0, tm.Count);
        Assert.Empty(hits);
        Assert.False(File.Exists(path), "off 档不得落盘 (库文件必须不被触碰)");
        Assert.Equal(1, after.WritesSuppressed - before.WritesSuppressed);
        Assert.Equal(1, after.RecallsSuppressed - before.RecallsSuppressed);
        Directory.Delete(dir, true);
    }

    [Fact]
    public void Off_档_不读取既有库文件()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tmsw-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "think-memory.json");
        new ThinkMemory(mode: ThinkMemorySwitch.Mode.On).Save(path);      // 先落一个空库文件 (存在)
        Assert.True(File.Exists(path));
        var tm = ThinkMemory.Load(path, ThinkMemorySwitch.Mode.Off);
        Assert.Equal(0, tm.Count);
        Directory.Delete(dir, true);
    }

    // ── HitCount 语义修复 (R449: 原实现只在 refs 命中时计数 ⇒ refs 空时恒 0) ──
    [Fact]
    public void ApplyCitationBoost_依据不命中时也计被引用次数()
    {
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.On);
        var id = tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f } });   // refs 空
        Assert.False(tm.ApplyCitationBoost(id, "https://example.com/none"));
        var rec = tm.Recall(new float[] { 1f, 0f });
        // 记录仍在库: 直接取形状断言
        var shape = tm.Shape();
        Assert.Equal(1, shape.HitPositive);          // 被引用过 (修复前恒 0)
        Assert.Equal(0, shape.RefHitPositive);       // 但没有具体依据被采纳
        Assert.NotNull(rec);
    }

    [Fact]
    public void ApplyCitationBoost_依据命中时提升置信并计RefHit()
    {
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.On);
        var rec = new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f }, AvgConfidence = 0.5 };
        rec.Refs.Add("https://example.com/a");
        rec.RefConfidences.Add(0.5);
        var id = tm.Write(rec);
        Assert.True(tm.ApplyCitationBoost(id, "https://example.com/a"));
        var shape = tm.Shape();
        Assert.Equal(1, shape.HitPositive);
        Assert.Equal(1, shape.RefHitPositive);
    }

    // ── 形状快照 / 维度不一致可见化 ──
    [Fact]
    public void Shape_计出负样本无依据与维度分布()
    {
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.On);
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f }, Outcome = "positive" });
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f, 0f }, Outcome = "negative" });
        tm.Write(new ThinkRecord { QuestionEmbedding = Array.Empty<float>() });
        var s = tm.Shape();
        Assert.Equal(3, s.Count);
        Assert.Equal(1, s.Negative);
        Assert.Equal(3, s.Unbacked);
        Assert.Equal(1, s.ZeroDim);
        Assert.Contains("2:1", s.Dimensions);
        Assert.Contains("3:1", s.Dimensions);
        Assert.Equal("on", s.Mode);
    }

    [Fact]
    public void Recall_维度不一致被显式计数而非静默()
    {
        var before = ThinkMemoryStats.Snapshot();
        var tm = new ThinkMemory(mode: ThinkMemorySwitch.Mode.On);
        tm.Write(new ThinkRecord { QuestionEmbedding = new float[] { 1f, 0f, 0f } });
        var hits = tm.Recall(new float[] { 1f, 0f });               // 2 维查询 vs 3 维记录
        var after = ThinkMemoryStats.Snapshot();
        Assert.Empty(hits);
        Assert.Equal(1, after.DimMismatch - before.DimMismatch);
    }
}
