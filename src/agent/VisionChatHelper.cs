using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;


public static partial class VisionChatHelper
{
    /// <summary>本地图 → base64 data URL (png/jpg/jpeg/webp; >4MB 拒绝)。</summary>
    public static string ToDataUrl(string localPath)
    {
        if (!File.Exists(localPath))
            throw new FileNotFoundException($"图像附件不存在: {localPath}");
        var bytes = File.ReadAllBytes(localPath);
        if (bytes.Length > 4 * 1024 * 1024)
            throw new InvalidOperationException($"图像超过 4MB 上限: {bytes.Length}B ({localPath})");
        var ext = Path.GetExtension(localPath).ToLowerInvariant() switch
        {
            ".png" => "image/png",
            ".jpg" or ".jpeg" => "image/jpeg",
            ".webp" => "image/webp",
            _ => "image/png",
        };
        return $"data:{ext};base64,{Convert.ToBase64String(bytes)}";
    }
}
