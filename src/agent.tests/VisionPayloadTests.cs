using agent.modelqueue;
using agent.config;
using Xunit;

namespace agent.tests;


/// <summary>v0.12.0 A3 (真缺陷 63/64) VisionPayload 测试: base64 data URL + coding 端点改写。</summary>
public class VisionPayloadTests
{
    [Fact]
    public void DataUrl_LocalJpegPath_ConvertsWithSniffedMime()
    {
        var tmp = Path.GetTempFileName();
        // JPEG magic bytes (扩展名 .tmp 故意误导 — 嗅探优先于扩展名)
        File.WriteAllBytes(tmp, new byte[] { 0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46 });
        try
        {
            var url = VisionPayload.ToDataUrl(tmp);
            Assert.StartsWith("data:image/jpeg;base64,", url);
            // 解码回验内容一致
            var b64 = url[(url.IndexOf(',') + 1)..];
            Assert.Equal(new byte[] { 0xFF, 0xD8, 0xFF, 0xE0 }, Convert.FromBase64String(b64)[..4]);
        }
        finally { File.Delete(tmp); }
    }

    [Fact]
    public void DataUrl_HttpUrl_Passthrough()
    {
        Assert.Equal("https://example.com/a.png", VisionPayload.ToDataUrl("https://example.com/a.png"));
        Assert.Equal("data:image/png;base64,AAAA", VisionPayload.ToDataUrl("data:image/png;base64,AAAA"));
    }

    [Fact]
    public void ChatEndpoint_CodingPath_RewrittenToV4()
    {
        Assert.Equal(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            VisionPayload.ToChatEndpoint("https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"));
        // 非 coding 端点原样放行
        Assert.Equal("https://api.deepseek.com/v1/chat/completions",
            VisionPayload.ToChatEndpoint("https://api.deepseek.com/v1/chat/completions"));
    }
}
