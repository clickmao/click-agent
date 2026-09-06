using Xunit;

public class PivotMarkerTests
{
    [Theory]
    [InlineData("不要之前的目标了，给我写一首诗")]
    [InlineData("算了，改成帮我设计REST API")]
    [InlineData("放弃这个方案，重新开始")]
    [InlineData("不要了，先做别的")]
    public void PivotMarkers_AreCovered(string text)
    {
        string[] markers = { "不要之前", "不用之前", "放弃", "重新开始", "取消之前", "先不做", "不管之前",
            "算了", "改成", "改为", "换成", "不要了", "还是做", "换一个" };
        Assert.Contains(markers, m => text.Contains(m, System.StringComparison.Ordinal));
    }
}
