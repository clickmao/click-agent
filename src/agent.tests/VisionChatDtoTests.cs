using System.Text.Json;
using agent;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.12.0 R201 — 多模态 content 双形态 DTO (计划 R2 §1) 对抗测试:
/// 纯文本→string / 带图→parts[] / 反序列化往返 / AOT 安全手写 converter。
/// </summary>
public class VisionChatDtoTests
{
    [Fact]
    public void TextOnly_Serializes_As_String()
    {
        var msg = OpenAIMultimodalMessage.Text("user", "你好");
        var json = JsonSerializer.Serialize(msg);
        // STJ 默认转义非 ASCII — 用往返反序列化验证 (实质等价):
        var back = JsonSerializer.Deserialize<OpenAIMultimodalMessage>(json);
        Assert.NotNull(back);
        Assert.False(back!.HasParts);
        Assert.Equal("你好", back.Content);
        Assert.DoesNotContain("image_url", json);
    }

    [Fact]
    public void WithImage_Serializes_As_Parts_Array()
    {
        var msg = OpenAIMultimodalMessage.WithImage("user", "描述这张图", "https://x/demo.png");
        var json = JsonSerializer.Serialize(msg);
        Assert.Contains("\"type\":\"text\"", json);
        Assert.Contains("\"type\":\"image_url\"", json);
        Assert.Contains("https://x/demo.png", json);
    }

    [Fact]
    public void Base64_DataUrl_Passes_Through()
    {
        var msg = OpenAIMultimodalMessage.WithImage("user", "看图", "data:image/png;base64,aGVsbG8=");
        var json = JsonSerializer.Serialize(msg);
        Assert.Contains("data:image/png;base64,aGVsbG8=", json);
    }

    [Fact]
    public void Parts_Array_Deserializes_Back()
    {
        var json = "{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"提取表格\"},{\"type\":\"image_url\",\"image_url\":{\"url\":\"https://x/a.png\"}}]}";
        var msg = JsonSerializer.Deserialize<OpenAIMultimodalMessage>(json);
        Assert.NotNull(msg);
        Assert.True(msg!.HasParts);
        Assert.Equal(2, msg.ContentParts!.Count);
        Assert.Equal("提取表格", msg.ContentParts[0].Text);
        Assert.Equal("https://x/a.png", msg.ContentParts[1].ImageUrl!.Url);
    }

    [Fact]
    public void String_Content_Deserializes_Back()
    {
        var msg = JsonSerializer.Deserialize<OpenAIMultimodalMessage>("{\"role\":\"user\",\"content\":\"纯文本\"}");
        Assert.NotNull(msg);
        Assert.False(msg!.HasParts);
        Assert.Equal("纯文本", msg.Content);
    }
}
