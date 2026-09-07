using agent.intent;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R116 (真缺陷 47): 创作类文本 ("写一首诗") 不得归为 code_generation。
/// </summary>
public class IntentCreativeTests
{
    [Theory]
    [InlineData("帮我写一首关于秋天的短诗")]
    [InlineData("写一篇关于冬天的散文")]
    [InlineData("写个故事给我听")]
    public void Creative_Text_Is_Not_CodeGeneration(string input)
    {
        var intent = IntentRecognizer.Recognize(input);
        Assert.NotEqual(IntentRecognizer.Intents.CodeGeneration, intent);
    }

    [Theory]
    [InlineData("帮我写一个快速排序算法")]
    [InlineData("写个HTTP服务器")]
    public void Code_Text_Still_CodeGeneration(string input)
    {
        var intent = IntentRecognizer.Recognize(input);
        Assert.Equal(IntentRecognizer.Intents.CodeGeneration, intent);
    }
}
