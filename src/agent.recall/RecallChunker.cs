// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.recall;


public static class RecallChunker
{
    /// <summary>按段落边界切块, 单块不超过 chunkChars (超长段落硬切), 保留原文, 无重叠。</summary>
    public static List<string> Split(string text, int chunkChars)
    {
        if (chunkChars < 64)
        {
            chunkChars = 64;
        }
        var parts = new List<string>();
        var cur = new StringBuilder();
        int i = 0;
        while (i < text.Length)
        {
            int nl = text.IndexOf('\n', i);
            if (nl < 0)
            {
                nl = text.Length;
            }
            int len = nl - i + (nl < text.Length ? 1 : 0);
            if (cur.Length > 0 && cur.Length + len > chunkChars)
            {
                parts.Add(cur.ToString());
                cur.Clear();
            }
            if (len > chunkChars)
            {
                for (int p = i; p < nl; p += chunkChars)
                {
                    int take = Math.Min(chunkChars, nl - p);
                    if (cur.Length > 0)
                    {
                        parts.Add(cur.ToString());
                        cur.Clear();
                    }
                    parts.Add(text.Substring(p, take));
                }
            }
            else
            {
                cur.Append(text, i, len);
            }
            i = nl + (nl < text.Length ? 1 : 0);
        }
        if (cur.Length > 0)
        {
            parts.Add(cur.ToString());
        }
        return parts;
    }
}
