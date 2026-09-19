using System.Linq;
using Panlingo.LanguageIdentification.FastText;

namespace agent.nlp;

/// <summary>
/// 语言识别 — fastText lid.176 官方模型 (176 种语言包), 语言判定的**唯一依据**。
/// 取代一切「CJK 码点区间 / 中文白名单字符集」硬编码: 新语言、新梗、混排文本都由模型输出决定。
/// AOT: 原生 fastText 经 P/Invoke; 已在 env -i 下 NativeAOT 产物实测跑通 (7.05 MB 单文件 + libfasttext.so)。
/// </summary>
public static class LanguageIdentifier
{
    private static readonly object Sync = new();
    private static FastTextDetector? _detector;

    private static FastTextDetector? Detector()
    {
        if (_detector is not null)
        {
            return _detector;
        }

        lock (Sync)
        {
            if (_detector is null)
            {
                var d = new FastTextDetector();
                d.LoadDefaultModel();
                _detector = d;
            }

            return _detector;
        }
    }

    /// <summary>返回 ISO 639-1 语言码 (zh/ru/en/ja/ko/ar/hi/de/th ...), 无法判定返回 "und"。</summary>
    public static string Detect(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return "und";
        }

        var detector = Detector();
        if (detector is null)
        {
            return "und";
        }

        try
        {
            lock (Sync)
            {
                var labels = detector.Predict(text, 1, 0f).ToList();
                if (labels.Count == 0)
                {
                    return "und";
                }

                const string Prefix = "__label__";
                var label = labels[0].Label ?? string.Empty;
                return label.StartsWith(Prefix, StringComparison.Ordinal) ? label[Prefix.Length..] : label;
            }
        }
        catch (Exception)
        {
            return "und";
        }
    }

    /// <summary>两种文本是否同一语言 — 跨轮指代/修正判定的首个前提 (原先靠 CJK 区间猜)。</summary>
    public static bool SameLanguage(string a, string b)
    {
        var la = Detect(a);
        return la != "und" && la == Detect(b);
    }

    /// <summary>该文本的主导语言是否属于 CJK 语族 (由模型输出推导, 非码点表)。</summary>
    public static bool IsCjkDominant(string text)
    {
        var lang = Detect(text);
        return lang is "zh" or "ja" or "ko";
    }
}
