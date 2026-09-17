using agent.config;

namespace agent.modelqueue;


/// <summary>模型目录条目 (C.6.2) — 除 API-KEY 外全部参数; key 只存环境变量名。</summary>
/// <summary>capabilities: 字段解析 (v0.12.0 — 缺失时保守默认 text-only)</summary>
public static class ModelCapabilitiesParser
{
    public static ModelCapabilities Parse(Dictionary<string, object?> d)
    {
        var c = new ModelCapabilities();
        if (!d.TryGetValue("capabilities", out var raw) || raw is not Dictionary<string, object?> cd)
            return c;
        bool? Get(string k) => cd.TryGetValue(k, out var v) && v is bool b ? b : null;
        c.Text = Get("text") ?? true;
        c.ImageInput = Get("image_input") ?? false;
        c.VideoInput = Get("video_input") ?? false;
        c.AudioInput = Get("audio_input") ?? false;
        c.FilePdf = Get("file_pdf") ?? false;
        c.FileXlsx = Get("file_xlsx") ?? false;
        c.ImageOutput = Get("image_output") ?? false;
        return c;
    }
}
