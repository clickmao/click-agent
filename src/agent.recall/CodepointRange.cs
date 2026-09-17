// R480: 独立文本召回模块 —— 分词面。
// 【语言无关令】这里没有任何文件后缀/语言标签分支: 字符类 → 切分规则全部来自
// RecallTokenizerOptions(可配置数据), 默认值只是一组「常见表意文字区间」。
using System.Text;

namespace agent.recall;


/// <summary>半开区间 [Start, End) 的码点范围。</summary>
public readonly record struct CodepointRange(int Start, int End)
{
    public bool Contains(int cp) => cp >= Start && cp < End;
}
