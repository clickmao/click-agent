// R480: 独立文本召回模块 —— 产出物自带地址 (链接面)。
// 用户令: 「跨文件跨url相当于不需要主动分类, 但自己就包含了链接指向…唯一的问题就是需要内容中自带链接地址或文件地址」
// 因此本文件只做一件事: 把正文里**已经存在**的地址抽出来随文档落盘 ⇒ 召回不需要分类, 只需要沿地址走。
// 语言无关: 链接语法全部来自 RecallLinkOptions(可配置), 不做任何文件后缀判断。
using System.Buffers.Binary;
using System.Text;

namespace agent.recall;


public sealed class RecallLinkOptions
{
    public bool MarkdownTargets { get; init; } = true;
    public bool BareUrls { get; init; } = true;
    public bool RelativeAddresses { get; init; } = true;
    public int MaxLinksPerDoc { get; init; } = 64;
    public int MaxLinkChars { get; init; } = 512;
    public string[] Schemes { get; init; } = { "http://", "https://" };

    public static RecallLinkOptions Default { get; } = new();
}
