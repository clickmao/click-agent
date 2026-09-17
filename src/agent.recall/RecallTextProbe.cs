// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.recall;


public static class RecallTextProbe
{
    /// <summary>通用二进制探测: NUL 字节占比超阈值即视为非文本 (与后缀无关)。</summary>
    public static bool LooksBinary(ReadOnlySpan<byte> bytes, double nulRatio)
    {
        if (bytes.Length == 0)
        {
            return false;
        }
        int nul = 0;
        for (int i = 0; i < bytes.Length; i++)
        {
            if (bytes[i] == 0)
            {
                nul++;
            }
        }
        return nul > 0 && (double)nul / bytes.Length > nulRatio;
    }
}
