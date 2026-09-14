using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace agent.modelqueue;

/// <summary>
/// R430: **本地通道输入指纹** (只观测, 不参与生成/判定)。
///
/// 动机 (R429 遗留): 门判/判官钉死缓存后判定结论恒定, 但生成文本仍逐轮不同 (raw_len 4 种取值)
/// ⇒ 「同一 prompt 两次调用是否逐位相同」必须能机械分辨, 否则无法区分:
///   ① 输入不同 (prompt 文本 / 请求字段被改动)  —— 修在输入构造侧;
///   ② 引擎不确定 (llama.cpp 数值/调度漂移)     —— 修在引擎侧。
/// 只用静态哈希 (无随机盐、无时间戳、编码固定 UTF-8) ⇒ 同一输入必同值。
/// 放在 modelqueue 层: 该层被 llamacpp 与 agent 共同引用, 不引入反向依赖。
/// </summary>
public static class LocalInputFingerprint
{
    /// <summary>SHA-256 前 8 字节 → 16 个小写十六进制字符 (足够区分, 便于落盘逐轮对比)。</summary>
    public static string Sha16(string? text)
    {
        var bytes = Encoding.UTF8.GetBytes(text ?? string.Empty);
        return Convert.ToHexString(SHA256.HashData(bytes), 0, 8).ToLowerInvariant();
    }

    /// <summary>请求关键字段摘要 (指纹不同时 → 直接读这里定位是哪个字段变了)。</summary>
    public static string Describe(
        int maxTokens, float temperature, string[] samplers, bool cachePrompt, int seed,
        int topK, float topP, float minP, float repeatPenalty) =>
        string.Format(CultureInfo.InvariantCulture,
            "np={0};t={1:0.###};sp={2};cp={3};seed={4};tk={5};tp={6:0.###};mp={7:0.###};rp={8:0.###}",
            maxTokens, temperature, string.Join('+', samplers), cachePrompt ? "1" : "0",
            seed, topK, topP, minP, repeatPenalty);
}
