// R480: 独立文本召回模块 —— 段写入 + 索引构建/追加。
// 主键命名空间: 文本 token 首字节 ≥ 0x21 或 ≥ 0xC2(UTF-8 多字节), 因此 0x01/0x02 前缀
// 只可能来自本模块自己写入的「文档键」, 不会与正文 token 冲突 (单一定义处, 读侧同一函数)。
using System.Text;

namespace agent.recall;


public static class RecallKeys
{
    public const byte IdPrefix = 0x01;
    public const byte PathPrefix = 0x02;

    public static byte[] IdKey(string id) => Prefix(IdPrefix, id);
    public static byte[] PathKey(string path) => Prefix(PathPrefix, path);

    private static byte[] Prefix(byte prefix, string value)
    {
        var body = Encoding.UTF8.GetBytes(value);
        var buf = new byte[body.Length + 1];
        buf[0] = prefix;
        body.CopyTo(buf, 1);
        return buf;
    }
}
