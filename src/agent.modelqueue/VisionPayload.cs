namespace agent.modelqueue;

/// <summary>
/// v0.12.0 A3 (真缺陷 63/64) 视觉载荷工具:
/// 63 — -img 本地路径 → base64 data URL (云端无法读本地相对路径, 真机 HTTP 400 code 1210
///       "图片输入格式/解析错误" 实证)。http(s)/data: 已合法原样放行。
/// 64 — 智谱 coding 端点不收图像 (真机 1210 实证; glm-5.3-flash 视觉走标准 v4 chat 端点,
///       data URL 真机已验 1445 tok 描述准确) → 带图请求改写端点。
/// AOT 安全: 仅 File/Convert/字符串操作, 无反射。
/// </summary>
public static class VisionPayload
{
    /// <summary>图像附件 → OpenAI 兼容 image_url.url。magic bytes 嗅探优先于扩展名
    /// (testimg-apple.png 实际为 JPEG 内容 — 扩展名会误导 MIME)。</summary>
    public static string ToDataUrl(string src)
    {
        if (src.StartsWith("data:", StringComparison.Ordinal) ||
            src.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
            src.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            return src; // 已可传输形态 (data URL / 公网 URL) — 放行

        var path = Path.IsPathRooted(src)
            ? src
            : Path.Combine(Directory.GetCurrentDirectory(), src);
        var bytes = File.ReadAllBytes(path);
        return $"data:{DetectMime(bytes) ?? "application/octet-stream"};base64,{Convert.ToBase64String(bytes)}";
    }

    /// <summary>magic bytes → MIME (JPEG FFD8 / PNG 8950 / GIF / WEBP)。null = 未知。</summary>
    public static string? DetectMime(byte[] b)
    {
        if (b.Length >= 3 && b[0] == 0xFF && b[1] == 0xD8) return "image/jpeg";
        if (b.Length >= 4 && b[0] == 0x89 && b[1] == 0x50 && b[2] == 0x4E && b[3] == 0x47) return "image/png";
        if (b.Length >= 3 && b[0] == 0x47 && b[1] == 0x49 && b[2] == 0x46) return "image/gif";
        if (b.Length >= 12 && b[8] == 0x57 && b[9] == 0x45 && b[10] == 0x42 && b[11] == 0x50) return "image/webp";
        return null;
    }

    /// <summary>带图请求端点改写: "/api/coding/" → "/api/" (coding 端点不收图, 真机实证)。</summary>
    public static string ToChatEndpoint(string endpoint)
        => endpoint.Contains("/api/coding/", StringComparison.Ordinal)
            ? endpoint.Replace("/api/coding/", "/api/", StringComparison.Ordinal)
            : endpoint;
}
